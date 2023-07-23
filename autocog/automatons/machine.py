
from typing import Any, Dict, List, Tuple, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel

from .instance import Instance
from .format import Text, Choice, Enum, Repeat, Select, ControlEdge, Regex, Record

import enum
class ParseState(enum.Enum):
    start=1
    content=2
    ready=3

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

    def parse_step(self, instance: Instance, LMs: Dict[str,Any], formats: Dict[str,Any]):
        internal = instance.astate().internal
        if internal == ParseState.start:
            raise Exception("Current state is not ready!")

        stop = '\n'
        offset = instance.idx
        if instance.need_prompt():
            expected = self.get_expectations(instance=instance)
            # print(f"expected={[ e.prompt for e in expected ]}")
            if len(expected) == 0:
                raise Exception("No expectation!")
            choice = 0 if len(expected) == 1 else instance.known_choice(expected)
            if isinstance(choice, list):
                choices = [ expected[c].prompt for c in choice ]
                c = LMs['text'].choose(prompt=instance.header+instance.prompt, choices=choices)
                choice = choice[c]

            if expected[choice].vstate.label == 'exit':
                # TODO check for @ptag[idx].__next
                choices = [ c for (c,l) in zip(formats['next'].choices, formats['next'].limits) if l is None or l > 0 ]
                instance.prompt += 'exit(next): '
                if len(LMs) == 0:
                    instance.next = choices[0] if len(choices) > 0 else None
                elif len(choices) > 1:
                    choice = LMs['text'].choose(prompt=instance.header+instance.prompt, choices=[c[0] for c in choices])
                    instance.next = choices[choice]
                elif len(choices) == 1:
                    instance.next = choices[0]
                else:
                    instance.next = None
                instance.prompt += ('' if instance.next is None else instance.next) + '\n'
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
                    content = LM.complete(prompt=instance.header+instance.prompt, stop=stop)
                elif isinstance(fmt, Choice):
                    if isinstance(fmt, Enum):
                        choices = fmt.choices
                    elif isinstance(fmt, Repeat) or isinstance(fmt, Select):
                        assert len(fmt.source) > 0
                        assert fmt.source[0] == ''
                        choices = instance.ravel_path(fmt.source[1:])
                        assert isinstance(choices, list)
                        if isinstance(fmt, Select):
                            choices = list(map(lambda i: f"{i+1}", range(len(choices))))
                    else:
                        raise Exception(f"Unknown Choice format: {fmt}")
                    assert len(choices) > 0
                    choice = LMs['text'].choose(prompt=instance.header+instance.prompt, choices=choices)
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

    async def execute(self, instance: Instance, LMs: Dict[str,Any], formats: Dict[str,Any], out=None, limit=None):
        #print(f"instance.content={instance.content}")
        # assert 'text' in LMs
        idx = 0
        if out is not None:
            out.write(instance.header)
        while self.parse_step(instance, LMs, formats):
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
