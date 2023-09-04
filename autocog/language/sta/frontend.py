from parsimonious.nodes import NodeVisitor

from .grammar import grammar
from .ast import Program, Variable, Value, Reference, Prompt

class Visitor(NodeVisitor):
    def visit_program(self, node, visited_children):
        assert len(visited_children) == 2

        program = Program()
        if not 'children' in visited_children[0]:
            return program

        visited_children = visited_children[0]['children']

        for child in visited_children:
            if isinstance(child, Variable):
                program.variables.append(child)
            elif isinstance(child, Prompt):
                program.prompts.append(child)
            else:
                raise Exception(f"Unknown: {child}")
        return program

    def visit_declaration__(self, node, visited_children):
        assert len(visited_children) == 2
        return visited_children[1]

    def visit_declaration(self, node, visited_children):
        assert len(visited_children) == 1
        return visited_children[0]

    def visit_def_decl(self, node, visited_children):
        assert len(visited_children) == 7
        name = visited_children[2]
        assert name['kind'] == 'identifier'
        name = name['text']
        initializer = visited_children[4]
        return Variable(name=name, initializer=initializer)

    def visit_arg_decl(self, node, visited_children):
        assert len(visited_children) == 7
        name = visited_children[2]
        assert name['kind'] == 'identifier'
        name = name['text']
        initializer = visited_children[4]
        if 'children' in initializer:
            assert len(initializer['children']) == 1
            initializer = initializer['children'][0]
        else:
            initializer = None
        return Variable(name=name, initializer=initializer, is_argument=True)

    def visit_initializer(self, node, visited_children):
        if len(visited_children) > 0:
            assert len(visited_children) == 3
            return visited_children[2]
        else:
            return None

    def visit_value_expr(self, node, visited_children):
        assert len(visited_children) == 1
        return visited_children[0]

    def visit_int_literal__(self, node, visited_children):
        assert len(visited_children) == 1
        return visited_children[0]

    def visit_int_literal(self, node, visited_children):
        assert len(visited_children) == 0
        return Value(value=int(node.text))

    def visit_refexpr(self, node, visited_children):
        assert len(visited_children) == 2
        node = visited_children[1]
        assert node['kind'] == 'identifier'
        return Reference(name=node['text'])

    def visit_prompt_decl(self, node, visited_children):
        assert len(visited_children) == 18
        name = visited_children[2]
        assert name['kind'] == 'identifier'
        prompt =  Prompt(name=name['text'])
        variables = visited_children[5]
        fields = visited_children[7]
        channels = visited_children[9]
        flows = visited_children[11]
        returns = visited_children[13]
        annots = visited_children[15]
        return prompt

    # def visit_(self, node, visited_children):
    #     assert len(visited_children) == 1
    #     pass

    def generic_visit(self, node, visited_children):
        if len(visited_children) > 0:
            return { 'kind' : node.expr_name, 'children' : visited_children }
        else:
            return { 'kind' : node.expr_name, 'text' : node.text }

def frontend(program:str):
    visitor = Visitor()
    return visitor.visit(grammar.parse(program))
