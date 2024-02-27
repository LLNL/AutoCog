
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable, Union
from abc import abstractmethod
from pydantic import BaseModel

from .ir import Field as IrField

def to_abstract_label(path):
    return '.'.join([ p for (p,i) in path ])

def get_abstract_at(abstracts, path):
    return abstracts[to_abstract_label(path)]

def to_concrete_label(path):
    return '.'.join([ p if i is None else f"{p}[{i}]" for (p,i) in path ])

def get_concrete_at(concretes, path):
    return concretes[to_concrete_label(path)]

class Frame(BaseModel):
    state: Dict[str,Optional[bool]]
    counts: Dict[str,int] = {}
    data: Dict = {}
    
    def read(self, path):
        # print(f"path={path}")
        data = self.data
        # print(f"data={data}")
        for i in range(len(path)):
            (lbl,idx) = path[i]
            # print(f"lbl={lbl} idx={idx}")
            data = data[lbl]
            # print(f"data[lbl]={data}")
            if idx is not None:
                data = data[idx]
                # print(f"data[idx]={data}")
        return data

    def ravel_rec(self, path, data):
        if len(path) == 0:
            return data

        (lbl,idx) = path[0]

        data = data[lbl]
        if idx is not None:
            assert isinstance(data, list)
            return self.ravel_rec(path[1:], data[idx])
        elif isinstance(data, list):
            res = []
            for d in data:
                r = self.ravel_rec(path[1:], d)
                if isinstance(r, list):
                    res += r
                else:
                    res.append(r)
            return res
        else:
            return self.ravel_rec(path[1:], data)

    def ravel(self, path):
        return self.ravel_rec(path, self.data)

    def write(self, abstracts, path, data):
        ptr = self.data
        for i in range(len(path)):
            (lbl,idx) = path[i]
            abstract = get_abstract_at(abstracts, path[:i+1])[0]

            count = None
            if abstract.field.is_list():
                if idx is None:
                    assert not lbl in ptr
                    assert data is None
                    assert i == len(path) - 1
                    ptr.update({ lbl : list() })
                    break
                else:
                    clbl = to_concrete_label(path[:i] + [ ( path[i][0], None ) ])
                    assert clbl in self.counts
                    count = self.counts[clbl]
                    assert idx < self.counts[clbl]

            if not lbl in ptr:
                ph = lambda: None if i == len(path) - 1 else dict()
                ptr.update({ lbl : ph() if count is None else [ ph() for i in range(count) ] })

            if i == len(path) - 1:
                if abstract.field.is_list():
                    ptr[lbl][idx] = data
                else:
                    ptr[lbl] = data
            else:
                ptr = ptr[lbl]
                if abstract.field.is_list():
                    ptr = ptr[idx]
    
    def check_parent_for_unknown_list_size(self, field):
        parents = []
        parent_field = field.parent
        while isinstance(parent_field, IrField):
            parents = [ parent_field ] + parents
            if parent_field.is_list():
                raise Exception()
            parent_field = parent_field.parent
        return parents
    
    def locate_and_insert(self, abstracts, concretes, path, data):
        cursor = []
        distribute = None
        for (p,i) in path:
            cursor.append((p,i))
            abstract = get_abstract_at(abstracts, cursor)[0]
            if abstract.field.is_list() and i is None:
                if data is None:
                    assert len(cursor) == len(path)
                else:
                    assert isinstance(data,list)
                    distribute = to_concrete_label(cursor)
                break

        if distribute is not None:
            if distribute in self.counts:
                assert self.counts[distribute] == len(data)
            else:
                self.counts.update({ distribute : len(data) })

            if len(data) > 0:
                for (i,d) in enumerate(data):
                    lpath = cursor[:-1] + [ (cursor[-1][0], i) ]
                    self.state.update({ to_concrete_label(lpath) : True })
                    lpath += path[len(cursor):]
                    self.locate_and_insert(abstracts, concretes, lpath, d)
            else:
                lpath = cursor[:-1] + [ (cursor[-1][0], None) ]
                self.locate_and_insert(abstracts, concretes, lpath, None)

            for i in range(len(data),abstract.field.range[1]):
                lpath = cursor[:-1] + [ (cursor[-1][0], i) ]
                self.state.update({ to_concrete_label(lpath) : False })

        elif isinstance(data, dict):
            for (k,v) in data.items():
                lpath = path + [ (k,None) ]
                abstract = get_abstract_at(abstracts, lpath)[0]
                if isinstance(v,list):
                    assert not abstract.field.range is None
                    assert len(v) >= abstract.field.range[0]
                    assert len(v) <= abstract.field.range[1]

                    clbl = to_concrete_label(lpath)
                    if clbl in self.counts:
                        assert self.counts[clbl] == len(v)
                    else:
                        self.counts.update({ clbl : len(v) })

                    if len(v) > 0:
                        for (i,w) in enumerate(v):
                            lpath = path + [ (k,i) ]
                            self.state.update({ to_concrete_label(lpath) : True })
                            self.locate_and_insert(abstracts, concretes, lpath, w)
                    else:
                        self.locate_and_insert(abstracts, concretes, lpath, None)

                    for i in range(len(v),abstract.field.range[1]):
                        lpath = path + [ (k,i) ]
                        self.state.update({ to_concrete_label(lpath) : False })
                else:
                    self.locate_and_insert(abstracts, concretes, lpath, v)

        else:
            self.write(abstracts, path, data)
            self.state.update({ to_concrete_label(path) : True })

    def finalize(self, abstracts, concretes):
        do_not_visit = []
        for (clbl,state) in self.state.items():
            if state is False:
                do_not_visit.append(clbl)
        add_to_do_not_visit = []
        for (clbl,state) in self.state.items():
            for clbl_ in do_not_visit:
                if len(clbl) > len(clbl_) and  clbl.startswith(clbl_):
                    assert state is None, f"clbl={clbl} state={state}"
                    add_to_do_not_visit.append(clbl)
                    break
        for clbl in add_to_do_not_visit:
            self.state.update({ clbl : False })
