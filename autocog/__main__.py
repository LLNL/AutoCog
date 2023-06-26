
import sys
import json
import asyncio

from .utility.server import serve
from .utility.args2arch import parseargs

async def run(arch, commands):
    return await asyncio.gather(*[
        arch(tag, **inputs)
        for (tag,inputs) in commands
    ])

def main(arch, commands, opath, flask_host, flask_port, flask_debug):
    if commands is None:
        serve(arch, host=flask_host, port=flask_port, debug=flask_debug)
    else:
        res = asyncio.run(run(arch, commands))
        if opath is None:
            print(json.dumps(res, indent=4))
        else:
            with open(opath,'w') as F:
                json.dump(res, F, indent=4)

if __name__ == "__main__":
    main(**parseargs(argv=sys.argv[1:]))