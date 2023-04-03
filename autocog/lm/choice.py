
import numpy
from typing import List

class TokenChoiceTree:
    def __init__(self, llm, token=None, depth=0, parent=None, use_path_length_normalization=True):
        self.llm = llm
        self.token = token
        self.depth = depth
        self.parent = parent # only used for GraphViz
        self.children = {}
        self.proba = None # probability of this token to be produced given its parent. None for the root.
        self.cumul = 1. # probability of this path being taken (product of `causal`). "1." for the root.
        self.use_path_length_normalization = use_path_length_normalization

    def __add(self, sequence:List[int]):
        tok = sequence[0]
        if not tok in self.children:
            self.children.update({ tok : TokenChoiceTree(self.llm, token=tok, depth=self.depth+1, parent=self) })
        tree = self.children[tok]
        return tree if len(sequence) == 1 else tree.__add(sequence[1:])

    def add(self, text:str):
        return self.__add(self.llm.tokenize(text))

    def decode(self):
        return '' if self.token is None else self.llm.detokenize([self.token])

    def eval(self, prompt):
        if self.token is not None:
            prompt += self.decode()

        probs = numpy.exp(self.llm.greedy(prompt))
        for tree in self.children.values():
            tree.proba = probs[tree.token]
            tree.cumul = self.cumul * tree.proba
            tree.eval(prompt)

    def prob(self):
        if self.depth == 0 or self.cumul is None:
            return None
        return numpy.power(self.cumul, 1./self.depth) if self.use_path_length_normalization else self.cumul

    @classmethod
    def run(cls, llm, prompt, texts, **kwargs):
        tree = cls(llm, **kwargs)
        leaves = [ tree.add(t) for t in texts ]
        tree.eval(prompt)
        return (tree, [ l.prob() for l in leaves ])

    @classmethod
    def choose(cls, llm, prompt, texts, **kwargs):
        return numpy.argmax(cls.run(llm, prompt, texts, **kwargs)[1])

    def depthfirst(self):
        yield self
        for c in self.children.values():
            yield from c.depthfirst()

    def toGraphViz(self):
        cnt = 0
        dotstr = ""
        for t in self.depthfirst():
            t.id = cnt
            cnt += 1
            if t.parent is not None:
                label = f"{t.decode()}\\n{int(t.prob()*10e12)/10e6}"
            else:
                label = "ROOT"
            dotstr += f'n_{t.id} [label="{label}"];'
            if t.parent is not None:
                dotstr += f'n_{t.parent.id} -> n_{t.id};'
        return dotstr
