
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
from .ast import Path     as AstPath
from .ast import Call     as AstCall
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
from .ir import Call       as IrCall
from .ir import Dataflow   as IrDataflow
from .ir import Input      as IrInput

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

class Backend(BaseModel):
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
        if isinstance(type, AstTypeRef):

            if type.name == 'text':
                length = None
                if len(type.arguments) == 1:
                    arg = type.arguments[0]
                    if arg.name is not None and arg.name != 'length':
                        raise Exception(f"Builtin format `text` expect only `length` arguments (got: {args})")
                    length = arg.value.eval(values=values)
                elif len(type.arguments) > 1:
                    raise Exception(f"Builtin format `text` expect single `length` arguments (got: {args})")
                fmt = IrCompletion(name=pathname, length=length)
                self.program.formats.update({ pathname : fmt })
                return fmt

            if type.name in self.formats:
                syntax = self.formats[type.name]
            elif type.name in self.structs:
                syntax = self.structs[type.name]
            else:
                raise Exception(f"Reference to `{type.name}` is not match as either a format or struct")
            arguments = [ var for var in syntax.variables if var.is_argument ]

            args = {}
            kw = False
            for (a,arg) in enumerate(type.arguments):
                if arg.name is None:
                    if kw:
                        raise Exception(f"Found non-keyword argument after at least one keyword argument.")
                    args.update({ arguments[a].name : arg.value })
                else:
                    kw = True
                    args.update({ arg.name : arg.value })

            loc_values = copy.deepcopy(values)
            for arg in arguments:
                if arg.name in args:
                    value = args[arg.name].eval(values=loc_values)
                else:
                    if arg.initializer is None:
                        raise Exception(f"Argument {arg.name} of {syntax.name} is not provided and no default was provided.")
                    value = arg.initializer.eval(values=loc_values)
                loc_values.update({ arg.name : value })

            refname = type.name
            if len(arguments) > 0:
                # argvals = [ f"{arg.name}={loc_values[arg.name]}" for arg in arguments ]
                argvals = [ f"{loc_values[arg.name]}" for arg in arguments ]
                refname += '<' + ','.join(argvals) + '>'

            if type.name in self.formats:
                concrete = self.resolve_type(type=syntax.type, path=path+[refname], values=loc_values)
                concrete.refname = refname
                if syntax.annotation is not None:
                    concrete.desc.append(syntax.annotation.eval(loc_values))
                return concrete

            elif type.name in self.structs:
                return TmpRecord(name=pathname, fields=syntax.fields, syntax=syntax, values=loc_values)

            else:
                raise Exception(f"Unknown type: {refname}: {type}\n{self.program.formats}\n{self.formats}")

        elif isinstance(type, AstRecord):
            rec_values = copy.deepcopy(values)
            return TmpRecord(name=pathname, fields=type.fields, syntax=type, values=rec_values)

        elif isinstance(type, AstEnumType):
            if type.kind == 'enum':
                assert isinstance(type.source, list)
                fmt = IrEnum(name=pathname, values=[ s.eval(values=values) for s in type.source ])
                self.program.formats.update({ pathname : fmt })
                return fmt

            elif type.kind == 'repeat' or type.kind == 'select':
                path = IrPath(
                    is_input=type.source.is_input,
                    prompt=type.source.prompt,
                    steps=[ ( step.name, range_from_slice(step.slice, values) ) for step in type.source.steps ]
                )
                fmt = IrChoice(name=pathname, path=path, mode=type.kind)
                self.program.formats.update({ pathname : fmt })
                return fmt

            else:
                raise NotImplementedError(f"Process enum type:\n\t{type}")

        else:
            raise Exception(f"Unexpected class for AST type node: {type}")
        
    def append_fields(self, prompt: IrPrompt, fields: List[AstField], parent: Union[IrPrompt,IrField], ihn_path:List[str], values:Dict[str,Any]):
        depth = 1 if isinstance(parent, IrPrompt) else parent.depth + 1
        for f,fld in enumerate(fields):
            fld_path = ihn_path+[fld.name]
            fmt = self.resolve_type(fld.type, fld_path, values=values) # TODO accumulate values along path
            field = IrField(
                name=fld.name,
                format=None if isinstance(fmt, TmpRecord) else fmt,
                range=range_from_slice(fld.range, values),
                depth=depth,
                index=f,
                parent=parent
            )
            self.fields.update({ '.'.join(fld_path) : field })
            prompt.fields.append(field)
            if isinstance(fmt, TmpRecord):
                self.append_fields(prompt=prompt, fields=fmt.fields, parent=field, ihn_path=fld_path, values=fmt.values)
                if isinstance(fmt.syntax, AstStruct):
                    for annotation in fmt.syntax.annotations:
                        path = fld_path + [ s.name for s in annotation.what.steps ]
                        path = '.'.join(path)
                        self.fields[path].desc.append(annotation.label.eval(fmt.values))

    def compile(self, **kwargs):
        self.formats.update({ s.name : s for s in self.ast.formats })
        self.structs.update({ s.name : s for s in self.ast.structs })

        for p in self.ast.prompts:
            prompt = IrPrompt(name=p.name)
            values = {} # TODO from global and promt variables
            self.append_fields(
                prompt=prompt,
                fields=p.fields,
                parent=prompt,
                ihn_path=[p.name],
                values=values
            )
            self.program.prompts.update({ prompt.name : prompt })
            for annotation in p.annotations:
                annot = annotation.label.eval(values)
                if len(annotation.what.steps) > 0:
                    path = [p.name] + [ s.name for s in annotation.what.steps ]
                    path = '.'.join(path)
                    self.fields[path].desc.append(annot)
                else:
                    prompt.desc.append(annot)
            for channel in p.channels:
                assert not channel.target.is_input
                assert channel.target.prompt is None
                tgt = [ ( s.name, None if s.slice is None else s.slice.start.eval(values) ) for s in channel.target.steps ]
                if isinstance(channel.source, AstPath):
                    assert len(channel.source.steps) == 1
                    assert channel.source.steps[0].slice is None
                    src = [ ( s.name, None if s.slice is None else s.slice.start.eval(values) ) for s in channel.source.steps ]
                    if channel.source.is_input:
                        prompt.channels.append(IrInput(src=src, tgt=tgt))
                    elif channel.source.prompt is not None:
                        prompt.channels.append(IrDataflow(prompt=channel.source.prompt.name, src=src, tgt=tgt))
                    else:
                        prompt.channels.append(IrDataflow(prompt=None, src=src, tgt=tgt))
                elif isinstance(channel.source, AstCall):
                    raise NotImplementedError(f"Channel with Call source: {channel.source}")
                else:
                    raise Exception(f"Unexpected channel source: {channel.source}")
