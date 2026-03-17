"""SiliconDNA Utils - Advanced Hot Reloading Mechanism"""

import asyncio
import importlib
import logging
import os
import sys
import hashlib
import time
from pathlib import Path
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass, field
from datetime import datetime


logger = logging.getLogger("silicon_dna.hot_reload")


@dataclass
class ModuleInfo:
    name: str
    path: Path
    last_hash: str
    last_modified: float
    loaded_at: datetime = field(default_factory=datetime.utcnow)
    reload_count: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class ReloadEvent:
    module_name: str
    old_hash: str
    new_hash: str
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None


class HotReloadManager:
    """
    Advanced hot reloading mechanism for real-time code injection.
    Allows developers to modify Python code without restarting the event loop.
    """

    def __init__(
        self,
        watch_dirs: List[str],
        watch_modules: List[str],
        on_reload: Optional[Callable] = None,
        debounce_seconds: float = 0.5,
    ):
        self.watch_dirs = [Path(d) for d in watch_dirs]
        self.watch_modules = watch_modules
        self.on_reload = on_reload
        self.debounce_seconds = debounce_seconds

        self._modules: Dict[str, ModuleInfo] = {}
        self._running = False
        self._watch_task: Optional[asyncio.Task] = None
        self._last_check: Dict[str, float] = {}
        self._reload_callbacks: List[Callable] = []
        self._reload_history: List[ReloadEvent] = []

    def add_module(self, module_name: str, file_path: str):
        """Add a module to watch for changes."""
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"Module file not found: {path}")
            return

        file_hash = self._compute_hash(path)

        self._modules[module_name] = ModuleInfo(
            name=module_name,
            path=path,
            last_hash=file_hash,
            last_modified=path.stat().st_mtime,
        )

        logger.info(f"Watching module: {module_name} at {path}")

    def register_callback(self, callback: Callable):
        """Register a callback to be called on module reload."""
        self._reload_callbacks.append(callback)

    def _compute_hash(self, path: Path) -> str:
        """Compute MD5 hash of file contents."""
        try:
            with open(path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute hash for {path}: {e}")
            return ""

    async def start(self):
        """Start watching for file changes."""
        self._running = True
        self._watch_task = asyncio.create_task(self._watch_loop())
        logger.info("Hot reload manager started")

    async def stop(self):
        """Stop watching for file changes."""
        self._running = False
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
        logger.info("Hot reload manager stopped")

    async def _watch_loop(self):
        """Main watch loop that monitors file changes."""
        while self._running:
            try:
                await asyncio.sleep(1)

                for module_name, module_info in self._modules.items():
                    current_mtime = module_info.path.stat().st_mtime

                    if current_mtime != module_info.last_modified:
                        now = time.time()
                        last_check = self._last_check.get(module_name, 0)

                        if now - last_check < self.debounce_seconds:
                            continue

                        self._last_check[module_name] = now
                        await self._reload_module(module_name)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Watch loop error: {e}")

    async def _reload_module(self, module_name: str):
        """Reload a specific module."""
        module_info = self._modules[module_name]
        old_hash = module_info.last_hash

        try:
            new_hash = self._compute_hash(module_info.path)

            if new_hash == old_hash:
                return

            logger.info(f"Detected change in {module_name}, reloading...")

            if module_name in sys.modules:
                old_module = sys.modules[module_name]

                importlib.reload(old_module)

                module_info.last_hash = new_hash
                module_info.last_modified = module_info.path.stat().st_mtime
                module_info.loaded_at = datetime.utcnow()
                module_info.reload_count += 1
                module_info.errors = []

                event = ReloadEvent(
                    module_name=module_name,
                    old_hash=old_hash,
                    new_hash=new_hash,
                    timestamp=datetime.utcnow(),
                    success=True,
                )
                self._reload_history.append(event)

                logger.info(f"Successfully reloaded {module_name}")

                for callback in self._reload_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(
                                module_name, old_module, sys.modules.get(module_name)
                            )
                        else:
                            callback(
                                module_name, old_module, sys.modules.get(module_name)
                            )
                    except Exception as e:
                        logger.error(f"Reload callback error: {e}")

                if self.on_reload:
                    try:
                        if asyncio.iscoroutinefunction(self.on_reload):
                            await self.on_reload(module_name)
                        else:
                            self.on_reload(module_name)
                    except Exception as e:
                        logger.error(f"on_reload callback error: {e}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to reload {module_name}: {error_msg}")

            module_info.errors.append(error_msg)

            event = ReloadEvent(
                module_name=module_name,
                old_hash=old_hash,
                new_hash="",
                timestamp=datetime.utcnow(),
                success=False,
                error_message=error_msg,
            )
            self._reload_history.append(event)

    def force_reload(self, module_name: str):
        """Force reload a specific module immediately."""
        if module_name in self._modules:
            self._last_check[module_name] = 0
            asyncio.create_task(self._reload_module(module_name))
            logger.info(f"Force reload triggered for {module_name}")
        else:
            logger.warning(f"Module {module_name} not being watched")

    def get_status(self) -> Dict[str, Any]:
        """Get current hot reload status."""
        return {
            "running": self._running,
            "watched_modules": [
                {
                    "name": m.name,
                    "path": str(m.path),
                    "reload_count": m.reload_count,
                    "last_reload": m.loaded_at.isoformat() if m.loaded_at else None,
                    "errors": m.errors[-5:] if m.errors else [],
                }
                for m in self._modules.values()
            ],
            "recent_reloads": [
                {
                    "module": e.module_name,
                    "timestamp": e.timestamp.isoformat(),
                    "success": e.success,
                }
                for e in self._reload_history[-10:]
            ],
        }

    def get_watch_dirs(self) -> List[str]:
        return [str(d) for d in self.watch_dirs]


class CodeInjector:
    """
    Inject new code logic into running modules without full reload.
    """

    def __init__(self):
        self._patches: Dict[str, Callable] = {}

    def register_patch(self, target_function: str, patch: Callable):
        """Register a patch for a specific function."""
        self._patches[target_function] = patch
        logger.info(f"Registered patch for {target_function}")

    def inject_function(self, module_name: str, function_name: str, new_func: Callable):
        """Inject a new function into a module."""
        if module_name in sys.modules:
            module = sys.modules[module_name]
            setattr(module, function_name, new_func)
            logger.info(f"Injected {function_name} into {module_name}")
        else:
            logger.error(f"Module {module_name} not loaded")

    def get_original_function(
        self, module_name: str, function_name: str
    ) -> Optional[Callable]:
        """Get original function before any patches."""
        if module_name in sys.modules:
            return getattr(sys.modules[module_name], function_name, None)
        return None


def create_hot_reload_manager(
    project_root: str,
    modules_to_watch: List[str],
    on_reload: Optional[Callable] = None,
) -> HotReloadManager:
    """Factory function to create hot reload manager with common config."""
    watch_dirs = [
        project_root,
        os.path.join(project_root, "cogs"),
        os.path.join(project_root, "core"),
    ]

    manager = HotReloadManager(
        watch_dirs=watch_dirs,
        watch_modules=modules_to_watch,
        on_reload=on_reload,
    )

    for module_name in modules_to_watch:
        module = sys.modules.get(module_name)
        if module and hasattr(module, "__file__") and module.__file__:
            manager.add_module(module_name, module.__file__)

    return manager
