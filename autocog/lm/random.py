
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from .lm import LM

import numpy

class RLM(LM):
    vocab: List[str]
    rvocab: Dict[str, int]

    def __init__(self, **kwargs):
        vocab = [ chr(c) for c in range(ord(' '), ord('~')) ] + [ '\n' ]
        rvocab = { c : i for (i,c) in  enumerate(vocab) }
        super().__init__(model=None, vocab=vocab, rvocab=rvocab, **kwargs)

    def tokenize(self, text:str, whole:bool=True) -> List[int]:
        return [ self.rvocab[c] for c in text ]

    def detokenize(self, tokens:List[int], whole:bool=True) -> str:
        return ''.join([ self.vocab[i] for i in tokens ])

    def impl_greedy(self, prompt: str):
        probas = numpy.random.rand(len(self.vocab))
        return numpy.log(probas / probas.sum())
