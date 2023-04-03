
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from .local import LocalLM

try:
    import llama_cpp
except:
    llama_cpp = "Package `llama_cpp` needed for LLaMa wrapper (pip install git+https://github.com/tristanvdb/llama-cpp-python@choice-dev)"
    print(f"Warning: {llama_cpp}")

class Llama(LocalLM):
    @staticmethod
    def create(model_path:str, logits_all=True, verbose=False, n_ctx=2048):
        return { 'model' : llama_cpp.Llama(model_path=model_path, logits_all=logits_all, verbose=verbose, n_ctx=n_ctx) }

    def __init__(self, model, completion_kwargs:Dict[str,Any]={}, **kwargs):
        if isinstance(llama_cpp,str):
            raise Exception(f"Error: {llama_cpp}")
        super().__init__(model=model, completion_kwargs=completion_kwargs, **kwargs)

    def tokenize(self, text:str) -> List[int]:
        return self.model.tokenize(bytes(text, 'utf-8'))[1:]

    def detokenize(self, tokens:List[int]) -> str:
        return self.model.detokenize(tokens).decode("utf-8", errors="ignore")

    def complete(self, prompt: str, stop:str='\n') -> str:
        return self.model(prompt, stop=[stop], **self.completion_kwargs)['choices'][0]['text'] + stop

    def impl_greedy(self, prompt: str) -> List[float]:
        output = self.model(prompt, max_tokens=1, logprobs=-1, full_logprobs=True)
        return output['choices'][0]['logprobs'][0]
