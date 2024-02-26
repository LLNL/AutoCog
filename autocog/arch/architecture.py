from typing import Any, Dict, List, Tuple, Union, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel
import asyncio

import os, sys, json, copy, pathlib

from .cogs import Cog, Automaton
from .orchestrator import Orchestrator, Serial

from ..lm.lm import LM

from ..sta.syntax  import Syntax
from ..sta.compile import compile

class CognitiveArchitecture(BaseModel):
    orchestrator: Orchestrator
    lm: LM
    syntax: Syntax
    cogs: Dict[str,Cog] = {}

    def __init__(self, lm: LM, syntax: Syntax, Orch=Serial, **kwargs):
        super().__init__(orchestrator=Orch(**kwargs), lm=lm, syntax=syntax)

    def reset(self):
        """Reset the state of stateful Cogs. Usefull when testing tools"""
        for cog in self.cogs.values():
            cog.reset()

    def register(self, cog:Cog):
        self.cogs.update({cog.tag:cog})
        self.orchestrator.cogs.update({cog.tag:cog})

    def load(self, tag:str, filepath:Optional[str]=None, program:Optional[str]=None, language:Optional[str]=None, **kwargs):
        if program is None:
            assert filepath is not None
            ext = filepath.split('.')[-1]
            if language is None:
                language = ext
            else:
                assert language == ext
            with open(filepath, 'r') as F:
                program = F.read()
        else:
            assert filepath is None
            if language is None:
                raise Exception("Must specify `language`")

        if language == 'sta':
            cog = compile(arch=self, tag=tag, source=program)
        elif language == 'py':
            raise NotImplementedError(f"Python COG")
        else:
            raise Exception(f"Unrecognized file language: {language}")
        self.register(cog)
        return cog
    
    async def __call__(self, tag:str, **inputs):
        return (await self.orchestrator.execute(jobs=[ (tag,inputs) ], pid=0, progress=False))[0][0]

    async def run(self, commands, progress:bool=True):
        jobs = []
        for cmd in commands:
            tag = cmd['tag']
            del cmd['tag']
            jobs.append( (tag,cmd) )
        return await self.orchestrator.execute(jobs=jobs, pid=0, progress=progress)

    def toGraphViz(self):
        dotstr = ''
        for (tag,cog) in self.cogs.items():
            if isinstance(cog, STA):
                dotstr += "subgraph cluster_sta_" + tag.replace('-','_') + " {\n"
                dotstr += cog.toGraphViz() + "\n"
                dotstr += "}\n"
        return dotstr
