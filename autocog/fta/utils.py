
def depthfirst(tree):
    yield tree
    children = tree.children
    if isinstance(children, dict):
        children = children.values()
    for c in children:
        if c.parent is None:
            c.parent = tree
        yield from depthfirst(c)
