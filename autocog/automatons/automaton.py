
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable
from abc import abstractmethod
from pydantic import BaseModel\

from ..cogs import Cog
from .format import Format

class Automaton(Cog):
    """Base class for an Automaton."""
    orchestrator: "Orchestrator"
    formats: Dict[str,Format] = {}

    @abstractmethod
    async def __call__(self, fid:int, **inputs) -> Tuple[Any,Any]:
        pass
