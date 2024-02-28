from typing import Any, Dict, List, Tuple, Union, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel
import uuid
import asyncio

try:
    import tqdm
except:
    tqdm = None

from .cogs import Cog, Automaton, Page
from ..lm.lm import LM
from .utility import PromptPipe
    
class Orchestrator(BaseModel):
    pages: List[Page]
    cogs: Dict[str,Cog] = {}

    def __init__(self):
        super().__init__(pages=[ Page.root() ])

    def job(self, tag:str, entry:str, inputs:Any, parent:int):
        if not tag in self.cogs:
            raise Exception(f"No registered Cog for {tag}")
        cog = self.cogs[tag]
        assert cog.has(entry)

        pid = len(self.pages)
        page = cog.page(id=pid, parent=parent, entry=entry)
        self.pages.append(page)
        self.pages[parent].subs.append(pid)

        return cog(page, **inputs)

    def coropage(self, jobs:List[Tuple[str,str,Any]], pid:int):
        return [ self.job(tag, entry, inputs, pid) for (tag, entry, inputs) in jobs ]

class Serial(Orchestrator):
    async def execute(self, jobs:List[Tuple[str,Any]], parent:int, progress:bool=False):
        if progress and tqdm is not None:
            progress = tqdm.tqdm
        else:
            progress = lambda x: x

        return [ await coro for coro in progress(super().coropage(jobs, parent)) ]

class Async(Orchestrator):
    async def execute(self, jobs:List[Tuple[str,str,Any]], parent:int, progress:bool=False):
        if progress and tqdm is not None:
            gather = tqdm.asyncio.gather
        else:
            gather = asyncio.gather

        return await gather(*super().coroutines(jobs, parent))
