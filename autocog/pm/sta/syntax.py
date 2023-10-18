
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

            print(f"field.depth={field.depth}")
            assert field.depth == len(stack), f"field.name={field.name} field.depth={field.depth} stack={stack}"

            path = field_path_from_stack(prompt.fields, stack)
            print(f"path={path}")
            
            uid = f'text.{path}'
            text = field.mechanics(self.prompt_indent)
            text = fta.create(uid=uid, cls=Text, text=text)
            current.successors.append(text)

            if field.format is None:
                uid = f'next.{path}'
                next = fta.create(uid=uid, cls=Text, text='\n')
                text.successors.append(next)
                current = next

            elif isinstance(field.format, Completion):
                uid = f'data.{path}'
                data = fta.create(uid=uid, cls=Complete, length=field.format.length)
                text.successors.append(data)
                uid = f'next.{path}'
                next = fta.create(uid=uid, cls=Text, text='\n')
                data.successors.append(next)
                current = next

            elif isinstance(field.format, Enum) or  isinstance(field.format, Choice):
                choices = field.format.values if isinstance(field.format, Enum) else []
                uid = f'data.{path}'
                data = fta.create(uid=uid, cls=Choose, choices=choices)
                text.successors.append(data)
                uid = f'next.{path}'
                next = fta.create(uid=uid, cls=Text, text='\n')
                data.successors.append(next)
                current = next

            else:
                raise Exception(f"Unexpected: field.format={field.formats}")

            follow = fid + 1
            if follow < len(prompt.fields):
                follow = prompt.fields[follow]
                next = stack_elem(fid+1)
                for d in range(field.depth, follow.depth-1, -1):
                    # TODO check if range is NOT complete
                    stack = stack[:-1]
                stack.append(next)
            else:
                stack.clear()
            
        return fta
