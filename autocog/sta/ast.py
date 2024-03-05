from typing import Any, Dict, List, Tuple, Optional, NamedTuple, Callable, Union
from abc import abstractmethod
from pydantic import BaseModel

class ASTNode(BaseModel):
    def toGraphViz(self):
        nodes = {}
        edges = []
        self.toGraphVizRec(nodes, edges)
        dotstr = ''
        for (tag,lbl) in nodes.items():
            dotstr += f'{tag} [label="{lbl}"];\n'
        for (src,tgt,lbl) in edges:
            dotstr += f'{src} -> {tgt} [label="{lbl}"];\n'
        return dotstr
        
    def toGraphVizRec(self, nodes: Dict[str,str], edges: List[Tuple[str,str,str]]):
        tag = f"n_{len(nodes)}"
        nodes.update({ tag : self.gvlbl() })
        for (lbl,idx,node) in self.gvtree():
            assert node is not None, f"self={self}"
            ctag = node.toGraphVizRec(nodes, edges)
            edges.append(( tag, ctag, lbl if idx is None else f"{lbl}[{idx}]" ))
        return tag

    def gvlbl(self):
        return self.__class__.__name__

    def gvtree(self):
        yield from ()

class Expression(ASTNode):

    def gvtree(self):
        yield from super().gvtree()

    def eval(self, values:Dict[str,Any]):
        raise NotImplementedError()

class Value(Expression):
    value: Union[int,str]
    is_fstring: bool = False

    def gvtree(self):
        yield from super().gvtree()

    def gvlbl(self):
        if isinstance(self.value, int):
            return self.value
        elif self.is_fstring:
            return f'f\\"{self.value}\\"'
        else:
            return f'\\"{self.value}\\"'

    def eval(self, values:Dict[str,Any]):
        if self.is_fstring:
            return self.value.format(**values)
        else:
            return self.value

class Reference(Expression):
    name: str

    def gvtree(self):
        yield from super().gvtree()

    def gvlbl(self):
        return f'${self.name}'

    def eval(self, values:Dict[str,Any]):
        if self.name in values:
            return values[self.name]
        else:
            raise Exception(f"Cannot find {self.name} in {','.join(values.keys())}") 

class Slice(ASTNode):
    start: Expression
    stop: Optional[Expression] = None

    def gvtree(self):
        yield from super().gvtree()
        yield ("start",None,self.start)
        if self.stop is not None:
            yield ("stop",None,self.stop)

class Step(ASTNode):
    name: str
    slice: Optional[Slice] = None

    def gvtree(self):
        yield from super().gvtree()
        if self.slice is not None:
            yield ("slice",None,self.slice)

    def gvlbl(self):
        return f"{self.__class__.__name__}\\n{self.name}"
    
class Path(ASTNode):
    steps: List[Step] = []
    is_input: bool = False
    prompt: Optional[str] = None

    def gvtree(self):
        yield from super().gvtree()
        for (i,step) in enumerate(self.steps):
            yield ("step",i,step)

    def gvlbl(self):
        return f"{self.__class__.__name__}\\n{self.prompt}\\n{self.is_input}"

class Kwarg(ASTNode):
    name: str
    source: Path
    mapped: bool = False

    def gvtree(self):
        yield from super().gvtree()
        yield ("source",None,self.source)

    def gvlbl(self):
        return f"{self.__class__.__name__}\\n{self.name}\\n{self.mapped}"

class Bind(ASTNode):
    source: Path
    target: str

    def gvtree(self):
        yield from super().gvtree()
        yield ("source",None,self.source)

    def gvlbl(self):
        return f"{self.__class__.__name__}\\n{self.target}"
    
class Call(ASTNode):
    extern: Optional[str] = None
    entry:  Optional[str] = None
    kwargs: List[Kwarg]   = []
    binds:  List[Bind]    = []

    def gvtree(self):
        yield from super().gvtree()
        for (i,n) in enumerate(self.kwargs):
            yield ("kwarg",i,n)
        for (i,n) in enumerate(self.binds):
            yield ("bind",i,n)

    def gvlbl(self):
        return f"{self.__class__.__name__}\\n{self.extern}\\n{self.entry}"

class Argument(ASTNode):
    value: Expression
    name: Optional[str] = None

    def gvtree(self):
        yield from super().gvtree()
        yield ("value",None,self.value)

    def gvlbl(self):
        if self.name:
            return f"{self.__class__.__name__}\\n{self.name}"
        else:
            return f"{self.__class__.__name__}"

class TypeRef(ASTNode):
    name:   str
    arguments: List[Argument] = []

    def gvtree(self):
        yield from super().gvtree()
        for (i,arg) in enumerate(self.arguments):
            yield ("argument",i,arg)

    def gvlbl(self):
        return f"{self.__class__.__name__}\\n{self.name}"

class EnumType(ASTNode):
    kind: str
    arguments: List[Argument] = []
    source: Union[Path,List[Expression]]

    def gvtree(self):
        yield from super().gvtree()
        for (i,arg) in enumerate(self.arguments):
            yield ("argument",i,arg)
        if isinstance(self.source, Path):
            yield ("path",None,self.source)
        else:
            for (i,src) in enumerate(self.source):
                yield ("value",i,src)

    def gvlbl(self):
        return f"{self.__class__.__name__}\\n{self.kind}"

class Declaration(ASTNode):
    name: str

    def gvtree(self):
        yield from super().gvtree()

    def gvlbl(self):
        return f"{self.__class__.__name__}\\n{self.name}"

class Variable(Declaration):
    initializer: Optional[Expression]
    is_argument: bool = False

    def gvtree(self):
        yield from super().gvtree()
        if self.initializer is not None:
            yield ("initializer", None, self.initializer)

class Scope(ASTNode):
    variables: List[Variable] = []

    def gvtree(self):
        yield from super().gvtree()
        for (i,decl) in enumerate(self.variables):
            yield ("variable",i,decl)

class Annotation(ASTNode):
    what: Path
    label: Expression

    def gvtree(self):
        yield from super().gvtree()
        yield ("what",None,self.what)
        yield ("label",None,self.label)

class Record(ASTNode):
    fields:      List["Field"]

    def gvtree(self):
        yield from super().gvtree()
        for (i,n) in enumerate(self.fields):
            yield ("field",i,n)

class Field(Declaration):
    range: Optional[Slice]
    type: Union[Record,TypeRef,EnumType]

    def gvtree(self):
        yield from super().gvtree()
        if self.range is not None:
            yield ("range",None,self.range)
        yield ("type",None,self.type)

class Format(Declaration,Scope):
    type:       Union[TypeRef,EnumType]
    annotation: Optional[Expression] = None

    def gvtree(self):
        yield from super().gvtree()
        yield ("type",None,self.type)
        if self.annotation is not None:
            yield ("annotation",None,self.annotation)

class Struct(Declaration,Scope,Record):
    annotations: List[Annotation] = []

    def gvtree(self):
        yield from super().gvtree()
        for (i,n) in enumerate(self.annotations):
            yield ("annotation",i,n)

class Channel(ASTNode):
    target: Path
    source: Union[Path,Call]

    def gvtree(self):
        yield from super().gvtree()
        yield ("target",None,self.target)
        yield ("source",None,self.source)

class RetField(ASTNode):
    field: Path
    rename: Optional[Expression] = None

    def gvtree(self):
        yield from super().gvtree()
        yield ("field",None,self.field)
        if self.rename is not None:
            yield ("rename",None,self.rename)

class RetBlock(ASTNode):
    fields: List[RetField] = []
    alias:  Optional[Expression]  = None

    def gvtree(self):
        yield from super().gvtree()
        for (i,n) in enumerate(self.fields):
            yield ("field",i,n)
        if self.alias is not None:
            yield ("alias",None,self.alias)

class Flow(ASTNode):
    prompt: str
    limit:  Optional[Expression] = None
    alias:  Optional[Expression] = None

    def gvtree(self):
        yield from super().gvtree()
        if self.limit is not None:
            yield ("limit",None,self.limit)
        if self.alias is not None:
            yield ("alias",None,self.alias)

    def gvlbl(self):
        return f"{self.__class__.__name__}\\n{self.prompt}"

class Prompt(Struct):
    channels: List[Channel]      = []
    flows:    List[Flow]         = []
    returns:  Optional[RetBlock] = None

    def gvtree(self):
        yield from super().gvtree()
        for (i,n) in enumerate(self.channels):
            yield ("channel",i,n)
        for (i,n) in enumerate(self.flows):
            yield ("flow",i,n)
        if self.returns is not None:
            yield ("return",None,self.returns)

class Program(Scope):
    formats:     List[Format]     = []
    structs:     List[Struct]     = []
    prompts:     List[Prompt]     = []
    flows:       List[Flow]       = []
    annotations: List[Annotation] = []

    def gvtree(self):
        yield from super().gvtree()
        for (i,n) in enumerate(self.formats):
            yield ("format",i,n)
        for (i,n) in enumerate(self.structs):
            yield ("struct",i,n)
        for (i,n) in enumerate(self.prompts):
            yield ("prompt",i,n)
        for (i,n) in enumerate(self.flows):
            yield ("flow",i,n)
        for (i,n) in enumerate(self.annotations):
            yield ("annotation",i,n)
