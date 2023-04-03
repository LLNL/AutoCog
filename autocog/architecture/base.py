from typing import Any, Dict, List, Tuple, Union, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel
import asyncio

import os, sys, json, copy, pathlib

from ..cogs import Cog
from .orchestrator import Orchestrator, Sequential as SeqOrch

from ..automatons.sta.automaton import StructuredThoughtAutomaton as STA

class CognitiveArchitecture(BaseModel):
    orchestrator: Orchestrator
    cogs: Dict[str,Cog] = {}

    def __init__(self, Orch=SeqOrch, **kwargs):
        super().__init__(orchestrator=Orch(**kwargs))

    def reset(self):
        for cog in self.cogs.values():
            cog.reset()

    def register(self, cog:Cog):
        self.cogs.update({cog.tag:cog})
        self.orchestrator.cogs.update({cog.tag:cog})

    def load(self, tag:str, filepath:str, **kwargs):
        if filepath.endswith('.sta'):
            with open(filepath, 'r') as F:
                program = F.read()
            (program,config) = STA.parse(program=program, **kwargs)
            cog = STA.compile(tag=tag, config=config, orchestrator=self.orchestrator, **program)
        else:
            raise Exception(f"Unrecognized file extension: {filepath}")
        self.register(cog)
        return cog
    
    def __call__(self, tag:str, **inputs):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # 'RuntimeError: There is no current event loop...'
            loop = None

        if loop and loop.is_running():
            return self.orchestrator.job(tag, inputs)
        else:
            return asyncio.run(self.orchestrator.job(tag, inputs))

    def toGraphViz(self):
        dotstr = ''
        for (tag,cog) in self.cogs.items():
            if isinstance(cog, STA):
                dotstr += "subgraph cluster_sta_" + tag.replace('-','_') + " {\n"
                dotstr += cog.toGraphViz() + "\n"
                dotstr += "}\n"
        return dotstr
