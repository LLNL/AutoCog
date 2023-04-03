
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from abc import abstractmethod

from .lm import LM
from .choice import TokenChoiceTree

class TokenizerLM(LM):
    @abstractmethod
    def tokenize(self, text:str) -> List[int]:
        """"""

    @abstractmethod
    def detokenize(self, tokens:List[int]) -> str:
        """"""

class LocalLM(TokenizerLM):
    model: Any
    completion_kwargs: Dict[str,Any]

    retries:int=10
    delta:float=1.
    growth:float=2.

    @abstractmethod
    def impl_greedy(self, prompt:str) -> List[float]:
        pass

    def greedy(self, prompt:str) -> List[float]:
        delta = self.delta
        errors = []
        while len(errors) < self.retries:
            try:
                return self.impl_greedy(prompt)
            except Exception as e:
                errors.append(e)
                time.sleep(delta)
                delta *= self.growth
        params = f"retries={self.retries}, delta={self.delta}s, growth={self.growth}x"
        errors = '\n - '.join(list(set(map(str,errors))))
        raise Exception(f"Persisting exception when calling {self.__class__.__name__}.greedy()\n  => {params}\n - {errors}")

    def choose(self, prompt: str, choices: List[str]) -> int:
        return TokenChoiceTree.choose(self, prompt=prompt, texts=choices)
