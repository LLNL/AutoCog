
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable
from abc import abstractmethod
from pydantic import BaseModel

from .machine import StateMachine
from .base import Step, Path
from .port import Port

class Callee(BaseModel):
    cog: Optional[str] = None
    entry: Optional[str] = None

    @staticmethod
    def parse(text:Optional[str]):
        if text is None:
            return None
        call = text.split('@')
        cog = call[0].strip()
        if len(cog) == 0:
            cog = None
        entry = None
        if len(call) == 2:
            entry = call[1].strip()
            if len(entry) == 0:
                entry = None
        return Callee(cog=cog, entry=entry)

class Channel(BaseModel):
    machine:  StateMachine
    target:   Path
    source:   Optional[Port]
    call:     Optional[Callee]
    kwargs:   Optional[Dict[str,Port]]

    @staticmethod
    def parse(text:str):
        pass # TODO 
    
    def __init__(self, machine, target:str, source:Optional[str]=None, call:Optional[str]=None, kwargs:Dict[str,str]={}):
        super().__init__(
            machine=machine,
            source=None if source is None else Port.parse(source),
            target=Path.parse(target),
            call=Callee.parse(call),
            kwargs={ k : Port.parse(v) for (k,v) in kwargs }
        )