Usage
=====

## Inside a Notebook

Most of the development is done inside Python notebook (jupiterlab).
Eventually, several notebooks demonstrating various part of AutoCog will be provided in the [share](./share) folder.
To get an idea of our progress, take a look at the [WIP Notebook](./share/wip.ipynb).

## Command line

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

Currently, the AutoCog application only saves the output of the commands in a JSON file.

> TODO v0.5: saving the "pages"

## Web Application

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
