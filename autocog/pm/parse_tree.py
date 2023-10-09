
from parsimonious.nodes import NodeVisitor

class GenericVisit(NodeVisitor):
    def generic_visit(self, node, visited_children):
        if len(visited_children) > 0:
            return { 'kind' : node.expr_name, 'children' : visited_children }
        else:
            return { 'kind' : node.expr_name, 'text' : node.text }

def tree2list(root, nodes, pid=None):
    nodes.append({ 'kind' : root['kind'], 'pid' : pid })
    nid = len(nodes)-1
    if 'text' in root:
        nodes[-1].update({ 'text' : root['text'] })
    if 'children' in root:
        for child in root['children']:
            tree2list(child, nodes, nid)

def prog2gv(grammar, program):
    visitor = GenericVisit()
    tree = visitor.visit(grammar.parse(program))
    nodes = []
    tree2list(tree, nodes)
    dotstr = ''
    for (nid,node) in enumerate(nodes):
        label = node['kind']
        dotstr += f"n_{nid} [label=\"{label}\"];\n"
        if node['pid'] is not None:
            dotstr += f"n_{node['pid']} -> n_{nid};\n"
    return dotstr
