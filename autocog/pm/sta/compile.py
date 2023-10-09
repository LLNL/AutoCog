
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable, Union
from abc import abstractmethod
from pydantic import BaseModel

import copy

from .frontend import frontend

from .ast import Program  as AstProgram
from .ast import Scope    as AstScope
from .ast import Format   as AstFormat
from .ast import Struct   as AstStruct
from .ast import Field    as AstField
from .ast import Record   as AstRecord
from .ast import TypeRef  as AstTypeRef
from .ast import EnumType as AstEnumType
from .ast import Slice    as AstSlice

from .ir import Object     as IrObject
from .ir import Program    as IrProgram
from .ir import Prompt     as IrPrompt
from .ir import Field      as IrField
from .ir import Format     as IrFormat
from .ir import Completion as IrCompletion
from .ir import Enum       as IrEnum
from .ir import Choice     as IrChoice
from .ir import Range      as IrRange
from .ir import Record     as IrRecord
from .ir import Path       as IrPath

class TmpRecord(IrObject):
    fields: List[AstField]
    syntax: AstRecord
    values: Dict[str,Any]

def range_from_slice(slice: Optional[AstSlice], values:Dict[str,Any]):
    if slice is None:
        return None
    start = slice.start.eval(values)
    stop  = start if slice.stop is None else slice.stop.eval(values)
    return (start, stop)

class Compiler(BaseModel):
    formats: Dict[str,AstFormat] = {}
    structs: Dict[str,AstStruct] = {}
    fields:  Dict[str,IrField]   = {}

    source:  str
    ast:     AstProgram
    program: IrProgram

    def __init__(self, source:str, **kwargs):
        super().__init__(
            source=source,
            ast=frontend(source),
            program=IrProgram()
        )
        self.compile(**kwargs)

    def resolve_type(self, type: Union[AstRecord,AstTypeRef,AstEnumType], path:List[str], values:Dict[str,Any]):
        pathname = '.'.join(path)
        if isinstance(type, AstRecord):
            rec_values = copy.deepcopy(values)
            return TmpRecord(name=pathname, fields=type.fields, syntax=type, values=rec_values)

        elif isinstance(type, AstTypeRef):
            refname = type.name
            args = {}
            for (a,arg) in enumerate(type.arguments):
                # TODO enforce same rules as for python args/kwargs
                refname += ':'
                value = arg.value.eval(values=values)
                if arg.name is not None:
                    refname += f'{arg.name}='
                    args.update({ arg.name : value })
                else:
                    args.update({ a : value })
                refname += f'{value}'

            if refname in self.program.formats:
                return self.program.formats[refname]

            elif refname in self.program.records:
                return self.program.records[refname]

            elif type.name in self.formats:
                syntax = self.formats[type.name]
                loc_values = copy.deepcopy(values)
                loc_values.update({}) # TODO syntax.variables
                concrete = self.resolve_type(type=syntax.type, path=path+[refname], values=loc_values)
                # TODO annot?
                return concrete

            elif type.name in self.structs:
                syntax = self.structs[type.name]
                rec_values = copy.deepcopy(values)
                rec_values.update({}) # TODO syntax.variables
                return TmpRecord(name=pathname, fields=syntax.fields, syntax=syntax, values=rec_values)

            elif type.name == 'text':
                length = None
                if len(args) == 1:
                    if 0 in args:
                        length = args[0]
                    elif 'length' in args:
                        length = args['length']
                    else:
                        raise Exception(f"Builtin format `text` expect only `length` arguments (got: {args})")
                elif len(args) > 1:
                    raise Exception(f"Builtin format `text` expect single `length` arguments (got: {args})")
                fmt = IrCompletion(name=pathname, length=length, annonymous=True)
                self.program.formats.update({ pathname : fmt })
                return fmt

            else:
                raise Exception(f"Unknown type: {refname}: {type}\n{self.program.formats}\n{self.formats}")

        elif isinstance(type, AstEnumType):
            if type.kind == 'enum':
                assert isinstance(type.source, list)
                fmt = IrEnum(name=pathname, values=[ s.eval(values=values) for s in type.source ], annonymous=True)
                self.program.formats.update({ pathname : fmt })
                return fmt

            elif type.kind == 'repeat' or type.kind == 'select':
                path = IrPath(
                    is_input=type.source.is_input,
                    prompt=type.source.prompt,
                    steps=[ ( step.name, range_from_slice(step.slice, values) ) for step in type.source.steps ]
                )
                fmt = IrChoice(name=pathname, path=path, mode=type.kind, annonymous=True)
                self.program.formats.update({ pathname : fmt })
                return fmt

            else:
                raise NotImplementedError(f"Process enum type:\n\t{type}")

        else:
            raise Exception(f"Unexpected class for AST type node: {type}")
        
    def append_fields(self, prompt: IrPrompt, fields: List[AstField], parent: Union[IrPrompt,IrField], path:List[str], values:Dict[str,Any]):
        depth = 1 if isinstance(parent, IrPrompt) else parent.depth + 1
        for f in fields:
            fld_path = path+[f.name]
            fmt = self.resolve_type(f.type, fld_path, values=values) # TODO accumulate values along path
            field = IrField(
                name=f.name,
                format=None if isinstance(fmt, TmpRecord) else fmt,
                range=range_from_slice(f.range, values),
                depth=depth,
                parent=parent
            )
            self.fields.update({ '.'.join(fld_path) : field })
            prompt.fields.append(field)
            if isinstance(fmt, TmpRecord):
                self.append_fields(prompt=prompt, fields=fmt.fields, parent=field, path=fld_path, values=fmt.values)

    def compile(self, **kwargs):
        self.formats.update({ s.name : s for s in self.ast.formats })
        self.structs.update({ s.name : s for s in self.ast.structs })

        for p in self.ast.prompts:
            prompt = IrPrompt(name=p.name)
            self.append_fields(
                prompt=prompt,
                fields=p.fields,
                parent=prompt,
                path=[p.name],
                values={} # TODO from global and promt variables
            )
            # TODO channels
            self.program.prompts.update({ prompt.name : prompt })
