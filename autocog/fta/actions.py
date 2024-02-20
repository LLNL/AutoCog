
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel

import uuid
import json

from .vocab import Vocab, Token

class Action(BaseModel):
    uid: str
    successors: List[str] = []

    def __init__(self, uid:Optional[str]=None, **kwargs):
        if uid is None:
            uid = str(uuid.uuid4())
        super().__init__(uid=uid, **kwargs)

    @abstractmethod
    def prepare(self, lm):
        pass

    @abstractmethod
    def step(self, lm, prompt:List[Token], step:int, min_branch:int, max_branch:int, tok_clip:float) -> Dict[Token,float]:
        pass

    @abstractmethod
    def next(self, prompt:List[Token]):
        pass

    def toGraphVizTag(self):
        return 'n_'+self.uid.replace('-','_').replace('.','_').replace('[','_').replace(']','_')

    def toGraphVizNode(self, label_with_uid:bool=False):
        label = self.uid if label_with_uid else self.toGraphVizLabel()
        return f'{self.toGraphVizTag()} [label="{label}", shape="{self.toGraphVizShape()}"];'

class Text(Action):
    text: str
    tokens: List[Token] = []

    def __init__(self, uid:str, text:str, successors: List[str]=[]):
        super().__init__(uid=uid, successors=successors, text=text)

    def prepare(self, lm):
        self.tokens.extend(lm.tokenize(self.text))

    def step(self, lm, prompt:List[Token], step:int, min_branch:int, max_branch:int, tok_clip:float) -> Dict[Token,float]:
        return { self.tokens[step] : 1. } if step < len(self.tokens) else {}

    def next(self, prompt:List[Token]):
        return None if len(self.successors) == 0 else self.successors[0]

    def toGraphVizShape(self):
        return 'rectangle'

    def toGraphVizLabel(self):
        return json.dumps(self.text.replace(r'\n',r'\l'))[1:-1]

class Choose(Action):
    choices: List[Tuple[str,List[Token]]]

    def __init__(self, uid:str, choices:List[str], successors: List[str]=[]):
        super().__init__(uid=uid, successors=successors, choices=[ ( c, [] ) for c in choices ])

    def prepare(self, lm):
        for choice in self.choices:
            choice[1].extend(lm.tokenize(choice[0]))

    def step(self, lm, prompt:List[Token], step:int, min_branch:int, max_branch:int, tok_clip:float) -> Dict[Token,float]:
        raise NotImplementedError(f"Choose.step(prompt={prompt})")

    def next(self, prompt:List[Token]):
        raise NotImplementedError()

    def toGraphVizShape(self):
        return 'diamond'

    def toGraphVizLabel(self):
        return '\n'.join(map(lambda x: repr(x[0]), self.choices))

class Complete(Action):
    length: int = 1
    seeds: Optional[List[str]]
    forbid: Optional[List[str]] = None
    stop: Optional[List[Tuple[str,List[Token]]]] = None
    vocab: Optional[Vocab] = None

    def __init__(self, uid:str, length:int=1, seeds: Optional[List[str]] = None, stop: Optional[List[str]] = None, forbid: Optional[List[str]] = None, successors: List[str]=[]):
        if stop is not None:
            stop = [ ( s, [] ) for s in stop ]
        super().__init__(uid=uid, successors=successors, length=length, forbid=forbid, stop=stop, seeds=seeds)

    def prepare(self, lm):
        raise NotImplementedError()

    def step(self, lm, prompt:List[Token], step:int, min_branch:int, max_branch:int, tok_clip:float) -> Dict[Token,float]:
        raise NotImplementedError()

    def next(self, prompt:List[Token]):
        raise NotImplementedError()

    def toGraphVizShape(self):
        return 'ellipse'

    def toGraphVizLabel(self):
        return f"length={self.length}\nvocab={self.vocab.toGraphVizLabel() if self.vocab is not None else ''}\nstop={'' if self.stop is None else ', '.join(map(lambda x: x[0], self.stop))}\n"
