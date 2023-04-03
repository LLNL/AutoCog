
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable
from abc import abstractmethod
from pydantic import BaseModel

from ..cogs import Cog
#from ..architecture.orchestrator import Orchestrator

class Format(BaseModel):
    label: str
    desc: str
    caster: Optional[Callable] = None

class Text(Format):
    max_token: int
    base: Optional[str] = None

class Choice(Format):
    pass

class Enum(Choice):
    choices: List[str]

class ControlEdge(Enum):
    limits: List[Optional[int]]
    
    def __init__(self, desc:str, edges:List[Tuple[str,int]]):
        (choices, limits) = zip(*edges) if len(edges) > 0 else ([],[])
        super().__init__(label='next', desc=desc, choices=choices, limits=limits)

class Repeat(Choice):
    source: List[str]

class Regex(Format):
    expr: str

class Record(Format):
    parent: Optional["Record"] = None
    base: Optional["Record"] = None
    children: List[Tuple[str,Format,int]] = []

    def append(self, label:str, fmt:Format, cnt:int=0):
        self.children.append( ( label, fmt, cnt ) )

class Automaton(Cog):
    """Base class for an Automaton."""
    orchestrator: "Orchestrator"
    formats: Dict[str,Format] = {}

    @abstractmethod
    async def __call__(self, fid:int, **inputs) -> Tuple[Any,Any]:
        pass
