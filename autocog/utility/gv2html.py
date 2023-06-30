
import io, os, uuid, json, pathlib

import graphviz

def gv2svg(dotstr):
    return graphviz.Digraph(body=dotstr).pipe(format='svg').decode("utf-8")
