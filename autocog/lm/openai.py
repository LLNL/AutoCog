
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from .lm import LM

import time

try:
    import openai
    import tiktoken
except:
    print("Warning: Package `openai` and `tiktoken` needed for OpenAI wrapper (`pip install openai tiktoken`)")
    openai = None

class OpenAI(LM):
    max_tokens: int = 500
    model: str = "text-davinci-003" # "text-curie-001"
    temperature: float = 0.
    complete_bias: Dict[str,int] = { '\n' : -10 , ' ' : -10 }

    retries:int=10
    delta:float=1.
    growth:float=2.

    @staticmethod
    def create(**kwargs):
        return kwargs
    
    def __call_with_retry(self, **kwargs):
        retry = self.retries
        delta = self.delta
        while retry > 0:
            retry -= 1
            try:
                res = openai.Completion.create(**kwargs)
                return res
            except:
                time.sleep(delta)
                delta *= self.growth
        raise Exception(f"Persisting RateLimitError when contacting OpenAI with {self.model} (retries={self.retries}, delta={self.delta}s, growth={self.growth}x)")

    def tokenize(self, text:str):
        if openai is None:
            raise Exception("Error: Package `openai` and `tiktoken` needed for OpenAI wrapper (`pip install openai tiktoken`)")
        return tiktoken.encoding_for_model(self.model).encode(text)

    def detokenize(self, tokens:List[int]):
        if openai is None:
            raise Exception("Error: Package `openai` and `tiktoken` needed for OpenAI wrapper (`pip install openai tiktoken`)")
        return tiktoken.encoding_for_model(self.model).decode(tokens)

    def complete(self, prompt: str, stop:str='\n') -> str:
        if openai is None:
            raise Exception("Error: Package `openai` and `tiktoken` needed for OpenAI wrapper (`pip install openai tiktoken`)")
        res = self.__call_with_retry(
                        model=self.model,
                        prompt=prompt,
                        max_tokens=self.max_tokens,
                        stop=stop,
                        temperature=self.temperature,
                        logit_bias = { self.tokenize(s)[0] : w for (s,w) in self.complete_bias.items() }
                )
        assert len(res.choices) == 1

        return res.choices[0].text + stop

    def choose(self, prompt: str, choices: List[str]) -> int:
        if openai is None:
            raise Exception("Error: Package `openai` and `tiktoken` needed for OpenAI wrapper (`pip install openai tiktoken`)")

        tokens = [ self.tokenize(c) for c in choices ]
        token_by_idx = list(zip(*tokens))
        same_tokens = list(map(lambda x: len(set(x)) == 1, token_by_idx))
        while len(same_tokens) > 0:
            while len(same_tokens) > 0 and same_tokens[0]:
                prompt += self.detokenize([token_by_idx[0][0]])
                same_tokens = same_tokens[1:]
                token_by_idx = token_by_idx[1:]
            if len(same_tokens) == 0:
                break
            logit_bias = { c : 100 for c in set(token_by_idx[0]) }
            
            res = self.__call_with_retry(model=self.model, prompt=prompt, max_tokens=1, temperature=self.temperature, logit_bias=logit_bias)

            assert len(res.choices) == 1
            res = res.choices[0].text
            tok = self.tokenize(res)
            assert len(tok) == 1
            tok = tok[0]
            matches = [ c for (c,t) in enumerate(list(token_by_idx[0])) if tok == t ]
            if len(matches) == 1:
                return matches[0]
            prompt += res
            same_tokens = same_tokens[1:]
            token_by_idx = token_by_idx[1:]
        
        raise Exception("Should not be reached")