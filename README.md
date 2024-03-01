&#9881; Automaton & Cognition
=============================

[![PIP](https://github.com/LLNL/AutoCog/workflows/pip/badge.svg?branch=master)](https://github.com/LLNL/AutoCog/actions)
[![Frontend](https://github.com/LLNL/AutoCog/workflows/frontend/badge.svg?branch=master)](https://github.com/LLNL/AutoCog/actions)
[![CLI](https://github.com/LLNL/AutoCog/workflows/cli/badge.svg?branch=master)](https://github.com/LLNL/AutoCog/actions)

Auotmaton & Cognition explores mechanism to build simple automaton that drive cognitive processes.
To this end, we defined a programming model, Structured Thoughts, which compiles to a collection of automaton.
Each automaton defines a prompt and guides its completion.
Completed prompts are parsed and the etracted data flows to the next prompt.

## Getting started

### Install

As simple as `pip install -U git+https://github.com/LLNL/AutoCog`.

But, you'll probably want to clone the repository to get the library of programs:
```
git clone https://github.com/LLNL/AutoCog
pip install -U ./AutoCog
```

### LLM Setup

#### LLama.cpp and GGUF models

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

#### HuggingFace Transformers

> TODO v0.6: connection for HuggingFace Transformers package (use to have it but not tested)

### Inside a Notebook

Most of the development is done inside Python notebook (jupiterlab).
Eventually, several notebooks demonstrating various part of AutoCog will be provided in the [share](./share) folder.
To get an idea of our progress, take a look at the [WIP Notebook](./share/wip.ipynb).

### Command line

We are building a command line tool to use AutoCog.

`python3 -m autocog --help`

```
usage: __main__.py [-h] [--version] [--orch ORCH] [--gguf GGUF] [--gguf-ctx GGUF_CTX] [--syntax SYNTAX] [--cogs COGS] [--command COMMAND] [--output OUTPUT] [--prefix PREFIX] [--serve] [--host HOST] [--port PORT] [--debug]

optional arguments:
  -h, --help           show this help message and exit
  --version            show program's version number and exit
  --orch ORCH          Type of orchestrator: `serial` or `async`. (default: serial)
  --gguf GGUF          Load a model from a GGUF file using llama.cpp (and llama-cpp-python) (default: None)
  --gguf-ctx GGUF_CTX  Context size for GGUF models (default: 4096)
  --syntax SYNTAX      One of `Llama-2-Chat`, `ChatML`, `Guanaco` or a dictionary of the kwargs to initialize a Syntax object (inlined JSON or path to a file). (default: None)
  --cogs COGS          Files to load as cog in the architecture, prefix with its identifier else the filename is used. For example, `some/cognitive/mcq.sta` and `my.tool:some/python/tool.py` will load a Structured Thought
                       Automaton as `mcq` and a Python file as `my.tool`. (default: None)
  --command COMMAND    Command to be executed by the architecture as a dictionary. `__tag` identify the cog while `__entry` identify the entry point in this cog (defaults to `main`). All other field will be forwarded as
                       keyworded args. Example: `{ "__tag" : "writer", "__entry" : "main", **kwarg }` (inlined JSON or path to a file). Can also provide one or more list of dictionary. (default: None)
  --output OUTPUT      Directory where results are stored. (default: /home/tristan/projects/LLM/AutoCog)
  --prefix PREFIX      String to identify this instance of AutoCog (default: autocog)
  --serve              Whether to launch the flask server. (default: False)
  --host HOST          Host for flask server. (default: localhost)
  --port PORT          Port for flask server. (default: 5000)
  --debug              Whether to run the flask server in debug mode. (default: False)
```

Some examples:
```
python3 -m autocog --gguf /data/models/tinyllama-2-1b-miniguanaco.Q4_K_M.gguf --syntax Guanaco \
                   --cogs mmlu.repeat_cot:library/mmlu-exams/repeat-cot.sta \
                   --command '{ "__tag" : "mmlu.repeat_cot", "topic" : "arithmetic", "question" : "What is 3*4+9?", "choices" : [ "16", "21", "39", "42" ] }'
```
```
python3 -m autocog --gguf /data/models/llama-2-7b-chat.Q4_K_M.gguf --syntax Llama-2-Chat \
                   --syntax '{ "prompt_with_format" : false, "prompt_with_index" : false, "prompt_indent" : "" }' \
                   --cogs mmlu.repeat_cot:library/mmlu-exams/repeat-cot.sta \
                   --cogs mmlu.select_cot:library/mmlu-exams/select-cot.sta \
                   --command '{ "__tag" : "mmlu.repeat_cot", "topic" : "arithmetic", "question" : "What is 3*4+9?", "choices" : [ "16", "21", "39", "42" ] }' \
                   --command '{ "__tag" : "mmlu.select_cot", "topic" : "arithmetic", "question" : "What is 3*4+9?", "choices" : [ "16", "21", "39", "42" ] }'
```

### Web Application

The goal is to provide a development environment.
Particularly, the ability to inspect and edit/replay `frames`.
These are created for each execution of an `Automaton` (nested when an `Automaton` call another `Automaton`).
Upon ending, the execution trace of the `Automaton` is saved in the corresponding frame.

Eventually, we want to use these traces for two purposes:
 - replay: edit part of the trace then restart the program from that point
 - finetuning: select "succesful" frames to finetune models

Run the command below at the root of the repository to launch a server. It uses [quart](http://pgjones.gitlab.io/quart).
```
python3 -m autocog --serve --host 0.0.0.0 --port 5000 --cogs mmlu.repeat_cot:library/mmlu-exams/repeat-cot.sta
```

![Webapp -- Work in Progress](./share/webapp/webapp.png)]

### Testing (TODO update for v0.4)

Minimal testing with [`pipenv run tests/runall.sh`](./tests/runall.sh):
 - [Unit-tests](./tests/unittests)
 - Llama.cpp wrapper (must set $LLAMA_CPP_MODEL_PATH)
 - OpenAI wrapper (must set $OPENAI_API_KEY)
 
Currently only pushes to master trigger GitHub actions.
It tests `pip install` and `STA dataflow` (only set of unit-tests so far).
Looking for way to tests the LLM on GitHub (don't want to expose an API key or move the 4GB minimum of Llama 7B q4).

## Contributing

Contributions are welcome!

So far there is only one rule: **linear git history** (no merge commits).
Only the master branch have stable commits, other branches might be rebased without notice.

Version number will increase for each push to master and have a matching tag.

## License

AutoCog is distributed under the terms of the Apache License (Version 2.0) with LLVM exceptions.

All new contributions must be made under Apache-2.0 license (with LLVM exceptions).

SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

LLNL-CODE-850523
