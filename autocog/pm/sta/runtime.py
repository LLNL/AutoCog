
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
                assert isinstance(data,list)
                distribute = to_concrete_label(cursor)
                break

        if distribute is not None:
            if distribute in self.counts:
                assert self.counts[distribute] == len(data)
            else:
                self.counts.update({ distribute : len(data) })
            for (i,d) in enumerate(data):
                lpath = cursor[:-1] + [ (cursor[-1][0], i) ]
                self.state.update({ to_concrete_label(lpath) : True })
                lpath += path[len(cursor):]
                self.locate_and_insert(abstracts, concretes, lpath, d)

        elif isinstance(data, dict):
            for (k,v) in data.items():
                if isinstance(v,list):
                    raise NotImplementedError("List inside dictionary for channel data")
                else:
                    lpath = path + [ (k,None) ]
                    print(f"TAIL-REC: lpath={lpath}")
                    self.locate_and_insert(abstracts, concretes, lpath, v)

        else:
            ptr = self.data
            for i in range(len(path)):
                (lbl,idx) = path[i]
                abstract = get_abstract_at(abstracts, path[:i+1])[0]
                
                count = None
                if abstract.field.is_list():
                    assert idx is not None
                    clbl = to_concrete_label(path[:i] + [ ( path[i][0], None ) ])
                    assert clbl in self.counts
                    count = self.counts[clbl]
                    assert idx < self.counts[clbl]

                if not lbl in ptr:
                    ph = lambda: None if i == len(path) - 1 else {}
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
            self.state.update({ to_concrete_label(path) : True })

    def OLD_insert(self, field_map, target, data):
        field = field_map['.'.join(target)]

        if isinstance(data, list):
            children = []
            list_field = field
            while isinstance(list_field, IrField):
                if list_field.is_list():
                    break
                children = [ list_field ] + children
                list_field = list_field.parent
            print(f"list_field: {list_field.path()}")

            if not list_field.path() in self.counts:
                self.counts.update({ list_field.path() : len(data) })
            elif self.counts[list_field.path()] == len(data):
                pass
            else:
                raise Exception("When adding list data to frame, enclosing list field must never have been seen or have the same size.")
            parents = self.check_parent_for_unknown_list_size(list_field)

            tgt_data = self.data
            for p in parents:
                if not p.name in tgt_data:
                    tgt_data.update({ p.name : {} })
                tgt_data = tgt_data[p.name]

            if not list_field.name in tgt_data:
                tgt_data.update({ list_field.name : [ {} for i in range(len(data)) ] })

            if len(children) > 0:
                for i in range(len(data)):
                    tgt_item = tgt_data[list_field.name][i]
                    for c in children[:-1]:
                        if not c.name in tgt_item:
                            tgt_item.update({ c.name : {} })
                        tgt_item = tgt_item[c.name]
                    assert not children[-1].name in tgt_item
                    tgt_item.update({ children[-1].name : data[i] })
            else:
                for i in range(len(data)):
                    tgt_data[list_field.name][i] = data[i]

        else:
            self.check_parent_for_unknown_list_size(field)
            # TODO