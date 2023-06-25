
import os, sys, json
import asyncio
import argparse

try:
    import flask
except:
    flask = None

from autocog import CogArch
from autocog.architecture.utility import PromptTee

import autocog.lm

def argparser():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--version',  action='version', version=f'AutoCog v0.1.0') # TODO `autocog.version:str=read('VERSION')`

    parser.add_argument('--lm',       action='append', help="""Inlined JSON or path to a JSON file: `{ 'text' : { 'cls' : "OpenAI", ... } }` see TODO for details.""")
    parser.add_argument('--program',  action='append', help="""Inlined JSON or path to a JSON file: `{ 'writer' : { 'filepath' : './library/writer/simple.sta', ... } }` see TODO for details.""")
    parser.add_argument('--tool',     action='append', help="""Inlined JSON or path to a JSON file: `{ 'search' : { 'cls' : "SerpApi", ... } }` see TODO for details.""")

    parser.add_argument('--prefix',   help="""String to identify this instance of AutoCog (used when displaying and saving the prompts)""", default='autocog')
    parser.add_argument('--tee',      help="""Filepath or `stdout` or `stderr`. If present, prompts will be append to that file as they are executed.""")
    parser.add_argument('--fmt',      help="""Format string used to save individual prompts to files. If present but empty (or `default`), `results/{p}/{c}/{t}-{i}.txt` is used. `p` is the prefix. `c` is the sequence id of the call. `t` is the prompt name. `i` is the prompt sequence id. WARNING! This will change as the schema is obsolete!""")

    parser.add_argument('--host',     help="""Host for flask server.""", default='localhost')
    parser.add_argument('--port',     help="""Port for flask server.""", default='5000')
    parser.add_argument('--debug',    help="""Whether to run the flask server in debug mode.""", action='store_true')


    parser.add_argument('--command',  action='append', help="""Inlined JSON or path to a JSON file: `{ 'callee' : 'writer',  ... }` see TODO for details.""")
    parser.add_argument('--opath',    help="""If present, JSON outputs of the commands will be stored in that file. If missing, they are written to stdout.""")
    
    return parser

def parseargs(argv):
    parser = argparser()
    args = parser.parse_args(argv)
    
    LMs = {}
    if args.lm is not None:
        for lm in args.lm:
            LMs.update(lm)
    programs = {}
    if args.program is not None:
        for prog in args.program:
            programs.update(prog)
    tools = {}
    if args.tool is not None:
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

    return {
        'arch' : CogArch(pipe=PromptTee(**pipe_kwargs)), 'opath' : args.opath,
        'LMs' : LMs, 'programs' : programs, 'tools' : tools, 'commands' : args.command,
        'flask_host' : args.host, 'flask_port' : int(args.port), 'flask_debug' : args.debug
    }

def autocog_server_index():
    return 'hello world !!!'

def autocog_server_register():
    raise NotImplementedError() # TODO register a tool

def autocog_server_load():
    raise NotImplementedError() # TODO load a program

def autocog_server_execute():
    raise NotImplementedError() # TODO execute a `cog`

# TODO method of CogArch?
async def run(arch, LMs, programs, tools, commands, opath, flask_host, flask_port, flask_debug):
    for fmt in list(LMs.keys()):
        desc = LMs[fmt]
        cls = desc["cls"]
        if cls in autocog.lm.__dict__:
            cls = autocog.lm.__dict__[cls]
        del desc["cls"]
        LMs.update({ fmt : cls(**desc) })
    arch.orchestrator.LMs.update(LMs)

    for (tag,program) in programs.items():
        arch.load(tag=tag, **program)

    for (tag,tool) in tools.items():
        raise NotImplementedError()

    if commands is not None:
        res = await asyncio.gather(*[
            arch(tag, **inputs)
            for (tag,inputs) in commands
        ])

        if opath is None:
            print(json.dumps(res, indent=4))
        else:
            with open(opath,'w') as F:
                json.dump(res, F, indent=4)
    else:
        app = flask.Flask(__name__, template_folder=os.path.realpath('share/webapp')) # TODO install ressources with pip
        app.add_url_rule('/',         view_func=autocog_server_index)
        app.add_url_rule('/register', view_func=autocog_server_register)
        app.add_url_rule('/load',     view_func=autocog_server_load)
        app.add_url_rule('/execute',  view_func=autocog_server_execute)
        app.run(host=flask_host, port=flask_port, debug=flask_debug)

if __name__ == "__main__":
    asyncio.run(run(**parseargs(argv=sys.argv[1:])))