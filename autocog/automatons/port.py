
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable
from abc import abstractmethod
from pydantic import BaseModel

import json

from .base import Path

class Port(BaseModel):
    mapped: bool

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

class Input(Port):
    key: Path

class Prompt(Port):
    tag:  Optional[str]
    path: Path
