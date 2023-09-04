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

class Value(Expression):
    value: Union[int,str]
    is_fstring: bool = False

    def gvtree(self):
        yield from super().gvtree()

    def gvlbl(self):
        if isinstance(self.value, int):
            return self.value
        elif is_fstring:
            return f'f"{self.value}"'
        else:
            return f'"{self.value}"'

class Reference(Expression):
    name: str

    def gvtree(self):
        yield from super().gvtree()

    def gvlbl(self):
        return f'@{self.name}'

class Path(ASTNode):
    def gvtree(self):
        yield from super().gvtree()

class Call(ASTNode):
    def gvtree(self):
        yield from super().gvtree()

class TypeRef(ASTNode):
    name:   str
    params: List[Tuple[Optional[str],Expression]]

    def gvtree(self):
        yield from super().gvtree()
        for (p,(lbl,expr)) in enumerate(self.params):
            raise NotImplementedError()

class Declaration(ASTNode):
    name: str

    def gvtree(self):
        yield from super().gvtree()

    def gvlbl(self):
        return f"{self.__class__.__name__}: {self.name}"

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
    fields:      List["Field"]    = []
    annotations: List[Annotation] = []

    def gvtree(self):
        yield from super().gvtree()
        for (i,n) in enumerate(self.fields):
            yield ("field",i,n)
        for (i,n) in enumerate(self.annotations):
            yield ("annotation",i,n)

class Field(Declaration):
    type:       Union[Record,TypeRef]
    annotation: str

    def gvtree(self):
        yield from super().gvtree()
        yield ("type",None,self.type)

class Format(Declaration,Scope):
    type:       TypeRef
    annotation: str

    def gvtree(self):
        yield from super().gvtree()
        yield ("type",None,self.type)
    
class Struct(Declaration,Scope,Record):
    def gvtree(self):
        yield from super().gvtree()

class Channel(ASTNode):
    target: Path
    source: Union[Path,Call]

    def gvtree(self):
        yield from super().gvtree()
        yield ("target",None,self.target)
        yield ("source",None,self.source)

class RetField(ASTNode):
    field: Path
    rename: Optional[str]

    def gvtree(self):
        yield from super().gvtree()
        yield ("field",None,self.field)

class RetBlock(ASTNode):
    fields: List[RetField] = []
    alias:  Optional[str]  = None

    def gvtree(self):
        yield from super().gvtree()
        for (i,n) in enumerate(self.fields):
            yield ("field",i,n)

class Flow(ASTNode):
    prompt: str
    alias:  Optional[str] = None

    def gvtree(self):
        yield from super().gvtree()

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
