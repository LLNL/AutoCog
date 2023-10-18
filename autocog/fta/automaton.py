
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel

from .vocab import Token
from .actions import Action, Choose
from ..lm.lm import LM

class FiniteTokenTree(BaseModel):
    token: Optional[Token] = None
    proba:float = 1.
    children: Dict[Token,"FiniteTokenTree"] = {}

class FiniteThoughtAutomaton(BaseModel):
    actions: Dict[str,Action] = {}

    def create(self, cls, **action):
        act = cls(**action)
        self.actions.update({ act.uid : act })
        return act

    def greedy_rec(self, lm:LM, prompt:List[Token], root:FiniteTokenTree, action:Action, step:int=0, **kwargs):
        branches = action.step(lm=lm, step=step, prompt=prompt, **kwargs)
        for (tok,prob) in branches.items():
            tree = FiniteTokenTree(token=tok, proba=prob)
            root.children.update({tok:tree})
            self.greedy_rec(prompt=prompt+[tok], root=tree, action=action, step=step+1, **kwargs)
        if len(branches) == 0:
            aid = action.next(prompt=prompt)
            self.greedy_rec(prompt=prompt, root=root, action=self.actions[aid], step=0, **kwargs)

    def greedy(self, lm: LM, entry:str, header:str='', min_branch:int=2, max_branch:int=5, tok_clip:float=.9):
        header = lm.tokenize(header)
        root = FiniteTokenTree()
        self.greedy_rec(lm=lm, prompt=header, root=root, action=self.actions[entry], min_branch=min_branch, max_branch=max_branch, tok_clip=tok_clip)
        return root

    def toGraphViz(self):
        dotstr = ""
        for act in self.actions.values():
            dotstr += act.toGraphVizNode() + '\n'
        for act in self.actions.values():
            stags = list(set([ None if s is None else self.actions[s].toGraphVizTag() for s in act.successors ]))
            if len(stags) == 1:
                if stags[0] is None:
                    dotstr += f'  {act.toGraphVizTag()} -> {act.toGraphVizTag()}_end [label="*"];\n'
                else:
                    dotstr += f'  {act.toGraphVizTag()} -> {stags[0]} [label="*"];\n'
            elif len(stags) > 1:
                assert isinstance(act, Choose)
                assert len(stags) == len(act.choices)
                for (stag,(text,toks)) in zip(stags,act.choices):
                    dotstr += f'  {act.toGraphVizTag()} -> {stag} [label="{text}"];\n'
            else:
                dotstr += f'  {act.toGraphVizTag()} -> {act.toGraphVizTag()}_end [label="*"];\n'
        return dotstr