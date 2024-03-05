import os, sys, json
import asyncio

from .serpapi import SerpAPI
from .minepdf import PdfMiner
from .orgmode import OrgMode
from .feed    import RssFeed

tools = { X.__name__.lower() : X for X in [ SerpAPI, PdfMiner, OrgMode, RssFeed ] }

def load_json(x):
    if x == '':
        return {}
    elif x.endswith('.json'):
        assert os.path.exists(x)
        return json.load(open(x))
    else:
        return json.loads(x)

if __name__ == '__main__':
    tool = sys.argv[1].lower()
    kwargs = load_json(sys.argv[2])
    inputs = load_json(sys.argv[3])
    output = sys.argv[4] if len(sys.argv) > 4 else None

    tool = tools[tool](tag=tool, **kwargs)
    out = asyncio.run(tool(**inputs))
    if output is None:
        print(json.dumps(out, indent=4))
    else:
        json.dump(out, open(output, 'w'), indent=4)
