
from typing import Any, Dict, List, Tuple, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel


import gc
import time

try:
    import torch
except:
    torch = None

def clear_caches():
    gc.collect()
    if torch is not None:
        torch.cuda.empty_cache()

class LM(BaseModel):
    model: Any

    retries:int=3
    delta:float=1.
    growth:float=4.
    
    @abstractmethod
    def tokenize(self, text:str) -> List[int]:
        """"""

    @abstractmethod
    def detokenize(self, tokens:List[int]) -> str:
        """"""

    @abstractmethod
    def impl_greedy(self, prompt:str):
        """"""

    def greedy(self, prompt:str):
        delta = self.delta
        errors = []
        while len(errors) < self.retries:
            try:
                return self.impl_greedy(prompt)
            except Exception as e:
                errors.append(e)
                time.sleep(delta)
                clear_caches()
                delta *= self.growth
        params = f"retries={self.retries}, delta={self.delta}s, growth={self.growth}x"
        errors = '\n - '.join(list(set(map(str,errors))))
        raise Exception(f"Persisting exception when calling {self.__class__.__name__}.greedy()\n  => {params}\n - {errors}")
