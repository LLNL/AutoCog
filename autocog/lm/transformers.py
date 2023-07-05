
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from .choice import ChoiceLM

try:
    import transformers
    from transformers import AutoTokenizer, AutoModelForCausalLM
except:
    transformers = "Package `transformers` needed for (Huggingface's) transformers wrapper"
    print(f"Warning: {transformers}")

class TfLM(ChoiceLM):
    tokenizer: Any
    device: str

    @staticmethod
    def create(model_path:str, device:str='cuda', T=None, M=None):
        if T is None:
            T = transformers.AutoTokenizer
        if M is None:
            M = transformers.AutoModelForCausalLM

        tokenizer = T.from_pretrained(model_path)
        model = M.from_pretrained(model_path)
        if device is not None:
            model = model.to(device)
        return { 'model' : model, 'tokenizer' : tokenizer, 'device' : device }

    def __init__(self, model, tokenizer, device:str, completion_kwargs:Dict[str,Any]={}, **kwargs):
        if isinstance(transformers,str):
            raise Exception(f"Error: {transformers}")
        super().__init__(model=model, tokenizer=tokenizer, device=device, completion_kwargs=completion_kwargs, **kwargs)

    def tokenize(self, text:str) -> List[int]:
        return self.tokenizer.encode(text, add_special_tokens=True)

    def detokenize(self, tokens:List[int]) -> str:
        return self.tokenizer.decode(tokens)

    def impl_greedy(self, prompt: str) -> List[float]:
        input_ids = self.tokenizer.encode(prompt, add_special_tokens=True, return_tensors='pt')
        if self.device is not None:
            input_ids = input_ids.to(self.device)
        logits = self.model(input_ids=input_ids).logits
        logits = logits[0,0].tolist()
        return logits

    def complete(self, prompt: str, stop:str='\n') -> str:
        input_ids = self.tokenizer.encode(prompt, add_special_tokens=True, return_tensors='pt')
        if self.device is not None:
            input_ids = input_ids.to(self.device)
        output_sequences = self.model.generate(
            input_ids=input_ids,
            do_sample=True,
            num_return_sequences=1,
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=0,
            early_stopping=True,
            bad_words_ids=[ [ self.tokenizer.encode(stop)[0] ] ],
            **self.completion_kwargs
        )
        tokens = output_sequences[0].tolist()
        tokens = tokens[input_ids.shape[1]:]
        output_text = self.detokenize(tokens)
        if output_text.find(stop) != -1:
            ## it seems that when `max_new_tokens` is set it does not stop on `bad_words_ids`
            # for (i,tok) in enumerate(tokens):
            #     text = self.detokenize([tok])
            #     if text.find(stop) != -1:
            #         import json
            #         print(f'Warning: Token {tok} produces {json.dumps(text)} seen at idx={i} of len={len(tokens)}')
            output_text = output_text.split('\n')[0]
        return output_text + stop
