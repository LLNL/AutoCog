
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel

from .vocab import Token
from .actions import Action, Choose, Text, Complete
from ..lm.lm import LM, GreedyLM

import numpy

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

    def decode(self, llm:LM):
        return '' if self.token is None else llm.detokenize([self.token])

    def eval(self, llm:GreedyLM, prompt:str):
        if self.token is not None:
            prompt += self.decode(llm)

        probs = numpy.exp(llm.greedy(prompt))
        if len(self.children) == 0:
            return [ [] ]
        else:
            tails = []
            for tree in self.children.values():
                tree.proba = probs[tree.token]
                tree.cumul = self.cumul * tree.proba
                tails += [ [ ( tree.token, tree.proba ) ] + tail for tail in tree.eval(llm, prompt) ]
            return tails

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
                label = f"{t.decode(llm)}"
            else:
                label = "ROOT"
            dotstr += f'n_{t.id} [label="{label}"];'
            if t.parent is not None:
                dotstr += f'n_{t.parent.id} -> n_{t.id};'
        return dotstr

class FiniteTokenTree(BaseModel):
    text:     str = ''
    token:    List[Token] = []
    probas:   Optional[List[float]] = None
    children: List["FiniteTokenTree"] = []

    id: Optional[int] = None
    parent: Optional["FiniteTokenTree"] = None

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
            dotstr += f'n_{tree.id} [label="{label}"];\n'
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
        print(f"FTA.greedy_rec")
        print(f"  action = {action}")

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
            print(f"action.choices={action.choices}")
            for (text_,tokens_) in action.choices:
                tct.add_tokens(tokens_)
            print(f"tct={tct.toGraphViz(lm)}")

            actions = {}
            if len(action.successors) == 1:
                for (text_,tokens_) in action.choices:
                    actions.update({ text_ : action.successors[0] })
            else:
                for ((text_,tokens_), succ) in zip(action.choices, action.successors):
                    actions.update({ text_ : succ })
            assert len(actions) == len(action.choices)

            tok_probas = tct.eval(lm, text)
            print(f"tok_probas={tok_probas}")

            texts = list(list(zip(*action.choices))[0])
            print(f"texts={texts}")

            trees = []
            for tok_proba in tok_probas:
                (tokens_, probas) = zip(*tok_proba)
                tokens_ = list(tokens_)
                probas = list(probas)
                print(f"tokens_={tokens_}")
                text_ = lm.detokenize(tokens_)
                assert text_ in texts, f"Not found: \"{text_}\""
                tree = FiniteTokenTree(text=text_, tokens=tokens_, probas=probas)
                act = self.actions[actions[text_]]
                tree.children += self.greedy_rec(lm=lm, text=text+text_, tokens=tokens+tokens_, action=act)
                trees.append(tree)
            return trees
        else:
            raise NotImplementedError(f"Case of {action.__class__.__name__} action")

    def greedy(self, lm: LM):
        print(f"FTA.greedy")
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