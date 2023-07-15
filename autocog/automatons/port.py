
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable
from abc import abstractmethod
from pydantic import BaseModel

import json

from .base import Path
from .instance import Instance

class Port(BaseModel):
    mapped: bool

    @abstractmethod
    def retrieve(self, curr:str, stacks: Dict[str,List[Instance]], idx:int):
        pass

    @staticmethod
    def parse(text:str):
        if text[0] == '!':
            mapped = True
            text = text[1:]
        else:
            mapped = False

        try:
            return Constant(value=json.loads(text), mapped=mapped)
        except:
            pass

        if text[0] == '?':
            return Input(key=Path.parse(text[1:]), mapped=mapped)

        text = text.strip().split('.')
        return Prompt(tag=None if len(text[0]) == 0 else text[0], path=Path.parse(text[1:]), mapped=mapped)

class Constant(Port):
    value: Any

    def retrieve(self, stacks: Dict[str,List[Instance]], curr=None, idx=None):
        return value

class Input(Port):
    key: Path

    def retrieve(self, stacks: Dict[str,Any], curr=None, idx=None):
        return self.key.retrieve(stacks['__inputs__'])

class Prompt(Port):
    tag:  Optional[str]
    path: Path

    def retrieve(self, curr:str, stacks: Dict[str,List[Instance]], idx=-1):
        # print(f"curr={curr}")
        # print(f"ptag={self.tag}")
        stack = stacks[curr if self.tag is None else self.tag]
        if len(stack) == 0 or idx > len(stacks):
            return None
        return self.path.retrieve(stack[idx].content)
        
