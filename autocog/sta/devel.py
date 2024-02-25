from .frontend import frontend
from .grammar import grammar

from ..parse_tree import prog2gv

from ..utility.pynb import wrap_graphviz, display

def wrap_frontend(program, display_parse_tree=True, rule=None):
    if display_parse_tree:
        display(wrap_graphviz(prog2gv(grammar, program)))
    return frontend(program, rule=rule)
