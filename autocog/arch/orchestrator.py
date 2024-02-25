from typing import Any, Dict, List, Tuple, Union, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel
import uuid
import asyncio

try:
    import tqdm
except:
    tqdm = None

from .cogs import Cog, Automaton
from ..lm.lm import LM
from .utility import PromptPipe

# TODO StateMachine -> FTA ?
#from ..automatons.machine import StateMachine
class StateMachine:
    pass
# TODO Instance -> Frame ?
#from ..automatons.instance import Instance
class Instance:
    pass

class Frame(BaseModel):
    pid:     Optional[int] = None
    ctag:    Optional[str] = None
    stacks:  Optional[Dict[str,Any]] = None
    prompts: Optional[Dict[str,List[str]]] = None
    subs:    List[int]     = []
    
class Orchestrator(BaseModel):
    frames: List[Frame] = []
    LMs: Dict[str,LM] = {}
    pipe: Optional[PromptPipe] = None
    limit: Optional[int] = None
    cogs: Dict[str,Cog] = {}

    def __init__(self, pipe:Optional[PromptPipe]=None):
        super().__init__(pipe=pipe)
        self.frames.append(Frame())

    def job(self, ctag:str, inputs:Any, pid:int=0):
        if not ctag in self.cogs:
            raise Exception(f"No registered Cog for {ctag}")
        cog = self.cogs[ctag]

        fid = len(self.frames)
        self.frames.append(Frame(pid=pid, ctag=ctag))
        self.frames[pid].subs.append(fid)
        if issubclass(cog.__class__, Automaton):
            if not self.pipe is None:
                self.pipe.next()
            return ( fid, cog(fid=fid, **inputs) )
        else:
            return ( fid, cog(**inputs) )

    def coroframe(self, jobs:List[Tuple[str,Any]], pid:int):
        return [ self.job(ctag, inputs, pid) for (ctag, inputs) in jobs ]

    def callback(self, fid, result):
        frame = self.frames[fid]
        if issubclass(self.cogs[frame.ctag].__class__, Automaton):
            frame.stacks = { key : stack if key.startswith('__') else [ st.content for st in stack ] for (key,stack) in  result[1].items() }
            frame.prompts = { key : [ st.header + st.prompt for st in stack ] for (key,stack) in  result[1].items() if not key.startswith('__') }
            return result[0]
        else:
            return result

    @abstractmethod
    def prompt(self, fid:int, machine:StateMachine, instances:List[Instance], header:str, formats:Dict):
        return [ machine.execute(
            instance=instance, LMs=self.LMs, header=header, formats=formats,
            out=None if self.pipe is None else self.pipe.set(tag=machine.tag, idx=idx),
            limit=self.limit,
        ) for (idx, instance) in enumerate(instances) ]

class Serial(Orchestrator):
    async def execute(self, jobs:List[Tuple[str,Any]], pid:int=0, progress:bool=False):
        if progress and tqdm is not None:
            progress = tqdm.tqdm
        else:
            progress = lambda x: x
        return [ ( Orchestrator.callback(self, fid, await coro), fid ) for (fid, coro) in progress(super().coroframe(jobs, pid)) ]

    async def prompt(self, fid:int, machine:StateMachine, instances:Instance, header:str, formats:Dict):
        return [ await coro for coro in super().prompt(fid, machine, instances, header, formats) ]

class Async(Orchestrator):
    async def execute(self, jobs:List[Tuple[str,Any]], pid:int=0, progress:bool=False):
        if progress and tqdm is not None:
            gather = tqdm.asyncio.gather
        else:
            gather = asyncio.gather

        (fids, coros) = zip(*[ (fid, coro) for (fid, coro) in super().coroframe(jobs, pid) ])
        results = await asyncio.gather(*coros)
        return [ ( Orchestrator.callback(self, fid, result), fid ) for (fid, result) in zip(fids, results) ]

    async def prompt(self, fid:int, machine:StateMachine, instances:Instance, header:str, formats:Dict):
        return await asyncio.gather(*super().prompt(fid, machine, instances, header, formats))