"""SiliconDNA Database Module - RethinkDB Key Storage"""

import logging
import asyncio
from typing import Optional, Any, List, Dict
import rethinkdb as r


logger = logging.getLogger("silicon_dna.rethinkdb")


class RethinkDBManager:
    """
    Async RethinkDB connection manager for modular key storage
    and complex JSON document retrieval.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 28015,
        database: str = "silicon_dna",
        auth_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.auth_key = auth_key
        self.timeout = timeout
        self.connection: Optional[r.RethinkDB] = None
        self._connected = False
        self._lock = asyncio.Lock()

    async def connect(self) -> bool:
        """Establish async RethinkDB connection."""
        async with self._lock:
            if self._connected:
                return True

            try:
                self.connection = r.connect(
                    host=self.host,
                    port=self.port,
                    db=self.database,
                    auth_key=self.auth_key,
                    timeout=self.timeout,
                )
                await self._check_connection()
                self._connected = True
                logger.info(f"Connected to RethinkDB: {self.database}")

                await self._ensure_tables()
                return True
            except Exception as e:
                logger.error(f"RethinkDB connection failed: {e}")
                self._connected = False
                return False

    async def _check_connection(self):
        """Verify connection is alive."""
        if self.connection:
            await r.db(self.database).table_list().run(self.connection)

    async def _ensure_tables(self):
        """Create required tables if they don't exist."""
        if not self.connection:
            return

        try:
            tables = await r.db(self.database).table_list().run(self.connection)

            required_tables = {
                "app_keys": ["key"],
                "documents": ["id"],
                "json_store": ["key"],
            }

            for table, primary_key in required_tables.items():
                if table not in tables:
                    await (
                        r.db(self.database)
                        .table_create(table, primary_key=primary_key[0])
                        .run(self.connection)
                    )
                    logger.info(f"Created RethinkDB table: {table}")
        except Exception as e:
            logger.warning(f"Table creation warning: {e}")

    async def disconnect(self):
        """Close RethinkDB connection."""
        async with self._lock:
            if self.connection:
                self.connection.close()
                self._connected = False
                logger.info("RethinkDB disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected and self.connection is not None

    async def table(self, table_name: str):
        """Get a table reference."""
        if not self.is_connected:
            raise RuntimeError("RethinkDB not connected")
        return r.db(self.database).table(table_name)

    async def insert(
        self,
        table: str,
        data: Dict[str, Any],
        conflict: str = "error",
    ) -> Optional[str]:
        """
        Insert a document into a table.

        Args:
            table: Table name
            data: Document to insert
            conflict: How to handle conflicts ("error", "replace", "update")

        Returns:
            Generated document ID if successful
        """
        if not self.is_connected:
            logger.warning("RethinkDB not connected, skipping insert")
            return None

        try:
            result = (
                await r.db(self.database)
                .table(table)
                .insert(data, conflict=conflict)
                .run(self.connection)
            )

            if result.get("errors", 0) > 0:
                logger.error(f"RethinkDB insert error: {result.get('first_error')}")
                return None

            return result.get("generated_keys", [None])[0]
        except Exception as e:
            logger.error(f"RethinkDB insert failed: {e}")
            return None

    async def get(self, table: str, doc_id: str) -> Optional[Dict]:
        """Get a document by ID."""
        if not self.is_connected:
            return None

        try:
            result = (
                await r.db(self.database).table(table).get(doc_id).run(self.connection)
            )
            return result
        except Exception as e:
            logger.error(f"RethinkDB get failed: {e}")
            return None

    async def get_by_key(self, table: str, key: str, value: Any) -> Optional[Dict]:
        """Get a document by a specific key field."""
        if not self.is_connected:
            return None

        try:
            result = (
                await r.db(self.database)
                .table(table)
                .filter({key: value})
                .run(self.connection)
            )
            docs = list(result)
            return docs[0] if docs else None
        except Exception as e:
            logger.error(f"RethinkDB get_by_key failed: {e}")
            return None

    async def update(
        self,
        table: str,
        doc_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """Update a document by ID."""
        if not self.is_connected:
            return False

        try:
            result = (
                await r.db(self.database)
                .table(table)
                .get(doc_id)
                .update(updates)
                .run(self.connection)
            )
            return result.get("replaced", 0) > 0
        except Exception as e:
            logger.error(f"RethinkDB update failed: {e}")
            return False

    async def delete(self, table: str, doc_id: str) -> bool:
        """Delete a document by ID."""
        if not self.is_connected:
            return False

        try:
            result = (
                await r.db(self.database)
                .table(table)
                .get(doc_id)
                .delete()
                .run(self.connection)
            )
            return result.get("deleted", 0) > 0
        except Exception as e:
            logger.error(f"RethinkDB delete failed: {e}")
            return False

    async def list_all(
        self,
        table: str,
        limit: int = 100,
    ) -> List[Dict]:
        """List all documents in a table."""
        if not self.is_connected:
            return []

        try:
            result = (
                await r.db(self.database).table(table).limit(limit).run(self.connection)
            )
            return list(result)
        except Exception as e:
            logger.error(f"RethinkDB list_all failed: {e}")
            return []

    async def query(
        self,
        table: str,
        filter_dict: Dict[str, Any],
        limit: int = 100,
    ) -> List[Dict]:
        """Query documents with filters."""
        if not self.is_connected:
            return []

        try:
            result = (
                await r.db(self.database)
                .table(table)
                .filter(filter_dict)
                .limit(limit)
                .run(self.connection)
            )
            return list(result)
        except Exception as e:
            logger.error(f"RethinkDB query failed: {e}")
            return []

    async def store_json(
        self,
        key: str,
        data: Any,
        replace: bool = True,
    ) -> bool:
        """
        Store JSON data with a key in json_store table.

        Args:
            key: Unique key for the data
            data: JSON-serializable data
            replace: Whether to replace existing

        Returns:
            Success status
        """
        if not self.is_connected:
            return False

        doc = {"key": key, "data": data}

        if replace:
            existing = await self.get("json_store", key)
            if existing:
                await self.update("json_store", key, {"data": data})
                return True

        result = await self.insert("json_store", doc, conflict="replace")
        return result is not None

    async def retrieve_json(self, key: str) -> Optional[Any]:
        """Retrieve JSON data by key."""
        return await self.get_by_key("json_store", "key", key)

    async def delete_json(self, key: str) -> bool:
        """Delete JSON data by key."""
        if not self.is_connected:
            return False

        doc = await self.get_by_key("json_store", "key", key)
        if doc and "id" in doc:
            return await self.delete("json_store", doc["id"])
        return False
