from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from .tool import Tool

try:
    import orgparse
except:
    print("Warning: Package `orgparse` needed for org-mode (pip install orgparse)")
    orgparse = None

def org_to_dict_rec(node):
    res = {
        'heading' : node.heading,
        'body' : node.body
    }
    if isinstance(node, orgparse.node.OrgNode):
        res.update({
            'properties' : node.properties,
            'priority'   : node.priority,
            'todo' : node.todo
        })
    if len(node.children) > 0:
        res.update({ 'content' : [ org_to_dict_rec(c) for c in node.children ] })
    return res

def org_to_dict(filepath):
    D = orgparse.load(filepath)
    return org_to_dict_rec(D)

class OrgMode(Tool):
    async def __call__(self, filepath:str):
        if orgparse is None:
            raise Exception("Fatal: Package `orgparse` needed for org-mode (pip install orgparse)")
        return org_to_dict(filepath)
