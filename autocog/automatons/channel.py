
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable
from abc import abstractmethod
from pydantic import BaseModel

from .machine import StateMachine
from .base import Step, Path
from .port import Port

class Callee(BaseModel):
    cog: Optional[str] = None
    entry: Optional[str] = None

class Channel(BaseModel):
    machine:  StateMachine
    target:   Path
    source:   List[Port]
    call:     Optional[Callee]
    kwargs:   Optional[Dict[str,Port]]

    @staticmethod
    def parse(text:str):
        pass # TODO 
    
    def __init__(self, machine, source:str, target:str, call:Optional[str]=None, kwargs:Dict[str,str]={}):
        source = [ Port.parse(s) for s in source.split(',') ]
        target = Path.parse(target)
        
        if call is not None:
            call = call.split('@')
            call = Callee(call[0].strip(), call[1].strip())

        kwargs = { k : Port.parse(v) for (k,v) in kwargs }

        super().__init__(machine=machine, source=source, target=target, call=call, kwargs=kwargs)