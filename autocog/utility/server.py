
import os

try:
    from quart import Quart, render_template, websocket
except:
    raise Exception("You must install `quart` to use AutoCog's server")

app = Quart('autocog', template_folder=os.path.realpath('share/webapp')) # TODO install ressources with pip
arch = None

@app.route("/")
async def index():
    return await render_template("index.html", arch=arch)

@app.route("/api/v0/register")
async def api_v0_register():
    raise NotImplementedError() # TODO register a tool

@app.route("/api/v0/load")
async def api_v0_load():
    raise NotImplementedError() # TODO load a program

@app.route("/api/v0/execute")
async def api_v0_execute():
    raise NotImplementedError() # TODO execute a `cog`

def serve(arch_, host='0.0.0.0', port=1001, debug=False):
    global arch
    arch = arch_
    app.run(host=host, port=port, debug=debug)