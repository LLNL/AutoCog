
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable, Union
from abc import abstractmethod
from pydantic import BaseModel

Range = Optional[Tuple[int,int]]

class Type:
    name: str
    desc:  Optional[str] = None

class Field:
    label: str
    desc:  Optional[str] = None
    depth: int
    type:  Type
    range: Range

class Channel:
    src: Field
    tgt: Field

class Call(Channel):
    callee: Tuple[str,str]
    kwargs: Dict[str,Any] = {} # TODO Any?
    binds:  Any = None # TODO Any?

class Prompt:
    desc:     Optional[str] = None
    fields:   List[Field]   = []
    channels: List[Channel] = []

class Program:
    desc:    Optional[str]    = None
    entries: Dict[str,str]    = {}

    prompts: Dict[str,Prompt] = {}
    types:   Dict[str,Type]   = {}

    def toGraphViz(self):
        raise NotImplementedError()

# Specialization of Type

class Completion(Type):
    length: int
    within: Optional[List[str]] = None

class Enum(Type):
    values: List[str]

class Choice(Type):
    source: Field
    mode: str

class Record(Type):
    fields: List[Tuple[str,Type,Range]]
