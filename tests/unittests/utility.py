from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from io import StringIO

from autocog import CogArch
from autocog.tools.tool import Tool

from autocog.architecture.utility import PromptOut

class DataSource(Tool):
    data: Any

    async def __call__(self):
        return self.data

class IterTextSource(Tool):
    text: str = '{c}'
    counter: int = 0

    def reset(self):
        super().reset()
        self.counter = 0

    async def __call__(self):
        text = self.text.format(c=self.counter)
        self.counter += 1
        return text

async def run_sample(arch:CogArch, sample:str, **inputs):
    # TODO PromptOut -> structured capture that matches stacks
    arch.orchestrator.pipe = PromptOut(prefix=sample, output=StringIO())
    arch.reset()
    res = await arch(sample, **inputs)
    return {
        'sample' : sample,
        'inputs' : inputs,
        'output' : res[0],
        'prompts' : arch.orchestrator.pipe.output.getvalue(),
        'exectrace' : None # from stacks to list of (stm.tag + st.content + st.counts)
    }

def print_sample(arch:CogArch, sample:str, inputs, output, prompts, exectrace):
    print(f"sample={sample}")
    print(f"inputs={inputs}")
    print(f"output={output}")
    print(f"prompts={prompts}")
    print(f"exectrace={exectrace}")

def print_results(arch, results):
    for result in results:
        print_sample(arch, **result)