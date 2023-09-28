
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable, Union
from abc import abstractmethod
from pydantic import BaseModel

from .ast import Path

Range = Optional[Tuple[int,int]]

class Object(BaseModel):
    name: str
    desc:  Optional[str] = None

class Format(Object):
    pass

class Field(Object):
    depth:  int
    format: Optional[Format]
    range:  Range
    parent: Union["Prompt","Field"]

class Record(Object):
    fields: List[Field] = []

class Channel(BaseModel):
    tgt: Field

class Prompt(Object):
    fields:   List[Field]   = []
    channels: List[Channel] = []

class Program(BaseModel):
    desc:    Optional[str]    = None
    entries: Dict[str,str]    = {}

    prompts: Dict[str,Prompt] = {}
    formats: Dict[str,Format] = {}
    records: Dict[str,Record] = {}

    def toGraphViz(self):
        raise NotImplementedError()

# Specialization of `Format`

class Completion(Format):
    length: Optional[int]
    within: Optional[List[str]] = None

class Enum(Format):
    values: List[str]

class Choice(Format):
    path: Path
    mode: str

# Specialization of `Channel`

class Call(Channel):
    callee: Tuple[str,str]
    kwargs: Dict[str,Any] = {} # TODO Any?
    binds:  Any = None # TODO Any?

class Dataflow(Channel):
    src: Field

class Input(Channel):
    src: List[str]
