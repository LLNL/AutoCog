
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel

from .vocab import Token, Vocab
from .actions import Action, Choose, Text, Complete
from .ftt import FTT_Proba, FiniteTokenTree
from .tct import TokenChoiceTree
from .beam import beam_search

from ..lm.lm import LM

import copy
import json
import numpy

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

    def __collect_predeccessors(self, predeccessors: Dict[str,List[str]], cuid:str, pred:str):
        if not cuid in predeccessors:
            predeccessors.update({ cuid : [] })
        if not pred in predeccessors[cuid]:
            predeccessors[cuid].append(pred)

        for succ in self.actions[cuid].successors:
            self.__collect_predeccessors(predeccessors=predeccessors, cuid=succ, pred=cuid)

    def simplify(self):
        predeccessors = {}
        for succ in self.actions['root'].successors:
            self.__collect_predeccessors(predeccessors=predeccessors, cuid=succ, pred='root')

        # Traverse in reverse order so we always move toward the root
        for (cuid, preds) in list(predeccessors.items())[::-1]:
            if len(preds) != 1:
                continue
            curr = self.actions[cuid]
            pred = self.actions[preds[0]]
            if isinstance(pred,Text) and isinstance(curr, Text):
                pred.text += curr.text
                pred.successors.clear()
                pred.successors.extend(curr.successors)
                del self.actions[cuid]

    def greedy_rec(self, ptree:FiniteTokenTree, lm:LM, tokens:List[Token], action:Action):
        if isinstance(action, Text):
            tree = FiniteTokenTree(parent=ptree, tokens=action.tokens)
            if len(action.successors) == 1:
                act = self.actions[action.successors[0]]
                tree.append(self.greedy_rec(ptree=tree, lm=lm, tokens=tokens+action.tokens, action=act))
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
                    actions.update({ text.strip() : action.successors[0] })
            else:
                for ((text,tokens_), succ) in zip(action.choices, action.successors):
                    actions.update({ text.strip() : succ })
            assert len(actions) == 0 or len(actions) == len(action.choices), f"action={action} actions={actions}"

            tok_probas = tct.eval(lm, tokens)
            choices_as_texts = list(list(zip(*action.choices))[0])

            trees = []
            for tok_proba in tok_probas:
                (tokens_, probas) = zip(*tok_proba)
                tokens_ = list(tokens_)
                probas = list(probas)
                tree = FiniteTokenTree(parent=ptree, tokens=tokens_, probas=probas)
                trees.append(tree)
                if len(actions) > 0:
                    text = lm.detokenize(tokens_, whole=False).strip()
                    assert text in actions, f"Not found \"{text}\" (from action={action.uid}) in {','.join(actions.keys())}"
                    act = self.actions[actions[text]]
                    tree.append(self.greedy_rec(ptree=tree, lm=lm, tokens=tokens+tokens_, action=act))
            return trees
        elif isinstance(action, Complete):
            trees = []
            for (new_tokens, probas) in beam_search(lm, tokens, vocab=action.vocab, stop=action.stop, length=action.length, beams=action.beams, ahead=action.ahead):
                tree = FiniteTokenTree(parent=ptree, tokens=new_tokens, probas=probas)
                if len(action.successors) == 1:
                    act = self.actions[action.successors[0]]
                    tree.append(self.greedy_rec(ptree=tree, lm=lm, tokens=tokens+new_tokens, action=act))
                else:
                    assert len(action.successors) == 0
                trees.append(tree)
            return trees
        else:
            raise NotImplementedError(f"Case of {action.__class__.__name__} action")

    def greedy(self, lm: LM):
        for action in self.actions.values():
            action.prepare(lm)
        root = FiniteTokenTree.root()
        root.append(self.greedy_rec(ptree=root, lm=lm, tokens=[], action=self.actions['root']))
        return root

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
