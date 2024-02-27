from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from pydantic import BaseModel
from abc import abstractmethod

from ..sta.ir import Program, Return, Control
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
            next = sta.parse(syntax=self.arch.syntax, stacks=stacks, ftt=ftt)
            if isinstance(next, Return):
                frame = stacks[ptag][-1]
                if len(next.fields) == 1 and '_' in next.fields:
                    return frame.read(next.fields['_'])
                else:
                    return { fld : frame.read(path) for (fld,path) in next.fields.items() }
            elif isinstance(next, Control):
                ptag = next.prompt
                raise NotImplementedError("Control flow limits")
            else:
                raise Exception("Unrecognized flow operation")

        raise Exception("Should be unreachable!!!")
