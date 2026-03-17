"""SiliconDNA Core - Command Interface Protocols"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


logger = logging.getLogger("silicon_dna.commands")


class CommandType(Enum):
    SLASH = "slash"
    MESSAGE = "message"
    USER = "user"
    MESSAGE_COMPONENT = "message_component"


class OptionType(Enum):
    STRING = 1
    INTEGER = 2
    BOOLEAN = 3
    USER = 4
    CHANNEL = 5
    ROLE = 6
    MENTIONABLE = 7
    NUMBER = 8
    ATTACHMENT = 9


@dataclass
class CommandOption:
    name: str
    description: str
    option_type: OptionType
    required: bool = False
    choices: Optional[List[Dict[str, Any]]] = None
    autocomplete: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None


@dataclass
class Command:
    name: str
    description: str
    callback: Callable
    options: List[CommandOption] = field(default_factory=list)
    guild_only: bool = False
    dm_only: bool = False
    nsfw: bool = False
    cooldown: int = 0


@dataclass
class Modal:
    title: str
    custom_id: str
    components: List[Dict[str, Any]]
    callback: Callable


class AutocompleteHandler:
    """Handles autocomplete suggestions for slash commands."""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register(self, command_name: str, handler: Callable):
        self._handlers[command_name] = handler

    async def get_suggestions(
        self, command_name: str, focused_option: str, value: str
    ) -> List[Dict[str, Any]]:
        if command_name in self._handlers:
            handler = self._handlers[command_name]
            if asyncio.iscoroutinefunction(handler):
                return await handler(focused_option, value)
            return handler(focused_option, value)
        return []


class CommandInterface:
    """
    Main command interface for SiliconDNA.
    Supports Discord slash commands, autocomplete, and modal interactions.
    """

    def __init__(self, mongodb_manager=None):
        self.commands: Dict[str, Command] = {}
        self.modal_handlers: Dict[str, Callable] = {}
        self.autocomplete = AutocompleteHandler()
        self.mongodb = mongodb_manager
        self._cooldowns: Dict[str, Dict[str, float]] = {}

    def register_command(
        self,
        name: str,
        description: str,
        callback: Callable,
        options: Optional[List[CommandOption]] = None,
        **kwargs,
    ):
        """Register a new slash command."""
        command = Command(
            name=name,
            description=description,
            callback=callback,
            options=options or [],
            **kwargs,
        )
        self.commands[name] = command

        if any(opt.autocomplete for opt in command.options):
            logger.info(f"Registered autocomplete command: {name}")

        logger.info(f"Registered slash command: {name}")
        return command

    def register_modal(self, custom_id: str, callback: Callable):
        """Register a modal interaction handler."""
        self.modal_handlers[custom_id] = callback
        logger.info(f"Registered modal handler: {custom_id}")

    def option(
        self,
        name: str,
        description: str,
        option_type: OptionType,
        required: bool = False,
        **kwargs,
    ):
        """Helper to create command options."""
        return CommandOption(
            name=name,
            description=description,
            option_type=option_type,
            required=required,
            **kwargs,
        )

    async def execute_command(
        self,
        command_name: str,
        user_id: str,
        guild_id: Optional[str],
        options: Dict[str, Any],
        interaction_object,
    ) -> Optional[Any]:
        """Execute a registered command with proper logging and error handling."""
        start_time = datetime.utcnow()

        if command_name not in self.commands:
            logger.warning(f"Command not found: {command_name}")
            return None

        command = self.commands[command_name]

        if not await self._check_cooldown(command, user_id):
            logger.warning(
                f"Cooldown active for user {user_id} on command {command_name}"
            )
            return None

        execution_time = 0
        success = True
        error_message = None
        result = None

        try:
            if asyncio.iscoroutinefunction(command.callback):
                result = await command.callback(interaction_object, options)
            else:
                result = command.callback(interaction_object, options)

            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            if self.mongodb:
                await self.mongodb.log_command(
                    command_name=command_name,
                    user_id=user_id,
                    guild_id=guild_id,
                    execution_time_ms=execution_time,
                    success=True,
                    raw_input={"options": options},
                )

            logger.info(f"Command {command_name} executed in {execution_time:.2f}ms")
            return result

        except Exception as e:
            success = False
            error_message = str(e)
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.error(f"Command {command_name} failed: {error_message}")

            if self.mongodb:
                await self.mongodb.log_command(
                    command_name=command_name,
                    user_id=user_id,
                    guild_id=guild_id,
                    execution_time_ms=execution_time,
                    success=False,
                    error_message=error_message,
                    raw_input={"options": options},
                )

                await self.mongodb.log_error(
                    error_type="CommandExecution",
                    error_message=error_message,
                    component="CommandInterface",
                    stack_trace=None,
                )

            return None

    async def _check_cooldown(self, command: Command, user_id: str) -> bool:
        """Check if user is in cooldown for command."""
        if command.cooldown <= 0:
            return True

        key = f"{command.name}:{user_id}"
        now = datetime.utcnow().timestamp()

        if key not in self._cooldowns:
            self._cooldowns[key] = {}

        last_used = self._cooldowns[key].get(command.name, 0)

        if now - last_used < command.cooldown:
            return False

        self._cooldowns[key][command.name] = now
        return True

    def get_command_list(self) -> List[Dict[str, Any]]:
        """Get list of commands formatted for Discord."""
        return [
            {
                "name": cmd.name,
                "description": cmd.description,
                "options": [
                    {
                        "name": opt.name,
                        "description": opt.description,
                        "type": opt.option_type.value,
                        "required": opt.required,
                        "choices": opt.choices,
                        "autocomplete": opt.autocomplete,
                    }
                    for opt in cmd.options
                ],
            }
            for cmd in self.commands.values()
        ]

    async def handle_autocomplete(
        self,
        command_name: str,
        focused_option: str,
        value: str,
    ) -> List[Dict[str, Any]]:
        """Handle autocomplete requests."""
        return await self.autocomplete.get_suggestions(
            command_name, focused_option, value
        )

    async def handle_modal(
        self,
        custom_id: str,
        data: Dict[str, Any],
        interaction_object,
    ) -> Optional[Any]:
        """Handle modal submission."""
        if custom_id not in self.modal_handlers:
            logger.warning(f"Modal handler not found: {custom_id}")
            return None

        callback = self.modal_handlers[custom_id]

        try:
            if asyncio.iscoroutinefunction(callback):
                return await callback(interaction_object, data)
            return callback(interaction_object, data)
        except Exception as e:
            logger.error(f"Modal callback failed: {e}")
            return None


def create_slash_command(
    name: str,
    description: str,
    options: Optional[List[CommandOption]] = None,
    **kwargs,
):
    """Decorator to register slash commands."""

    def decorator(func: Callable):
        func._command_metadata = {
            "name": name,
            "description": description,
            "options": options or [],
            **kwargs,
        }
        return func

    return decorator
