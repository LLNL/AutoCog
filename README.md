&#9881; Automaton & Cognition
=============================

[![PIP](https://github.com/LLNL/AutoCog/workflows/pip/badge.svg)](https://github.com/LLNL/AutoCog/actions)
[![STA Dataflow](https://github.com/LLNL/AutoCog/workflows/dataflow/badge.svg)](https://github.com/LLNL/AutoCog/actions)

Blantly, AutoCog aims at bridging the gap between Symbolic and Connectionnist approaches of Artificial Intelligence.
To this end, it provides the necessary components to build **complete** programming languages that are **executed** by language models.
With these programming languages, it becomes possible to implement symbolic AI algorithms on top of LM.

This is a research software: it is subject to abrupt, not-backward compatible, changes!
However, we try to keep the [Demo](./demo.ipynb) up to date. A [preprint](https://arxiv.org/abs/2306.10196) of our submission to CGO-24 is available.
The syntax presented in the paper is already a bit out-of-date...
A full [list of publications](./PAPERS.md) will be maintained.

AutoCog is a framework to design [programming models (PM)](https://en.wikipedia.org/wiki/Programming_model)
for [language models (LM)](https://en.wikipedia.org/wiki/Language_model).
It permits developers to devise Cognitive Architecture (`CogArch`) aggregating callable objects (`Cog`).
`Cog` takes a _structured document_ as input and returns another _structured document_.
They can be simple wrapper arround various API or Python code.
They can also be `Automaton` which drive Language Models (`LM`).

Currently, AutoCog provides Structured Thoughts Automaton as its sole Execution/Programming Model.
STA's language is basically "cognitive assembly", it is extremelly low-level and will be a pain to maintain.
However, we do think that it is a step forward compared to manually crafting sequences of prompts.

## Getting started

### Install

As simple as `pip install -U git+https://github.com/LLNL/AutoCog`.

But, you'll probably want to clone the repository to get the library of programs:
```
git clone https://github.com/LLNL/AutoCog
pip install -U ./AutoCog
```

### Inside a Notebook

Most of the development is done using `jupiter-lab`.
To get started take a look at the [Demo](./demo.ipynb).
Several notebooks demonstrate various part of AutoCog in the [share](./share) folder.

### Command line

#### Architecture

Very limited for now but the goal is for AutoCog's `main` to build a `CogArch` then either serve an API or run a batch of commands.

Low maintenance API, it uses JSON (filepath or inlined) to call `CogArch.build` then either `CogArch.run` or `CogArch.serve`.
The arguments are:
 - name of the architecture
 - dictionary of LMs: `{ format : { "cls" : LM, kwarg : value } }`
 - dictionary of STAs: `{ tag : ( file , { macro : value } ) }`
 - dictionary of tools: `{ tag : { "cls" : Tool, kwarg : value } }` (TODO)
 - commands or server config
   - commands: `[ ( tag, **inputs ) ]`
   - server config: TODO
```
python3 -m autocog "test-0" \
                   '{ "text" : { "cls" : "OpenAI", "max_tokens" : 20, "temperature" : 0.4 } }' \
                   '{ "fortune" : [ "./library/fortune.sta", {} ] }' \
                   '{}' \
                   '[ [ "fortune", { "question" : "Is Eureka, CA a good place for a computer scientist who love nature?" } ] ]'
```

#### Tools

Tools can be tested using the `main` from `autocog.tools`.
The first argument is the name (class) of the tool (tool need to be added in `main`).
The second is the keyword arguments for the constructor of the tool.
The third argument is the keyword arguments for calling the tools.
Both third and fourth can either be inlined JSON or the path to a JSON file.
The fourth (optional) argument is the file where the JSON ouput should be written (stdout if missing)

```
python3 -m autocog.tools pdfminer '{}' '{ "filepath" : "sta-arxiv.pdf" }' pdf.json
python3 -m autocog.tools orgmode '{}' '{ "filepath" : "share/example.org" }' org.json
python3 -m autocog.tools serpapi '{ "apikey" : "'$SERPAPI_API_KEY'" }' '{ "engine" : "google_scholar", "query" : "Structured Thought Automaton" }'
```

### Testing

Minimal testing with [`pipenv run tests/runall.sh`](./tests/runall.sh):
 - [Unit-tests](./tests/unittests)
 - Llama.cpp wrapper (must set $LLAMA_CPP_MODEL_PATH)
 - OpenAI wrapper (must set $OPENAI_API_KEY)
 
Currently only pushes to master trigger GitHub actions.
It tests `pip install` and `STA dataflow` (only set of unit-tests so far).
Looking for way to tests the LLM on GitHub (don't want to expose an API key or move the 4GB minimum of Llama 7B q4).

## Contributing

Contributions are welcome and encouraged!

We need to setup proper categories (pull-request templates) but I see:
 - libraries of reusable and composable cognitive programs:
   - GOFAI algorithms
   - cognitive drivers: uses one or more tools
 - tools
   - grep, sed, awk, jq/yq, tree-sitter, ...
   - various APIs: HuggingFace, OpenAI, search, vector-store
 - execution/programming models
   - high-level languages that compile to STA
   - other execution models:
 - features...

## License

AutoCog is distributed under the terms of the Apache License (Version 2.0) with LLVM exceptions.

All new contributions must be made under Apache-2.0 license (with LLVM exceptions).

SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

LLNL-CODE-850523
