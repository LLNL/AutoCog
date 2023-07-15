
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

    def path(self, idx:bool=False):
        if idx:
            fmt = lambda s: s.key
        else:
            fmt = lambda s: f"{s.key}[{s.idx}]" if s.idx is None else f"{s.key}"
        return '.'.join([ s.key for s in self.steps ])

    def retrieve(self, data:Dict, depth:int=0):
        # print(f"steps={self.steps}")
        # print(f"data={data}")
        # print(f"depth={depth}")
        if depth == len(self.steps):
            return data
        assert isinstance(data,dict)
        step = self.steps[depth]
        if not step.key in data:
            return None
        data = data[step.key]
        if data is None:
            return None
        if step.idx is not None:
            assert isinstance(data,list)
            if step.idx < len(data):
                data = data[step.idx]
            else:
                return None
        return self.retrieve(data,depth+1)
