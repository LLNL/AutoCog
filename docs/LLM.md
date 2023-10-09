AutoCog's LLM wrappers
======================

Currently, AutoCog has three LM wrappers: HuggingFace Transformers, LLaMa.cpp (GGML), and OpenAI API.

## Class Hierarchy

Class hierarchy in a nutshell ("declares" means **abstract** methods):
 * `LM`: declares `tokenize`, `detokenize`, `complete`, and `choose`.
   * `GreedyLM`: defines `greedy` and declares `greedy_impl`
     * `ChoiceLM`: defines `choose` and `TokenChoiceTree` class (TCT)
       * `TfLM` and `LLaMa`: defines `tokenize`, `detokenize`, `complete`, and `greedy_impl`
   * `OpenAI`: defines `tokenize`, `detokenize`, `complete`, and `choose`

**WIP**: Finite Thought Automaton (FTA) will become the main interface to complete prompts within AutoCog.
We are wroking on an implementation using `greedy`. We will also implement it based on `complete` and `choose`.

**Note**: for both TCT and FTA we need to implement:
 * HuggingFace pipeline
 * C++ implementation in LLaMa.cpp

## Usage

### HuggingFace Tranformers

Python packages: `transformers`

Intantiate:
```
from autocog.lm import TfLM
# create *one* instance of the model (and tokenizer)
tflm = TfLM.create(model_path='gpt2-medium', device='cpu')
# wrap the instance with specific `completion` arguments
llm = TfLM(**tflm, completion_kwargs={ 'max_new_tokens' : 20 })
```

### Llama.cpp

We currently use a modified version of the `llama-cpp-python` package.
It provides python bindings and will build `LLama.cpp`.
Our changes permit us to implement `greedy` completion (returnning full logprob).
```
pip install -y git+https://github.com/tristanvdb/llama-cpp-python@choice-dev
```

The easiest way to get the models is to use TheBloke's GGUF repositories on HuggingFace.
 - https://huggingface.co/TheBloke/Llama-2-7B-GGUF
 - https://huggingface.co/TheBloke/Llama-2-13B-GGUF
 - ...

```
from autocog.lm import Llama
llama = Llama.create(model_path="", n_ctx=4096)
llm = Llama(**llama, completion_kwargs={ 'max_tokens' : 20, 'temperature' : 0.4 })
```


### OpenAI API

**NOTE**: Some features are not available with OpenAI API, esp. LLM.greedy which returns the full vector of logprobs.

Python packages: `openai`, `tiktoken`

Set `OPENAI_API_KEY` before starting the notebook or:
```
import openai
openai.api_key = XXX
```

Instantiate a LLM:
```
from autocog.lm import OpenAI
llm = OpenAI(model='text-davinci-003', max_tokens=20, temperature=0.4)
```
