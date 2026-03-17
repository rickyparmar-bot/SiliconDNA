"""SiliconDNA Core Module - Event Loop Management with Graceful Shutdown"""

import asyncio
import signal
import logging
from typing import Optional, Callable, List, Any
from datetime import datetime


logger = logging.getLogger("silicon_dna.event_loop")


class GracefulShutdownError(Exception):
    """Exception raised when graceful shutdown encounters critical errors."""

    pass


class SiliconDNAEventLoop:
    """
    Main event loop manager for SiliconDNA.
    Handles graceful startup, continuous operation, and rigorous graceful shutdown.
    Ensures Redis connections close, MongoDB writes finalize, and tasks terminate cleanly.
    """

    def __init__(self, shutdown_timeout: int = 30):
        self.is_running: bool = False
        self.start_time: Optional[datetime] = None
        self.shutdown_callbacks: List[Callable] = []
        self.tasks: List[asyncio.Task] = []
        self.shutdown_timeout = shutdown_timeout
        self._shutdown_reason: Optional[str] = None

    async def start(self):
        """Start the event loop and all background tasks."""
        logger.info("Starting SiliconDNA event loop...")
        self.is_running = True
        self.start_time = datetime.utcnow()
        logger.info(f"SiliconDNA started at {self.start_time}")

    async def stop(self, reason: str = "Shutdown"):
        """
        Gracefully stop the event loop with rigorous database cleanup.

        Steps:
        1. Set is_running to False
        2. Execute registered shutdown callbacks (database flush/close)
        3. Cancel all background tasks with timeout
        4. Log final uptime
        """
        logger.info(f"Stopping SiliconDNA: {reason}")
        self._shutdown_reason = reason
        self.is_running = False

        await self._execute_shutdown_callbacks()

        await self._cancel_pending_tasks()

        if self.start_time:
            uptime = datetime.utcnow() - self.start_time
            logger.info(f"Total uptime: {uptime}")

        logger.info("SiliconDNA stopped successfully")

    async def _execute_shutdown_callbacks(self):
        """Execute all registered shutdown callbacks in order."""
        logger.debug(f"Executing {len(self.shutdown_callbacks)} shutdown callbacks...")

        for i, callback in enumerate(self.shutdown_callbacks):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
                logger.debug(f"Shutdown callback {i + 1} completed")
            except Exception as e:
                logger.error(f"Shutdown callback {i + 1} error: {e}")

        logger.debug("All shutdown callbacks executed")

    async def _cancel_pending_tasks(self):
        """Cancel all pending tasks with timeout."""
        logger.debug(f"Cancelling {len(self.tasks)} pending tasks...")

        for i, task in enumerate(self.tasks):
            if task.done():
                continue

            task.cancel()

            try:
                await asyncio.wait_for(task, timeout=self.shutdown_timeout)
                logger.debug(f"Task {i + 1} cancelled cleanly")
            except asyncio.CancelledError:
                logger.debug(f"Task {i + 1} cancelled")
            except asyncio.TimeoutError:
                logger.warning(f"Task {i + 1} did not cancel within timeout")
            except Exception as e:
                logger.error(f"Task {i + 1} cancellation error: {e}")

        logger.debug("All tasks processed")

    def register_shutdown_callback(self, callback: Callable):
        """
        Register a callback to be called during shutdown.
        Use for: database.flush_writes(), redis.disconnect(), etc.

        Args:
            callback: Sync or async callable with no arguments
        """
        self.shutdown_callbacks.append(callback)
        logger.debug(f"Registered shutdown callback: {callback.__name__}")

    def add_task(self, task: asyncio.Task):
        """Add a task to be managed by the event loop."""
        self.tasks.append(task)

    async def run_forever(self):
        """Main run loop - override with custom logic."""
        await self.start()
        try:
            while self.is_running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await self.stop("Cancelled")

    async def wait_for_signal(self, signals: List[int] = None):
        """
        Wait for termination signals and initiate graceful shutdown.

        Args:
            signals: List of signal numbers (default: SIGINT, SIGTERM)
        """
        if signals is None:
            signals = [signal.SIGINT, signal.SIGTERM]

        loop = asyncio.get_event_loop()
        signal_handlers = []

        for sig in signals:
            handler = loop.create_future()
            signal_handlers.append((sig, handler))

            def make_handler(fut, sig_num):
                def handler():
                    if not fut.done():
                        fut.set_result(sig_num)

                return handler

            loop.add_signal_handler(sig, make_handler(handler, sig))

        try:
            done, _ = await asyncio.wait(
                [h for _, h in signal_handlers],
                return_when=asyncio.FIRST_COMPLETED,
            )
            sig_num = next(iter(done)).result()
            await self.stop(f"Signal {sig_num} received")
        except Exception as e:
            logger.error(f"Signal handling error: {e}")
            await self.stop("Error")


class GracefulShutdownManager:
    """
    Context manager for graceful shutdown with database cleanup.
    Automatically registers database shutdown callbacks when instantiated.
    """

    def __init__(
        self,
        event_loop: SiliconDNAEventLoop,
        mongodb_manager=None,
        redis_manager=None,
        rethinkdb_manager=None,
    ):
        self.event_loop = event_loop
        self.mongodb = mongodb_manager
        self.redis = redis_manager
        self.rethinkdb = rethinkdb_manager
        self._callbacks_registered = False

    async def __aenter__(self):
        """Register database shutdown callbacks."""
        if self._callbacks_registered:
            return self

        if self.mongodb:

            async def mongodb_shutdown():
                logger.info("Flushing MongoDB writes...")
                if hasattr(self.mongodb, "flush_writes"):
                    await self.mongodb.flush_writes()
                await self.mongodb.disconnect()

            self.event_loop.register_shutdown_callback(mongodb_shutdown)

        if self.redis:

            async def redis_shutdown():
                logger.info("Closing Redis connections...")
                await self.redis.disconnect()

            self.event_loop.register_shutdown_callback(redis_shutdown)

        if self.rethinkdb:

            async def rethinkdb_shutdown():
                logger.info("Closing RethinkDB connections...")
                await self.rethinkdb.disconnect()

            self.event_loop.register_shutdown_callback(rethinkdb_shutdown)

        self._callbacks_registered = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Initiate graceful shutdown on context exit."""
        if exc_type is not None:
            await self.event_loop.stop(f"Exception: {exc_type.__name__}")
        return False


class ShutdownSequence:
    """
    Utility class for manual shutdown sequence control.
    Provides step-by-step shutdown with error handling.
    """

    def __init__(self):
        self.steps: List[Callable] = []

    def add_step(self, name: str, callback: Callable):
        """Add a named shutdown step."""
        self.steps.append((name, callback))

    async def execute(self, timeout_per_step: int = 10):
        """Execute all shutdown steps in sequence."""
        logger.info(f"Executing shutdown sequence with {len(self.steps)} steps...")

        for name, callback in self.steps:
            logger.debug(f"Executing shutdown step: {name}")
            try:
                if asyncio.iscoroutinefunction(callback):
                    await asyncio.wait_for(callback(), timeout=timeout_per_step)
                else:
                    await asyncio.wait_for(
                        asyncio.to_thread(callback), timeout=timeout_per_step
                    )
                logger.debug(f"Shutdown step completed: {name}")
            except asyncio.TimeoutError:
                logger.error(f"Shutdown step timeout: {name}")
            except Exception as e:
                logger.error(f"Shutdown step error ({name}): {e}")

        logger.info("Shutdown sequence completed")
