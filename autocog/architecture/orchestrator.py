from typing import Any, Dict, List, Tuple, Union, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel
import uuid
import asyncio

from ..cogs import Cog
from ..lm.lm import LM
from ..automatons.base import Automaton
from ..automatons.machine import StateMachine, Instance
from .utility import PromptPipe

class Frame(BaseModel):
    pid:     Optional[int] = None
    ctag:    Optional[str] = None
    stacks:  Any           = None
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
            frame.stacks = result[1]
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
    async def execute(self, jobs:List[Tuple[str,Any]], pid:int=0):
        return [ Orchestrator.callback(self, fid, await coro) for (fid, coro) in super().coroframe(jobs, pid) ]

    async def prompt(self, fid:int, machine:StateMachine, instances:Instance, header:str, formats:Dict):
        return [ await coro for coro in super().prompt(fid, machine, instances, header, formats) ]

class Async(Orchestrator):
    async def execute(self, jobs:List[Tuple[str,Any]], pid:int=0):
        (fids, coros) = zip(*[ (fid, coro) for (fid, coro) in super().coroframe(jobs, pid) ])
        results = await asyncio.gather(*coros)
        return [ Orchestrator.callback(self, fid, result) for (fid, result) in zip(fids, results) ]

    async def prompt(self, fid:int, machine:StateMachine, instances:Instance, header:str, formats:Dict):
        return await asyncio.gather(*super().prompt(fid, machine, instances, header, formats))