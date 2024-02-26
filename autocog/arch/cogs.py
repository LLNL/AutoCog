from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from pydantic import BaseModel
from abc import abstractmethod

from ..sta.ir import Program
from ..sta.automaton import Automaton as STA
from ..sta.runtime import Frame

class Cog(BaseModel):
    tag: str

    def reset(self):
        pass

    @abstractmethod
    async def __call__(self, **inputs) -> Tuple[Any,Any]:
        pass

class Automaton(Cog):
    arch: "CogArch"
    program: Program
    prompts: Dict[str,STA]

    async def __call__(self, fid:Optional[int]=None, **inputs) -> Tuple[Any,Any]:
        stacks = {}
        ptag = 'main'
        while True:
            if not ptag in stacks:
                stacks.update({ ptag : [] })

            sta = self.prompts[ptag]
            fta = sta.instantiate(syntax=self.arch.syntax, stacks=stacks, inputs=inputs)
            fta.simplify()
            ftt = fta.greedy(lm=self.arch.lm)
            text = ftt.best()[0]
            (next, result) = sta.parse(syntax=self.arch.syntax, stacks=stacks, text=text)
            if next is None:
                return result
            else:
                ptag = next

        raise Exception("Should be unreachable!!!")
