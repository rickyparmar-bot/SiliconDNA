"""SiliconDNA - Base Cog Template"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging


class BaseCog(ABC):
    """
    Base class for all modular cogs in SiliconDNA.
    Each cog must be self-contained and handle its own errors.
    Constraint: Keep under 500 lines per module.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger: Optional[logging.Logger] = None
        self.is_loaded = False

    async def load(self):
        """Called when cog is loaded. Override in subclass."""
        self.logger = logging.getLogger(f"silicon_dna.cog.{self.__class__.__name__}")
        self.logger.info(f"Loading {self.__class__.__name__}...")
        self.is_loaded = True

    async def unload(self):
        """Called when cog is unloaded. Override in subclass."""
        if self.logger:
            self.logger.info(f"Unloading {self.__class__.__name__}...")
        self.is_loaded = False

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """
        Main execution logic. Must be implemented in subclass.
        """
        raise NotImplementedError

    async def handle_error(self, error: Exception, context: Optional[Dict] = None):
        """Handle errors gracefully - prevent crash propagation."""
        if self.logger:
            self.logger.error(f"Error in {self.__class__.__name__}: {error}")
            if context:
                self.logger.error(f"Context: {context}")

    def validate_config(self, required_keys: list) -> bool:
        """Validate required configuration keys."""
        return all(key in self.config for key in required_keys)
