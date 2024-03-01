
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel

from .vocab import Token, Vocab
from .actions import Action, Choose, Text, Complete
from ..lm.lm import LM

import json
import numpy

def depthfirst(tree):
    yield tree
    children = tree.children
    if isinstance(children, dict):
        children = children.values()
    for c in children:
        c.parent = tree
        yield from c.depthfirst()

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

class FiniteTokenTree(BaseModel):
    tokens:   List[Token] = []
    probas:   Optional[List[float]] = None
    children: List["FiniteTokenTree"] = []

    id: Optional[int] = None
    parent: Optional["FiniteTokenTree"] = None

    def collect(self, tokens: List[Token] = [], probas:List[float] = []):
        if len(self.children) == 0:
            return [ (tokens, probas) ]
        results = []
        for child in self.children:
            results += child.collect(
                tokens=tokens+self.tokens,
                probas=probas if self.probas is None else probas + self.probas
            )
        return results

    def results(self, lm, normalized=True):
        if normalized:
            scoring = lambda probas: numpy.power(numpy.prod(probas), 1./len(probas))
        else:
            scoring = lambda probas: numpy.prod(probas)

        results = self.collect()
        results = [ (lm.detokenize(tokens), scoring(probas)) for (tokens,probas) in results ]
        return list(sorted(results, key=lambda x: x[-1] ))

    def toGraphViz(self, lm):
        cnt = 0
        dotstr = ""
        for tree in depthfirst(self):
            tree.id = cnt
            cnt += 1
            label = json.dumps(lm.detokenize(tree.tokens, whole=False).replace(r'\n',r'\l'))[1:-1]
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

    def greedy_rec(self, lm:LM, tokens:List[Token], action:Action):
        if isinstance(action, Text):
            tree = FiniteTokenTree(tokens=action.tokens)
            if len(action.successors) == 1:
                act = self.actions[action.successors[0]]
                tree.children += self.greedy_rec(lm=lm, tokens=tokens+action.tokens, action=act)
            else:
                assert len(action.successors) == 0
            return [ tree ]
        elif isinstance(action, Choose):
            tct = TokenChoiceTree()
            for (text,tokens_) in action.choices:
                tct.add_tokens(tokens_)

            actions = {}
            if len(action.successors) == 1:
                for (text,tokens_) in action.choices:
                    actions.update({ text : action.successors[0] })
            else:
                for ((text,tokens_), succ) in zip(action.choices, action.successors):
                    actions.update({ text : succ })
            assert len(actions) == len(action.choices), f"action={action} actions={actions}"

            tok_probas = tct.eval(lm, tokens)
            choices_as_texts = list(list(zip(*action.choices))[0])

            trees = []
            for tok_proba in tok_probas:
                (tokens_, probas) = zip(*tok_proba)
                tokens_ = list(tokens_)
                probas = list(probas)
                text = lm.detokenize(tokens_, whole=False)
                assert text in choices_as_texts, f"Not found \"{text}\" (from action={action.uid}) in {choices_as_texts}"
                tree = FiniteTokenTree(tokens=tokens_, probas=probas)
                act = self.actions[actions[text]]
                tree.children += self.greedy_rec(lm=lm, tokens=tokens+tokens_, action=act)
                trees.append(tree)
            return trees
        elif isinstance(action, Complete):
            trees = []
            for (new_tokens, probas) in beam_search(lm, tokens, vocab=action.vocab, stop=action.stop, length=action.length, beams=action.beams, ahead=action.ahead):
                tree = FiniteTokenTree(tokens=new_tokens, probas=probas)
                if len(action.successors) == 1:
                    act = self.actions[action.successors[0]]
                    tree.children += self.greedy_rec(lm=lm, tokens=tokens+new_tokens, action=act)
                else:
                    assert len(action.successors) == 0
                trees.append(tree)
            return trees
        else:
            raise NotImplementedError(f"Case of {action.__class__.__name__} action")

    def greedy(self, lm: LM):
        for action in self.actions.values():
            action.prepare(lm)
        branches = self.greedy_rec(lm=lm, tokens=[], action=self.actions['root'])
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
