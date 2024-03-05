from parsimonious.nodes import NodeVisitor

from .grammar import grammar
from .ast import *

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
            elif isinstance(child, Format):
                program.formats.append(child)
            elif isinstance(child, Prompt):
                program.prompts.append(child)
            elif isinstance(child, Struct):
                program.structs.append(child)
            elif isinstance(child, dict) and child['kind'] == 'flow_block':
                program.flows += child['children']
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

    def visit_struct_decl(self, node, visited_children):
        assert len(visited_children) == 12

        name = visited_children[2]
        assert name['kind'] == 'identifier'

        variables = visited_children[5]
        if variables is not None and 'children' in variables:
            assert variables['kind'] == 'var_decls', f"{variables}"
            variables = variables['children']
        else:
            variables = []

        fields = visited_children[7]
        assert fields['kind'] == 'field_decls', f"{fields}"
        assert len(fields['children']) > 0

        annots = visited_children[9]
        if annots is not None and 'children' in annots:
            annots = annots['children'][0]
            assert annots['kind'] == 'annot_block', f"{annots}"
            annots = annots['children']
        else:
            annots = []

        return Struct(
            name=name['text'],
            variables=variables,
            fields=fields['children'],
            annotations=annots
        )

    def visit_format_decl(self, node, visited_children):
        assert len(visited_children) == 12

        name = visited_children[2]
        assert name['kind'] == 'identifier'

        variables = visited_children[5]
        if variables is not None and 'children' in variables:
            assert variables['kind'] == 'var_decls', f"{variables}"
            variables = variables['children']
        else:
            variables = []

        annot = visited_children[9]
        if 'children' in annot:
            annot = annot['children'][0]
        else:
            annot = None

        return Format(
            name=name['text'],
            variables=variables,
            type=visited_children[7],
            annotation=annot
        )

    def visit_prompt_decl(self, node, visited_children):
        assert len(visited_children) == 18
        name = visited_children[2]
        assert name['kind'] == 'identifier'

        variables = visited_children[5]
        # print(f"variables={variables}")
        if variables is not None and 'children' in variables:
            assert variables['kind'] == 'var_decls', f"{variables}"
            variables = variables['children']
        else:
            variables = []

        fields = visited_children[7]
        assert fields['kind'] == 'field_decls', f"{fields}"
        assert len(fields['children']) > 0

        channels = visited_children[9]
        if channels is not None:
            assert channels['kind'] == 'channel_block', f"{channels}"
            channels = channels['children']
        else:
            channels = []

        flows = visited_children[11]
        if flows is not None:
            assert flows['kind'] == 'flow_block', f"{flows}"
            flows = flows['children']
        else:
            flows = []

        annots = visited_children[15]
        if annots is not None:
            assert annots['kind'] == 'annot_block', f"{annots}"
            annots = annots['children']
        else:
            annots = []

        prompt = Prompt(
            name=name['text'],
            variables=variables,
            fields=fields['children'],
            channels=channels,
            returns=visited_children[13],
            flows=flows,
            annotations=annots
        )
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
        arr_slice = field_name['children'][1]
        if 'children' in arr_slice:
            assert len(arr_slice['children']) == 1
            arr_slice = arr_slice['children'][0]
        else:
            arr_slice = None
        
        field_defn = visited_children[2]
        if isinstance(field_defn, ASTNode):
            type = field_defn
        elif field_defn['kind'] == 'field_decls':
            type = Record(fields=field_defn['children'])
        else:
            raise Exception(f"{field_defn}")
        return Field(name=name['text'], type=type, range=arr_slice)

    def visit_field_defn(self, node, visited_children):
        assert len(visited_children) == 1
        return visited_children[0]

    def visit_field_detail(self, node, visited_children):
        assert len(visited_children) == 7
        type = visited_children[2]
        assert len(type['children']) == 1
        type = type['children'][0]
        annot = visited_children[4]
        assert len(annot['children']) == 1
        annot = annot['children'][0]
        return { 'kind' : node.expr_name, 'children' : [ type, annot ] }

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
        source = visited_children[4]['children'][0]
        assert isinstance(source, Path) or isinstance(source, Call), f"{source}"
        return Channel(
            target=visited_children[2],
            source=source
        )

    def visit_path_expr(self, node, visited_children):
        assert len(visited_children) == 1
        return visited_children[0]

    def visit_input_path_expr(self, node, visited_children):
        assert len(visited_children) == 2
        path = visited_children[1]
        assert isinstance(path, Path), f"{path}"
        path.is_input = True
        return path

    def visit_global_path_expr(self, node, visited_children):
        assert len(visited_children) == 3
        path = visited_children[2]
        assert isinstance(path, Path), f"{path}"
        path.prompt = visited_children[0]
        assert path.prompt['kind'] == 'identifier', f"{path.prompt}"
        path.prompt = path.prompt['text']
        return path

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

    def visit_annot_expr(self, node, visited_children):
        assert len(visited_children) == 4
        return visited_children[2]

    def visit_string_expr(self, node, visited_children):
        assert len(visited_children) == 1
        return visited_children[0]

    def visit_repeat_def(self, node, visited_children):
        assert len(visited_children) == 7
        arguments = visited_children[2]
        if 'children' in arguments:
            assert len(arguments['children']) == 1
            arguments = arguments['children'][0]
            assert arguments['kind'] == 'param_list'
            arguments = arguments['children']
        else:
            arguments = []
        return EnumType(kind='repeat', source=visited_children[5], arguments=arguments)

    def visit_select_def(self, node, visited_children):
        assert len(visited_children) == 7
        arguments = visited_children[2]
        if 'children' in arguments:
            assert len(arguments['children']) == 1
            arguments = arguments['children'][0]
            assert arguments['kind'] == 'param_list'
            arguments = arguments['children']
        else:
            arguments = []
        return EnumType(kind='select', source=visited_children[5], arguments=arguments)

    def visit_enum_def(self, node, visited_children):
        assert len(visited_children) == 7
        arguments = visited_children[2]
        if 'children' in arguments:
            assert len(arguments['children']) == 1
            arguments = arguments['children'][0]
            assert arguments['kind'] == 'param_list'
            arguments = arguments['children']
        else:
            arguments = []
        source = visited_children[5]
        assert source['kind'] == 'string_expr_list'
        return EnumType(kind='enum', source=source['children'], arguments=arguments)
    
    def visit_string_expr_list__(self, node, visited_children):
        if len(visited_children) == 1:
            return visited_children[0]
        else:
            return None

    def visit_string_expr_list_cont(self, node, visited_children):
        assert len(visited_children) == 4
        return visited_children[3]

    def visit_string_expr_list(self, node, visited_children):
        assert len(visited_children) == 2
        children = [ visited_children[0] ]
        if visited_children[1] is not None:
            children += visited_children[1]['children']
        return { 'kind' : node.expr_name, 'children' : children }

    def visit_from_stmt(self, node, visited_children):
        assert len(visited_children) == 5
        return visited_children[2]

    def visit_return_stmt__(self, node, visited_children):
        if len(visited_children) == 1:
            return visited_children[0]
        else:
            return None

    def visit_return_stmt(self, node, visited_children):
        assert len(visited_children) == 3
        visited_children = visited_children[2]['children']
        assert len(visited_children) == 1
        return visited_children[0]

    def visit_return_expr(self, node, visited_children):
        assert len(visited_children) == 3
        path = visited_children[0]
        assert isinstance(path, Path), f"{path}"
        return RetBlock(fields=[RetField(field=path)])

    def visit_return_block(self, node, visited_children):
        assert len(visited_children) == 5
        alias = visited_children[2]
        if 'children' in alias:
            assert len(alias['children']) == 1
            alias = alias['children'][0]
        else:
            alias = None
        fields = visited_children[3]['children']
        return RetBlock(alias=alias, fields=fields)

    def visit_return_as_stmt__(self, node, visited_children):
        assert len(visited_children) == 2
        return visited_children[0]

    def visit_return_as_stmt(self, node, visited_children):
        assert len(visited_children) == 5
        return visited_children[2]

    def visit_return_from_stmt__(self, node, visited_children):
        assert len(visited_children) == 2
        return visited_children[0]

    def visit_return_from_stmt(self, node, visited_children):
        assert len(visited_children) == 6
        return RetField(
            field=visited_children[2],
            rename=visited_children[3]
        )

    def visit_ret_rename__(self, node, visited_children):
        if len(visited_children) == 1:
            return visited_children[0]
        else:
            return None

    def visit_ret_rename(self, node, visited_children):
        assert len(visited_children) == 4
        return visited_children[3]

    def visit_flow_block__(self, node, visited_children):
        if len(visited_children) == 1:
            return visited_children[0]
        else:
            return None

    def visit_flow_block(self, node, visited_children):
        assert len(visited_children) == 6
        return { 'kind' : node.expr_name, 'children' : visited_children[4]['children'] }

    def visit_flow_stmt__(self, node, visited_children):
        assert len(visited_children) == 2
        return visited_children[0]

    def visit_flow_stmt(self, node, visited_children):
        assert len(visited_children) == 7
        prompt = visited_children[2]
        assert prompt['kind'] == 'identifier'
        limit = visited_children[3]
        if 'children' in limit:
            assert len(limit['children']) == 1
            limit = limit['children'][0]
        else:
            limit = None
        alias = visited_children[5]
        if 'children' in alias:
            assert len(alias['children']) == 1
            alias = alias['children'][0]
        else:
            alias = None
        return Flow( prompt=prompt['text'], limit=limit, alias=alias )

    def visit_flow_limit(self, node, visited_children):
        assert len(visited_children) == 5
        return visited_children[2]

    def visit_flow_as_stmt(self, node, visited_children):
        assert len(visited_children) == 3
        return visited_children[2]

    def visit_annot_block__(self, node, visited_children):
        if len(visited_children) == 1:
            return visited_children[0]
        else:
            return None

    def visit_annot_block(self, node, visited_children):
        assert len(visited_children) == 6
        return { 'kind' : node.expr_name, 'children' : visited_children[4]['children'] }

    def visit_annot_stmt__(self, node, visited_children):
        assert len(visited_children) == 2
        return visited_children[0]

    def visit_annot_stmt(self, node, visited_children):
        assert len(visited_children) == 6
        return Annotation(
            what=visited_children[0],
            label=visited_children[4]
        )

    def visit_var_decl(self, node, visited_children):
        assert len(visited_children) == 2
        return visited_children[1]['children'][0]
        

    def visit_def_decl(self, node, visited_children):
        assert len(visited_children) == 7
        name = visited_children[2]
        assert name['kind'] == 'identifier'
        return Variable( name=name['text'], initializer=visited_children[4] )

    def visit_arg_decl(self, node, visited_children):
        assert len(visited_children) == 7
        name = visited_children[2]
        assert name['kind'] == 'identifier'
        initializer = visited_children[4]
        if 'children' in initializer:
            initializer = initializer['children'][0]
        else:
            initializer = None
        return Variable( name=name['text'], initializer=initializer, is_argument=True )

    def visit_initializer(self, node, visited_children):
        assert len(visited_children) == 3
        return visited_children[2]

    def visit_call_block(self, node, visited_children):
        assert len(visited_children) == 9

        extern = visited_children[4]
        extern = extern['children'][0] if 'children' in extern else None

        entry = visited_children[5]
        entry = entry['children'][0] if 'children' in entry else None

        kwargs = visited_children[6]
        kwargs = kwargs['children'] if 'children' in kwargs else []

        binds = visited_children[7]
        binds = binds['children'] if 'children' in binds else []

        return Call( extern=extern, entry=entry, kwargs=kwargs, binds=binds )

    def visit_extern_stmt__(self, node, visited_children):
        assert len(visited_children) == 2
        return visited_children[0]

    def visit_extern_stmt(self, node, visited_children):
        assert len(visited_children) == 5
        node = visited_children[2]
        assert node['kind'] == 'identifier'
        return node['text']

    def visit_entry_stmt__(self, node, visited_children):
        assert len(visited_children) == 2
        return visited_children[0]

    def visit_entry_stmt(self, node, visited_children):
        assert len(visited_children) == 5
        node = visited_children[2]
        assert node['kind'] == 'identifier'
        return node['text']

    def visit_kwarg_stmt__(self, node, visited_children):
        assert len(visited_children) == 2
        return visited_children[0]

    def visit_kwarg_stmt(self, node, visited_children):
        assert len(visited_children) == 9
        name = visited_children[2]
        assert name['kind'] == 'identifier'

        mapped = visited_children[4]
        assert len(mapped['children']) == 1
        mapped = mapped['children'][0]['text'] == 'map'

        return Kwarg(
            name=name['text'],
            source=visited_children[6],
            mapped=mapped
        )

    def visit_bind_stmt__(self, node, visited_children):
        assert len(visited_children) == 2
        return visited_children[0]

    def visit_bind_stmt(self, node, visited_children):
        assert len(visited_children) == 9
        target = visited_children[6]
        assert target['kind'] == 'identifier'
        return Bind(
            source=visited_children[2],
            target=target['text']
        )

    # def visit_(self, node, visited_children):
    #     assert len(visited_children) == 1
    #     pass

    def generic_visit(self, node, visited_children):
        if len(visited_children) > 0:
            return { 'kind' : node.expr_name, 'children' : visited_children }
        else:
            return { 'kind' : node.expr_name, 'text' : node.text }

def frontend(program:str, rule=None):
    visitor = Visitor()
    G = grammar
    if rule is not None:
        G = G[rule]
    return visitor.visit(G.parse(program))
