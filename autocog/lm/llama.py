
from typing import Any, Dict, List, Tuple, Union, Optional, Callable
from .lm import LM

try:
    import llama_cpp
except:
    llama_cpp = "Package `llama_cpp` needed for LLaMa wrapper (pip install git+https://github.com/tristanvdb/llama-cpp-python@choice-dev)"
    print(f"Warning: {llama_cpp}")

class Llama(LM):
    model: Any

    def __init__(self, model_path:str, logits_all=True, verbose=False, n_ctx=2048, **kwargs):
        if isinstance(llama_cpp,str):
            raise Exception(f"Error: {llama_cpp}")
        super().__init__(
            model=llama_cpp.Llama(model_path=model_path, logits_all=logits_all, verbose=verbose, n_ctx=n_ctx), **kwargs
        )

    def tokenize(self, text:str, whole:bool=True) -> List[int]:
        if not isinstance(text,str):
            raise Exception(f'text={text}')

        if text == '\n':
            return [ self.model.token_nl() ]

        if not whole:
            text = '\n ' + text

        tokens = self.model.tokenize(bytes(text, 'utf-8'))

        if not whole:
            while tokens[0] != self.model.token_nl():
                tokens = tokens[1:]
            return tokens[1:]
        elif tokens[0] == self.model.token_bos():
            return tokens[1:]
        else:
            return tokens

    def detokenize(self, tokens:List[int], whole:bool=True) -> str:
        if not whole:
            tokens = [ self.model.token_nl() ] + tokens
        tokens = [ self.model.token_bos() ] + tokens + [ self.model.token_eos() ]
        text = self.model.detokenize(tokens).decode("utf-8", errors="replace")
        if text.endswith('<|im_end|>'):
            text = text[:-len('<|im_end|>')]
        return text

    def impl_greedy(self, prompt: Union[str,List[int]]) -> List[float]:
        output = self.model.create_completion(prompt, max_tokens=1, logprobs=-1, full_logprobs=True)
        return output['choices'][0]['logprobs'][0]
