
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
from .ast import Step     as AstStep
from .ast import Prompt   as AstPrompt
from .ast import Channel  as AstChannel
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
from .ir import Kwarg      as IrKwarg
from .ir import Call       as IrCall
from .ir import Dataflow   as IrDataflow
from .ir import Input      as IrInput
from .ir import Control    as IrControl
from .ir import Return     as IrReturn

from .automaton import Automaton as STA
from ..arch.cogs import Automaton as CogAutomaton

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

class Context(BaseModel):
    formats: Dict[str,AstFormat] = {}
    structs: Dict[str,AstStruct] = {}
    fields:  Dict[str,IrField]   = {}

def resolve_type(type: Union[AstRecord,AstTypeRef,AstEnumType], path:List[str], values:Dict[str,Any], program: IrProgram, ctx:Context):
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
            program.formats.update({ pathname : fmt })
            return fmt

        if type.name in ctx.formats:
            syntax = ctx.formats[type.name]
        elif type.name in ctx.structs:
            syntax = ctx.structs[type.name]
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

        if type.name in ctx.formats:
            concrete = resolve_type(
                type=syntax.type,
                path=path+[refname],
                values=loc_values,
                program=program,
                ctx=ctx
            )
            concrete.refname = refname
            if syntax.annotation is not None:
                concrete.desc.append(syntax.annotation.eval(loc_values))
            return concrete

        elif type.name in ctx.structs:
            return TmpRecord(name=pathname, fields=syntax.fields, syntax=syntax, values=loc_values)

        else:
            raise Exception(f"Unknown type: {refname}: {type}\n{program.formats}\n{ctx.formats}")

    elif isinstance(type, AstRecord):
        rec_values = copy.deepcopy(values)
        return TmpRecord(name=pathname, fields=type.fields, syntax=type, values=rec_values)

    elif isinstance(type, AstEnumType):
        arguments = [ 'width' ]
        casts = { 'width' : int }
        args = {}
        kw = False
        for (a,arg) in enumerate(type.arguments):
            if arg.name is None:
                if kw:
                    raise Exception(f"Found non-keyword argument after at least one keyword argument.")
                args.update({ arguments[a] : arg.value.eval(values=values) })
            else:
                kw = True
                args.update({ arg.name : arg.value.eval(values=values) })

        args = { k : casts[k](arg) if k in casts else arg for (k,arg) in args.items() }

        if type.kind == 'enum':
            assert isinstance(type.source, list)
            fmt = IrEnum(name=pathname, values=[ s.eval(values=values) for s in type.source ], **args)
            program.formats.update({ pathname : fmt })
            return fmt

        elif type.kind == 'repeat' or type.kind == 'select':
            path = IrPath(
                is_input=type.source.is_input,
                prompt=type.source.prompt,
                steps=[ ( step.name, range_from_slice(step.slice, values) ) for step in type.source.steps ]
            )
            fmt = IrChoice(name=pathname, path=path, mode=type.kind, **args)
            program.formats.update({ pathname : fmt })
            return fmt

        else:
            raise NotImplementedError(f"Process enum type:\n\t{type}")

    else:
        raise Exception(f"Unexpected class for AST type node: {type}")
    
def append_fields(prompt: IrPrompt, fields: List[AstField], parent: Union[IrPrompt,IrField], ihn_path:List[str], values:Dict[str,Any], program: IrProgram, ctx:Context):
    depth = 1 if isinstance(parent, IrPrompt) else parent.depth + 1
    for f,fld in enumerate(fields):
        fld_path = ihn_path+[fld.name]
        fmt = resolve_type(
            fld.type,
            fld_path,
            values=values,
            program=program,
            ctx=ctx
        ) # TODO accumulate values along path
        field = IrField(
            name=fld.name,
            format=None if isinstance(fmt, TmpRecord) else fmt,
            range=range_from_slice(fld.range, values),
            depth=depth,
            index=f,
            parent=parent
        )
        ctx.fields.update({ '.'.join(fld_path) : field })
        prompt.fields.append(field)
        if isinstance(fmt, TmpRecord):
            append_fields(
                prompt=prompt,
                fields=fmt.fields,
                parent=field,
                ihn_path=fld_path,
                values=fmt.values,
                program=program,
                ctx=ctx
            )
            if isinstance(fmt.syntax, AstStruct):
                for annotation in fmt.syntax.annotations:
                    path = fld_path + [ s.name for s in annotation.what.steps ]
                    path = '.'.join(path)
                    ctx.fields[path].desc.append(annotation.label.eval(fmt.values))

def compile_steps(steps: List[AstStep], values:Dict[str,Any]):
    return [ ( s.name, None if s.slice is None else s.slice.start.eval(values) ) for s in steps ]

def compile_channel(channel: AstChannel, values:Dict[str,Any]):
    assert not channel.target.is_input
    assert channel.target.prompt is None
    tgt = compile_steps(channel.target.steps, values)
    if isinstance(channel.source, AstPath):
        assert len(channel.source.steps) == 1
        assert channel.source.steps[0].slice is None
        src = compile_steps(channel.source.steps, values)
        if channel.source.is_input:
            return IrInput(src=src, tgt=tgt)
        elif channel.source.prompt is not None:
            return IrDataflow(prompt=channel.source.prompt, src=src, tgt=tgt)
        else:
            return IrDataflow(prompt=None, src=src, tgt=tgt)
    elif isinstance(channel.source, AstCall):
        kwargs = {
            kwarg.name : IrKwarg(
                is_input=kwarg.source.is_input,
                prompt=kwarg.source.prompt,
                path=compile_steps(kwarg.source.steps, values),
                mapped=kwarg.mapped
            ) for kwarg in channel.source.kwargs
        }
        binds = {}
        for bind in channel.source.binds:
            assert not bind.source.is_input
            assert bind.source.prompt is None
            binds.update({ bind.target : compile_steps(bind.source.steps, values) })
        return IrCall(
            extern=channel.source.extern,
            entry=channel.source.entry,
            kwargs=kwargs,
            binds=binds,
            tgt=tgt
        )
    else:
        raise Exception(f"Unexpected channel source: {channel.source}")

def compile_prompt(ast: AstPrompt, program: IrProgram, ctx:Context):
    prompt = IrPrompt(name=ast.name)
    values = {} # TODO from global and prompt variables
    append_fields(
        prompt=prompt,
        fields=ast.fields,
        parent=prompt,
        ihn_path=[ast.name],
        values=values,
        program=program,
        ctx=ctx
    )

    for annotation in ast.annotations:
        annot = annotation.label.eval(values)
        if len(annotation.what.steps) > 0:
            path = [ast.name] + [ s.name for s in annotation.what.steps ]
            path = '.'.join(path)
            ctx.fields[path].desc.append(annot)
        else:
            prompt.desc.append(annot)

    for channel in ast.channels:
        prompt.channels.append(compile_channel(channel, values))

    for flow in ast.flows:
        tgt = flow.prompt if flow.alias is None else flow.alias.eval(values)
        assert not tgt in prompt.flows

        limit = 1 if flow.limit is None else flow.limit.eval(values)
        ctrl = IrControl( prompt=flow.prompt, limit=limit )
        prompt.flows.update({ tgt : ctrl })

    if ast.returns is not None:
        tgt = 'return' if ast.returns.alias is None else ast.returns.alias.eval(values)
        assert not tgt in prompt.flows
        fields = {}
        if len(ast.returns.fields) == 1 and (ast.returns.fields[0].rename is None or ast.returns.fields[0].rename == '_'):
            field = ast.returns.fields[0]
            assert not field.field.is_input
            assert field.field.prompt is None
            path = compile_steps(field.field.steps, values)
            fields.update({ '_' : path })
        else:
            for field in ast.returns.fields:
                assert not field.field.is_input
                assert field.field.prompt is None
                path = compile_steps(field.field.steps, values)
                fld = path[-1][0] if field.rename is None else field.rename.eval(values)
                fields.update({ fld : path })
        prompt.flows.update({ tgt : IrReturn(fields=fields) })

    return prompt

def compile(arch:"CogArch", tag:str, source:str):
    program = IrProgram()
    ctx = Context()

    ast = frontend(source)

    ctx.formats.update({ s.name : s for s in ast.formats })
    ctx.structs.update({ s.name : s for s in ast.structs })

    program.prompts.update({ prompt.name : compile_prompt(prompt, program, ctx) for prompt in ast.prompts })

    stas = {}
    for (ptag,prompt) in program.prompts.items():
        sta = STA(prompt=prompt)
        sta.build_abstract()
        sta.build_concrete()
        stas.update({ptag:sta})

    return CogAutomaton(tag=tag, arch=arch, program=program, prompts=stas)
