
from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable, Union
from abc import abstractmethod
from pydantic import BaseModel

Range = Optional[Tuple[int,int]]

class Object(BaseModel):
    name: str
    desc:  List[str] = []

def range_to_str(r):
    if r is None:
        return ''
    elif r[0] == r[1]:
        return f'[{r[0]}]'
    else:
        return f'[{r[0]}:{r[1]}]'

class Path(BaseModel):
    steps: List[Tuple[str,Range]]
    is_input: bool
    prompt: Optional[str]

    def str(self):
        res = ''
        if self.is_input:
            res += '?'
        elif self.prompt is not None:
            res += self.prompt + '.'
        res += '.'.join([ s[0] + range_to_str(s[1]) for s in self.steps ])
        return res

SrcPath = List[Tuple[str,Optional[int]]]

class Format(Object):
    refname: Optional[str] = None

    def str(self):
        raise NotImplementedError()

    def label(self):
        if self.refname is None:
            return self.str()
        else:
            return self.refname

class Field(Object):
    depth:  int
    index:  int
    format: Optional[Format]
    range:  Range
    parent: Union["Prompt","Field"]

    def tag(self):
        return f"{self.name}_{self.depth}_{self.index}"

    def path(self):
        return f"{self.parent.path()}.{self.name}" if isinstance(self.parent, Field) else self.name
    
    def coords(self):
        return self.parent.coords() + [ self.index ] if isinstance(self.parent, Field) else [ self.index ]

    def is_list(self):
        return self.range is not None

    def is_record(self):
        return self.format is None
    
    def mechanics(self, indent):
        fmt = '(record)' if self.is_record() else '(' + self.format.label() + ')'
        return f"{indent*self.depth}{self.name}{fmt}{range_to_str(self.range)}:"

class Record(Object):
    fields: List[Field] = []

class Channel(BaseModel):
    tgt: List[Tuple[str,Optional[int]]]

class Control(BaseModel):
    prompt: str
    limit: int

class Return(BaseModel):
    fields: Dict[str,SrcPath]

class Prompt(Object):
    fields:   List[Field] = []
    channels: List[Channel] = []
    flows:    Dict[str,Union[Control,Return]] = {}

    def mechanics(self, mech, indent):
        mechs  = [ 'start:' ]
        mechs += [ fld.mechanics(indent) +  ' ' + ' '.join(fld.desc) for fld in self.fields ]
        if len(self.flows) > 0:
            mechs += [ 'next: select which of ' + ','.join(self.flows.keys()) + " will be the next step." ]
        mechs = '\n'.join(mechs)
        return mech + '\n```\n' + mechs + '\n```'

    def formats(self, fmt, lst):
        # TODO add enum, repeat, select, and text description as needed
        # TODO next if len(self.flows) > 0
        formats = [ fld.format for fld in self.fields if fld.format is not None and fld.format.refname is not None ]
        if len(formats) > 0:
            fmtstrs = []
            for f in formats:
                fmtstrs.append(f"{lst}{f.label()}: {f.str()}")
                fmtstrs += [ f"  {lst}{desc}" for desc in f.desc ]
            return '\n' + fmt + '\n' + '\n'.join(fmtstrs)
        else:
            return ''

    def header(self, mech:str, indent:str, fmt:str, lst:str):
        return ' '.join(self.desc) + '\n' + self.mechanics(mech=mech, indent=indent) + self.formats(fmt=fmt, lst=lst)

class Program(BaseModel):
    desc:    Optional[str]    = None
    entries: Dict[str,str]    = {}

    prompts: Dict[str,Prompt] = {}
    formats: Dict[str,Format] = {}
    records: Dict[str,Record] = {}

    def toGraphViz(self):
        raise NotImplementedError()

# Specialization of `Format`

class Completion(Format):
    length: Optional[int]
    within: Optional[List[str]] = None

    def str(self):
        res = 'text'
        if self.length is not None:
            res += f'({self.length})'
        return res

class Enum(Format):
    values: List[str]
    width: int = 0

    def str(self):
        str = '","'.join(self.values)
        return f'enum("{str}")'

class Choice(Format):
    path: Path
    mode: str
    width: int = 0

    def str(self):
        return f'{self.mode}({self.path.str()})'

# Specialization of `Channel`

class Kwarg(BaseModel):
    is_input: bool
    prompt:   Optional[str]
    path:     SrcPath
    mapped:   bool

class Call(Channel):
    extern: Optional[str]
    entry:  Optional[str]
    kwargs: Dict[str,Kwarg]
    binds:  Optional[Dict[str,SrcPath]]

class Dataflow(Channel):
    prompt: Optional[str]
    src: SrcPath

class Input(Channel):
    src: SrcPath
