
from typing import Any, Dict, List, Tuple, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel

class LM(BaseModel):
    @abstractmethod
    def complete(self, prompt: str, stop:str='\n') -> str:
        """Given a header, a prompt, and a stop string, returns the completion (including the stop string)"""

    @abstractmethod
    def choose(self, prompt: str, choices: List[str]) -> int:
        """Given a header, a prompt, and a list of choices, returns the index of the selected choice"""
