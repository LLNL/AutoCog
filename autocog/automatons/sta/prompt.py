from typing import Any, Dict, List, Tuple, Union, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel
import itertools

from ..format import Format, Record
from ..instance import Instance
from ..channel import Channel
from ..port import Input
from .thought import VirtualState
from .machine import StructuredThoughtMachine
from ...architecture.orchestrator import Orchestrator

class DataEdge(BaseModel):
    stm: StructuredThoughtMachine
    tgt: VirtualState
    src: Optional[Tuple[StructuredThoughtMachine,VirtualState]] = None

class StructuredThoughtPrompt(BaseModel):
    stm:   StructuredThoughtMachine
    desc:  str
    channels: List[Channel] = [] # TODO split between copies, cumuls, and calls
    formats: Dict[str,Format] = {}
    parameters: List[str] = []

    preamble:     str = "You are a helpful AI assistant."
    basics:       str = "You are using an interactive questionnaire."
    mechs:        str = "Follow this structure after the start prompt:"
    fmts:         str = "Each prompt expects one of the following formats:"
    postscriptum: str = "Terminate each prompt with a newline. Use as many statement with `thought` format as needed."

    header: str = "{preamble} {automaton} {prompt}\n{basics}\n{mechs}\n```\n{mechanics}```\n{fmts}\n{formats}\n{postscriptum}\n\nstart(record):\n"

    def toGraphViz(self):
        dotstr = 'ranksep=1;\n'
        dotstr += self.stm.toGraphViz()
        return dotstr

    def build(self, stmts:List[Dict]):
        # print(f"StructuredThoughtPrompt.build(tag={self.stm.tag})")
        self.stm.add_state(self.stm.tag, VirtualState(label=self.stm.tag, path=[], fmt='record', desc=self.desc))
        stag_to_ordered_children = {}
        stag_to_parent = {}
        stack = []
        previous = self.stm.tag
        for (s,(label,path,data)) in enumerate(stmts):
            # print(f"  label = {label}")
            # print(f"    path  = {path}")
            # print(f"    data  = {data}")
            # print(f"    previous = {previous}")
            if label.find('.') != -1:
                raise Exception("State label cannot contain '.' only letters, digits, and underscore.")
            stag = "{}.{}".format(label,'.'.join(map(lambda x: str(x[0]),path)))
            vstate = VirtualState(label=label, path=path, **data)
            self.stm.add_state(stag, vstate)
            if vstate.fmt != 'record' and vstate.is_list:
                self.stm.transitions[stag].update({ stag : 0 })

            delta = len(path) - len(stack)
            # print(f"    delta  = {delta}")
            if delta > 0:
                assert delta == 1
                self.stm.transitions[previous].update({ stag : 1 })
                stack.append(previous)
                stag_to_ordered_children.update({ previous : [] })
            elif delta < 0:
                for d in range(1, -delta+1):
                    # print(f"    d = {d}")
                    if self.stm.states[stack[-d]].is_list:
                        self.stm.transitions[previous].update({ stack[-d] : -d })
                stack = stack[:delta]
                self.stm.transitions[previous].update({ stag : delta })
            else:
                self.stm.transitions[previous].update({ stag : 0 })
            stag_to_ordered_children[stack[-1]].append(stag)
            stag_to_parent.update({ stag : stack[-1] })
            previous = stag

        self.stm.add_state(f"exit", VirtualState(label="exit", path=[], fmt='next', desc=""))
        delta = -len(stack)
        assert delta < 0
        self.stm.transitions[previous].update({ stack[-d] : -d for d in range(1, -delta+1) if self.stm.states[stack[-d]].is_list })
        self.stm.transitions[previous].update({ "exit" : delta })

        tgt_to_src = { stag : {} for stag in self.stm.states.keys() }
        for (src,tgts) in self.stm.transitions.items():
            for (tgt,delta) in tgts.items():
                tgt_to_src[tgt].update({ src : delta })

        predsuccs = {}
        for (parent_stag,ordered_children) in stag_to_ordered_children.items():
            for (child_idx,child_stag) in enumerate(ordered_children):
                if child_idx == 0:
                    pred = None
                    succ = child_idx + 1
                elif child_idx == len(ordered_children) - 1:
                    pred = child_idx - 1
                    succ = None
                else:
                    succ = child_idx - 1
                    pred = child_idx + 1

        print(f"stag_to_ordered_children={stag_to_ordered_children}")
        # Add a skip edge for list that can be empty
        for (parent_stag,ordered_children) in stag_to_ordered_children.items():
            print(f"parent_stag={parent_stag}")
            if len(ordered_children) == 1:
                continue # TODO assert not is_list or list_range[0] > 0
            parent_vs = self.stm.states[parent_stag]
            for (child_idx,child_stag) in enumerate(ordered_children):
                child_vs = self.stm.states[child_stag]
                if child_vs.fmt != 'record' or not child_vs.is_list or child_vs.list_range[0] > 0:
                    continue
                if child_idx == 0:
                    src = parent_stag
                    tgt = ordered_children[child_idx+1]
                    delta = 1
                elif child_idx < len(ordered_children) - 1:
                    src = ordered_children[child_idx-1]
                    tgt = ordered_children[child_idx+1]
                    delta = 0
                else:
                    continue # TODO
                self.stm.transitions[src].update({ tgt : delta })
                tgt_to_src[tgt].update({ src : delta })
            for (child_idx,child_stag) in enumerate(ordered_children):
                print(f"  child_stag={child_stag}")
                child_vs = self.stm.states[child_stag]
                print(f"  child_vs={child_vs}")
                if child_vs.is_list and child_vs.list_range[0] == 0:
                    tr = []
                    for (src_stag,src_delta) in tgt_to_src[child_stag].items():
                        print(f"    src_stag={src_stag}")
                        if src_stag == child_stag:
                            continue
                        src_vs = self.stm.states[src_stag]
                        print(f"    src_vs={src_vs}")
                        for (tgt_stag,tgt_delta) in self.stm.transitions[child_stag].items():
                            print(f"      tgt_stag={tgt_stag}")
                            if tgt_stag == src_stag or tgt_stag == child_stag:
                                continue
                            tgt_vs = self.stm.states[tgt_stag]
                            print(f"      tgt_vs={tgt_vs}")
                            no_label = lambda tag: '.'.join(tag.split('.')[1:])
                            src_is_sibling  = no_label(src_stag).startswith(no_label(parent_stag)) and len(src_vs.path) == len(child_vs.path)
                            assert (not src_is_sibling) or src_vs.path[-1] < child_vs.path[-1]
                            src_is_parent   = src_stag == parent_stag
                            tgt_is_sibling  = no_label(tgt_stag).startswith(no_label(parent_stag)) and len(tgt_vs.path) == len(child_vs.path)
                            assert (not tgt_is_sibling) or child_vs.path[-1] < tgt_vs.path[-1]
                            tgt_is_ancestor = no_label(child_stag).startswith(no_label(tgt_stag))

                            print(f"      > {src_is_sibling} {src_is_parent} {tgt_is_sibling} {tgt_is_ancestor}")

                            # connect inputs to outputs that are siblings and ancestors, do not loop parent to any ancestor.
                            if ( src_is_sibling and ( tgt_is_sibling or tgt_is_ancestor ) ) or ( src_is_parent and tgt_is_sibling ):
                                print(f"      >>> delta={src_delta+tgt_delta}")
                                tr.append(( src_stag, tgt_stag, src_delta+tgt_delta ))
                    for (src,tgt,delta) in tr:
                        self.stm.transitions[src].update({ tgt : delta })
                        tgt_to_src[tgt].update({ src : delta })

    @classmethod
    def create(cls, ptag:str, desc:str, stmts:List[Dict], **config):
        #print(f"config={config}")
        stp = cls(stm=StructuredThoughtMachine(tag=ptag), desc=desc, **config)
        stp.build(stmts)
        return stp

    def add_channel(self, desc: Dict):
        #print(f"desc={desc}")
        assert 'target' in desc
        if desc['target'] in self.parameters:
            raise Exception(f"State {desc['target']} seen more than once when adding channel the prompt {self.stm.tag}.")
        self.parameters.append(desc['target'])

        channel = Channel( machine=self.stm, **desc )
        self.channels.append(channel)
        inputs = []
        if isinstance(channel.source, Input):
            inputs.append(channel.source)
        for port in channel.kwargs:
            if isinstance(port, Input):
                inputs.append(port)
        return [ channel.source ] if isinstance(channel.source, Input) else []

    def __visible_states(self):
        states_by_labels = { stag : [] for stag in set(map(lambda x: x.split('.')[0], self.stm.states.keys())) }
        for (stag,vs) in self.stm.states.items():
            vtag = stag.split('.')[0]
            states_by_labels[vtag].append(stag)
        vtag_to_stag = { vtag : stags[0] for (vtag,stags) in states_by_labels.items() if len(stags) == 1 }
        path_to_stag = { tuple(self.stm.states[stag].path) : stag for (vtag,stag) in vtag_to_stag.items() if len(self.stm.states[stag].path) > 0 }

        parent_by_vtag = {}
        children_by_vtag = {}
        for (vtag,stag) in vtag_to_stag.items():
            if len(self.stm.states[stag].path) > 1:
                path_ = self.stm.states[stag].path[:-1]
                path_ = tuple(path_)
                parent = path_to_stag[path_]
            elif len(self.stm.states[stag].path) == 1:
                parent = self.stm.tag
            else:
                parent = None

            parent_by_vtag.update({ vtag : parent })
            if parent is not None:
                if not parent in children_by_vtag:
                    children_by_vtag.update({ parent : [] })
                children_by_vtag[parent].append(vtag)

        return (vtag_to_stag, parent_by_vtag, children_by_vtag)

    def __fill_content_skeleton_rec(self, vtag, content, counts, needed, vtag_to_stag, children_by_vtag):
        #print(f"__fill_content_skeleton_rec(vtag={vtag})")
        for child_vtag in children_by_vtag[vtag_to_stag[vtag]]:
            #print(f"  child_vtag={child_vtag}")
            if child_vtag in needed:
                child_stag = vtag_to_stag[child_vtag]
                if child_stag in children_by_vtag:
                    if not self.stm.states[child_stag].is_list:
                        content.update({ child_vtag : {} })
                        self.__fill_content_skeleton_rec(child_vtag, content[child_vtag], counts, needed, vtag_to_stag, children_by_vtag)
                    else:
                        content.update({ child_vtag : [] })
                        child_stag = vtag_to_stag[child_vtag]
                        if counts[child_stag][0] is not None:
                            for i in range(counts[child_stag][0]):
                                content[child_vtag].append({})
                                self.__fill_content_skeleton_rec(child_vtag, content[child_vtag][-1], counts, needed, vtag_to_stag, children_by_vtag)
                else:
                    if not self.stm.states[child_stag].is_list:
                        content.update({ child_vtag : None })
                    else:
                        content.update({ child_vtag : [] })
                        child_stag = vtag_to_stag[child_vtag]
                        if counts[child_stag][0] is not None:
                            for i in range(counts[child_stag][0]):
                                content[child_vtag].append(None)
                    counts.update({ child_stag : ( counts[child_stag][0], True ) })

    def __find_source_prompt(self, ptag, stacks: Dict[str,Any], path:List[str]):
        src_prompt = None
        for p in path[::-1]:
            if p in ptag:
                src_prompt = p
                break
        return src_prompt

    def __channel_data(self, ptag, src_vtag, stacks: Dict[str,Any], path:List[str]):
        if ptag is None:
            data = [ stack[src_vtag] for stack in stacks['__inputs__'] ]
        else:
            src_prompt = self.__find_source_prompt(ptag=ptag, stacks=stacks, path=path)
            if src_prompt is None:
                return None

            if not src_prompt in stacks:
                raise Exception("Channels' source not found in stack!")

            data = []
            for st in stacks[src_prompt][-1]:
                data += st.ravel(src_vtag)

        if len(data) == 1:
            data = data[0]

        if data is None:
            raise Exception("Channels' data not found!")

        return data

    def __needed_from_counts(self, counts, parent_by_vtag, vtag_to_stag):
        needed = []
        for (stag,(cnt,seen)) in counts.items():
            if seen:
                vtag = stag.split('.')[0]
                needed.append(vtag)
                p = parent_by_vtag[vtag]
                while p is not None:
                    if counts[p][0] is None:
                        raise Exception(f"Count of {p} not set (ancestor of {stag} which is set)")
                    p = p.split('.')[0]
                    needed.append(p)
                    p = parent_by_vtag[p]
        needed = list(set(needed))
        N = [ self.stm.states[vtag_to_stag[ntag]].tag('') for ntag in needed if ntag != self.stm.tag ]
        for (vtag,vs) in self.stm.states.items():
            for n in N:
                if vs.tag('').startswith(n):
                    counts.update({ vtag : ( counts[vtag][0], True ) })
                    needed.append(vtag)
        return list(set(needed))

    def __channel_kwargs(self, channel, stacks, path):
        keys = []
        kwargs = []
        for (k,v) in channel.kwargs.items():
            arg_is_mapped = False
            data = None
            if v == 'True':
                data = True
            if v == 'False':
                data = False
            if data is None:
                try:
                    data = int(v)
                except:
                    pass
            if data is None:
                try:
                    data = float(v)
                except:
                    pass
            if data is None and len(v) > 1 and v[0] == '"' and v[-1] == '"':
                data = v[1:-1]
            if data is None:
                if v[0] == '!':
                    v = v[1:]
                    arg_is_mapped = True
                data = self.__channel_data(channel.prompt, v, stacks, path)
                assert data is not None

            keys.append(k)
            if arg_is_mapped and isinstance(data,list):
                kwargs.append(data)
            else:
                kwargs.append([data])

        return [ { k : v for (k,v) in zip(keys,kwarg) } for kwarg in itertools.product(*kwargs) ]

    def __ravel_mapped_path_rec(self, data, path):
        if len(path) == 0:
            return data
        results = []
        for d in data:
            if path[0] in d:
                if len(path) == 1:
                    if isinstance(d[path[0]], list):
                        res = d[path[0]]
                    else:
                        res = [ d[path[0]] ]
                else:
                    res = self.__ravel_mapped_path_rec(self, d[path[0]], path[1:])
                del d[path[0]]
                for r in res:
                    r.update(d)
                results += res
        return results

    def finalize_data_for_loading(self, data, tgt, fmt):
        need_dict = issubclass(fmt.__class__, Record)

        if isinstance(data,dict) and not need_dict:
            assert tgt in data
            data = data[tgt]

        if need_dict:
            assert isinstance(data,dict)
        else:
            assert isinstance(data,str) or isinstance(data,bool) or isinstance(data,int) or isinstance(data,float)

        return data

    def __channel_load(self, channel, data, vtag_to_stag, counts, stash):
        assert not channel.target in stash
        tgt_stag = vtag_to_stag[channel.target]
        tgt_state = self.stm.states[tgt_stag]
        # print(f"states[{tgt_stag}]={tgt_state}")
        tgt_fmt = self.formats[tgt_state.fmt]
        # print(f"formats[{tgt_state.fmt}]={tgt_fmt}")
        need_dict = issubclass(tgt_fmt.__class__, Record)

        # import json
        # print(f"data={json.dumps(data, indent=4)}")
        if counts[tgt_stag][0] is None:
            if not isinstance(data,list):
                data = [data]
            counts[tgt_stag] = ( len(data), True )
            data = { 'data' : data }
        else:
            counts[tgt_stag] = ( 1, True )
            data = { 'data' : data }

        if isinstance(data,list):
            data_ = []
            for d_ in data:
                if isinstance(d_['data'], list):
                    data_.append({ 'data' : [ self.finalize_data_for_loading(d, channel.target, tgt_fmt) for d in d_['data'] ] })
                else:
                    data_.append({ 'data' : self.finalize_data_for_loading(d_['data'], channel.target, tgt_fmt) })
            data = data_
        elif isinstance(data['data'], list):
            data = { 'data' : [ self.finalize_data_for_loading(d, channel.target, tgt_fmt) for d in data['data'] ] }
        else:
            data = { 'data' : self.finalize_data_for_loading(data['data'], channel.target, tgt_fmt) }

        # print(f"channel.target={channel.target}")
        # print(f"channel.source={channel.source}")
        # print(f"states[{tgt_stag}]={self.stm.states[tgt_stag]}")
        # print(f"data={json.dumps(data, indent=4)}")

        stash.update({ channel.target : data })

    async def execute(self, fid:int, orchestrator:Orchestrator, stacks: Dict[str,List[Instance]], path:List[str], automaton_desc:str=''):
        datas = [ None for c in self.channels ]
        calls = []
        jobs = []
        for (c,channel) in enumerate(self.channels):
            if channel.call is None:
                assert not channel.source.mapped
                datas[c] = channel.source.retrieve(curr=self.stm.tag, stacks=stacks)
            else:
                raise NotImplementedError()
                kwargs = [{}] # TODO self.__channel_kwargs(channel, stacks, path)
                calls.append(( c, len(jobs), len(kwargs) ))
                jobs += [ (channel.call, kw) for kw in kwargs ]

        if len(calls) > 0:
            retvals = await orchestrator.execute(jobs=jobs, pid=fid)
            for (c,idx,num) in calls:
                raise NotImplementedError() # TODO save FIDs
                datas[c] = retvals[idx] if num == 1 else retvals[idx:idx+num]

        path_to_stag_vs = { vs.p() : (stag,vs) for (stag,vs) in self.stm.states.items() }
        st = self.stm.init()
        for (c,channel) in enumerate(self.channels):
            (stag,vs) = path_to_stag_vs[channel.target.path()]

            data = datas[c]
            if data is None:
                # assert vs.is_list and vs.list_range[0] == 0
                st.counts.update({ stag : 0 })
                continue
            if vs.is_list:
                assert isinstance(data,list)
                n = len(data)
                assert n >= vs.list_range[0]
                assert n <= vs.list_range[1]
                st.counts.update({ stag : n })
            else:
                assert not isinstance(data,list), f"channel={channel} data={data}"
                st.counts.update({ stag : None })
            st.write_path(path=channel.target.steps, data=data)
        # print(f"counts={st.counts}")

        header = self.header.format(
            preamble=self.preamble,
            automaton=automaton_desc,
            prompt=self.desc,
            basics=self.basics,
            mechs=self.mechs,
            mechanics=self.stm.mechanics(),
            fmts=self.fmts,
            formats='\n'.join([ f"- {k}: {v.desc}" for (k,v) in self.formats.items() if k != 'next' or len(v.choices) > 1 ]),
            postscriptum=self.postscriptum
        )
        return await self.stm.execute(
            instance=st, LMs=orchestrator.LMs, header=header, formats=self.formats,
            out=None if orchestrator.pipe is None else orchestrator.pipe.set(tag=self.stm.tag, idx=0),
            limit=orchestrator.limit,
        )
