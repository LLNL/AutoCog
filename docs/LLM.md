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

#### Clone and build llama.cpp

```
git clone https://github.com/ggerganov/llama.cpp.git
python3 -m pip install -r llama.cpp/requirements.txt
make -C llama.cpp -j4 # runs make in subdir with 4 processes
```

#### Download and convert weights

We show how to use [OpenLLaMa](https://github.com/openlm-research/open_llama) instead of Meta's LLaMa.
You might need to install the `git-lfs` package.
```
git clone https://huggingface.co/openllmplayground/openalpaca_3b_600bt_preview
python3 llama.cpp/convert.py models/7B/
./llama.cpp/quantize models/7B/ggml-model-f16.bin models/7B/ggml-model-q4_0.bin q4_0
```
This download script support all sizes of LLaMa: 7B, 13B, 30B, and 65B (download them all at once with `7B,13B,30B,65B` as 1st argument).

#### Install python binding

It will install its own `llama.cpp` so you only need to preserve the models.
```
!pip install -y git+https://github.com/tristanvdb/llama-cpp-python@choice-dev
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
