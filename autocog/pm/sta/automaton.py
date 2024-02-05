
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable, Union
from abc import abstractmethod
from pydantic import BaseModel

import copy
import time

from .ir import Prompt as IrPrompt 
from .ir import Field  as IrField

from .syntax import Syntax

from ...fta.automaton import FiniteThoughtAutomaton as FTA
from ...fta.actions import Action, Choose, Complete, Text

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
            parents = [ parent.tag() ] + parents
            parent = parent.parent
        return parents

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

    def tag(self):
        return ConcreteState.make_tag(self.abstract, self.indices)

    def name(self):
        return self.abstract.name()

    def index(self):
        return ','.join(map(str,self.indices))

    def path(self):
        return list(zip(self.abstract.parents(),self.indices))

    def prompt(self, syntax):
        field = self.abstract.field
        indent = syntax.prompt_indent * len(self.indices)
        fmt = '(record)' if field.is_record() else '(' + field.format.label() + ')'
        idx = f'[{self.indices[-1]}]' if field.is_list() else ''
        prompt = indent + self.name() + fmt + idx + ':'
        if not field.is_record():
            prompt += ' '
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
            # print(f"field={fld.tag()}")
            # for i in range(len(stack)):
            #     print(f"  stack[{i}]={[ s.tag() for s in stack[i]]}")

            state = AbstractState(field=fld)
            if fld.range is not None:
                state.flow = state
            self.abstracts.update({ state.tag() : state })

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

        # print(f"{'>   '*indent}- {curr}:")
        # print(f"{'>   '*indent}  depth   = {depth}")
        # print(f"{'>   '*indent}  parents = {parents}")
        # print(f"{'>   '*indent}  indices = {indices}")

        assert len(indices) == depth + 1
        count = indices[-1]

        # print(f"{'>   '*indent}  count   = {count}")

        ###########################################

        if current is not None:
            is_list   = current.is_list()
            is_record = current.is_record()
        else:
            is_list   = False
            is_record = True

        # print(f"{'>   '*indent}  is_list   = {is_list}")
        # print(f"{'>   '*indent}  is_record = {is_record}")

        if is_list:
            flows = count <  current.range[1]
            exits = count >= current.range[0]
        elif is_record:
            flows = count == 0
            exits = count >  0
        else:
            flows = True
            exits = True

        # print(f"{'>   '*indent}  flows={flows} ({abstract.flow is not None})")
        # print(f"{'>   '*indent}  exits={exits} ({abstract.exit is not None})")

        flows = flows and (abstract.flow is not None)
        exits = exits and (abstract.exit is not None)

        ###########################################

        ctag = ConcreteState.make_tag(abstract=abstract, indices=indices[1:])
        # print(f"{'>   '*indent}  ctag = {ctag}")
        if ctag in self.concretes:
            # print(f"{'>   '*indent}  FOUND: {ctag}")
            return ctag
        
        concrete = ConcreteState(abstract=abstract, indices=indices[1:])
        self.concretes.update({ ctag : concrete })

        ###########################################

        if flows:
            # print(f"{'>   '*indent}  FLOW: {abstract.flow.tag()}")
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
            # print(f"{'>   '*indent}  EXIT: {abstract.exit.tag()}")
            new_indices = copy.deepcopy(indices)
            if abstract.depth() > abstract.exit.depth():
                delta = abstract.depth() - abstract.exit.depth()
                new_indices = new_indices[:-delta]
                new_indices[-1] += 1
            else:
                new_indices[-1] = 0
            next = self.build_concrete_rec(abstract=abstract.exit, indices=new_indices, indent=indent+1)
            concrete.exits.append(next)

        ###########################################

        return concrete.tag()
    
    def get_sequence(self):
        sequence = ['root@']
        while True:
            state = self.concretes[sequence[-1]]
            assert len(state.successors) <= 1
            if len(state.successors) == 1:
                sequence.append(state.successors[0])
            else:
                break
        return sequence

    def get_reversed_exits(self, sequence):    
        reversed_exits = {}
        for s in sequence:
            for e in self.concretes[s].exits:
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
                assert len(state.exits) == 0
                delete_set.append(stag)
                if stag in reversed_exits:
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

    def instantiate_branch(self, syntax: Syntax, data: Any, fta: FTA, concrete: ConcreteState):
        if len(concrete.successors) == 0:
            return None

        ctag = concrete.tag().replace('@','_')
        choices = [ self.concretes[succ].prompt(syntax) for succ in concrete.successors ]
        # branch = f'branch.{ctag}.{len(fta.actions)}'
        branch = f'branch.{ctag}'
        fta.create(uid=branch, cls=Choose, choices=choices)

        for succ in concrete.successors:
            successor = self.concretes[succ]
            tag = successor.tag().replace('@','_')

            if successor.abstract.field.format is None:
                prev = branch
            else:
                # uid = f'field.{tag}.{len(fta.actions)}'
                uid = f'field.{tag}'
                fta.create(uid=uid, cls=Text, text='TODO') # TODO ACTION_KWARGS(successor.abstract.field.format)
                fta.connect(branch, uid)
                prev = uid

            # endl = f'endl.{tag}.{len(fta.actions)}'
            endl = f'endl.{tag}'
            fta.create(uid=endl, cls=Text, text='\n')
            fta.connect(prev, endl)

            next = self.instantiate_branch(syntax=syntax, data=data, fta=fta, concrete=successor)
            if next is not None:
                fta.connect(endl, next)

        return branch

    def instantiate(self, syntax: Syntax, data: Any):
        fta = FTA()

        header = self.prompt.header(
            mech=syntax.header_mechanic,
            indent=syntax.prompt_indent,
            fmt=syntax.header_formats,
            lst=syntax.format_listing
        )

        header = syntax.header_pre_post[0] + header + syntax.header_pre_post[1]
        fta.create( uid='root', cls=Text, text=header + '\nstart:\n')
        fta.connect('root', self.instantiate_branch(syntax=syntax, data=data, fta=fta, concrete=self.concretes['root@']))

        return fta
        
    def toGraphViz_abstract(self):
        dotstr = ''
        for state in self.abstracts.values():
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
                dotstr += f'{state.tag()} -> {state.flow.tag()} [label="{label}", color={color}, constraint={constraint}];\n'
            if state.exit is not None:
                constraint = 'false'
                if state.exit.depth() == state.depth():
                    constraint = 'true'
                if state.field is None:
                    assert False, f'{state.tag()} -> {state.exit.tag()}'
                elif state.field.range is None:
                    label = ''
                    color = 'purple'
                else:
                    label = f'i >= {state.field.range[0]}'
                    color = 'red'
                dotstr += f'{state.tag()} -> {state.exit.tag()} [label="{label}", color={color}, constraint={constraint}];\n'
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

            label = []
            path = curr.path()
            for (p,i) in path:
                astate = self.abstracts[p]
                lbl = astate.field.name
                if astate.field.range is not None:
                    lbl += f"[{i}]"
                label.append(lbl)
            label = '.'.join(label) if len(label) > 0 else 'root'

            dotstr += f'{curr.tag()} [label="{label}", fillcolor="{fillcolor}", style="filled"];\n'

            for next in curr.flows:
                dotstr += f'{curr.tag()} -> {next} [color=green, constraint=false];\n'
            for next in curr.exits:
                dotstr += f'{curr.tag()} -> {next} [color=red, constraint=false];\n'
            for next in curr.successors:
                dotstr += f'{curr.tag()} -> {next} [color=blue, constraint=true];\n'
        return dotstr.replace('@','__')
