"""SiliconDNA Cogs - Moderation Module

Complete isolation - errors in this cog never propagate to main system.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


logger = logging.getLogger("silicon_dna.cogs.moderation")


class ModerationCog:
    """
    Moderation cog with isolated error handling.
    Includes kick, ban, timeout, and message purging.
    """

    def __init__(self, mongodb_manager=None, redis_manager=None):
        self.mongodb = mongodb_manager
        self.redis = redis_manager
        self._action_history = []
        self._banned_users = set()
        self._timeout_users = {}

    async def load(self):
        """Load the moderation cog."""
        logger.info("ModerationCog loaded")

    async def unload(self):
        """Unload the moderation cog."""
        logger.info("ModerationCog unloaded")

    async def _log_action(
        self,
        action_type: str,
        target_user: str,
        moderator: str,
        guild_id: str,
        reason: str = "",
        duration: Optional[int] = None,
    ):
        """Log moderation action to database."""
        action = {
            "action_type": action_type,
            "target_user": target_user,
            "moderator": moderator,
            "guild_id": guild_id,
            "reason": reason,
            "duration": duration,
            "timestamp": datetime.utcnow(),
        }
        self._action_history.append(action)

        if self.mongodb:
            try:
                await self.mongodb.log_command(
                    command_name=f"moderation_{action_type}",
                    user_id=moderator,
                    guild_id=guild_id,
                    execution_time_ms=0,
                    success=True,
                    raw_input=action,
                )
            except Exception as e:
                logger.error(f"Failed to log moderation action: {e}")

    async def kick(
        self,
        user_id: str,
        guild_id: str,
        moderator_id: str,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Kick a user from the guild."""
        try:
            logger.info(f"Kicking user {user_id} from guild {guild_id}")

            await self._log_action(
                action_type="kick",
                target_user=user_id,
                moderator=moderator_id,
                guild_id=guild_id,
                reason=reason,
            )

            return {"success": True, "action": "kick", "user_id": user_id}

        except Exception as e:
            logger.error(f"Kick failed: {e}")
            if self.mongodb:
                await self.mongodb.log_error(
                    error_type="ModerationKick",
                    error_message=str(e),
                    component="ModerationCog",
                    metadata={"user_id": user_id, "guild_id": guild_id},
                )
            return {"success": False, "error": str(e)}

    async def ban(
        self,
        user_id: str,
        guild_id: str,
        moderator_id: str,
        reason: str = "",
        duration: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Ban a user from the guild."""
        try:
            logger.info(f"Banning user {user_id} from guild {guild_id}")

            self._banned_users.add(user_id)

            await self._log_action(
                action_type="ban",
                target_user=user_id,
                moderator=moderator_id,
                guild_id=guild_id,
                reason=reason,
                duration=duration,
            )

            return {
                "success": True,
                "action": "ban",
                "user_id": user_id,
                "permanent": duration is None,
            }

        except Exception as e:
            logger.error(f"Ban failed: {e}")
            if self.mongodb:
                await self.mongodb.log_error(
                    error_type="ModerationBan",
                    error_message=str(e),
                    component="ModerationCog",
                    metadata={"user_id": user_id, "guild_id": guild_id},
                )
            return {"success": False, "error": str(e)}

    async def unban(
        self,
        user_id: str,
        guild_id: str,
        moderator_id: str,
    ) -> Dict[str, Any]:
        """Unban a user."""
        try:
            if user_id in self._banned_users:
                self._banned_users.remove(user_id)
                logger.info(f"Unbanned user {user_id} in guild {guild_id}")

                await self._log_action(
                    action_type="unban",
                    target_user=user_id,
                    moderator=moderator_id,
                    guild_id=guild_id,
                )

                return {"success": True, "action": "unban", "user_id": user_id}

            return {"success": False, "error": "User not banned"}

        except Exception as e:
            logger.error(f"Unban failed: {e}")
            return {"success": False, "error": str(e)}

    async def timeout(
        self,
        user_id: str,
        guild_id: str,
        moderator_id: str,
        duration_seconds: int,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Timeout a user."""
        try:
            if duration_seconds > 2419200:
                return {
                    "success": False,
                    "error": "Timeout duration exceeds maximum (28 days)",
                }

            timeout_until = datetime.utcnow() + timedelta(seconds=duration_seconds)
            self._timeout_users[user_id] = timeout_until

            logger.info(
                f"Timed out user {user_id} for {duration_seconds}s in guild {guild_id}"
            )

            await self._log_action(
                action_type="timeout",
                target_user=user_id,
                moderator=moderator_id,
                guild_id=guild_id,
                reason=reason,
                duration=duration_seconds,
            )

            return {
                "success": True,
                "action": "timeout",
                "user_id": user_id,
                "duration": duration_seconds,
                "until": timeout_until.isoformat(),
            }

        except Exception as e:
            logger.error(f"Timeout failed: {e}")
            if self.mongodb:
                await self.mongodb.log_error(
                    error_type="ModerationTimeout",
                    error_message=str(e),
                    component="ModerationCog",
                    metadata={"user_id": user_id, "duration": duration_seconds},
                )
            return {"success": False, "error": str(e)}

    async def remove_timeout(
        self, user_id: str, guild_id: str, moderator_id: str
    ) -> Dict[str, Any]:
        """Remove timeout from a user."""
        try:
            if user_id in self._timeout_users:
                del self._timeout_users[user_id]
                logger.info(f"Removed timeout from user {user_id} in guild {guild_id}")

                await self._log_action(
                    action_type="remove_timeout",
                    target_user=user_id,
                    moderator=moderator_id,
                    guild_id=guild_id,
                )

                return {"success": True, "action": "remove_timeout", "user_id": user_id}

            return {"success": False, "error": "User not timed out"}

        except Exception as e:
            logger.error(f"Remove timeout failed: {e}")
            return {"success": False, "error": str(e)}

    async def purge_messages(
        self,
        guild_id: str,
        channel_id: str,
        moderator_id: str,
        count: int,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Purge messages from a channel."""
        try:
            if count < 1 or count > 100:
                return {
                    "success": False,
                    "error": "Message count must be between 1 and 100",
                }

            logger.info(
                f"Purging {count} messages from channel {channel_id} in guild {guild_id}"
            )

            await self._log_action(
                action_type="purge",
                target_user=channel_id,
                moderator=moderator_id,
                guild_id=guild_id,
                reason=reason,
                duration=count,
            )

            return {
                "success": True,
                "action": "purge",
                "count": count,
                "channel_id": channel_id,
            }

        except Exception as e:
            logger.error(f"Purge failed: {e}")
            if self.mongodb:
                await self.mongodb.log_error(
                    error_type="ModerationPurge",
                    error_message=str(e),
                    component="ModerationCog",
                    metadata={"channel_id": channel_id, "count": count},
                )
            return {"success": False, "error": str(e)}

    def is_banned(self, user_id: str) -> bool:
        """Check if user is banned."""
        return user_id in self._banned_users

    def is_timed_out(self, user_id: str) -> bool:
        """Check if user is timed out and if timeout is still active."""
        if user_id not in self._timeout_users:
            return False

        if datetime.utcnow() < self._timeout_users[user_id]:
            return True

        del self._timeout_users[user_id]
        return False

    def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """Get current moderation status for a user."""
        return {
            "banned": self.is_banned(user_id),
            "timed_out": self.is_timed_out(user_id),
        }

    def get_action_history(self, limit: int = 50) -> list:
        """Get recent moderation actions."""
        return self._action_history[-limit:]
