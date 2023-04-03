
import os, sys, json
import asyncio
from autocog import CogArch
from autocog.architecture import PromptTee

import autocog.lm

# TODO method of CogArch?
async def run(arch, LMs, stas, tools, commands):
    
    for fmt in list(LMs.keys()):
        desc = LMs[fmt]
        cls = desc["cls"]
        if cls in autocog.lm.__dict__:
            cls = autocog.lm.__dict__[cls]
        del desc["cls"]
        print(desc)
        LMs.update({ fmt : cls(**desc) })

    for tag in list(stas.keys()):
        stas[tag] = arch.load(tag=tag, filepath=stas[tag][0], **stas[tag][1])
        stas[tag].LMs.update(LMs)

    for tag in list(tools.keys()):
        raise NotImplementedError()

    res = await asyncio.gather(*[
        arch(tag, **inputs)
        for (tag,inputs) in commands
    ])
    return [ r[0] for r in res ]

if __name__ == "__main__":
    # TODO proper command line handling
    argv = sys.argv[1:]
    print(json.dumps(asyncio.run(run(
        arch=CogArch(cogctx={'prompt_out':PromptTee(prefix=argv[0])}),
        LMs=json.loads(argv[1]),
        stas=json.loads(argv[2]),
        tools = json.loads(argv[3]),
        commands = json.loads(argv[4])
    )), indent=4))