
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from pydantic import BaseModel

from .vocab import Token, Vocab

from ..lm.lm import LM

import numpy

def beam_search(lm: LM, tokens: List[Token], vocab:Vocab, stop:Union[str,List[Token]], length: int, beams: int, ahead: int):
    assert beams == 1
    assert ahead == 1
    assert vocab.bounds is None

    if isinstance(stop,str):
        stop = lm.tokenize(stop)
    
    new_tokens = []
    probas = []
    while len(new_tokens) < length:
        prob = numpy.exp(lm.greedy(tokens+new_tokens))

        new_token = numpy.argmax(prob)

        new_tokens.append(new_token)
        probas.append(prob[new_token])

        if new_tokens[-len(stop):] == stop:
            new_tokens = new_tokens[:-len(stop)]
            probas = probas[:-len(stop)]
            break

    return [ ( new_tokens, probas ) ]
