
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel

from .vocab import Token, Vocab
from .actions import Action, Choose, Text, Complete
from ..lm.lm import LM

import numpy

class TokenChoiceTree:
    def __init__(self, token=None, depth=0, parent=None):
        self.token = token
        self.depth = depth
        self.parent = parent # only used for GraphViz
        self.children = {}
        self.proba = None

    def add_tokens(self, sequence:List[int]):
        tok = sequence[0]
        if not tok in self.children:
            self.children.update({ tok : TokenChoiceTree(token=tok, depth=self.depth+1, parent=self) })
        tree = self.children[tok]
        return tree if len(sequence) == 1 else tree.add_tokens(sequence[1:])

    def decode(self, lm:LM):
        return '' if self.token is None else lm.detokenize([self.token])

    def eval(self, lm:LM, prompt:str):
        if self.token is not None:
            prompt += self.decode(lm)

        probs = numpy.exp(lm.greedy(prompt))
        if len(self.children) == 0:
            return [ [] ]
        else:
            tails = []
            for tree in self.children.values():
                tree.proba = probs[tree.token]
                tails += [ [ ( tree.token, tree.proba ) ] + tail for tail in tree.eval(lm, prompt) ]
            return tails

    def depthfirst(self):
        yield self
        for c in self.children.values():
            yield from c.depthfirst()

    def toGraphViz(self, lm):
        cnt = 0
        dotstr = ""
        for t in self.depthfirst():
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

class TokenBeamTree:
    def __init__(self, token=None, depth=0, parent=None):
        self.token = token
        self.depth = depth
        self.parent = parent # only used for GraphViz
        self.children = {}
        self.proba = None

    @staticmethod
    def search(lm: LM, text: str, tokens: List[Token], vocab:Vocab, stops:List[str], length: int, beams: int, ahead: int):
        assert beams == 1
        assert ahead == 1
        assert vocab.bounds is None

        new_tokens = []
        probas = []
        full_text = lm.detokenize(tokens)
        while not any([ full_text.endswith(stop) for stop in stops ]) and len(new_tokens) < length:
            prob = numpy.exp(lm.greedy(full_text))
            new_token = numpy.argmax(prob)
            probas.append(prob[new_token])
            new_tokens.append(new_token)
            full_text = lm.detokenize(tokens + new_tokens)

        return [ ( full_text[len(text):], new_tokens, probas ) ]

class FiniteTokenTree(BaseModel):
    text:     str = ''
    tokens:   List[Token] = []
    probas:   Optional[List[float]] = None
    children: List["FiniteTokenTree"] = []

    id: Optional[int] = None
    parent: Optional["FiniteTokenTree"] = None

    def collect(self, text: str = '', tokens: List[Token] = [], probas:List[float] = []):
        if len(self.children) == 0:
            return [ (text, tokens, probas) ]
        results = []
        for child in self.children:
            results += child.collect(
                text=text+self.text,
                tokens=tokens+self.tokens,
                probas=probas if self.probas is None else probas + self.probas
            )
        return results

    def best(self):
        return list(sorted([ (text, tokens, probas, numpy.prod(probas)) for (text,tokens,probas) in self.collect() ], key=lambda x: x[3] ))[-1]

    def depthfirst(self):
        yield self
        for c in self.children:
            c.parent = self
            yield from c.depthfirst()
    
    def toGraphViz(self):
        import json
        cnt = 0
        dotstr = ""
        for tree in self.depthfirst():
            tree.id = cnt
            cnt += 1
            label = json.dumps(tree.text.replace(r'\n',r'\l'))[1:-1]
            # dotstr += f'n_{tree.id}' + ' [shape=record, label="{{' + label + '|' + str(tree.probas) + '}}"];\n'
            dotstr += f'n_{tree.id} [label="{label}\\n{numpy.prod(tree.probas)}"];\n'
            if tree.parent is not None:
                dotstr += f'n_{tree.parent.id} -> n_{tree.id};\n'
        return dotstr

class FiniteThoughtAutomaton(BaseModel):
    actions: Dict[str,Action] = {}

    def create(self, cls, **action):
        act = cls(**action)
        self.actions.update({ act.uid : act })
        return act

    def connect(self, src:str, tgt:str):
        assert src in self.actions
        assert tgt in self.actions
        self.actions[src].successors.append(tgt)

    def simplify(self):
        pass # TODO concatenate chains of text-actions: need predecessors map

    def greedy_rec(self, lm:LM, text:str, tokens:List[Token], action:Action):
        if isinstance(action, Text):
            tree = FiniteTokenTree(text=action.text, tokens=action.tokens)
            if len(action.successors) == 1:
                act = self.actions[action.successors[0]]
                tree.children += self.greedy_rec(lm=lm, text=text+action.text, tokens=tokens+action.tokens, action=act)
            else:
                assert len(action.successors) == 0
            return [ tree ]
        elif isinstance(action, Choose):
            tct = TokenChoiceTree()
            for (text_,tokens_) in action.choices:
                tct.add_tokens(tokens_)

            actions = {}
            if len(action.successors) == 1:
                for (text_,tokens_) in action.choices:
                    actions.update({ text_ : action.successors[0] })
            else:
                for ((text_,tokens_), succ) in zip(action.choices, action.successors):
                    actions.update({ text_ : succ })
            assert len(actions) == len(action.choices)

            tok_probas = tct.eval(lm, text)
            texts = list(list(zip(*action.choices))[0])

            trees = []
            for tok_proba in tok_probas:
                (tokens_, probas) = zip(*tok_proba)
                tokens_ = list(tokens_)
                probas = list(probas)
                text_ = lm.detokenize(tokens_)
                assert text_ in texts, f"Not found: \"{text_}\""
                tree = FiniteTokenTree(text=text_, tokens=tokens_, probas=probas)
                act = self.actions[actions[text_]]
                tree.children += self.greedy_rec(lm=lm, text=text+text_, tokens=tokens+tokens_, action=act)
                trees.append(tree)
            return trees
        elif isinstance(action, Complete):
            trees = []
            for (new_text, new_tokens, probas) in TokenBeamTree.search(lm, text, tokens, action.vocab, action.stops, action.length, action.beams, action.ahead):
                tree = FiniteTokenTree(text=new_text, tokens=new_tokens, probas=probas)
                if len(action.successors) == 1:
                    act = self.actions[action.successors[0]]
                    tree.children += self.greedy_rec(lm=lm, text=text+new_text, tokens=tokens+new_tokens, action=act)
                else:
                    assert len(action.successors) == 0
                trees.append(tree)
            return trees
        else:
            raise NotImplementedError(f"Case of {action.__class__.__name__} action")

    def greedy(self, lm: LM):
        for action in self.actions.values():
            action.prepare(lm)
        branches = self.greedy_rec(lm=lm, text='', tokens=[], action=self.actions['root'])
        assert len(branches) > 0
        if len(branches) == 1:
            return branches[0]
        else:
            return FiniteTokenTree(children=branches)

    def toGraphViz(self, label_with_uid:bool=False):
        dotstr = ""
        for act in self.actions.values():
            dotstr += act.toGraphVizNode(label_with_uid=label_with_uid) + '\n'
        for act in self.actions.values():
            stags = list(set([ None if s is None else self.actions[s].toGraphVizTag() for s in act.successors ]))
            if len(stags) == 1:
                if stags[0] is None:
                    dotstr += f'  {act.toGraphVizTag()} -> {act.toGraphVizTag()}_end [label="*"];\n'
                else:
                    dotstr += f'  {act.toGraphVizTag()} -> {stags[0]} [label="*"];\n'
            elif len(stags) > 1:
                assert isinstance(act, Choose)
                assert not None in stags
                assert len(stags) == len(act.choices), f"action={act}"
                for (stag,(text,toks)) in zip([ self.actions[s].toGraphVizTag() for s in act.successors ],act.choices):
                    dotstr += f'  {act.toGraphVizTag()} -> {stag} [label="{text}"];\n'
            # else:
            #     dotstr += f'  {act.toGraphVizTag()} -> {act.toGraphVizTag()}_end [label="*"];\n'
        return dotstr
