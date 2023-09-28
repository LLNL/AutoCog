
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable, Union
from abc import abstractmethod
from pydantic import BaseModel

from .frontend import frontend

from .ast import Program  as AstProgram
from .ast import Scope    as AstScope
from .ast import Format   as AstFormat
from .ast import Struct   as AstStruct
from .ast import Field    as AstField
from .ast import Record   as AstRecord
from .ast import TypeRef  as AstTypeRef
from .ast import EnumType as AstEnumType

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

class TmpRecord(IrObject):
    fields: List[AstField]

class Compiler(BaseModel):
    formats: Dict[str,AstFormat] = {}
    structs: Dict[str,AstStruct] = {}

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
        if isinstance(type, AstRecord):
            return TmpRecord(name=".".join(path), fields=type.fields)

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
                raise NotImplementedError(f"Instantiate format:\n\t{type}")
            elif type.name in self.structs:
                raise NotImplementedError(f"Instantiate struct:\n\t{type}")
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
                fmt = IrCompletion(name='text', length=length)
                self.program.formats.update({ refname : fmt })
                return fmt
            else:
                raise Exception(f"Unknown type: {refname}: {type}\n{self.program.formats}\n{self.formats}")

        elif isinstance(type, AstEnumType):
            if type.kind == 'enum':
                assert isinstance(type.source, list)
                fmt = IrEnum(name=".".join(path), values=[ s.eval(values=values) for s in type.source ])
                self.program.formats.update({ fmt.name : fmt })
                return fmt
            elif type.kind == 'repeat' or type.kind == 'select':
                fmt = IrChoice(name=".".join(path), path=type.source, mode=type.kind)
                self.program.formats.update({ fmt.name : fmt })
                return fmt
            else:
                raise NotImplementedError(f"Process enum type:\n\t{type}")

        else:
            raise Exception(f"Unexpected class for AST type node: {type}")
        
    def append_fields(self, prompt: IrPrompt, fields: List[AstField], parent: Union[IrPrompt,IrField], path:List[str]):
        depth = 1 if isinstance(parent, IrPrompt) else parent.depth + 1
        for f in fields:
            fmt = self.resolve_type(f.type, path+[f.name], values={}) # TODO accumulate values along path
            field = IrField(
                name=f.name,
                format=None if isinstance(fmt, TmpRecord) else fmt,
                range=None,
                depth=depth,
                parent=parent
            )
            prompt.fields.append(field)
            if isinstance(fmt, TmpRecord):
                self.append_fields(prompt=prompt, fields=fmt.fields, parent=field, path=path+[f.name])

    def compile(self, **kwargs):
        self.formats.update({ s.name : s for s in self.ast.formats })
        self.structs.update({ s.name : s for s in self.ast.structs })

        for p in self.ast.prompts:
            prompt = IrPrompt(name=p.name)
            self.append_fields(
                prompt=prompt,
                fields=p.fields,
                parent=prompt,
                path=[p.name]
            )
            # TODO channels
            self.program.prompts.update({ prompt.name : prompt })
