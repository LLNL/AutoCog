
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel

Token = int

class Vocab(BaseModel):
    """An empty Vocab means full vocabulary of the LM"""

    bounds: Optional[Tuple[Token,Token]] = None
    ranges: List[Tuple[Token,int]] = []
    tokstr: Optional[List[str]] = None

    def prepare(self, lm, texts: List[str]):
        tokens : List[Token] = []
        for t in texts:
            tokens += lm.tokenize(t)
        tokens = list(sorted(set(tokens)))
        assert len(tokens) > 1
        self.bounds = (tokens[0], tokens[-1])
        self.tokstr = [ lm.detokenize([t]) for t in tokens ]

        (base,prev) = (tokens[0], tokens[0])
        for tok in tokens[1:]:
            if tok == prev + 1:
                prev += 1
            else:
                self.ranges.append( (base, prev-base+1) )
                prev = tok
        self.ranges.append( (base, prev-base+1) )

    def has(self, tok:Token) -> bool:
        if self.bounds is None:
            return True # No range => full voc
        if tok < self.bounds[0] or tok > self.bounds[1]:
            return False

        for (b,l) in self.ranges:
            if tok >= b and tok < b + l:
                return True
        return False

    def toGraphVizLabel(self):
        return 'FULL' if len(self.ranges) == 0 else ', '.join(self.tokstr)
