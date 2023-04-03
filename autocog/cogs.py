from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from pydantic import BaseModel
from abc import abstractmethod

class Cog(BaseModel):
    """Base class for a component in a cognitive architecture"""
    tag: str

    def reset(self):
        pass

    @abstractmethod
    async def __call__(self, **inputs) -> Tuple[Any,Any]:
        pass
