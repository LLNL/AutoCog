
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable, Union
from abc import abstractmethod
from pydantic import BaseModel

from .ir import Prompt

from ...fta.automaton import FiniteThoughtAutomaton as FTA
from ...fta.actions import Choose, Complete, Text

class Syntax(BaseModel):
    def fta(self, prompt: Prompt):
        return None
