
import os
import sys
import json
import asyncio

from .utility.args2arch import parseargs

def main(arch, serve, host, port, debug, commands, output, prefix):
    if os.path.exists(f'{output}/{prefix}-pages.json'):
        pass # TODO load existing pages

    if commands is not None:
        res = asyncio.run(arch.run(commands))
        with open(f'{output}/{prefix}-results.json','w') as F:
            json.dump(res, F, indent=4)

    if serve:
        from .utility.server import serve
        serve(arch, host=host, port=port, debug=debug)

    # TODO save all pages of stacks of frames
    # with open(f'{opath}/{prefix}-pages.json','w') as F:
    #     json.dump(arch.orchestrator.pages, F, indent=4)

if __name__ == "__main__":
    main(**parseargs(argv=sys.argv[1:]))
