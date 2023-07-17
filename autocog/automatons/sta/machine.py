
from typing import Any, Dict, List, Tuple, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel

from ..machine import ParseState, StateMachine, Expectations as BaseExpectations

from .thought import VirtualState, ActualState
from .thought import StructuredThought

class Expectations(BaseExpectations):
    delta: int

    def args(self):
        return super().args() + [self.delta]

class StructuredThoughtMachine(StateMachine):
    tag:         str = ''
    states:      Dict[str, VirtualState] = {}
    transitions: Dict[str, Dict[str,int]] = {}

    def add_state(self, stag: str, vstate: VirtualState) -> int:
        if stag in self.states:
            raise Exception(f"State tags must be unique {vstate.tag}")
        self.states.update({ stag : vstate })
        self.transitions.update({ stag : {} })
        return stag

    def get_states(self, label:str):
        return [ vs for vs in self.states.values() if vs.label == label ]

    def get_candidate_vstate(self, tag):
        candidates = self.get_states(tag)
        if len(candidates) == 0:
            raise Exception(f"No matching state '{tag}' in prompt {self.tag}! {list(self.states.keys())}")
        elif len(candidates) > 1:
            raise Exception(f"More than one matching state '{tag}' in prompt {self.tag}!")
        return candidates[0]

    def gv_state_tag(self, path=None, state=None):
        if path is None and state is None:
            raise Exception("State must be set if path is not set.")
        elif state is not None and path is not None:
            raise Exception("State must *not* be set if path is set.")
        elif state is not None:
            path = state.path

        if len(path) == 0 and state is not None and state.label == 'exit':
            return self.tag + '_exit'
        elif len(path) == 0:
            return self.tag + '_root'
        else:
            
            return "{}_{}".format(self.tag, '_'.join(map(lambda x: str(x[0]),path)))

    def toGraphViz(self):
        max_depth = 0
        state_by_depth = {}
        exit = None
        stash = ''
        for (s,state) in self.states.items():
            depth = len(state.path)
            if state.label == 'exit':
                exit = state
            if depth > 0:
                if not depth in state_by_depth:
                    state_by_depth.update({ depth : [] })
                state_by_depth[depth].append(state)
            if max_depth < depth:
                max_depth = depth

        dotstr = f'  {self.tag}_root [label="{self.tag}", shape=Msquare];\n'
        for (d,states) in state_by_depth.items():
            states = list(sorted(states, key=lambda s: s.path[-1]))
            for s in states:
                label = s.label + '\\n'
                label += f'{s.fmt}'
                if s.max_count > 0:
                    label += f'[{s.max_count}]'
                label += f"\\n{'.'.join(map(lambda x: str(x[0]), s.path))}"

                dotstr += f'  {self.gv_state_tag(state=s)} [label="{label}", shape=rectangle];\n'

            if len(states) > 1:
                stags = " -> ".join([ self.gv_state_tag(state=s) for s in states ])
                dotstr += "  { rank=same; "+stags+" [ constraint=True, style=invis ] }\n"
            for s in states:
                parent = f"{self.tag}_root" if d == 1 else self.gv_state_tag(path=s.path[:-1])
                dotstr += f'  {parent} -> {self.gv_state_tag(state=s)} [constraint=True, style=dotted, arrowhead=none];\n'

        dotstr += f'  {self.tag}_exit [label="exit", shape=Msquare];\n'
        for s in state_by_depth[max_depth]:
            dotstr += f'  {self.gv_state_tag(state=s)} -> {self.tag}_exit [constraint=True, style=invis];\n'

        for (src,tgts) in self.transitions.items():
            srctag = self.gv_state_tag(state=self.states[src])
            for (tgt,depth) in tgts.items():
                tgttag = self.gv_state_tag(state=self.states[tgt])
                if depth > 0:
                    dotstr += f'  {srctag} -> {tgttag} [label="{depth}", color="green", constraint=False, style="solid"];\n'
                elif depth < 0:
                    dotstr += f'  {srctag} -> {tgttag} [label="{depth}", color="red", constraint=False, style="solid"];\n'
                else:
                    dotstr += f'  {srctag} -> {tgttag} [constraint=False, style="solid", color="blue"];\n'

        return dotstr

    def mechanics(self):
        tags = list(zip(*sorted([ (tag,vs.tag(self.tag)) for (tag,vs) in self.states.items() if len(vs.path) > 0 ], key=lambda x: x[1] )))[0]
        res = ''
        for tag in tags:
            vs = self.states[tag]
            res += '> ' * len(vs.path)
            res += vs.label
            if vs.max_count > 0:
                res += f'[{vs.max_count}]'
            res += f'({vs.fmt}): {vs.desc}\n'
        return res

    def get_expectations(self, instance: StructuredThought):
        expected = []
        transitions = self.transitions[instance.vstate().tag()]
        # print(f"transitions={transitions}")
        for (tgt,delta) in transitions.items():
            vs = self.states[tgt]
            prompt = ''.join([ '> ' for i in vs.path ])
            prompt += vs.label
            idx = 0
            if vs.max_count > 0:
                vs_ = instance.vstate(delta)
                if vs_ == vs:
                    idx = instance.astate(delta).idx + 1
                else:
                    idx = 0
                prompt += f"[{idx+1}]"
                if idx >= vs.max_count:
                    continue
            prompt += f"({vs.fmt}):"
            prompt += '\n' if vs.fmt == 'record' else ' '

            expected.append( Expectations(vstate=vs, prompt=prompt, idx=idx, delta=delta) )
        return expected

    def init(self, counts:Dict[str,Tuple[int,bool]]={}) -> StructuredThought:
        root = self.states[self.tag]
        aroot = ActualState(vstate=root)
        aroot.internal = ParseState.content
        return StructuredThought(stack=[ aroot ], counts=counts)
