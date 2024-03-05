Setup
=====

## Install AutoCog

As simple as `pip install -U git+https://github.com/LLNL/AutoCog`.

But, you'll probably want to clone the repository to get the library of programs:
```
git clone https://github.com/LLNL/AutoCog
pip install -U ./AutoCog
```

## LLM Setup

### LLama.cpp and GGUF models

We download model from [TheBloke](https://huggingface.co/TheBloke) on Hugging Face.
For example, you can donwload LlaMa 2 with 7B parameters and tuned for Chat with:
```
wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf
```
This is a 4 bits version, aka `Q4_K_M` in the name. It is the main model we use for testing.

To run GGUF model, we use a [modified version](https://github.com/tristanvdb/llama-cpp-python/tree/choice-dev) of the `llama-cpp-python` package.
It provides python bindings and will build `LLama.cpp`.
Our changes permit us to implement `greedy` completion (returning logprob for all tokens).
```
pip install -y git+https://github.com/tristanvdb/llama-cpp-python@choice-dev
```

> TODO v0.5: connect to low-level API in `llama-cpp-python` so that we can use the default release

### HuggingFace Transformers

> TODO v0.6: connection for HuggingFace Transformers package (use to have it but not tested)