from typing import Any, Dict, List, Tuple, Union, Optional, NamedTuple
import os, sys, json, copy, pathlib

from pydantic import BaseModel

class PromptPipe(BaseModel):
    prefix: str
    tag: Optional[str] = None
    idx: Optional[int] = None
    cnt: Optional[int] = None

    def next(self):
        if self.cnt is None:
            self.cnt = 0
        else:
            self.cnt += 1

    def set(self, tag, idx):
        assert self.cnt is not None
        self.tag = tag
        self.idx = idx
        return self

    def write(self, text):
        assert self.cnt is not None

class PromptOut(PromptPipe):
    output: Any = None

    def next(self):
        super().next()
        if self.output is not None:
            self.output.write(f'=== {self.prefix}[{self.cnt}] ===\n')

    def set(self, **kwargs):
        res = super().set(**kwargs)
        if self.output is not None:
            self.output.write(f'=== {self.tag}[{self.idx}] ===\n')
        return res

    def write(self, text):
        super().write(text)
        if self.output is not None:
            self.output.write(text)

class PromptTee(PromptPipe):
    fmt: Optional[str] = None
    tee: Optional[Any] = None

    def next(self):
        super().next()
        if self.tee is not None:
            self.tee.write(f'\n\n === {self.prefix}[{self.cnt}] === \n\n')
        if self.fmt is not None:
            path = self.fmt.format(p=self.prefix, c=self.cnt, t=self.tag, i=self.idx)
            pathlib.Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)

    def write(self, text):
        super().write(text)
        if self.tee is not None:
            self.tee.write(text)
        if self.fmt is not None:
            with open(self.fmt.format(p=self.prefix, c=self.cnt, t=self.tag, i=self.idx),'a') as F:
                F.write(text)
