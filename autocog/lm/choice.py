

from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple

import numpy

from .lm import LM, GreedyLM

class TokenChoiceTree:
    def __init__(self, token=None, depth=0, parent=None):
        self.token = token
        self.depth = depth
        self.parent = parent # only used for GraphViz
        self.children = {}
        self.proba = None # probability of this token to be produced given its parent. None for the root.
        self.cumul = 1. # probability of this path being taken (product of `causal`). "1." for the root.

    def add_tokens(self, sequence:List[int]):
        tok = sequence[0]
        if not tok in self.children:
            self.children.update({ tok : TokenChoiceTree(token=tok, depth=self.depth+1, parent=self) })
        tree = self.children[tok]
        return tree if len(sequence) == 1 else tree.add_tokens(sequence[1:])

    def add(self, llm:LM, text:str):
        return self.add_tokens(llm.tokenize(text))

    def decode(self, llm:LM):
        return '' if self.token is None else llm.detokenize([self.token])

    def eval(self, llm:GreedyLM, prompt:str):
        if self.token is not None:
            prompt += self.decode(llm)

        probs = numpy.exp(llm.greedy(prompt))
        tails = []
        for tree in self.children.values():
            tree.proba = probs[tree.token]
            tree.cumul = self.cumul * tree.proba
            tails += [ [ ( tree.token, tree.proba ) ] + tail for tail in tree.eval(llm, prompt) ]
        return tails

    def prob(self, use_path_length_normalization:bool=False):
        if self.depth == 0 or self.cumul is None:
            return None
        return numpy.power(self.cumul, 1./self.depth) if use_path_length_normalization else self.cumul

    @classmethod
    def run(cls, llm:GreedyLM, prompt:str, texts:List[str], use_path_length_normalization:bool=False, **kwargs):
        tree = cls(**kwargs)
        leaves = [ tree.add(llm, t) for t in texts ]
        tree.eval(llm, prompt)
        return (tree, [ l.prob(use_path_length_normalization=use_path_length_normalization) for l in leaves ])

    @classmethod
    def choose(cls, llm:GreedyLM, prompt:str, texts:List[str], **kwargs):
        return numpy.argmax(cls.run(llm, prompt, texts, **kwargs)[1])

    def depthfirst(self):
        yield self
        for c in self.children.values():
            yield from c.depthfirst()

    def toGraphViz(self, llm):
        cnt = 0
        dotstr = ""
        for t in self.depthfirst():
            t.id = cnt
            cnt += 1
            if t.parent is not None:
                label = f"{t.decode(llm)}\\n{int(t.prob()*10e12)/10e6}"
            else:
                label = "ROOT"
            dotstr += f'n_{t.id} [label="{label}"];'
            if t.parent is not None:
                dotstr += f'n_{t.parent.id} -> n_{t.id};'
        return dotstr

class ChoiceLM(GreedyLM):
    use_path_length_normalization:bool=False

    def choose(self, prompt: str, choices: List[str]) -> int:
        return TokenChoiceTree.choose(self, prompt=prompt, texts=choices, use_path_length_normalization=self.use_path_length_normalization)
