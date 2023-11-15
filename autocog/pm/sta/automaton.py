
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable, Union
from abc import abstractmethod
from pydantic import BaseModel

from .ir import Prompt as IrPrompt 
from .ir import Field  as IrField

from .syntax import Syntax

from ...fta.automaton import FiniteThoughtAutomaton as FTA
from ...fta.actions import Choose, Complete, Text

class AbstractState(BaseModel):
    field: Optional[IrField] = None

    flow: Optional["AbstractState"] = None
    exit: Optional["AbstractState"] = None

    def depth(self):
        return 0 if self.field is None else self.field.depth
    
    def tag(self):
        if self.field is None:
            return "root"
        else:
            return f"{self.field.name}_{self.field.depth}_{self.field.index}"

class Automaton(BaseModel):
    prompt: IrPrompt
    states: List[AbstractState] = []
    
    def build(self):
        assert len(self.states) == 0
        self.states.append(AbstractState())
        stack: List[List[AbstractState]] = [ [ self.states[0] ] ]

        for fld in self.prompt.fields:

            # for s,stack_ in enumerate(stack):
            #     print(f"> {s}: {' -> '.join(map(lambda st: st.tag(), stack_))}")
            # print(f"field: name={fld.name} depth={fld.depth} index={fld.index}")

            state = AbstractState(field=fld)
            if fld.range is not None:
                state.flow = state
            self.states.append(state)

            prev = stack[-1][-1]
            # print(f"prev: tag={prev.tag()} depth={prev.depth()}")
            if fld.index == 0:
                assert fld.depth == len(stack)
                prev.flow = state
                stack.append([])

            elif fld.depth < prev.depth():
                stack = stack[:fld.depth+1]
                prev.exit = stack[-1][-1]
                stack[-1][-1].exit = state

            else:
                prev.exit = state

            stack[-1].append(state)

        stack[-1][-1].exit = stack[0][0]

        return self

    def instantiate(self, syntax: Syntax, data: Any):
        fta = FTA()

        header = self.prompt.header(
            mech=syntax.header_mechanic,
            indent=syntax.prompt_indent,
            fmt=syntax.header_formats,
            lst=syntax.format_listing
        )

        abstract = self.states[0]
        concrete = fta.create(
            uid=abstract.tag(), cls=Text,
            text=syntax.header_pre_post[0] + header + syntax.header_pre_post[1] + '\nstart:\n'
        )

        return fta
        
    def toGraphViz(self):
        dotstr = ''
        for state in self.states:
            if state.flow is not None:
                constraint = 'true'
                dotstr += f'{state.tag()} -> {state.flow.tag()} [color=green, constraint={constraint}];\n'
            if state.exit is not None:
                constraint = 'false'
                if state.exit.depth() == state.depth():
                    constraint = 'true'
                dotstr += f'{state.tag()} -> {state.exit.tag()} [color=red, constraint={constraint}];\n'
        return dotstr
