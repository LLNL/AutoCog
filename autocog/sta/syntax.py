
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable, Union
from abc import abstractmethod
from pydantic import BaseModel

from .ir import Prompt, Completion, Enum, Choice

from ..fta.automaton import FiniteThoughtAutomaton as FTA
from ..fta.actions import Choose, Complete, Text

def field_path_from_stack(fields, stack):
    res = []
    for (fid,fcnt) in stack:
        step = f"{fields[fid].name}"
        if fcnt is not None:
            step += f"[{fcnt}]"
        res.append(step)
    return '.'.join(res)

syntax_kwargs = {
    'Llama-2-Chat' : {
        'header_pre'  : '[INST] <<SYS>>\n',
        'header_mid'  : '\n<</SYS>>\n',
        'header_post' : '\n[/INST]\n'
    },
    'Guanaco' : {
        'header_pre'  : '### Human: ',
        'header_mid'  : '\n',
        'header_post' : '\n### Assistant:\n'
    },
    'ChatML' : {
        'header_pre'  : '<|im_start|>system\n',
        'header_mid'  : '<|im_end|>\n<|im_start|>user\n',
        'header_post' : '<|im_end|>\n<|im_start|>assistant\n'
    }
}

class Syntax(BaseModel):
    header_mechanic: str = "You are using the following syntax:"
    header_formats:  str = "It includes the folowing named formats:"
    format_listing:  str = "- "
    prompt_indent:   str = "> "

    system_msg:  str = 'You are an AI expert interacting with your environment using a set of interactive questionnaires.'
    header_pre:  str = ''
    header_mid:  str = '\n'
    header_post: str = '\n'

    prompt_with_format: bool = True
    prompt_with_index:  bool = True
    prompt_zero_index:  bool = False
    
    @staticmethod
    def Llama2Chat(**kwargs):
        kwargs.update(syntax_kwargs['Llama-2-Chat'])
        return Syntax(**kwargs)

    @staticmethod
    def Guanaco(**kwargs):
        kwargs.update(syntax_kwargs['Guanaco'])
        return Syntax(**kwargs)

    @staticmethod
    def ChatML(**kwargs):
        kwargs.update(syntax_kwargs['ChatML'])
        return Syntax(**kwargs)

    def header(self, prompt: Prompt):
        header = prompt.header(
            mech=self.header_mechanic,
            indent=self.prompt_indent,
            fmt=self.header_formats,
            lst=self.format_listing
        )
        return self.header_pre + self.system_msg + self.header_mid + header + self.header_post + 'start:\n'
