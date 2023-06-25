
import os, sys, json
import asyncio
import argparse

from autocog import CogArch
from autocog.architecture import PromptTee

import autocog.lm

def argparser():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--version',  action='version', version=f'AutoCog v0.1.0') # TODO `autocog.version:str=read('VERSION')`

    parser.add_argument('--prefix',   help="""String to identify this instance of AutoCog (used when displaying and saving the prompts)""")
    parser.add_argument('--tee',      help="""Filepath or `stdout` or `stderr`. If present, prompts will be append to that file as they are executed.""")
    parser.add_argument('--fmt',      help="""Format string used to save individual prompts to files. If present but empty (or `default`), `results/{p}/{c}/{t}-{i}.txt` is used. `p` is the prefix. `c` is the sequence id of the call. `t` is the prompt name. `i` is the prompt sequence id. WARNING! This will change as the schema is obsolete!""")
    parser.add_argument('--opath',    help="""If present, JSON outputs will be stored in that file. If missing, JSON output are written to stdout.""")

    parser.add_argument('--lm',       action='append', help="""Inlined JSON or path to a JSON file: `{ 'text' : { 'cls' : "OpenAI", ... } }` see TODO for details.""")
    parser.add_argument('--program',  action='append', help="""Inlined JSON or path to a JSON file: `{ 'writer' : { 'filepath' : './library/writer/simple.sta', ... } }` see TODO for details.""")
    parser.add_argument('--tool',     action='append', help="""Inlined JSON or path to a JSON file: `{ 'search' : { 'cls' : "SerpApi", ... } }` see TODO for details.""")
    parser.add_argument('--command',  action='append', help="""Inlined JSON or path to a JSON file: `{ 'callee' : 'writer',  ... }` see TODO for details.""")
    
    return parser

def parseargs(args):
    parser = argparser()
    args = parser.parse_args(argv)
    
    LMs = {}
    for lm in args.lm:
        LMs.update(lm)
    programs = {}
    for prog in args.program:
        programs.update(prog)
    tools = {}
    for tool in args.tool:
        tools.update(tool)

    pipe_kwargs = { 'prefix' : args.prefix }
    if args.tee is not None:
        if args.tee == '-':
            pipe_kwargs.update({ 'tee' : sys.stdout })
        else:
            pipe_kwargs.update({ 'tee' : open(args.tee,'w') })

    if args.fmt is not None:
        if args.fmt == '' or args.fmt == 'default':
            pipe_kwargs.update({ 'fmt' : 'results/{p}/{c}/{t}-{i}.txt' })
        else:
            pipe_kwargs.update({ 'fmt' : args.fmt })

    return ({
        'arch' : CogArch(pipe=PromptTee(pipe_kwargs)),
        'LMs' : LMs, 'programs' : programs, 'tools' : tools,'commands' : args.command
    }, args.opath)
    
# TODO method of CogArch?
async def run(arch, LMs, programs, tools, commands):
    for fmt in list(LMs.keys()):
        desc = LMs[fmt]
        cls = desc["cls"]
        if cls in autocog.lm.__dict__:
            cls = autocog.lm.__dict__[cls]
        del desc["cls"]
        LMs.update({ fmt : cls(**desc) })
    arch.orchestrator.LMs.update(LMs)

    for tag in list(programs.keys()):
        arch.load(tag=tag, **programs[tag])

    for tag in list(tools.keys()):
        raise NotImplementedError()

    res = await asyncio.gather(*[
        arch(tag, **inputs)
        for (tag,inputs) in commands
    ])
    return [ r[0] for r in res ]

def main(argv=sys.argv[1:]):
    (kwargs,opath) = parseargs(argv)
    res = asyncio.run(run(**kwargs))
    if output is None:
        print(json.dumps(res, indent=4))
    else:
        with open(opath,'w') as F:
            json.dump(res, F, indent=4)

if __name__ == "__main__":
    main()