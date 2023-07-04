
from typing import Any, Dict, List, Tuple, Union, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel
from enum import Enum

from ..machine import VirtualState as BaseVS, ActualState as BaseAS, Instance, ParseState

class VirtualState(BaseVS):
    path: List[int]       #
    max_count: int = 0    # scalar state if zero else max sequence length

    def tag(self, ptag:Optional[str]=None):
        if ptag is None:
            ptag = self.label
        if len(self.path) == 0:
            return ptag
        return "{}.{}".format(ptag, '.'.join(map(str,self.path)))

class ActualState(BaseAS):
    children: List[Any] = []
    idx: int = 0

class StructuredThought(Instance):
    stack: List[ActualState]
    counts: Dict[str,Tuple[Optional[int],bool]]
    content: Dict[str,Any] = {}

    def astate(self, delta=0):
        return self.stack[-1+delta]

    def vstate(self, delta=0):
        return self.astate(delta=delta).vstate

    def __ravel_rec(self, lbl, content):
        if isinstance(content,list):
            res = []
            for content_ in content:
                res += self.__ravel_rec(lbl, content_)
            return res

        if isinstance(content,str) or isinstance(content,bool) or isinstance(content,int) or isinstance(content,float):
            return []
        elif not isinstance(content,dict):
            raise Exception("Unexpected...")

        if lbl in content:
            res = content[lbl]
            return res if isinstance(res, list) else [res]

        res = []
        for content_ in content.values():
            res += self.__ravel_rec(lbl, content_)
        return res
        
    def ravel(self, lbl):
        return self.__ravel_rec(lbl, self.content)

    def __ravel_path_rec(self, path, content):
        assert len(path) > 0
        if isinstance(content,dict) and path[0] in content:
            content = content[path[0]]
            if not isinstance(content,list):
                content = [content]
            if len(path) == 1:
                return content
        else:
            return []
        assert isinstance(content,list)

        res = []
        for content_ in content:
            res += self.__ravel_path_rec(path[1:], content_)
        return res

    def ravel_path(self, path):
        return self.__ravel_path_rec(path, self.content)
    
    def need_prompt(self):
        vstate = self.vstate()
        astate = self.astate()
        return astate.internal == ParseState.ready or ( vstate.fmt == 'record' and astate.internal == ParseState.content )

    def need_content(self):
        vstate = self.vstate()
        astate = self.astate()
        return astate.internal == ParseState.content and vstate.fmt != 'record'

    def get_content(self, delta=None):
        if delta == 0:
            delta = None
        content = self.content
        # print(f"content={content}")
        for astate in self.stack[1:delta]:
            # print(f"astate={astate}")
            if not astate.vstate.label in content:
                return None
            content = content[astate.vstate.label]
            if astate.vstate.max_count > 0:
                if not isinstance(content, list):
                    assert isinstance(content, str), f"content={content}"
                    content = [content]
                if astate.idx >= len(content):
                    #print(f"astate.idx={astate.idx}")
                    #print(f"content={content}")
                    #assert astate.idx == len(content) + 1
                    return None
                content = content[astate.idx]
            else:
                if isinstance(content, list):
                    if len(content) == 0:
                        return None
                    elif len(content) == 1:
                        content = content[0]
                    else:
                        raise Exception(f"content={content}")
        return content

    def set_content(self, data):
        # print(f"data={data}")
        # print(f"self.content={self.content}")
        parent_content = self.content
        # print(f"parent_content={parent_content}")
        for astate in self.stack[1:-1]:
            # print(f"astate={astate}")
            if not astate.vstate.label in parent_content or parent_content[astate.vstate.label] is None:
                parent_content.update({ astate.vstate.label : (None if astate.vstate.fmt != 'record' else dict()) if astate.vstate.max_count == 0 else list() })
                # print(f"parent_content={parent_content}")

            if astate.vstate.max_count == 0 and isinstance(parent_content[astate.vstate.label], list):
                assert len(parent_content[astate.vstate.label]) == 0
                parent_content.update({ astate.vstate.label : dict() })
            parent_content = parent_content[astate.vstate.label]
            # print(f"parent_content={parent_content}")
            if astate.vstate.max_count > 0:
                assert isinstance(parent_content, list)
                if astate.idx >= len(parent_content):
                    assert astate.idx == len(parent_content)
                    parent_content.append(None if astate.vstate.fmt != 'record' else dict())
                    # print(f"parent_content={parent_content}")
                parent_content = parent_content[astate.idx]
                # print(f"parent_content={parent_content}")
            else:
                assert not isinstance(parent_content, list)
        assert parent_content is not None

        astate = self.stack[-1]
        vstate = astate.vstate
        if vstate.label in parent_content:
            content = parent_content[vstate.label]
            if isinstance(content, list):
                assert vstate.max_count > 0
                assert astate.idx == len(content)
                content.append(data)
            else:
                assert content is None
                parent_content.update({ vstate.label : data })
        elif vstate.max_count > 0 and not isinstance(data, list):
            parent_content.update({ vstate.label : [ data ] })
        else:
            if isinstance(parent_content, list):
                print(parent_content)
            parent_content.update({ vstate.label : data })
        # print(f"self.content={self.content}")

    def __write_content_rec(self, vtag:str, data, content:Dict[str,Any], path:List[int]):
        if vtag in content:
            content.update({ vtag : data })
        else:
            for (f,content_) in content.items():
                if isinstance(content_, dict):
                    self.__write_content_rec(vtag, data, content_)
                elif isinstance(content_, list):
                    for c in content_:
                        self.__write_content_rec(vtag, data, c)

    def write_content(self, vtag:str, data:Any):
        # print(f"vtag={vtag}")
        # print(f"data={data}")
        self.__write_content_rec(vtag, data, self.content, [])

    def fork(self, vtag:str, data:Any):
        res = self.copy(deep=True)
        res.write_content(vtag, data)
        return res

    def known_choice(self, expected:List):
        if self.started:
            return list(range(len(expected)))
        candidates = []
        rejected = []
        unknown = []
        # print(f"self.counts.keys()={self.counts.keys()}")
        for (i,e) in enumerate(expected):
            # print(f"expected={e}")
            # print(f"e.vstate.tag()={e.vstate.tag()}")
            (cnt,seen) = self.counts[e.vstate.tag()]
            # print(f"(cnt,seen)=({cnt},{seen})")
            if seen:
                content = self.get_content(delta=e.delta-1)
                assert content is not None
                assert isinstance(content, dict), f"content={content}"
                assert e.vstate.label in content, f"content={content}"
                content = content[e.vstate.label]
                if not isinstance(content, list):
                    assert isinstance(content, str)
                    content = [content]
                assert isinstance(content, list), f"content={content}"
                # print(f"cnt={cnt}")
                # print(f"len(content)={len(content)}")
                # print(f"self.astate(e.delta).idx={self.astate(e.delta).idx}")
                current = self.astate(e.delta)
                if current.vstate == e.vstate and current.idx + 1 >= len(content):
                    # print(f"-> rejected")
                    rejected.append(i)
                else:
                    # print(f"-> candidates")
                    candidates.append(i)
            else:
                # print(f"-> unknown")
                unknown.append(i)

        # print(f"candidates={candidates}")
        # print(f"unknown={unknown}")
        # print(f"rejected={rejected}")
        candidates = sorted(candidates, key=lambda i: expected[i].delta)
        if len(candidates) > 0:
            return candidates[-1]
        else:
            assert len(unknown) > 0
            return unknown[0] if len(unknown) == 1 else unknown

    def build_astate(self, vstate: VirtualState, idx: int, delta: int):
        astate = ActualState(vstate=vstate, idx=idx)
        if delta > 0:
            assert delta == 1
            self.stack.append(astate)
        elif delta < 0:
            self.stack = self.stack[:delta]
            self.stack[-2].children.append(astate)
            self.stack[-1] = astate
        else:
            self.stack[-2].children.append(astate)
            self.stack[-1] = astate

        return astate
