
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

class Format(Object):
    annonymous: bool = False

    def str(self):
        raise NotImplementedError()

    def label(self):
        return self.str() if self.annonymous else self.name

class Field(Object):
    depth:  int
    format: Optional[Format]
    range:  Range
    parent: Union["Prompt","Field"]

class Record(Object):
    fields: List[Field] = []

class Channel(BaseModel):
    tgt: Field

class Prompt(Object):
    fields:   List[Field]   = []
    channels: List[Channel] = []

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

    def str(self):
        str = '","'.join(self.values)
        return f'enum("{str}")'

class Choice(Format):
    path: Path
    mode: str

    def str(self):
        return f'{self.mode}({self.path.str()})'

# Specialization of `Channel`

class Call(Channel):
    callee: Tuple[str,str]
    kwargs: Dict[str,Any] = {} # TODO Any?
    binds:  Any = None # TODO Any?

class Dataflow(Channel):
    src: Field

class Input(Channel):
    src: List[str]
