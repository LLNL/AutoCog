
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from pydantic import BaseModel

from .vocab import Token
from .utils import depthfirst

from ..lm.lm import LM

import numpy

class TokenChoiceTree:
    def __init__(self, token=None, depth=0):
        self.token = token
        self.depth = depth
        self.children = {}
        self.proba = None

    def add_tokens(self, sequence:List[int]):
        tok = sequence[0]
        if not tok in self.children:
            self.children.update({ tok : TokenChoiceTree(token=tok, depth=self.depth+1) })
        tree = self.children[tok]
        return tree if len(sequence) == 1 else tree.add_tokens(sequence[1:])

    def eval(self, lm:LM, prompt:List[Token]):
        if len(self.children) == 0:
            return [ [] ]
        else:
            probs = numpy.exp(lm.greedy(prompt))

            results = []
            for tree in self.children.values():
                head = [ ( tree.token, probs[tree.token] ) ]
                tails = tree.eval(lm, prompt+[tree.token])
                results += [ head + tail for tail in tails ]
            return results

    def toGraphViz(self, lm):
        assert self.token is None, "Should be called on the root"
        cnt = 0
        dotstr = ""
        for t in depthfirst(self):
            t.id = cnt
            cnt += 1
            if t.parent is not None:
                label = f"{t.decode(lm)}"
            else:
                label = "ROOT"
            dotstr += f'n_{t.id} [label="{label}"];'
            if t.parent is not None:
                dotstr += f'n_{t.parent.id} -> n_{t.id};'
        return dotstr
