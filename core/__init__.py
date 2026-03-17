"""SiliconDNA - Module initialization"""

from .config import get_config, SiliconDNAConfig
from .event_loop import SiliconDNAEventLoop

__all__ = [
    "get_config",
    "SiliconDNAConfig",
    "SiliconDNAEventLoop",
]
