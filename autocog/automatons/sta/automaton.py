from typing import Any, Dict, List, Tuple, Union, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel
import asyncio

import os, copy

from ..automaton import Automaton
from ..format import Text, Enum, Regex, Repeat, Record, ControlEdge
from ..port import Input

from ...architecture.orchestrator import Orchestrator

from .machine import VirtualState
from .prompt import StructuredThoughtPrompt

class StructuredThoughtAutomaton(Automaton):
    entry: str
    description: str = ''
    prompts:  Dict[str,StructuredThoughtPrompt]
    outputs: List[Tuple[StructuredThoughtPrompt,List[VirtualState]]] = []
    externs: Dict[str,Any] = {}
    inputs: List[str] = []

    @classmethod
    def __compile_formats(cls, formats:Dict):
        record_desc = 'Record mark the beginning of a nested prompt. It is always left empty.'
        if 'record' in formats:
            record_desc = formats['record'][0]
            del formats['record']

        text_desc = 'ASCII text in any form'
        text_count = 20
        if 'text' in formats:
            if len(formats['text'][0]) > 0:
                text_desc = formats['text'][0]
            if formats['text'][2] is not None:
                text_count = formats['text'][2]
            del formats['text']

        thought_desc = 'use thought to take notes as you perform a task (a few words per lines)'
        thought_base = 'text'
        thought_count = 15
        if 'thought' in formats:
            if len(formats['thought'][0]) > 0:
                thought_desc = formats['thought'][0]
            if formats['thought'][1] is not None:
                thought_base = formats['thought'][1]
            if formats['thought'][2] is not None:
                thought_count = formats['thought'][2]
            del formats['thought']

        bool_desc = 'a boolean value use either True/False or yes/no'
        bool_choices = [
            "True", "False", "TRUE", "FALSE", "true", "false",
            "Yes", "No", "YES", "NO", "yes", "no"
        ]
        bool_caster = lambda x: x.lower() == 'yes' or x.lower() == 'true'
        if 'bool' in formats:
            if len(formats['bool'][0]) > 0:
                bool_desc = formats['bool'][0]
            del formats['bool']
        res = {
          'record'  : Record (label='record',  desc=record_desc                                              ),
          'text'    : Text   (label='text',    desc=text_desc,    max_token=text_count                       ),
          'thought' : Text   (label='thought', desc=thought_desc, max_token=thought_count, base=thought_base ),
          'bool'    : Enum   (label='bool',    desc=bool_desc,    choices=bool_choices, caster=bool_caster   ),
        }
        for (lbl,(desc,parent,max_tok)) in formats.items():
            if parent is None:
                parent = 'text'
            if parent.startswith("enum="):
                fmt = Enum(label=lbl, desc=desc, choices=parent.split('=')[1].split(','))
            elif parent.startswith("repeat="):
                fmt = Repeat(label=lbl, desc=desc, source=parent.split('=')[1].split('.'))
            else:
                if max_tok is None:
                    max_tok = 0
                fmt = Text(label=lbl, desc=desc, max_token=max_tok, base=parent )
            res.update({ lbl : fmt })
        return res

    @classmethod
    def compile(cls, tag:str, entry:str, prompts:Dict[str,Any], outputs:List, formats:Dict, config:Dict[str,Any], description:str, orchestrator:Orchestrator):
        for ptag in prompts:
            if ptag.find('.') != -1:
                raise Exception("Prompt tag cannot contain '.' only letters, digits, and underscore.")

        sta = cls(
            tag=tag, entry=entry, description=description, orchestrator=orchestrator, formats=cls.__compile_formats(formats),
            prompts={ ptag : StructuredThoughtPrompt.create(ptag=ptag, desc=prompt['desc'], stmts=prompt['stmts'], **config) for (ptag,prompt) in prompts.items() }
        )

        for (ptag,prompt) in prompts.items():
            sta.formats.update({ f'{ptag}.next' : ControlEdge(desc=prompt['next'][1], edges=prompt['next'][0]) })
            sta.prompts[ptag].formats.update({ 'next' : sta.formats[f'{ptag}.next'] })

        for (ptag,prompt) in prompts.items():
            for channel in prompt['channels']:
                sta.inputs += sta.prompts[ptag].add_channel(desc=channel)

        for (ptag,prompt) in sta.prompts.items():
            for (vtag,vs) in prompt.stm.states.items():
                if vs.fmt == 'next':
                    continue
                if not vs.fmt in sta.formats:
                    raise Exception(f"Referencing unknown format: {vs.fmt}")
                if vtag != prompt.stm.tag:
                    fmt = vs.fmt
                    while fmt is not None:
                        F = sta.formats[fmt]
                        if not fmt in prompt.formats:
                            prompt.formats.update({ fmt : F })
                        if issubclass(F.__class__, Text):
                            fmt = F.base
                        else:
                            fmt = None

        for o in outputs:
            if not isinstance(o, dict):
                raise Exception("")
            if not 'prompt' in o:
                raise Exception("")
            if not 'source' in o:
                raise Exception("")
            if len(o) != 2:
                raise Exception("")
            (ptag,stags) = (o['prompt'],o['source'])
            if not isinstance(ptag, str):
                raise Exception("")
            if not isinstance(stags, list):
                raise Exception("")
            sta.outputs.append(( sta.prompts[ptag] , [ sta.prompts[ptag].stm.get_candidate_vstate(stag) for stag in stags ] ))

        #sta.inputs = list(set(sta.inputs))
        sta.externs = {} # TODO detect extern during compilation

        return sta

    @classmethod
    def preprocess(cls, program:str, **kwargs):
        program = program.split('\n')
        # TODO fold lines ending with \
        program = list(filter(lambda x: not x.startswith('#'), program))
        macros  = list(filter(lambda x: x.startswith('?'),     program))
        program = list(filter(lambda x: not x.startswith('?'), program))
        # TODO special characters (\n,\t) in macros and descriptions

        for m in macros:
            (k,v) = m[1:].split('=')
            if not k in kwargs:
                kwargs.update({k:v})

        reserved = [ 'automaton', 'prompt', 'mechanics', 'formats' ]
        writable = [ 'preamble', 'basics', 'mechs', 'fmts', 'postscriptum', 'header' ]

        for r in reserved + writable:
            if r in kwargs:
                raise Exception("Found (reserved) key '{r}' in kwargs when loading a STA!")
            kwargs.update({ r : '{'+r+'}' })

        preproc_program = []
        stp_kwargs = {}
        for line in program:
            used = False
            for r in writable:
                if line.startswith(f'{r}:'):
                    used = True
                    stp_kwargs.update({ r : line[len(r)+2:].strip() })
                    break
            if len(line) > 0 and not used:
                preproc_program.append(line)
        program = '\n'.join(preproc_program).format(**kwargs)

        fmt_line = None
        entry_line = None
        prompt_lines = []
        program = program.split('\n')
        for (l,line) in enumerate(program):
            if line.startswith("entry("):
                entry_line = l
            elif line.startswith("formats:"):
                fmt_line = l
            elif line.startswith("prompt("):
                prompt_lines.append(l)

        return ( fmt_line, entry_line, prompt_lines, program, stp_kwargs )

    @classmethod
    def parse_formats(cls, program:str, fmt_line:Optional[int]=None):
        formats = {}
        if fmt_line is not None:
            fmt_line += 1
            while fmt_line < len(program) and program[fmt_line].startswith('- '):
                (k,v) = program[fmt_line][2:].split(':')
                k = k.strip().split('(')
                if len(k) == 1:
                    p = None
                    k = k[0].strip()
                    l = None
                else:
                    p = k[1][:-1].strip()
                    k = k[0].strip()
                    l = p.split('[')
                    if len(l) == 1:
                        l = None
                    else:
                        p = l[0]
                        l = l[1][:-1]
                        l = int(l)
                formats.update({ k : ( v.strip(), p, l ) })
                fmt_line += 1
            assert fmt_line < len(program)
        return formats

    @classmethod
    def parse_channels(cls, program:str, p:int):
        channels = []
        while p < len(program) and program[p].startswith('- '):
            channel = {}
            args = program[p][2:].strip()
            idx = 0
            while idx < len(args):
                paren = args[idx:].find("(")
                space = args[idx:].find(" ")

                key = None
                value = None
                if paren == -1 and space == -1:
                    key = args[idx:]
                    idx = len(args)
                elif paren == -1:
                    key = args[idx:idx+space]
                    idx += space + 1
                elif space == -1:
                    key = args[idx:idx+paren]
                    idx += paren + 1
                    assert args[-1] == ')'
                    value = args[idx:-1].strip()
                    idx = len(args)
                elif paren < space:
                    key = args[idx:idx+paren]
                    idx += paren + 1
                    rparen = args[idx:].find(')')
                    assert rparen > 0
                    value = args[idx:idx+rparen].strip()
                    idx += rparen + 1
                elif space < paren:
                    key = args[idx:idx+space]
                    idx += space + 1
                else:
                    raise Exception("Not expected...")

                while idx < len(args) and args[idx] == ' ':
                    idx += 1

                assert key is not None
                assert len(key) > 0

                if key == 'target' or key == 'source' or key == 'call':
                    channel.update({ key : value })
                elif key == 'kwargs':
                    (k,v) = list(map(lambda x: x.strip(), value.split(',')))
                    if not 'kwargs' in channel:
                        channel.update({'kwargs':{}})
                    channel['kwargs'].update({ k : v })
                else:
                    raise Exception(f"Unknow channel parameter: {key}")

            channels.append(channel)
            p += 1
        return (channels, p)

    @classmethod
    def parse_statements(cls, program:List, p:int, indent:str='> '):
        stmts = []
        while p < len(program) and program[p].startswith(indent):
            depth = 0
            stmt = program[p]
            while len(stmt) > 0:
                if stmt.find(indent) == 0:
                    stmt = stmt[len(indent):]
                    depth += 1
                else:
                    break

            lbl_pos = None
            desc_pos = stmt.find(':')
            assert desc_pos > 0
            desc = stmt[desc_pos+1:].strip()

            cnt_pos = stmt.find('[')
            if cnt_pos > 0 and cnt_pos < desc_pos:
                is_list = True
                lbl_pos = cnt_pos
                t = stmt.find(']')
                assert t > cnt_pos+1
                list_range = list(map(int,stmt[cnt_pos+1:t].split(',')))
                if len(list_range) == 1:
                    list_range = (list_range[0],list_range[0])
                elif len(list_range) == 2:
                    list_range = (list_range[0],list_range[1])
                else:
                    raise Exception()
            else:
                is_list = False
                list_range = None

            fmt_pos = stmt.find('(')
            if fmt_pos > 0 and fmt_pos < desc_pos:
                if lbl_pos is None:
                    lbl_pos = fmt_pos
                t = stmt.find(')')
                fmt = stmt[fmt_pos+1:t].strip()
            else:
                fmt = None

            if lbl_pos is None:
                lbl_pos = desc_pos

            label = stmt[:lbl_pos].strip()

            stmts.append(( depth, label, is_list, list_range, fmt, desc ))
            p += 1

        path = []
        for s in range(len(stmts)):
            ( depth, label, is_list, list_range, fmt, desc ) = stmts[s]
            # print(f"depth={depth} label={label}")
            if len(path) < depth:
                assert depth - len(path) == 1, "Can only stack one at the time"
                path.append( (0, label) )
            elif len(path) > depth:
                path = path[:depth]
                path[-1] = ( path[-1][0]+1, label )
            else:
                path[-1] = ( path[-1][0]+1, label )

            if fmt is None and ( (s == len(stmts) - 1) or stmts[s+1][0] <= depth ):
                fmt = 'text'
            elif fmt is None:
                assert stmts[s+1][0] - depth == 1, "Can only stack one at the time"
                fmt = 'record'

            stmts[s] = ( label, copy.deepcopy(path), { 'is_list' : is_list, 'list_range' : list_range, 'fmt' : fmt, 'desc' : desc } )
        return (stmts, p)

    @classmethod
    def parse_prompts(cls, program:str, prompt_lines:List[int]=[]):
        prompts = {}
        outputs = []
        for p in prompt_lines:
            (ptag,prompt_desc) = program[p][len("prompt("):].split('):')
            ptag = ptag.strip()
            prompt_desc = prompt_desc.strip()
            p += 1

            (channels, p) = cls.parse_channels(program=program, p=p)
            (stmts, p) = cls.parse_statements(program=program, p=p, indent='> ')

            next = []
            next_desc = ''
            assert p < len(program) and program[p].startswith('__')
            if program[p].startswith('__next'):
                next = program[p][len('__next('):].split('):')
                next_desc = next[1].strip() 
                next = list(map(lambda x: x.strip(), next[0].split(',')))
                next = [ [n,None] if n.find('[') == -1 else [n.split('[')[0], int(n.split('[')[1][:-1])] for n in next ]
            elif program[p].startswith('__exit'):
                outs = program[p][len('__exit('):].split('):')[0].split(',')
                outs = map(lambda x: x.strip(), outs)
                outputs += [ { 'prompt' : ptag, 'source' : list(outs) } ]
            else:
                raise Exception("Unknown statement")

            prompts.update({ ptag : { 'desc' : prompt_desc, 'channels' : channels, 'stmts' : stmts, 'next' : ( next, next_desc ) }})

        return (prompts, outputs)

    @classmethod
    def parse(cls, program:str, **kwargs):
        ( fmt_line, entry_line, prompt_lines, program, kwargs ) = cls.preprocess(program=program, **kwargs)

        if entry_line is None:
            raise Exception("Must specify an entry point.")
        (entry,sta_desc) = program[entry_line][len('entry('):].split('):')
        sta_desc = sta_desc.strip()

        formats = cls.parse_formats(program=program, fmt_line=fmt_line)
        (prompts, outputs) = cls.parse_prompts(program=program, prompt_lines=prompt_lines)

        return ({ 'formats' : formats, 'entry' : entry, 'outputs' : outputs, 'prompts' : prompts, 'description' : sta_desc }, kwargs)

    def toGraphViz(self):
        dotstr = 'ranksep=1;\n'
        dotstr = self.tag.replace('-','_') + '_entry [label="",shape="diamond"];\n'

        dotstr += "subgraph cluster_" + self.tag.replace('-','_') + "_inputs {\n"
        for i in self.inputs:
            in_tag = f"{self.tag}_input_{i.key.path(True)}".replace('-','_').replace('[','_').replace(']','_').replace('.','_')
            dotstr += f"  {in_tag} [label=\"{i.key.path(True)}\", shape=\"octagon\"]\n"
        dotstr += "}\n"

        for (ptag,prompt) in self.prompts.items():
            dotstr += "subgraph cluster_" + self.tag.replace('-','_') + "_" + ptag + " {\n"
            dotstr += prompt.stm.toGraphViz() + "\n"
            dotstr += "}\n"

        for (ptag,prompt) in self.prompts.items():
                for ntag in prompt.formats['next'].choices:
                    dotstr += f"  {ptag}_exit -> {ntag}_root [constraint=True];\n"
        dotstr += f"  {self.tag.replace('-','_')}_entry -> {self.entry}_root [constraint=True];\n"

        path_to_vs = { ptag : { vs.p() : vs for (stag,vs) in prompt.stm.states.items() } for (ptag,prompt) in self.prompts.items() }
        for (ptag,prompt) in self.prompts.items():
            for (c,channel) in enumerate(prompt.channels):
                tgt_tag = prompt.stm.gv_state_tag(state=path_to_vs[prompt.stm.tag][channel.target.path()])
                if channel.source is not None:
                    if isinstance(channel.source, Input):
                        src_tag = f"{self.tag}_input_{channel.source.key.path(True)}".replace('-','_').replace('[','_').replace(']','_').replace('.','_')
                    else:
                        src_ptag = channel.source.tag
                        if src_ptag is None:
                            src_ptag = ptag
                        src_tag = self.prompts[src_ptag].stm.gv_state_tag(state=path_to_vs[src_ptag][channel.source.path.path()])
                elif channel.call is not None:
                    raise NotImplementedError() # TODO
                else:
                    raise Exception("Should not happen")
                dotstr += f"  {src_tag} -> {tgt_tag} [constraint=False, style=dashed];\n"

        return dotstr

    async def __call__(self, fid:int, **inputs) -> Tuple[Dict[str,Union[str,List[str]]],Any]:

        # TODO backup formats.next from each prompt
        nexts = {}
        for prompt in self.prompts.values():
            nexts.update({ prompt.stm.tag : prompt.formats['next'].copy(deep=True) })

        scratch = { k[0] : v for (k,v) in inputs.items() if k[0] == '@' }
        inputs  = { k    : v for (k,v) in inputs.items() if k[0] != '@' }
        stacks = { ptag : [] for ptag in self.prompts }
        stacks.update({ '__inputs__' : inputs, '__scratch__' : scratch })

        path = []
        current = self.prompts[scratch['entry'] if 'entry' in scratch else self.entry]
        while current != None:
            stacks[current.stm.tag].append(await current.execute(
                fid=fid, stacks=stacks, orchestrator=self.orchestrator, automaton_desc=self.description, path=path
            ))
            path.append(current.stm.tag)
            # print(f"stacks[current.stm.tag][-1]={stacks[current.stm.tag][-1]}")
            current = stacks[current.stm.tag][-1].next
            if current is not None:
                current = self.prompts[current]

        result = {}
        for (prompt,vss) in self.outputs:
            for vs in vss:
                res = stacks[prompt.stm.tag][-1].ravel(vs.label)
                if len(res) == 1:
                    res = res[0]
                result.update({ vs.label : res})

        for (ptag,fmt) in nexts.items():
            self.prompts[ptag].formats.update({ 'next' : fmt })

        return ( result, stacks )