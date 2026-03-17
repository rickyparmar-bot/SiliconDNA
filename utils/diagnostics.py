"""SiliconDNA Utils - Developer Diagnostics

Error viewer and real-time metrics dashboard for database monitoring.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque


logger = logging.getLogger("silicon_dna.diagnostics")


@dataclass
class ErrorEntry:
    id: str
    error_type: str
    message: str
    component: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSnapshot:
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


class ErrorViewer:
    """
    Real-time error tracking and viewing system.
    """

    def __init__(self, mongodb_manager=None):
        self.mongodb = mongodb_manager
        self._errors: deque = deque(maxlen=1000)
        self._error_counts: Dict[str, int] = {}

    async def record_error(
        self,
        error_type: str,
        message: str,
        component: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ErrorEntry:
        """Record a new error."""
        entry = ErrorEntry(
            id=f"err_{len(self._errors)}",
            error_type=error_type,
            message=message,
            component=component,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )

        self._errors.append(entry)

        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1

        if self.mongodb:
            try:
                await self.mongodb.log_error(
                    error_type=error_type,
                    error_message=message,
                    component=component,
                    stack_trace=metadata.get("stack_trace") if metadata else None,
                    **metadata,
                )
            except Exception as e:
                logger.error(f"Failed to persist error to MongoDB: {e}")

        logger.error(f"[{component}] {error_type}: {message}")
        return entry

    def get_recent_errors(
        self, limit: int = 50, component: Optional[str] = None
    ) -> List[ErrorEntry]:
        """Get recent errors, optionally filtered by component."""
        errors = list(self._errors)

        if component:
            errors = [e for e in errors if e.component == component]

        return errors[-limit:]

    def get_unresolved_errors(self, limit: int = 50) -> List[ErrorEntry]:
        """Get all unresolved errors."""
        return [e for e in self._errors if not e.resolved][-limit:]

    def mark_resolved(self, error_id: str) -> bool:
        """Mark an error as resolved."""
        for error in self._errors:
            if error.id == error_id:
                error.resolved = True
                error.resolved_at = datetime.utcnow()
                logger.info(f"Error {error_id} marked as resolved")
                return True
        return False

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors."""
        total = len(self._errors)
        resolved = sum(1 for e in self._errors if e.resolved)
        unresolved = total - resolved

        return {
            "total": total,
            "resolved": resolved,
            "unresolved": unresolved,
            "by_type": dict(self._error_counts),
            "by_component": self._get_errors_by_component(),
        }

    def _get_errors_by_component(self) -> Dict[str, int]:
        """Get error counts by component."""
        counts = {}
        for error in self._errors:
            counts[error.component] = counts.get(error.component, 0) + 1
        return counts

    def clear_resolved(self):
        """Clear all resolved errors from memory."""
        self._errors = deque([e for e in self._errors if not e.resolved], maxlen=1000)
        logger.info("Cleared resolved errors")


class MetricsDashboard:
    """
    Real-time metrics dashboard for database health monitoring.
    """

    def __init__(self, mongodb_manager=None, redis_manager=None):
        self.mongodb = mongodb_manager
        self.redis = redis_manager
        self._metrics: Dict[str, deque] = {
            "command_rate": deque(maxlen=60),
            "error_rate": deque(maxlen=60),
            "response_time": deque(maxlen=60),
            "cache_hits": deque(maxlen=60),
            "cache_misses": deque(maxlen=60),
        }
        self._start_time = datetime.utcnow()
        self._last_command_count = 0
        self._last_error_count = 0

    async def record_metric(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ):
        """Record a metric value."""
        snapshot = MetricSnapshot(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {},
        )

        if name not in self._metrics:
            self._metrics[name] = deque(maxlen=60)

        self._metrics[name].append(snapshot)

        if self.mongodb:
            try:
                await self.mongodb.log_telemetry(
                    metric_name=name,
                    value=value,
                    tags=tags,
                )
            except Exception as e:
                logger.error(f"Failed to log metric to MongoDB: {e}")

    async def update_system_metrics(self):
        """Update system-level metrics."""
        now = datetime.utcnow()

        command_count = len(list(self._metrics.get("command_rate", [])))
        error_count = len(list(self._metrics.get("error_rate", [])))

        commands_per_sec = (command_count - self._last_command_count) / max(
            1, (now - (self._start_time + timedelta(seconds=60))).total_seconds()
        )
        errors_per_sec = (error_count - self._last_error_count) / max(
            1, (now - (self._start_time + timedelta(seconds=60))).total_seconds()
        )

        await self.record_metric("system.commands_per_second", commands_per_sec)
        await self.record_metric("system.errors_per_second", errors_per_sec)

        self._last_command_count = command_count
        self._last_error_count = error_count

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metric values."""
        result = {}

        for name, snapshots in self._metrics.items():
            if snapshots:
                latest = snapshots[-1]
                values = [s.value for s in snapshots]

                result[name] = {
                    "current": latest.value,
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "samples": len(values),
                    "last_update": latest.timestamp.isoformat(),
                }

        return result

    def get_database_health(self) -> Dict[str, Any]:
        """Get database connection health metrics."""
        health = {
            "mongodb": {"connected": False, "latency_ms": None},
            "redis": {"connected": False, "latency_ms": None},
        }

        if self.mongodb:
            health["mongodb"]["connected"] = self.mongodb.is_connected

        if self.redis:
            health["redis"]["connected"] = self.redis.is_connected

        return health

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        hits = sum(1 for s in self._metrics.get("cache_hits", []) if s.value > 0)
        misses = sum(1 for s in self._metrics.get("cache_misses", []) if s.value > 0)
        total = hits + misses

        hit_rate = (hits / total * 100) if total > 0 else 0

        return {
            "hits": hits,
            "misses": misses,
            "total": total,
            "hit_rate_percent": round(hit_rate, 2),
        }

    def get_uptime(self) -> Dict[str, Any]:
        """Get system uptime."""
        delta = datetime.utcnow() - self._start_time
        return {
            "seconds": int(delta.total_seconds()),
            "formatted": str(delta).split(".")[0],
        }

    def get_full_dashboard(self) -> Dict[str, Any]:
        """Get complete dashboard data."""
        return {
            "metrics": self.get_current_metrics(),
            "database_health": self.get_database_health(),
            "cache_stats": self.get_cache_stats(),
            "uptime": self.get_uptime(),
            "error_summary": {
                "recent_errors": len(self._metrics.get("error_rate", [])),
            },
        }


class DiagnosticsManager:
    """
    Unified diagnostics manager combining error viewer and metrics dashboard.
    """

    def __init__(self, mongodb_manager=None, redis_manager=None):
        self.errors = ErrorViewer(mongodb_manager)
        self.metrics = MetricsDashboard(mongodb_manager, redis_manager)

    async def record_error(
        self,
        error_type: str,
        message: str,
        component: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record error and update error rate metric."""
        await self.errors.record_error(error_type, message, component, metadata)
        await self.metrics.record_metric("error_rate", 1.0, {"component": component})

    async def record_command(self, command_name: str, execution_time_ms: float):
        """Record command execution."""
        await self.metrics.record_metric("command_rate", 1.0, {"command": command_name})
        await self.metrics.record_metric(
            "response_time", execution_time_ms, {"command": command_name}
        )

    async def record_cache_hit(self):
        """Record cache hit."""
        await self.metrics.record_metric("cache_hits", 1.0)

    async def record_cache_miss(self):
        """Record cache miss."""
        await self.metrics.record_metric("cache_misses", 1.0)

    def get_status(self) -> Dict[str, Any]:
        """Get complete diagnostic status."""
        return {
            "errors": self.errors.get_error_summary(),
            "metrics": self.metrics.get_current_metrics(),
            "database_health": self.metrics.get_database_health(),
            "cache": self.metrics.get_cache_stats(),
            "uptime": self.metrics.get_uptime(),
        }
