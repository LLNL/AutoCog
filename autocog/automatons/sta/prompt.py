from typing import Any, Dict, List, Tuple, Union, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel
import itertools

from ..format import Format, Record
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
        stack = []
        previous = self.stm.tag
        for (s,(label,path,data)) in enumerate(stmts):
            # print(f"  label = {label}")
            # print(f"    path  = {path}")
            # print(f"    data  = {data}")
            # print(f"    previous = {previous}")
            if label.find('.') != -1:
                raise Exception("State label cannot contain '.' only letters, digits, and underscore.")
            stag = "{}.{}".format(label,'.'.join(map(str,path)))
            vstate = VirtualState(label=label, path=path, **data)
            self.stm.add_state(stag, vstate)
            if vstate.fmt != 'record' and vstate.max_count > 0:
                self.stm.transitions[stag].update({ stag : 0 })

            delta = len(path) - len(stack)
            # print(f"    delta  = {delta}")
            if delta > 0:
                assert delta == 1
                self.stm.transitions[previous].update({ stag : 1 })
                stack.append(previous)
            elif delta < 0:
                for d in range(1, -delta+1):
                    # print(f"    d = {d}")
                    if self.stm.states[stack[-d]].max_count > 0:
                        self.stm.transitions[previous].update({ stack[-d] : -d })
                stack = stack[:delta]
                self.stm.transitions[previous].update({ stag : delta })
            else:
                self.stm.transitions[previous].update({ stag : 0 })

            previous = stag
        self.stm.add_state(f"exit", VirtualState(label="exit", path=[], fmt='next', desc=""))
        delta = -len(stack)
        # print(f"    delta  = {delta}")
        assert delta < 0
        for d in range(1, -delta+1):
            # print(f"    d = {d}")
            if self.stm.states[stack[-d]].max_count > 0:
                self.stm.transitions[previous].update({ stack[-d] : -d })
        self.stm.transitions[previous].update({ "exit" : delta })

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
        return [ src for src in channel.source if isinstance(src, Input) ]

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
                    if self.stm.states[child_stag].max_count == 0:
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
                    if self.stm.states[child_stag].max_count == 0:
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
        
    async def execute(self, fid:int, orchestrator:Orchestrator, stacks: Dict[str,Any], path:List[str], automaton_desc:str=''):
        (vtag_to_stag, parent_by_vtag, children_by_vtag) = self.__visible_states()
        counts = { vtag : ( None if vs.max_count > 0 else 1, False ) for (vtag,vs) in self.stm.states.items() }
        stash = {}
        calls = []
        jobs = []
        for channel in self.channels:
            if channel.call is None:
                src_vtags = channel.source
                datas = []
                for src_vtag in src_vtags:
                    data = self.__channel_data(channel.prompt, src_vtag, stacks, path)
                    if data is None:
                        print(f"self.stm.tag={self.stm.tag}")
                        print(f"channel.target={channel.target}")
                        print(f"channel.source={channel.source}")
                        print(f"channel.prompt={channel.prompt}")
                        print(f"src_vtag={src_vtag}")
                        print(f"path={path}")
                        print(f"stacks={stacks}")
                    assert data is not None, f"channel={channel}\n\nsrc_vtag={src_vtag}"

                    if isinstance(data,str) or isinstance(data,bool) or isinstance(data,int) or isinstance(data,float) or isinstance(data,dict):
                        data = [data]
                    datas.append(data)

                if len(datas) == 1:
                    data = datas[0]
                else:
                    # print(f"datas={datas}")
                    data = [ { k:v for (k,v) in zip(channel.source,row) } for row in zip(*datas) ]
                self.__channel_load(channel, data, vtag_to_stag, counts, stash)
            else:
                kwargs = self.__channel_kwargs(channel, stacks, path)
                calls.append(( channel, len(jobs), len(kwargs) ))
                jobs += [ (channel.call, kw) for kw in kwargs ]

        if len(calls) > 0:
            retvals = await orchestrator.execute(jobs=jobs, pid=fid)
            for (channel,idx,num) in calls:
                if num == 1:
                    data = retvals[idx]
                else:
                    data = retvals[idx:idx+num]
                    assert all([ isinstance(d,list) for d in data ])
                    data = [ d_ for d in data for d_ in d ]
                self.__channel_load(channel, data, vtag_to_stag, counts, stash)

        # print(f"counts={counts}")
        # print(f"stash={stash}")
        needed = self.__needed_from_counts(counts, parent_by_vtag, vtag_to_stag)
        # print(f"needed={needed}")

        st = self.stm.init(counts)
        self.__fill_content_skeleton_rec(vtag=self.stm.tag, content=st.content, counts=counts, needed=needed, vtag_to_stag=vtag_to_stag, children_by_vtag=children_by_vtag)
        # print(f"st.content={st.content}")
        
        STs = [ st ]
        # for (i,st) in enumerate(STs):
        #     print(f"STs[{i}].content={st.content}")
        for (vtag,data) in stash.items():
            # print(f"vtag={vtag}")
            # print(f"data={data}")
            if isinstance(data,list) and len(data) > 0:
                sts = []
                for ST in STs:
                    for d in data:
                        res = ST.copy(deep=True)
                        res.write_content(vtag, **d)
                        sts.append(res)
                STs = sts
            elif isinstance(data,list):
                pass # FIXME?
            elif isinstance(data,dict):
                for ST in STs:
                    ST.write_content(vtag, **data)
            else:
                raise Exception("This should not happen...")
            # for (i,st) in enumerate(STs):
            #     print(f"STs[{i}].content={st.content}")

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
        return await orchestrator.prompt(fid=fid, machine=self.stm, instances=STs, header=header, formats=self.formats)