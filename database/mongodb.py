"""SiliconDNA Database Module - MongoDB Async Observability Layer"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId


logger = logging.getLogger("silicon_dna.mongodb")


class MongoDBManager:
    """
    Async MongoDB connection manager for database-first observability.
    Tracks every command execution, system error, and performance metric.
    """

    def __init__(
        self,
        uri: str,
        database_name: str,
        pool_size: int = 10,
        server_selection_timeout_ms: int = 5000,
        connect_timeout_ms: int = 5000,
    ):
        self.uri = uri
        self.database_name = database_name
        self.pool_size = pool_size
        self.server_selection_timeout_ms = server_selection_timeout_ms
        self.connect_timeout_ms = connect_timeout_ms
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self._connected = False

    async def connect(self) -> bool:
        """Establish async MongoDB connection."""
        try:
            self.client = AsyncIOMotorClient(
                self.uri,
                maxPoolSize=self.pool_size,
                serverSelectionTimeoutMS=self.server_selection_timeout_ms,
                connectTimeoutMS=self.connect_timeout_ms,
            )
            await self.client.admin.command("ping")
            self.db = self.client[self.database_name]
            self._connected = True
            logger.info(f"Connected to MongoDB: {self.database_name}")

            await self._ensure_indexes()
            return True
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            self._connected = False
            raise

    async def _ensure_indexes(self):
        """Create indexes for efficient querying."""
        try:
            await self.db.command_logs.create_index("timestamp")
            await self.db.command_logs.create_index(
                [("command_name", 1), ("timestamp", -1)]
            )
            await self.db.command_logs.create_index("user_id")

            await self.db.error_logs.create_index("timestamp")
            await self.db.error_logs.create_index("error_type")
            await self.db.error_logs.create_index("component")

            await self.db.telemetry.create_index("timestamp")
            await self.db.telemetry.create_index(
                [("metric_name", 1), ("timestamp", -1)]
            )

            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

    async def disconnect(self):
        """Close MongoDB connection gracefully."""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("MongoDB disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected and self.client is not None

    async def log_command(
        self,
        command_name: str,
        user_id: str,
        guild_id: Optional[str] = None,
        execution_time_ms: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
        raw_input: Optional[Dict[str, Any]] = None,
    ):
        """Log command execution to telemetry collection."""
        if not self.is_connected or not self.db:
            logger.warning("MongoDB not connected, skipping command log")
            return

        try:
            doc = {
                "command_name": command_name,
                "user_id": user_id,
                "guild_id": guild_id,
                "execution_time_ms": execution_time_ms,
                "success": success,
                "error_message": error_message,
                "raw_input": raw_input or {},
                "timestamp": datetime.utcnow(),
            }
            await self.db.command_logs.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to log command: {e}")

    async def log_error(
        self,
        error_type: str,
        error_message: str,
        component: str,
        stack_trace: Optional[str] = None,
        resolution_status: str = "pending",
        **metadata,
    ):
        """Log error to error collection."""
        if not self.is_connected or not self.db:
            logger.warning("MongoDB not connected, skipping error log")
            return

        try:
            doc = {
                "error_type": error_type,
                "error_message": error_message,
                "component": component,
                "stack_trace": stack_trace,
                "resolution_status": resolution_status,
                "metadata": metadata,
                "timestamp": datetime.utcnow(),
            }
            await self.db.error_logs.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to log error: {e}")

    async def log_telemetry(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        unit: str = "",
    ):
        """Log performance metric."""
        if not self.is_connected or not self.db:
            logger.warning("MongoDB not connected, skipping telemetry log")
            return

        try:
            doc = {
                "metric_name": metric_name,
                "value": value,
                "unit": unit,
                "tags": tags or {},
                "timestamp": datetime.utcnow(),
            }
            await self.db.telemetry.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to log telemetry: {e}")

    async def log_ml_prediction(
        self,
        model_name: str,
        input_features: Dict[str, Any],
        prediction: Any,
        confidence: float,
        prediction_type: str = "regression",
    ):
        """Log ML prediction for model monitoring."""
        if not self.is_connected or not self.db:
            return

        try:
            doc = {
                "model_name": model_name,
                "input_features": input_features,
                "prediction": str(prediction),
                "confidence": confidence,
                "prediction_type": prediction_type,
                "timestamp": datetime.utcnow(),
            }
            await self.db.ml_predictions.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to log ML prediction: {e}")

    async def get_command_history(
        self,
        command_name: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Retrieve recent command history with optional filters."""
        if not self.is_connected or not self.db:
            return []

        query = {}
        if command_name:
            query["command_name"] = command_name
        if user_id:
            query["user_id"] = user_id

        try:
            cursor = self.db.command_logs.find(query).sort("timestamp", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Failed to get command history: {e}")
            return []

    async def get_telemetry(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Retrieve telemetry for a specific metric."""
        if not self.is_connected or not self.db:
            return []

        query = {"metric_name": metric_name}
        if start_time:
            query["timestamp"] = {"$gte": start_time}
        if end_time:
            if "timestamp" in query:
                query["timestamp"]["$lte"] = end_time
            else:
                query["timestamp"] = {"$lte": end_time}

        try:
            cursor = self.db.telemetry.find(query).sort("timestamp", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Failed to get telemetry: {e}")
            return []

    async def get_recent_errors(
        self,
        component: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Retrieve recent errors, optionally filtered by component."""
        if not self.is_connected or not self.db:
            return []

        query = {}
        if component:
            query["component"] = component

        try:
            cursor = self.db.error_logs.find(query).sort("timestamp", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Failed to get recent errors: {e}")
            return []

    async def update_error_resolution(
        self,
        error_id: str,
        resolution_status: str = "resolved",
        resolution_notes: str = "",
    ):
        """Update error resolution status."""
        if not self.is_connected or not self.db:
            return

        try:
            await self.db.error_logs.update_one(
                {"_id": ObjectId(error_id)},
                {
                    "$set": {
                        "resolution_status": resolution_status,
                        "resolution_notes": resolution_notes,
                        "resolved_at": datetime.utcnow(),
                    }
                },
            )
        except Exception as e:
            logger.error(f"Failed to update error resolution: {e}")

    async def flush_writes(self):
        """Ensure all pending writes are completed."""
        if self.client:
            try:
                await self.client.admin.command("fsync")
                logger.debug("MongoDB writes flushed")
            except Exception as e:
                logger.warning(f"Flush warning: {e}")
