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
    libdir: List[str]

    def __init__(self, lm: LM, syntax: Syntax, libdir: List[str]=[], Orch=Serial, **kwargs):
        super().__init__(orchestrator=Orch(**kwargs), lm=lm, syntax=syntax, libdir=libdir)

        installed_libpath = os.path.realpath(os.path.dirname(__file__) + '/../library')
        repository_libpath = os.path.realpath(os.path.dirname(__file__) + '/../../share/library')
        system_libpath = os.path.realpath(os.path.dirname(__file__) + '/../../../../../share/autocog/library')
        # system_libpath = '/usr/local/share/autocog/library'

        if os.path.exists(installed_libpath):
            self.libdir.append(installed_libpath)
        elif os.path.exists(repository_libpath):
            self.libdir.append(repository_libpath)
        elif os.path.exists(system_libpath):
            self.libdir.append(system_libpath)

    def reset(self):
        """Reset the state of stateful Cogs. Usefull when testing tools"""
        for cog in self.orchestrator.cogs.values():
            cog.reset()

    def register(self, cog:Cog):
        self.orchestrator.cogs.update({cog.tag:cog})

    def load(self, tag:str, filepath:Optional[str]=None, program:Optional[str]=None, language:Optional[str]=None, **kwargs):
        if program is None:
            assert filepath is not None
            ext = filepath.split('.')[-1]
            if language is None:
                language = ext
            else:
                assert language == ext
            if filepath.startswith('@'):
                for libdir in self.libdir:
                    if os.path.exists(f"{libdir}/{filepath[1:]}"):
                        filepath = f"{libdir}/{filepath[1:]}"
                        break
                if filepath.startswith('@'):
                    raise Exception(f"Could not find {filepath[1:]} in any the library directories: {','.join(self.libdir)}")
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

    def get_single_cog(self):
        if len(self.orchestrator.cogs) == 0:
            raise Exception('No Cogs registered when one is expected')
        if len(self.orchestrator.cogs) > 1:
            raise Exception('More than one Cogs registered when only one is expected')
        return list(self.orchestrator.cogs.keys())[0]

    async def __call__(self, __tag:Optional[str]=None, __entry:str='main', **inputs):
        if __tag is None:
            __tag = self.get_single_cog()
        return (await self.orchestrator.execute(jobs=[ (__tag,__entry,inputs) ], parent=0, progress=False))[0]

    async def run(self, commands, progress:bool=True):
        jobs = []
        for cmd in commands:
            if '__tag' in cmd:
                tag = cmd['__tag']
                del cmd['__tag']
            else:
                tag = self.get_single_cog()
            if '__entry' in cmd:
                entry = cmd['__entry']
                del cmd['__entry']
            else:
                entry = 'main'
            jobs.append( (tag,entry,cmd) )
        return await self.orchestrator.execute(jobs=jobs, parent=0, progress=progress)

    def toGraphViz(self):
        dotstr = ''
        for (tag,cog) in self.orchestrator.cogs.items():
            if isinstance(cog, STA):
                dotstr += "subgraph cluster_sta_" + tag.replace('-','_') + " {\n"
                dotstr += cog.toGraphViz() + "\n"
                dotstr += "}\n"
        return dotstr
