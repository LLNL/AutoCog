
import os
import sys
import json
import asyncio

from .utility.args2arch import parseargs

def main(arch, serve, host, port, debug, commands, output):
    if os.path.exists(f'{opath}/frames.json'):
        pass # TODO load existing frames

    if commands is not None:
        res = asyncio.run(arch.run(commands))
        with open(f'{output}/results.json','w') as F:
            json.dump(res, F, indent=4)

    if serve:
        from .utility.server import serve
        serve(arch, host=host, port=port, debug=debug)

    # TODO save all frames
    # with open(f'{opath}/frames.json','w') as F:
    #     json.dump(arch.frames, F, indent=4)

if __name__ == "__main__":
    main(**parseargs(argv=sys.argv[1:]))
