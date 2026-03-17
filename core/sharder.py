"""SiliconDNA Core - Asynchronous Sharding Manager"""

import asyncio
import logging
import hashlib
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


logger = logging.getLogger("silicon_dna.core.sharder")


class ShardStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OVERLOADED = "overloaded"
    RECOVERING = "recovering"


@dataclass
class Shard:
    shard_id: int
    status: ShardStatus
    current_load: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ShardAllocation:
    shard_id: int
    assigned_at: datetime
    data_keys: List[str]


class ShardingManager:
    """
    Asynchronous sharding manager for distributing computational load.
    Ensures uninterrupted uptime as ML models evolve and adapt.
    """

    def __init__(
        self,
        num_shards: int = 4,
        max_load_per_shard: float = 0.8,
        heartbeat_interval: int = 30,
    ):
        self.num_shards = num_shards
        self.max_load_per_shard = max_load_per_shard
        self.heartbeat_interval = heartbeat_interval

        self._shards: Dict[int, Shard] = {}
        self._allocations: Dict[str, ShardAllocation] = {}
        self._is_running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._handlers: Dict[str, Callable] = {}

        self._initialize_shards()

    def _initialize_shards(self):
        """Initialize shard pool."""
        for i in range(self.num_shards):
            self._shards[i] = Shard(
                shard_id=i,
                status=ShardStatus.ACTIVE,
            )
        logger.info(f"Initialized {self.num_shards} shards")

    async def start(self):
        """Start the sharding manager."""
        if self._is_running:
            return

        self._is_running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info("Sharding manager started")

    async def stop(self):
        """Stop the sharding manager."""
        self._is_running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("Sharding manager stopped")

    async def _heartbeat_loop(self):
        """Monitor shard health and redistribute load."""
        while self._is_running:
            await asyncio.sleep(self.heartbeat_interval)

            for shard in self._shards.values():
                shard.last_heartbeat = datetime.utcnow()

                if shard.current_load > self.max_load_per_shard:
                    shard.status = ShardStatus.OVERLOADED
                    await self._redistribute_load(shard.shard_id)
                else:
                    shard.status = ShardStatus.ACTIVE

    async def _redistribute_load(self, overloaded_shard_id: int):
        """Redistribute load from overloaded shard."""
        overloaded = self._shards.get(overloaded_shard_id)
        if not overloaded:
            return

        target_shards = [
            s
            for s in self._shards.values()
            if s.shard_id != overloaded_shard_id and s.status == ShardStatus.ACTIVE
        ]

        if not target_shards:
            logger.warning(
                f"No available shards to handle load from shard {overloaded_shard_id}"
            )
            return

        keys_to_move = [
            key
            for key, alloc in self._allocations.items()
            if alloc.shard_id == overloaded_shard_id
        ]

        move_count = len(keys_to_move) // 2
        for key in keys_to_move[:move_count]:
            new_shard = min(target_shards, key=lambda s: s.current_load)
            self._allocations[key] = ShardAllocation(
                shard_id=new_shard.shard_id,
                assigned_at=datetime.utcnow(),
                data_keys=[key],
            )
            new_shard.current_load += 0.1

        overloaded.current_load = self.max_load_per_shard
        logger.info(f"Redistributed {move_count} keys from shard {overloaded_shard_id}")

    def route_key(self, key: str) -> int:
        """Determine which shard should handle a key."""
        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return hash_value % self.num_shards

    async def route_request(
        self,
        key: str,
        handler: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """
        Route request to appropriate shard and execute handler.

        Args:
            key: Request key for shard routing
            handler: Async callable to execute
            *args, **kwargs: Arguments for handler

        Returns:
            Handler result
        """
        shard_id = self.route_key(key)
        shard = self._shards.get(shard_id)

        if not shard or shard.status == ShardStatus.INACTIVE:
            fallback_id = self._get_fallback_shard()
            if fallback_id is not None:
                shard_id = fallback_id
                shard = self._shards[fallback_id]

        if not shard:
            raise RuntimeError("No active shards available")

        try:
            shard.total_requests += 1
            result = await handler(*args, **kwargs)
            shard.current_load = min(1.0, shard.current_load + 0.01)

            return result

        except Exception as e:
            shard.failed_requests += 1
            logger.error(f"Request failed on shard {shard_id}: {e}")
            raise

    def _get_fallback_shard(self) -> Optional[int]:
        """Get least loaded active shard as fallback."""
        active_shards = [
            s for s in self._shards.values() if s.status == ShardStatus.ACTIVE
        ]
        if not active_shards:
            return None
        return min(active_shards, key=lambda s: s.current_load).shard_id

    async def add_shard(self, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Add a new shard to the pool."""
        new_id = max(self._shards.keys()) + 1 if self._shards else 0

        self._shards[new_id] = Shard(
            shard_id=new_id,
            status=ShardStatus.ACTIVE,
            metadata=metadata or {},
        )

        self.num_shards += 1
        logger.info(f"Added new shard: {new_id}")

        return new_id

    async def remove_shard(self, shard_id: int) -> bool:
        """Remove a shard from the pool."""
        if shard_id not in self._shards:
            return False

        keys_to_redistribute = [
            key
            for key, alloc in self._allocations.items()
            if alloc.shard_id == shard_id
        ]

        for key in keys_to_redistribute:
            new_shard_id = self._get_fallback_shard()
            if new_shard_id is not None:
                self._allocations[key] = ShardAllocation(
                    shard_id=new_shard_id,
                    assigned_at=datetime.utcnow(),
                    data_keys=[key],
                )

        del self._shards[shard_id]
        self.num_shards -= 1

        logger.info(f"Removed shard: {shard_id}")
        return True

    def get_shard_status(self, shard_id: int) -> Optional[Dict[str, Any]]:
        """Get status of a specific shard."""
        shard = self._shards.get(shard_id)
        if not shard:
            return None

        return {
            "shard_id": shard.shard_id,
            "status": shard.status.value,
            "current_load": shard.current_load,
            "total_requests": shard.total_requests,
            "failed_requests": shard.failed_requests,
            "success_rate": (
                (shard.total_requests - shard.failed_requests) / shard.total_requests
                if shard.total_requests > 0
                else 0
            ),
            "last_heartbeat": shard.last_heartbeat.isoformat(),
        }

    def get_all_shards_status(self) -> List[Dict[str, Any]]:
        """Get status of all shards."""
        return [self.get_shard_status(shard_id) for shard_id in self._shards.keys()]

    def get_cluster_stats(self) -> Dict[str, Any]:
        """Get overall cluster statistics."""
        total_requests = sum(s.total_requests for s in self._shards.values())
        total_failures = sum(s.failed_requests for s in self._shards.values())

        active_shards = sum(
            1 for s in self._shards.values() if s.status == ShardStatus.ACTIVE
        )

        return {
            "total_shards": self.num_shards,
            "active_shards": active_shards,
            "total_requests": total_requests,
            "total_failures": total_failures,
            "success_rate": (
                (total_requests - total_failures) / total_requests
                if total_requests > 0
                else 0
            ),
            "avg_load": sum(s.current_load for s in self._shards.values())
            / max(1, len(self._shards)),
        }

    async def execute_on_all_shards(self, handler: Callable) -> Dict[int, Any]:
        """Execute a handler on all active shards."""
        results = {}

        for shard_id, shard in self._shards.items():
            if shard.status == ShardStatus.ACTIVE:
                try:
                    result = await handler(shard_id)
                    results[shard_id] = result
                except Exception as e:
                    results[shard_id] = {"error": str(e)}

        return results
