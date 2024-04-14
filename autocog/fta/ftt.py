
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from pydantic import BaseModel

from .vocab import Token
from .utils import depthfirst

import numpy
import json

fmt_float_or_Nnone = lambda x: 'none' if x is None else '{:.6f}'.format(x)

class FTT_Proba(BaseModel):
    tokens:        List[float] # proba of each token
    tokwise_count: int         # len(tokens) + parent.tokwise_count
    depth:         int = 0     # parent.depth + 1

    # Product of local token's probabilities (this node of the tree)
    local_prod:          Optional[float] # prod(tokens)
    local_prod_norm:     Optional[float] # local_prod^(1/len(token))
    local_proba:         Optional[float] = None # local_prod / sigma(sibling.local_prod)
    local_proba_norm:    Optional[float] = None # local_prod_norm / sigma(sibling.local_prod_norm)

    # Product of all token's probabilities (this path of the tree)
    tokwise_prod:        Optional[float] # local_prod * parent.tokwise_prod
    tokwise_prod_norm:   Optional[float] # tokwise_prod^(1/tokwise_count)
    tokwise_proba:       Optional[float] = None # tokwise_prod / sigma(sibling.tokwise_prod)
    tokwise_proba_norm:  Optional[float] = None # tokwise_prod_norm / sigma(sibling.tokwise_prod_norm)

    # Product of probabilities of each node on the path
    treewise_prod:       Optional[float] = None # local_proba * parent.treewise_prod
    treewise_prod_norm:  Optional[float] = None # treewise_prod ^ (1/depth)
    treewise_proba:      Optional[float] = None # treewise_prod / sigma(sibling.treewise_prod)
    treewise_proba_norm: Optional[float] = None # treewise_prod_norm / sigma(sibling.treewise_prod_norm)

    # Product of normalized probabilities of each node on the path
    treewise_norm_prod:       Optional[float] = None # local_proba_norm * parent.treewise_norm_prod
    treewise_norm_prod_norm:  Optional[float] = None # treewise_norm_prod ^ (1/depth)
    treewise_norm_proba:      Optional[float] = None # treewise_norm_prod / sigma(sibling.treewise_norm_prod)
    treewise_norm_proba_norm: Optional[float] = None # treewise_norm_prod_norm / sigma(sibling.treewise_norm_prod_norm)

    def local_as_str_list(self):
        return [
            fmt_float_or_Nnone(self.local_prod),
            fmt_float_or_Nnone(self.local_prod_norm),
            fmt_float_or_Nnone(self.local_proba),
            fmt_float_or_Nnone(self.local_proba_norm)
        ]

    def token_as_str_list(self):
        return [
            fmt_float_or_Nnone(self.tokwise_prod),
            fmt_float_or_Nnone(self.tokwise_prod_norm),
            fmt_float_or_Nnone(self.tokwise_proba),
            fmt_float_or_Nnone(self.tokwise_proba_norm)
        ]

    def tree_as_str_list(self):
        return [
            fmt_float_or_Nnone(self.treewise_prod),
            fmt_float_or_Nnone(self.treewise_prod_norm),
            fmt_float_or_Nnone(self.treewise_proba),
            fmt_float_or_Nnone(self.treewise_proba_norm)
        ]

    def norm_as_str_list(self):
        return [
            fmt_float_or_Nnone(self.treewise_norm_prod),
            fmt_float_or_Nnone(self.treewise_norm_prod_norm),
            fmt_float_or_Nnone(self.treewise_norm_proba),
            fmt_float_or_Nnone(self.treewise_norm_proba_norm)
        ]
    
    def toGraphVizRecord(self):
        recstr  = "|{ " + str(len(self.tokens)) + " | " + str(self.tokwise_count) + " | " + str(self.depth) + " }"
        recstr += "|{ local | " + " | ".join(self.local_as_str_list()) + " }"
        recstr += "|{ token | " + " | ".join(self.token_as_str_list()) + " }"
        recstr += "|{ tree  | " + " | ".join(self.tree_as_str_list())  + " }"
        recstr += "|{ norm  | " + " | ".join(self.norm_as_str_list())  + " }"
        return recstr

    @staticmethod
    def scoring(normalized=True, tokwise=True, proba=False):
        if proba:
            if normalized:
                if tokwise:
                    return lambda proba: proba.tokwise_proba_norm
                else:
                    return lambda proba: proba.treewise_proba_norm
            else:
                if tokwise:
                    return lambda proba: proba.tokwise_proba
                else:
                    return lambda proba: proba.treewise_roba
        else:
            if normalized:
                if tokwise:
                    return lambda proba: proba.tokwise_prod_norm
                else:
                    return lambda proba: proba.treewise_prod_norm
            else:
                if tokwise:
                    return lambda proba: proba.tokwise_prod
                else:
                    return lambda proba: proba.treewise_prod
    
    def __init__(self, tokens:List[float], parent:"FiniteTokenTree"):

        local_prod      = numpy.prod(tokens) if len(tokens) > 0 else 1.
        local_prod_norm = numpy.prod(numpy.power(tokens, 1./len(tokens))) if len(tokens) > 0 else 1.

        if parent.probas is None:
            depth = 0
            tokwise_count = len(tokens)
            tokwise_prod = local_prod
            tokwise_prod_norm = local_prod
        else:
            depth = parent.probas.depth + 1
            tokwise_count = len(tokens) + parent.probas.tokwise_count
            tokwise_prod = local_prod * parent.probas.tokwise_prod
            tokwise_prod_norm = numpy.power(tokwise_prod, 1./tokwise_count)

        super().__init__(
            tokens=tokens, tokwise_count=tokwise_count, depth=depth,
            local_prod=local_prod, local_prod_norm=local_prod_norm,
            tokwise_prod=tokwise_prod, tokwise_prod_norm=tokwise_prod_norm
        )

class FiniteTokenTree(BaseModel):
    tokens:   List[Token]
    probas:   Optional[FTT_Proba]
    children: List["FiniteTokenTree"] = []

    parent: Optional["FiniteTokenTree"] = None

    id: Optional[int] = None
    finalized: bool = False

    def __init__(self, tokens:List[Token], probas:Optional[List[float]]=None, parent: Optional["FiniteTokenTree"] = None):
        if len(tokens) > 0:
            assert parent is not None
            if probas is None:
                probas = FTT_Proba(tokens=[1.] * len(tokens), parent=parent)
            else:
                probas = FTT_Proba(tokens=probas, parent=parent)
        elif parent is not None:
            probas = FTT_Proba(tokens=[], parent=parent)
        else:
            assert parent is None
            assert probas is None
        super().__init__(tokens=tokens, probas=probas, parent=parent)

    @staticmethod
    def root():
        return FiniteTokenTree(tokens=[])

    def append(self, child):
        assert not self.finalized
        assert isinstance(child, FiniteTokenTree)
        self.children.append(child)

    def finalize(self):
        sum_local_prod = 0.
        sum_local_prod_norm = 0.
        sum_tokwise_prod = 0.
        sum_tokwise_prod_norm = 0.
        for child in self.children:
            assert child.parent is self
            sum_local_prod        += child.probas.local_prod
            sum_local_prod_norm   += child.probas.local_prod_norm
            sum_tokwise_prod      += child.probas.tokwise_prod
            sum_tokwise_prod_norm += child.probas.tokwise_prod_norm
        for child in self.children:
            child.probas.local_proba        = child.probas.local_prod        / sum_local_prod
            child.probas.local_proba_norm   = child.probas.local_prod_norm   / sum_local_prod_norm
            child.probas.tokwise_proba      = (child.probas.tokwise_prod      / sum_tokwise_prod     ) if sum_tokwise_prod > 0      else None
            child.probas.tokwise_proba_norm = (child.probas.tokwise_prod_norm / sum_tokwise_prod_norm) if sum_tokwise_prod_norm > 0 else None
        # TODO treewise_norm_prod
        self.finalized = True

    def collect(self, tokens: List[Token] = []):
        tokens = tokens + self.tokens
        if len(self.children) == 0 and self.finalized:
            return [ (tokens, self.probas) ]

        results = []
        for child in self.children:
            results += child.collect(tokens=tokens)
        return results

    def results(self, lm, **kwargs):
        scoring = FTT_Proba.scoring(**kwargs)

        results = self.collect()
        results = [ (lm.detokenize(tokens), scoring(probas)) for (tokens,probas) in results ]
        return list(sorted(results, key=lambda x: x[-1] ))

    def toGraphViz(self, lm):
        cnt = 0
        dotstr = ""
        for tree in depthfirst(self):
            tree.id = cnt
            cnt += 1
            label = lm.detokenize(tree.tokens, whole=False).strip()
            if len(label) == 0:
                dotstr += f'n_{tree.id}' + '[shape=point];\n'
            else:
                if len(label) > 0 and label[0] == '\n':
                    label = label[1:]
                label = label.replace('<',r'\<').replace('>',r'\>')
                label = label.replace('{',r'\{').replace('}',r'\}')
                label = label.replace('[',r'\[').replace(']',r'\]')
                label = label.replace('"',r'\"')
                label = label.replace('|',r'\|')
                label = label.replace(' ',r'\ ')
                label = label.replace('\t',r'\t')
                label = label.replace('\n',r'\l')
                # label = json.dumps(label.replace(r'\n',r'\l'))[1:-1]
                # label = 'text'
                dotstr += f'n_{tree.id}' + '[shape=record, label="{' + label + '\l|finalized=' + str(tree.finalized) + '\l' + ( "" if tree.probas is None else tree.probas.toGraphVizRecord() ) + '}"];\n'
            if tree.parent is not None:
                dotstr += f'n_{tree.parent.id} -> n_{tree.id};\n'
        return dotstr
