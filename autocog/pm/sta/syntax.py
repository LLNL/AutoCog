
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable, Union
from abc import abstractmethod
from pydantic import BaseModel

from .ir import Prompt, Completion, Enum, Choice

from ...fta.automaton import FiniteThoughtAutomaton as FTA
from ...fta.actions import Choose, Complete, Text

def field_path_from_stack(fields, stack):
    res = []
    for (fid,fcnt) in stack:
        step = f"{fields[fid].name}"
        if fcnt is not None:
            step += f"[{fcnt}]"
        res.append(step)
    return '.'.join(res)

class Syntax(BaseModel):
    header_mechanic: str = "You are using the following syntax:"
    header_formats:  str = "It includes the folowing named formats:"
    format_listing:  str = "- "
    prompt_indent:   str = "> "

    header_pre_post: Tuple[str,str] = ('','') # ChatLlama: header_pre_post=('[INST]\n<<SYS>>You are an expert interacting with the world using an interactive prompting system.<</SYS>>','[/INST]')

    def fta(self, prompt: Prompt):
        fta = FTA()
        header = prompt.header(
            mech=self.header_mechanic,
            indent=self.prompt_indent,
            fmt=self.header_formats,
            lst=self.format_listing
        )
        current = fta.create(
            uid='header',
            cls=Text,
            text=self.header_pre_post[0] + header + self.header_pre_post[1] + '\nstart:\n'
        )
        stack_elem = lambda fid: ( fid, None if prompt.fields[fid].range is None else 1  )
        stack = [ stack_elem(0) ]
        preds = []
        while len(stack) > 0:
            (fid,fcnt) = stack[-1]
            field = prompt.fields[fid]

            # print(f"field.depth={field.depth}")
            assert field.depth == len(stack), f"field.name={field.name} field.depth={field.depth} stack={stack}"

            path = field_path_from_stack(prompt.fields, stack)
            # print(f"path={path}")
            
            act_text = fta.create(uid=f'text.{path}', cls=Text, text=field.mechanics(self.prompt_indent))
            act_next = fta.create(uid=f'next.{path}', cls=Text, text='\n')

            if field.format is None:
                act_data = None

            elif isinstance(field.format, Completion):
                act_data = fta.create(uid=f'data.{path}', cls=Complete, length=field.format.length)

            elif isinstance(field.format, Enum) or  isinstance(field.format, Choice):
                choices = field.format.values if isinstance(field.format, Enum) else []
                act_data = fta.create(uid=f'data.{path}', cls=Choose, choices=choices)

            else:
                raise Exception(f"Unexpected: field.format={field.formats}")

            if act_data is None:
                act_text.successors.append(act_next.uid)
            else:
                act_text.successors.append(act_data.uid)
                act_data.successors.append(act_next.uid)

            # TODO case of range[0] == 0 ??
            current.successors.append(act_text.uid)
            current = act_next

            follow = fid + 1
            if follow < len(prompt.fields):
                follow = prompt.fields[follow]
                next_depth = follow.depth-1
                next_stack = stack_elem(fid+1)
            else:
                next_depth = 0
                next_stack = None

            for d in range(field.depth, next_depth, -1):
                (fid_,fcnt_) = stack[-1]
                stack = stack[:-1]
                head = prompt.fields[fid_]
                if head.range is not None:
                    if fcnt_ < head.range[1]:
                        next_stack = (fid_,fcnt_+1)
                        if fcnt_ >= head.range[0]:
                            pass # TODO forward edge
                        break
            if next_stack is not None:
                stack.append(next_stack)

        return fta
