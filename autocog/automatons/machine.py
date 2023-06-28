
from typing import Any, Dict, List, Tuple, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel

from .base import Text, Choice, Enum, Repeat, ControlEdge, Regex, Record

# TODO clean-up the whole enumerator thingy...
import enum
from ..utility.enums import a_enumerator
class ParseState(enum.Enum):
    start   = a_enumerator(tag='start',   desc='')
    content = a_enumerator(tag='content', desc='')
    ready   = a_enumerator(tag='ready',   desc='')

class VirtualState(BaseModel):
    label: str            # 
    desc:  str = ''       # a description for the help
    fmt: str = 'text'     # format of the response

    @abstractmethod
    def tag(self, ptag:Optional[str]=None):
        if ptag is None:
            ptag = self.label
        return ptag

class ActualState(BaseModel):
    vstate: VirtualState
    internal: ParseState = ParseState.start

class Expectations(BaseModel):
    vstate: VirtualState
    prompt: str
    idx: int

    def args(self):
        return [self.vstate,self.idx]

class Instance(BaseModel):
    prompt: str = ''
    idx: int = 0

    next: Optional[str] = None

    started: bool = False

    @abstractmethod
    def vstate(self):
        """"""

    @abstractmethod
    def need_prompt(self):
        """"""

    @abstractmethod
    def need_content(self):
        """"""

    @abstractmethod
    def build_astate(self):
        """"""

    @abstractmethod
    def astate(self):
        """"""

    @abstractmethod
    def get_content(self):
        """"""

    @abstractmethod
    def set_content(self):
        """"""

    @abstractmethod
    def known_choice(self):
        """"""

    @abstractmethod
    def write_content(self):
        """"""

    @abstractmethod
    def fork(self):
        """"""

class StateMachine(BaseModel):
    tag:         str = ''
    states:      Dict[str, VirtualState] = {}

    @abstractmethod
    def toGraphViz(self) -> str:
        """"""

    @abstractmethod
    def mechanics(self) -> str:
        """"""

    @abstractmethod
    def init(self) -> Instance:
        """"""

    @abstractmethod
    def get_expectations(self, instance: Instance) -> List[Expectations]:
        """"""

    def __consume_prompt(self, instance: Instance, match: Expectations):
        instance.prompt += match.prompt
        instance.build_astate(*match.args())
        instance.astate().internal = ParseState.content
        return len(match.prompt)

    def parse_step(self, instance: Instance, LMs: Dict[str,Any], header:str, formats: Dict[str,Any]):
        internal = instance.astate().internal
        if internal == ParseState.start:
            raise Exception("Current state is not ready!")

        stop = '\n'
        offset = instance.idx
        if instance.need_prompt():
            expected = self.get_expectations(instance=instance)
            if len(expected) == 0:
                raise Exception("No expectation!")
            choice = 0 if len(expected) == 1 else instance.known_choice(expected)
            if isinstance(choice, list):
                choice = LMs['text'].choose(prompt=header+instance.prompt, choices=[ expected[c].prompt for c in choice ])

            if expected[choice].vstate.label == 'exit':
                choices = [ c for (c,l) in zip(formats['next'].choices, formats['next'].limits) if l is None or l > 0 ]
                if len(LMs) == 0:
                    # This happen when unit testing the dataflow (without LM)
                    #      tests/unittests/iteration-text-flow.sta
                    # For now just take the first choice, meaning that loops must be bounded.
                    # This will "exhaust" the branches from left to right.
                    # TODO mechanism to force a specfic path through the CFG? How to create matching dataflow production? Either use a call channel or a "fake" LM.
                    instance.next = choices[0] if len(choices) > 0 else None
                elif len(choices) > 1:
                    choice = LMs['text'].choose(prompt=header+instance.prompt+'exit(next): ', choices=[c[0] for c in choices])
                    instance.next = choices[choice]
                elif len(choices) == 1:
                    instance.next = choices[0]
                else:
                    instance.next = None
                return False

            offset += self.__consume_prompt(instance=instance, match=expected[choice])

        elif instance.need_content():
            content = instance.get_content()
            if content is not None:
                if not isinstance(content, str):
                    if isinstance(content, bool) or isinstance(content, int) or isinstance(content, float):
                        content = str(content)
                    else:
                        print(f"content={content}")
                        raise Exception(f"Trying to print object of class `{content.__class__.__name__}` in the prompt.")
                instance.prompt += content + stop
                offset += len(content) + len(stop)
            else:
                instance.started = True
                fmt = instance.vstate().fmt
                fmt = formats[fmt]
                content = None
                if isinstance(fmt, Text):
                    LM = None
                    while LM is None:
                        assert fmt.label in formats, f"Cannot find {fmt.label} in {formats.keys()}"
                        if fmt.label in LMs:
                            LM = LMs[fmt.label]
                        else:
                            assert fmt.base is not None, f"Probably reach the top of the format hierarchy and did not find a match in the provided LM configs: {LMs.keys()}"
                            assert fmt.base in formats, f"Cannot find {fmt.base} in {formats.keys()}"
                            fmt = formats[fmt.base]
                    assert LM is not None
                    content = LM.complete(prompt=header+instance.prompt, stop=stop)
                elif isinstance(fmt, Choice):
                    if isinstance(fmt, Enum):
                        choices = fmt.choices
                    elif isinstance(fmt, Repeat):
                        assert len(fmt.source) == 2
                        assert fmt.source[0] == ''
                        content = instance.content
                        assert fmt.source[1] in content
                        content = content[fmt.source[1]]
                        assert isinstance(content, list)
                        choices = content
                    else:
                        raise Exception(f"Unknown Choice format: {fmt}")
                    choice = LMs['text'].choose(prompt=header+instance.prompt, choices=choices)
                    content = choices[choice] + stop
                else:
                    raise Exception(f"Unknown format: {fmt}")
                assert content is not None
                instance.prompt += content
                stop_idx = instance.prompt[offset:].find(stop)
                if stop_idx >= 0:
                    val = instance.prompt[offset:offset+stop_idx]
                    if fmt.caster is not None:
                        val = fmt.caster(val)
                    instance.set_content(val)
                    offset += stop_idx + len(stop)
                else:
                    raise Exception("Could not find stop token for content!")
            instance.astate().internal = ParseState.ready

        else:
            raise Exception("This should not happen!")

        instance.idx = offset

        return True

    async def execute(self, instance: Instance, LMs: Dict[str,Any], header:str, formats: Dict[str,Any], out=None, limit=None):
        #print(f"instance.content={instance.content}")
        # assert 'text' in LMs
        idx = 0
        if out is not None:
            out.write(header)
        while self.parse_step(instance, LMs, header, formats):
            #print(f"> instance.idx:    {instance.idx}")
            #print(f'> instance.vstate: {instance.vstate().label}')
            if out is not None and idx < instance.idx:
                out.write(instance.prompt[idx:instance.idx])
            idx = instance.idx
            assert limit is None or idx < limit
        if instance.next is not None:
            for (c,ch) in enumerate(formats['next'].choices):
                if ch == instance.next and formats['next'].limits[c] is not None:
                    formats['next'].limits[c] -= 1
        return instance
