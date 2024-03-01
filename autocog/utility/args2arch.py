
import os
import sys
import json
import argparse

from ..config import version

from ..arch.architecture import CognitiveArchitecture as CogArch
from ..arch.orchestrator import Serial, Async

from ..sta.syntax import Syntax, syntax_kwargs

def argparser():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--version',  action='version', version=f'AutoCog {version}') # TODO `autocog.version:str=read('VERSION')`

    parser.add_argument('--orch',     help="""Type of orchestrator: `serial` or `async`.""", default='serial')

    parser.add_argument('--gguf',     help="""Load a model from a GGUF file using llama.cpp (and llama-cpp-python)""", default=None)
    parser.add_argument('--gguf-ctx', help="""Context size for GGUF models""", default=4096)
    parser.add_argument('--syntax',   help=f"""One of `{'`, `'.join(syntax_kwargs.keys())}` or a dictionary of the kwargs to initialize a Syntax object (inlined JSON or path to a file). If used more than once, only the first can be string, the next ones must be dictionaries, and later values override the earlier ones.""", default=None, action='append')
    parser.add_argument('--cogs',     help="""Files to load as cog in the architecture, prefix with its identifier else the filename is used. For example, `some/cognitive/mcq.sta` and `my.tool:some/python/tool.py` will load a Structured Thought Automaton as `mcq` and a Python file as `my.tool`.""", action='append')

    parser.add_argument('--command',  help="""Command to be executed by the architecture as a dictionary. `__tag` identify the cog while `__entry` identify the entry point in this cog (defaults to `main`). All other field will be forwarded as keyworded args. Example: `{ "__tag" : "writer", "__entry" : "main", **kwarg }` (inlined JSON or path to a file). Can also provide one or more list of dictionary.""", action='append')

    parser.add_argument('--output',   help="""Directory where results are stored.""", default=os.getcwd())
    parser.add_argument('--prefix',   help="""String to identify this instance of AutoCog""", default='autocog')

    parser.add_argument('--serve',    help="""Whether to launch the flask server.""", action='store_true')
    parser.add_argument('--host',     help="""Host for flask server.""", default='localhost')
    parser.add_argument('--port',     help="""Port for flask server.""", default='5000')
    parser.add_argument('--debug',    help="""Whether to run the flask server in debug mode.""", action='store_true')
    
    return parser

def parse_json(arg):
    if os.path.exists(arg):
        return json.load(open(arg))
    else:
        return json.loads(arg)

def parseargs(argv):
    parser = argparser()
    args = parser.parse_args(argv)

    if args.orch == 'serial':
        Orch = Serial
    elif args.orch == 'async':
        Orch = Async
    else:
        raise Exception(f"Unknown Orchestrator: {args.orch}")

    if args.gguf is not None:
        from autocog.lm import Llama
        lm = Llama(model_path=args.gguf, n_ctx=args.gguf_ctx)
    else:
        from autocog.lm import RLM
        lm = RLM()

    syntax = {}
    if len(args.syntax) > 0:
        if args.syntax[0] in syntax_kwargs:
            syntax.update(syntax_kwargs[args.syntax[0]])
        else:
            syntax.update(parse_json(args.syntax))
        for s in args.syntax[1:]:
            syntax.update(parse_json(s))
    syntax = Syntax(**syntax)

    arch = CogArch(Orch=Orch, lm=lm, syntax=syntax)

    for cog in args.cogs:
        cog = cog.split(':')
        if len(cog) == 2:
            (tag,filepath) = cog
        else:
            filepath = cog
            tag = filepath.split('/')[-1].split('.')[:-1]
        arch.load(tag=tag, filepath=filepath)

    return {
        'arch' : arch,  'serve' : args.serve, 'output' : args.output,
        'host' : args.host, 'port' : int(args.port), 'debug' : args.debug,
        'commands' : None if args.command is None else [ parse_json(cmd) for cmd in args.command ]
    }
