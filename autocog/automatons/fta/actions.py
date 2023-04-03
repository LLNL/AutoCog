
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel

import uuid

from .vocab import Vocab, Token
from ...lm.choice import TokenChoiceTree
from ...lm.local import TokenizerLM

class Action(BaseModel):
    uid: str
    successors: List[str] = []

    def __init__(self, uid:Optional[str]=None, **kwargs):
        if uid is None:
            uid = str(uuid.uuid4())
        super().__init__(uid=uid, **kwargs)

    @abstractmethod
    def step(self, lm, prompt:List[Token], step:int, min_branch:int, max_branch:int, tok_clip:float) -> Dict[Token,float]:
        pass

    @abstractmethod
    def next(self, prompt:List[Token]):
        pass

    def toGraphVizTag(self):
        return 'n_'+self.uid.replace('-','_')

    def toGraphVizNode(self):
        return f'{self.toGraphVizTag()} [label="{self.toGraphVizLabel()}", shape="{self.toGraphVizShape()}"];'

class Text(Action):
    text: str
    tokens: List[Token]

    def __init__(self, tokenizer:TokenizerLM, text:str, **kwargs):
        super().__init__(text=text, tokens=tokenizer.tokenize(text), **kwargs)

    def step(self, lm, prompt:List[Token], step:int, min_branch:int, max_branch:int, tok_clip:float) -> Dict[Token,float]:
        return { self.tokens[step] : 1. } if step < len(self.tokens) else {}

    def next(self, prompt:List[Token]):
        return None if len(self.successors) == 0 else self.successors[0]

    def toGraphVizShape(self):
        return 'rectangle'

    def toGraphVizLabel(self):
        return repr(self.text)

class Choose(Action):
    choices: List[Tuple[str,List[Token]]]

    def __init__(self, tokenizer:TokenizerLM, choices:List[str], **kwargs):
        super().__init__(choices=[ ( c, tokenizer.tokenize(c) ) for c in choices ], **kwargs)

    def step(self, lm, prompt:List[Token], step:int, min_branch:int, max_branch:int, tok_clip:float) -> Dict[Token,float]:
        raise NotImplementedError()

    def next(self, prompt:List[Token]):
        raise NotImplementedError()

    def toGraphVizShape(self):
        return 'diamond'

    def toGraphVizLabel(self):
        return '\n'.join(map(lambda x: repr(x[0]), self.choices))

class Complete(Action):
    vocab: Vocab
    length: int = 1
    stop: Optional[List[Tuple[str,List[Token]]]] = None

    def __init__(self, tokenizer:TokenizerLM, vocab:Optional[Union[Vocab,Dict[str,Any]]]=None, stop: Optional[List[str]] = None, **kwargs):
        if stop is not None:
            stop = [ ( s, tokenizer.tokenize(s) ) for s in stop ]
        if vocab is None:
            vocab = Vocab(tokenizer)
        elif isinstance(vocab,dict):
            vocab = Vocab(tokenizer, **vocab)
        super().__init__(stop=stop, vocab=vocab, **kwargs)

    def step(self, lm, prompt:List[Token], step:int, min_branch:int, max_branch:int, tok_clip:float) -> Dict[Token,float]:
        raise NotImplementedError()

    def next(self, prompt:List[Token]):
        raise NotImplementedError()

    def toGraphVizShape(self):
        return 'ellipse'

    def toGraphVizLabel(self):
        return f"length={self.length}\nvocab={self.vocab.toGraphVizLabel()}\nstop={', '.join(map(lambda x: x[0], self.stop))}\n"
