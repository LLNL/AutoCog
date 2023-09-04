from parsimonious.nodes import NodeVisitor

from .grammar import grammar
from .ast import ASTNode, Program, Variable, Value, Reference, Prompt, Field, TypeRef, Argument, Channel, Path, Step, Slice

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

    def visit_expression(self, node, visited_children):
        assert len(visited_children) == 1
        return visited_children[0]

    def visit_value_expr(self, node, visited_children):
        assert len(visited_children) == 1
        return visited_children[0]

    def visit_int_literal__(self, node, visited_children):
        assert len(visited_children) == 1
        return visited_children[0]

    def visit_int_literal(self, node, visited_children):
        assert len(visited_children) == 0
        return Value(value=int(node.text))

    def visit_string_literal(self, node, visited_children):
        assert len(visited_children) == 1
        return visited_children[0]

    def visit_val_string(self, node, visited_children):
        assert len(visited_children) == 3
        return Value(value=visited_children[1]['text'])

    def visit_fmt_string(self, node, visited_children):
        assert len(visited_children) == 3
        return Value(value=visited_children[1]['text'], is_fstring=True)

    def visit_refexpr(self, node, visited_children):
        assert len(visited_children) == 2
        node = visited_children[1]
        assert node['kind'] == 'identifier'
        return Reference(name=node['text'])

    def visit_prompt_decl(self, node, visited_children):
        assert len(visited_children) == 18
        name = visited_children[2]
        assert name['kind'] == 'identifier'

        fields = visited_children[7]
        assert fields['kind'] == 'field_decls', f"{fields}"
        assert len(fields['children']) > 0

        channels = visited_children[9]
        if channels is not None:
            assert channels['kind'] == 'channel_block', f"{channels}"
            channels = channels['children']
        else:
            channels = []

        prompt = Prompt(
            name=name['text'],
            fields=fields['children'],
            channels=channels
        )
        # variables = visited_children[5]
        # channels = visited_children[9]
        # flows = visited_children[11]
        # returns = visited_children[13]
        # annots = visited_children[15]
        return prompt

    def visit_is_record_field(self, node, visited_children):
        assert len(visited_children) == 6
        return visited_children[3]

    def visit_field_decl__(self, node, visited_children):
        assert len(visited_children) == 2
        return visited_children[1]

    def visit_field_decl(self, node, visited_children):
        assert len(visited_children) == 4
        field_name = visited_children[0]
        assert field_name['kind'] == 'field_name', f"{field_name}"
        assert len(field_name['children']) == 2
        name = field_name['children'][0]
        assert name['kind'] == "identifier"
        arr_slice = field_name['children'][1] # TODO
        field_defn = visited_children[2]
        if isinstance(field_defn, ASTNode):
            return Field(name=name['text'], type=field_defn)
        else:
            assert field_defn['kind'] == 'field_detail', f"{field_defn}"
            raise NotImplementedError('Field with details (annotation)')

    def visit_field_defn(self, node, visited_children):
        assert len(visited_children) == 1
        return visited_children[0]

    def visit_is_format_field(self, node, visited_children):
        assert len(visited_children) == 5
        visited_children = visited_children[2]['children']
        assert len(visited_children) == 1
        return visited_children[0]

    def visit_type_ref(self, node, visited_children):
        assert len(visited_children) == 3
        name = visited_children[0]
        assert name['kind'] == "identifier"
        arguments = visited_children[2]
        if 'children' in arguments:
            assert len(arguments['children']) == 1
            arguments = arguments['children'][0]
            assert arguments['kind'] == 'param_list'
            arguments = arguments['children']
        else:
            arguments = []
        return TypeRef(name=name['text'], arguments=arguments)

    def visit_param_list_cont(self, node, visited_children):
        assert len(visited_children) == 4
        return visited_children[3]

    def visit_param_list(self, node, visited_children):
        assert len(visited_children) == 2
        children = [ visited_children[0] ]
        if 'children' in visited_children[1]:
            assert len(visited_children[1]['children']) == 1
            assert visited_children[1]['children'][0]['kind'] == 'param_list'
            children += visited_children[1]['children'][0]['children']
        return { 'kind' : node.expr_name, 'children' : children }

    def visit_type_ref_param(self, node, visited_children):
        assert len(visited_children) == 5
        return visited_children[2]

    def visit_param_expr(self, node, visited_children):
        assert len(visited_children) == 2
        name = visited_children[0]
        if 'children' in name:
            assert len(name['children']) == 1
            name = name['children'][0]
            assert name['kind'] == 'identifier'
            name = name['text']
        else:
            name = None
        return Argument(value=visited_children[1], name=name)

    def visit_param_expr_kw(self, node, visited_children):
        assert len(visited_children) == 4
        return visited_children[0]

    def visit_channel_block__(self, node, visited_children):
        if len(visited_children) == 1:
            return visited_children[0]
        else:
            return None

    def visit_channel_block(self, node, visited_children):
        assert len(visited_children) == 6
        visited_children = visited_children[4]['children']
        return { 'kind' : node.expr_name, 'children' : visited_children }

    def visit_channel_stmt__(self, node, visited_children):
        assert len(visited_children) == 2
        return visited_children[0]

    def visit_channel_stmt(self, node, visited_children):
        assert len(visited_children) == 5
        return Channel(
            target=visited_children[2],
            source=visited_children[4]['children'][0]
        )

    def visit_local_path_expr(self, node, visited_children):
        assert len(visited_children) == 2
        path = visited_children[1]
        assert isinstance(path, Path), f"{path}"
        return path

    def visit_sub_path_expr__(self, node, visited_children):
        assert len(visited_children) == 2
        return visited_children[1]

    def visit_sub_path_expr(self, node, visited_children):
        assert len(visited_children) == 2
        if 'children' in visited_children[1]:
            assert len(visited_children[1]['children']) == 1
            path = visited_children[1]['children'][0]
            assert isinstance(path, Path), f"{path}"
        else:
            path = Path()
        step = visited_children[0]
        assert isinstance(step, Step), f"{step}"
        path.steps = [step] + path.steps
        return path

    def visit_path_step(self, node, visited_children):
        assert len(visited_children) == 2
        name = visited_children[0]
        assert name['kind'] == "identifier"
        slice = visited_children[1]
        if 'children' in slice:
            assert len(slice['children']) == 1
            slice = slice['children'][0]
            assert isinstance(slice,Slice), f"{slice}"
        else:
            slice = None
        return Step(name=name['text'], slice=slice)

    def visit_array_slice_cont(self, node, visited_children):
        if len(visited_children) > 0:
            assert len(visited_children) == 1
            return visited_children[0]
        else:
            return None

    def visit_array_slice__(self, node, visited_children):
        assert len(visited_children) == 4
        return visited_children[3]

    def visit_array_slice(self, node, visited_children):
        assert len(visited_children) == 6
        return Slice(
            start=visited_children[2],
            stop=visited_children[3]
        )

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
