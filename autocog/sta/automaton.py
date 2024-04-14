
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable, Union
from abc import abstractmethod
from pydantic import BaseModel

import copy
import time
import numpy

from .ir import Prompt     as IrPrompt
from .ir import Field      as IrField
from .ir import Completion as IrCompletion
from .ir import Enum       as IrEnum
from .ir import Choice     as IrChoice
from .ir import Input      as IrInput
from .ir import Dataflow   as IrDataflow
from .ir import Call       as IrCall
from .ir import Control    as IrControl

from .runtime import Frame

from .syntax import Syntax

from ..fta.automaton import FiniteThoughtAutomaton as FTA
from ..fta.automaton import FiniteTokenTree as FTT
from ..fta.actions import Action, Choose, Complete, Text

from ..lm.lm import LM

class AbstractState(BaseModel):
    field: Optional[IrField] = None

    flow: Optional["AbstractState"] = None
    exit: Optional["AbstractState"] = None

    def depth(self):
        return 0 if self.field is None else self.field.depth

    def tag(self):
        return "root" if self.field is None else self.field.tag()

    def parents(self):
        parents = []
        parent = self.field
        while isinstance(parent, IrField):
            parents = [ parent ] + parents
            parent = parent.parent
        return parents

    def label(self):
        path = []
        parent = self.field
        if parent is None:
            return 'root'
        while isinstance(parent, IrField):
            path = [ parent.name ] + path
            parent = parent.parent
        return '.'.join(path)

    def name(self):
        return "root" if self.field is None else self.field.name

class ConcreteState(BaseModel):
    abstract:   AbstractState
    indices:    List[int]
    flows:      List[str] = []
    exits:      List[str] = []
    successors: List[str] = []

    @staticmethod
    def make_tag(abstract, indices):
        return f"{abstract.tag()}@{'_'.join(map(str,indices))}"

    @staticmethod
    def make_label(abstract, indices):
        fields = []
        parent = abstract.field
        if parent is None:
            return 'root'
        while isinstance(parent, IrField):
            fields = [ parent ] + fields
            parent = parent.parent

        return '.'.join([ f"{f.name}[{i}]" if f.is_list() else f"{f.name}" for (f,i) in zip(fields,indices) ])

    def tag(self):
        return ConcreteState.make_tag(self.abstract, self.indices)

    def name(self):
        return self.abstract.name()

    def index(self):
        return ','.join(map(str,self.indices))

    def path(self):
        res = []
        for (p,i) in zip(self.abstract.parents(), self.indices):
            res.append( (p.name, i if p.is_list() else None) )
        return res

    def label(self):
        return ConcreteState.make_label(self.abstract,self.indices)
    
    def coords(self):
        if self.abstract.field is None:
            return []
        coord = []
        for (i,j) in zip(self.abstract.field.coords(), self.indices):
            coord.append(i)
            coord.append(j)
        return coord

    def prompt(self, syntax):
        field = self.abstract.field
        indent = syntax.prompt_indent * len(self.indices)
        prompt = indent + self.name()
        if syntax.prompt_with_format:
            fmt = '(record)' if field.is_record() else '(' + field.format.label() + ')'
            prompt += fmt
        if syntax.prompt_with_index:
            idx = self.indices[-1]
            if not prompt_zero_index:
                idx += 1
            idx = f'[{idx}]' if field.is_list() else ''
            prompt += idx
        prompt += ':'
        return prompt

class Automaton(BaseModel):
    prompt: IrPrompt
    abstracts: Dict[str,AbstractState] = {}
    concretes: Dict[str,ConcreteState] = {}

    def build_abstract(self):
        assert len(self.abstracts) == 0
        root = AbstractState()
        self.abstracts.update({ 'root' : root })
        stack: List[List[AbstractState]] = [ [ root ] ]

        for fld in self.prompt.fields:
            state = AbstractState(field=fld)
            if fld.range is not None:
                state.flow = state
            self.abstracts.update({ state.label() : state })

            prev = stack[-1][-1]
            if fld.index == 0:
                assert fld.depth == len(stack)
                prev.flow = state
                stack.append([])

            elif fld.depth < prev.depth():
                stack = stack[:fld.depth+1]
                prev.exit = stack[-1][-1]
                stack[-1][-1].exit = state

            else:
                prev.exit = state

            stack[-1].append(state)

        for i in range(len(stack)-1):
            stack[i+1][-1].exit = stack[i][-1]

        return self

    def build_concrete_rec(self, abstract:AbstractState, indices:List[int]=[0], indent=0):
        curr = abstract.tag()
        current = abstract.field
        depth = abstract.depth()
        parents = abstract.parents()

        assert len(indices) == depth + 1
        count = indices[-1]

        if current is not None:
            is_list   = current.is_list()
            is_record = current.is_record()
        else:
            is_list   = False
            is_record = True

        if is_list:
            flows = count <  current.range[1]
            exits = count >= current.range[0]
        elif is_record:
            flows = count == 0
            exits = count >  0
        else:
            flows = True
            exits = True

        flows = flows and (abstract.flow is not None)
        exits = exits and (abstract.exit is not None)

        ctag = ConcreteState.make_tag(abstract=abstract, indices=indices[1:])
        if ctag in self.concretes:
            return ctag
        
        concrete = ConcreteState(abstract=abstract, indices=indices[1:])
        self.concretes.update({ ctag : concrete })

        if flows:
            new_indices = copy.deepcopy(indices)
            if abstract.depth() < abstract.flow.depth():
                assert abstract.flow.depth() - abstract.depth() == 1
                new_indices.append(0)
            else:
                assert abstract.tag() == abstract.flow.tag()
                new_indices[-1] += 1
            next = self.build_concrete_rec(abstract=abstract.flow, indices=new_indices, indent=indent+1)
            concrete.flows.append(next)

        if exits:
            new_indices = copy.deepcopy(indices)
            if abstract.depth() > abstract.exit.depth():
                delta = abstract.depth() - abstract.exit.depth()
                new_indices = new_indices[:-delta]
                new_indices[-1] += 1
            else:
                new_indices[-1] = 0
            next = self.build_concrete_rec(abstract=abstract.exit, indices=new_indices, indent=indent+1)
            concrete.exits.append(next)

        return concrete.tag()
    
    def get_sequence(self):
        sequence = ['root@']
        while True:
            state = self.concretes[sequence[-1]]
            assert len(state.successors) <= 1
            if len(state.successors) == 1 and state.successors[0] != 'root@':
                sequence.append(state.successors[0])
            else:
                break
        return sequence

    def get_reversed_exits(self, sequence):    
        reversed_exits = {}
        for s in sequence:
            for e in self.concretes[s].exits:
                if e == 'root@':
                    continue
                if e in reversed_exits:
                    if not s in reversed_exits[e]:
                        reversed_exits[e].append(s)
                else:
                    reversed_exits.update({ e : [ s ] })
        return reversed_exits

    def exit_closure(self, exits):
        exits = copy.deepcopy(exits)
        closure = []
        while len(exits) > 0:
            todos = []
            for e in exits:
                if not e in closure:
                    closure.append(e)
                    state = self.concretes[e]
                    todos += state.exits
            exits = todos
        return closure
    
    def build_concrete(self):
        self.build_concrete_rec(abstract=self.abstracts['root'])

        for (tag, state) in self.concretes.items():
            if len(state.flows) > 0:
                assert len(state.flows) == 1
                assert len(state.exits) <= 1
                state.successors.append(state.flows[0])
                state.flows.clear()
            else:
                assert len(state.exits) == 1
                if state.exits[0] != 'root@':
                    state.successors.append(state.exits[0])
                    state.exits.clear()

        sequence = self.get_sequence()
        reversed_exits = self.get_reversed_exits(sequence)

        delete_set = []
        prev_deleted = False
        last_kept = None
        for (s,stag) in enumerate(sequence):

            state = self.concretes[stag]

            crange = None if state.abstract.field is None else state.abstract.field.range
            is_list_tail = crange is not None and state.indices[-1] >= crange[1]

            if is_list_tail:
                delete_set.append(stag)
                assert len(state.exits) == 0 or state.exits[0] == 'root@'
                if len(state.exits) == 1:
                    pred = self.concretes[sequence[s-1]]
                    assert len(pred.successors) == 1
                    assert pred.successors[0] == stag
                    pred.successors.clear()
                elif stag in reversed_exits:
                    assert len(state.successors) == 1, "Last node is the target of exit edges! Probably means that the last statement (at any level) is a list with variable number of elements."
                    succ = state.successors[0]
                    if not succ in reversed_exits:
                        reversed_exits.update({ succ : [] })
                    for e in reversed_exits[stag]:
                        if not e in reversed_exits[succ]:
                            reversed_exits[succ].append(e)
                    del reversed_exits[stag]
                prev_deleted = True
            else:
                if prev_deleted:
                    last_kept.successors = [ stag ]
                last_kept = state
                prev_deleted = False

        for stag in delete_set:
            del self.concretes[stag]

        for state in self.concretes.values():
            state.exits.clear()

        for (sink,srcs) in reversed_exits.items():
            for src in srcs:
                self.concretes[src].exits.append(sink)

        sequence = self.get_sequence()
        for (s,stag) in enumerate(sequence):
            state = self.concretes[stag]
            pred = self.concretes[sequence[s-1]] if s > 0 else None
            assert len(state.exits) == 0 or pred is not None
            exits = self.exit_closure(state.exits)
            for e in exits:
                if not e in pred.successors:
                    pred.successors.append(e)
            state.exits.clear()

    def filter_successors(self, frame: Frame, concrete: ConcreteState):
        order_by_coords = lambda cs: list(sorted(cs, key=lambda c: c.coords()))
        successors = order_by_coords([ self.concretes[succ] for succ in concrete.successors ])
        if len(successors) <= 1:
            return successors

        candidates = []
        for succ in successors:
            lbl = succ.label()
            state = frame.state[lbl]
            if state is None:
                candidates.append(succ)
            elif state is False:
                pass
            elif state is True:
                candidates.append(succ)
                break
            else:
                raise Exception(f"Unexpected state for {lbl}: {state}")

        assert len(candidates) > 0
        if len(candidates) == 1:
            return candidates

        return candidates

    def instantiate_rec(self, syntax: Syntax, frame: Frame, fta: FTA, concrete: ConcreteState):
        successors = self.filter_successors(frame=frame, concrete=concrete)
        ctag = concrete.tag().replace('@','_')
        branch = f'branch.{ctag}'
        if len(successors) == 0:
            return None
        elif len(successors) == 1:
            fta.create(uid=branch, cls=Text, text=successors[0].prompt(syntax))
        else:
            choices = [ succ.prompt(syntax) for succ in successors ]
            fta.create(uid=branch, cls=Choose, choices=choices)

        for successor in successors:
            lbl = successor.label()
            tag = successor.tag().replace('@','_')

            uid = f'field.{tag}'
            if successor.abstract.field.format is None:
                prev = branch
            else:
                fmt = successor.abstract.field.format
                if frame.state[lbl] is True:
                    path = [ ( p.name, i if p.is_list() else None ) for (p,i) in zip(successor.abstract.parents(), successor.indices) ]
                    fta.create(uid=uid, cls=Text, text=frame.read(path))
                elif isinstance(fmt, IrCompletion):
                    fta.create(uid=uid, cls=Complete, length=fmt.length, stop='\n')
                elif isinstance(fmt, IrEnum):
                    fta.create(uid=uid, cls=Choose, choices=fmt.values, width=fmt.width)
                elif isinstance(fmt, IrChoice):
                    assert not fmt.path.is_input
                    assert fmt.path.prompt is None
                    choices = frame.ravel(fmt.path.steps)
                    if fmt.mode == 'repeat':
                        pass
                    elif fmt.mode == 'select':
                        offset = 0 if syntax.prompt_zero_index else 1
                        choices = range(offset, offset + len(choices))
                    else:
                        raise Exception(f"Unexpected choice mode: {fmt.mode}")
                    choices = list(map(str,choices))
                    fta.create(uid=uid, cls=Choose, choices=choices, width=fmt.width)
                else:
                    raise Exception(f'Unknown format: {successor.abstract.field.format}')
                fta.connect(branch, uid)
                prev = uid

            endl = f'endl.{tag}'
            fta.create(uid=endl, cls=Text, text='\n')
            fta.connect(prev, endl)

            next = self.instantiate_rec(syntax=syntax, frame=frame, fta=fta, concrete=successor)
            if next is not None:
                fta.connect(endl, next)

        return branch

    def apply_source_to_data(self, src, data):
        if data is None:
            # TODO check that target is list with lower bound equal to zero
            return []

        for (fld,idx) in src:
            data = data[fld]
            if idx is not None:
                assert isinstance(data, list)
                data = data[idx]
        return data
        
    def collect_input_or_dataflow(self, channel, page, inputs):
        if isinstance(channel, IrInput):
            data = inputs

        elif isinstance(channel, IrDataflow):
            if channel.prompt is None:
                data = page.stacks[self.prompt.name]
                data = data[-2].data if len(data) > 1 else None    
            else:
                data = page.stacks[channel.prompt]
                data = data[-1].data if len(data) > 0 else None

        return self.apply_source_to_data(channel.src, data)

    def jobs_from_kwargs(self, kwargs, page, inputs):
        jobs = [ {} ]
        for (kw,arg) in kwargs.items():
            if arg.is_input:
                data = inputs
            else:
                raise NotImplementedError("Collect non-input kwargs")
            data = self.apply_source_to_data(arg.path, data)
            if arg.mapped:
                assert isinstance(data,list)
                njobs = []
                for d in data:
                    for job in jobs:
                        njob = copy.deepcopy(job)
                        njob.update({ kw : d })
                        njobs.append(njob)
                jobs = njobs
            else:
                for job in jobs:
                    job.update({ kw : data })

        return jobs

    async def execute_calls(self, arch, channel, page, inputs):

        tag = page.ctag if channel.extern is None else channel.extern
        jobs = self.jobs_from_kwargs(channel.kwargs, page, inputs)
        jobs = [ (tag,channel.entry,job) for job in jobs ]

        results = await arch.orchestrator.execute(jobs=jobs, parent=page.id, progress=False)

        data = []
        for result in results:
            for (kw,path) in channel.binds.items():
                assert len(path) == 1
                assert path[0][1] is None
                okw = path[0][0]
                val = result[okw]
                del result[okw]
                result.update({ kw : val })
            data.append(result)
        return data
        
    async def assemble(self, arch, page, inputs: Any):
        if not self.prompt.name in page.stacks:
            page.stacks.update({ self.prompt.name : [] })

        abstracts = { st.label() : ( st, {} ) for st in self.abstracts.values() }
        concretes = {}
        for st in self.concretes.values():
            albl = st.abstract.label()
            clbl = st.label()
            abstracts[albl][1].update({ clbl : st })
            concretes.update({ clbl : st })

        frame_state = { st.label() : None for st in self.concretes.values() if st.abstract.field is not None }
        frame = Frame(state=frame_state)
        page.stacks[self.prompt.name].append(frame)

        for channel in self.prompt.channels:
            if isinstance(channel, IrInput) or isinstance(channel, IrDataflow):
                data = self.collect_input_or_dataflow(channel, page, inputs)
            elif isinstance(channel, IrCall):
                data = await self.execute_calls(arch, channel, page, inputs)
            else:
                raise Exception(f"Unexpected channel: {channel}")
            frame.locate_and_insert(abstracts, concretes, channel.tgt, data)

        frame.finalize(abstracts, concretes)
        return frame

    def instantiate(self, syntax: Syntax, frame: Any, branches: Any, inputs: Any):
        fta = FTA()

        fta.create( uid='root', cls=Text, text=syntax.header(self.prompt))

        fta.connect('root', self.instantiate_rec(syntax=syntax, frame=frame, fta=fta, concrete=self.concretes['root@']))
        
        fta.create( uid='next.field', cls=Text, text='next: ')
        for (tag,act) in fta.actions.items():
            if tag != 'next.field' and len(act.successors) == 0:
                act.successors.append('next.field')

        next_choices = []
        for (ptag, flow) in self.prompt.flows.items():
            if isinstance(flow, IrControl) and flow.prompt in branches and branches[flow.prompt] >= flow.limit:
                continue
            next_choices.append(ptag)
        assert len(next_choices) > 0
        if len(next_choices) == 1:
            fta.create( uid='next.choice', cls=Text, text=next_choices[0])
        else:
            fta.create( uid='next.choice', cls=Choose, choices=next_choices)
        fta.connect('next.field', 'next.choice')
        return fta

    def parse(self, lm:LM, ftt:FTT, syntax: Syntax, stacks: Any):
        result = None

        results = ftt.results(lm=lm, normalized=True)
        # for r,res in enumerate(results):
        #     lines = res[0].split('\nstart:\n')[2].split('\n')
        #     print(f"[{r}]\n>  " + "\n>  ".join(lines) + f"\n[/{r}]")
        text = results[-1][0]
        lines = text.split('\nstart:\n')[2].split('\n')
        # print("[Lines]\n>  " + "\n>  ".join(lines) + "\n[/Lines]")

        abstracts = { st.label() : ( st, {} ) for st in self.abstracts.values() }
        
        frame = stacks[self.prompt.name][-1]
        prompts = { tag : state.prompt(syntax) for (tag,state) in self.concretes.items() if tag != 'root@' }
        curr = self.concretes['root@']
        idx = 0
        data = []
        while idx < len(lines) - 1:
            line = lines[idx]
            # print(f"  @{idx}: {line}")
            value = None
            for succ in curr.successors:
                pos = line.find(prompts[succ])
                if pos >= 0:
                    curr = self.concretes[succ]
                    value = line[pos + len(prompts[succ]):].strip()
                    break
            assert value is not None, f"Line \"{line}\" does not start with any of {[ prompts[succ] for succ in curr.successors ]}"
            lbl = curr.label()
            if frame.state[lbl] is None:
                frame.state[lbl] = True
                data.append( (curr,value) )
            idx += 1

        to_concrete_label = lambda path: '.'.join([ p if i is None else f"{p}[{i}]" for (p,i) in path ])
        for (curr,value) in data:
            if curr.abstract.field.is_list():
                path = curr.path()
                list_lbl = to_concrete_label(path[:-1] + [ ( path[-1][0], None) ])
                # statements are in order so I only care about the last so I simply overwrite
                frame.counts.update({ list_lbl : path[-1][1] + 1 })

        for (curr,value) in data:
            if not curr.abstract.field.is_record():
                fmt = curr.abstract.field.format
                if isinstance(fmt, IrChoice) and fmt.mode == 'select':
                    value = int(value)
                frame.write(abstracts, curr.path(), value)

        pos = lines[-1].find("next:")
        assert pos >= 0, f"Should find \"next: \" in \"{lines[-1]}\"!"
        next = lines[-1][pos+len("next:"):].strip()
        assert next in self.prompt.flows, f"next=\"{next}\" from line=\"{lines[-1]}\" not found in the prompts flow"
        next = self.prompt.flows[next]

        return next

    def toGraphViz_abstract(self):
        dotstr = ''
        for state in self.abstracts.values():
            dotstr += f'{self.prompt.name}_{state.tag()} [label="{state.label()}"];\n'
            if state.flow is not None:
                constraint = 'true'
                if state.field is None:
                    label = ''
                    color = 'blue'
                elif state.field.range is None:
                    label = ''
                    color = 'blue'
                else:
                    label = f'i < {state.field.range[1]}'
                    color = 'green'
                dotstr += f'{self.prompt.name}_{state.tag()} -> {self.prompt.name}_{state.flow.tag()} [label="{label}", color={color}, constraint={constraint}];\n'
            if state.exit is not None:
                constraint = 'false'
                if state.exit.depth() == state.depth():
                    constraint = 'true'
                if state.field is None:
                    assert False, f'{self.prompt.name}_{state.tag()} -> {self.prompt.name}_{state.exit.tag()}'
                elif state.field.range is None:
                    label = ''
                    color = 'purple'
                else:
                    label = f'i >= {state.field.range[0]}'
                    color = 'red'
                dotstr += f'{self.prompt.name}_{state.tag()} -> {self.prompt.name}_{state.exit.tag()} [label="{label}", color={color}, constraint={constraint}];\n'
        return dotstr
        
    def toGraphViz_concrete(self):
        dotstr = ''
        for curr in self.concretes.values():
            crange = None if curr.abstract.field is None else curr.abstract.field.range
            is_list_tail = crange is not None and curr.indices[-1] >= crange[1]
            is_record_node = ( curr.abstract.field is None ) or ( curr.abstract.field.format is None )

            fillcolor = "white"
            if is_list_tail:
                fillcolor = "red"
            elif is_record_node:
                fillcolor = "blue"
            elif crange is not None:
                fillcolor = "orange"
            else:
                fillcolor = "gray"

            dotstr += f'{curr.tag()} [label="{curr.label()}", fillcolor="{fillcolor}", style="filled"];\n'

            for next in curr.flows:
                dotstr += f'{curr.tag()} -> {next} [color=green, constraint=false];\n'
            for next in curr.exits:
                dotstr += f'{curr.tag()} -> {next} [color=red, constraint=false];\n'
            for next in curr.successors:
                dotstr += f'{curr.tag()} -> {next} [color=blue, constraint=true];\n'
        return dotstr.replace('@','__')
