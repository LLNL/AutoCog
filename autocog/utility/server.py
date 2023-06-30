
import os,json

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Union, Optional, NamedTuple

try:
    from quart import Quart, render_template, websocket
    from quart_schema import QuartSchema, validate_request, validate_response
except ModuleNotFoundError as e:
    print("You must install `quart` and `quart_schema` to use AutoCog's server")
    raise e

from ..config import version

from .gv2html import gv2svg

app = Quart('autocog',
            static_folder=os.path.realpath('share/webapp/static'), # TODO install ressources with pip
            template_folder=os.path.realpath('share/webapp/templates') # TODO install ressources with pip
           )
QuartSchema(app)

arch = None

@app.route("/")
async def index():
    global arch
    assert arch is not None
    return await render_template("main.html", version=version, arch=arch, json=json, gv2svg=gv2svg)

@dataclass
class RegisterInput:
    tag: str
    cls: str
    kwargs: Dict[str,Any]

@app.post("/api/v0/register")
@validate_request(RegisterInput)
async def api_v0_register(data: RegisterInput):
    global arch
    assert arch is not None
    raise NotImplementedError() # TODO register a tool

@dataclass
class LoadInput:
    tag: str
    filepath: str
    kwargs: Dict[str,Any]

@app.post("/api/v0/load")
@validate_request(LoadInput)
async def api_v0_load(data: LoadInput):
    global arch
    assert arch is not None
    raise NotImplementedError() # TODO load a program

@dataclass
class ExecuteInput:
    tag: str
    inputs: Dict[str,Any]

@app.post("/api/v0/execute")
@validate_request(ExecuteInput)
async def api_v0_execute(data: ExecuteInput):
    global arch
    assert arch is not None
    raise NotImplementedError() # TODO execute a `cog`

def serve(arch_, host='0.0.0.0', port=1001, debug=False):
    global arch
    arch = arch_

    app.run(host=host, port=port, debug=debug)
