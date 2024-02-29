
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from .lm import LM

try:
    import transformers
    from transformers import AutoTokenizer, AutoModelForCausalLM
except:
    transformers = "Package `transformers` needed for (Huggingface's) transformers wrapper"
    print(f"Warning: {transformers}")

class TfLM(LM):
    tokenizer: Any
    device: str

    def __init__(self,model_path:str, device:Optional[str], T=None, M=None, **kwargs):
        if isinstance(transformers,str):
            raise Exception(f"Error: {transformers}")

        if T is None:
            T = transformers.AutoTokenizer
        if M is None:
            M = transformers.AutoModelForCausalLM

        tokenizer = T.from_pretrained(model_path)
        model = M.from_pretrained(model_path)
        if device is not None:
            model = model.to(device)

        super().__init__(model=model, tokenizer=tokenizer, device=device, **kwargs)

    def tokenize(self, text:str, whole:bool=True) -> List[int]:
        return self.tokenizer.encode(text, add_special_tokens=True)

    def detokenize(self, tokens:List[int], whole:bool=True) -> str:
        return self.tokenizer.decode(tokens)

    def impl_greedy(self, prompt: str) -> List[float]:
        input_ids = self.tokenizer.encode(prompt, add_special_tokens=True, return_tensors='pt')
        if self.device is not None:
            input_ids = input_ids.to(self.device)
        logits = self.model(input_ids=input_ids).logits
        logits = logits[0,0].tolist()
        return logits
