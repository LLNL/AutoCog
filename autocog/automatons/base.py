
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable, Union
from abc import abstractmethod
from pydantic import BaseModel

class Step(BaseModel):
    key: str
    idx: Optional[int] = None

    @staticmethod
    def parse(text:str):
        text = text.split('[')
        key = text[0].strip()
        if len(text) > 1:
            assert text[1][-1] == ']'
            idx = int(text[1][:-1])
        else:
            idx = None
        return Step(key=key, idx=idx)

class Path(BaseModel):
    steps: List[Step] = []

    @staticmethod
    def parse(text:Union[str,List[str]]):
        if isinstance(text,str):
            text = text.split('.')
        return Path(steps=[ Step.parse(t.strip()) for t in text ])
