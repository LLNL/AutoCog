from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from pydantic import BaseModel
from abc import abstractmethod

from ..sta.ir import Program, Return, Control
from ..sta.automaton import Automaton as STA
from ..sta.runtime import Frame

from ..fta.automaton import FiniteThoughtAutomaton as FTA
from ..fta.automaton import FiniteTokenTree as FTT

class Page(BaseModel):
    id:      int
    parent:  Optional[int]
    ctag:    Optional[str]
    entry:   Optional[str]

    subs:    List[int] = []

    @staticmethod
    def root():
        return Page(id=0, parent=None, ctag=None, entry=None)

class AutomatonPage(Page):
    stacks:   Dict[str,List[Frame]]   = {}
    ftas:     Dict[str,List[FTA]]     = {}
    ftts:     Dict[str,List[FTT]]     = {}
    branches: Dict[str,Dict[str,int]] = {}

class Cog(BaseModel):
    tag: str
    arch: "CogArch"

    @abstractmethod
    def page(self, **kwarg):
        pass

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def has(self, entry):
        pass

    @abstractmethod
    async def __call__(self, __page: Page, **inputs) -> Any:
        pass

class Automaton(Cog):
    program: Program
    prompts: Dict[str,STA]

    def page(self, **kwarg):
        return AutomatonPage(ctag=self.tag, **kwarg)

    def reset(self):
        pass

    def has(self, entry):
        return entry in self.prompts

    async def __call__(self, __page: Optional[Page]=None, **inputs) -> Any:
        if __page is None:
            __page = self.arch.orchestrator.page(self)
        assert isinstance(__page, AutomatonPage)
        assert len(__page.stacks) == 0
        assert len(__page.ftas) == 0
        assert len(__page.ftts) == 0
        assert len(__page.branches) == 0
        ptag = __page.entry
        while True:
            sta = self.prompts[ptag]

            if not ptag in __page.branches:
                __page.branches.update({ ptag : {} })
                __page.stacks.update({ ptag : [] })
                __page.ftas.update({ ptag : [] })
                __page.ftts.update({ ptag : [] })

            frame = await sta.assemble(self.arch, __page, inputs)
            fta = sta.instantiate(syntax=self.arch.syntax, frame=frame, branches=__page.branches[ptag], inputs=inputs)
            __page.ftas[ptag].append(fta)
            fta.simplify()
            ftt = fta.greedy(lm=self.arch.lm)
            __page.ftts[ptag].append(ftt)
            next = sta.parse(lm=self.arch.lm, syntax=self.arch.syntax, stacks=__page.stacks, ftt=ftt)
            if isinstance(next, Return):
                if len(next.fields) == 1 and '_' in next.fields:
                    return frame.read(next.fields['_'])
                else:
                    return { fld : frame.read(path) for (fld,path) in next.fields.items() }
            elif isinstance(next, Control):
                if not next.prompt in __page.branches[ptag]:
                    __page.branches[ptag].update({ next.prompt : 1 })
                else:
                    __page.branches[ptag][next.prompt] += 1
                ptag = next.prompt
            else:
                raise Exception("Unrecognized flow operation")

        raise Exception("Should be unreachable!!!")

    def toGraphViz(self):
        dotstr = ''
        for (tag,prompt) in self.prompts:
            dotstr += prompt.toGraphViz_abstract()
        return dotstr
