&#9881; Automaton & Cognition
=============================

[![PIP](https://github.com/LLNL/AutoCog/workflows/pip/badge.svg)](https://github.com/LLNL/AutoCog/actions)
[![STA Dataflow](https://github.com/LLNL/AutoCog/workflows/dataflow/badge.svg)](https://github.com/LLNL/AutoCog/actions)

AutoCog primary goal is to provide the essential components for constructing comprehensive programming languages that can be effectively executed by language models (LMs). Through the utilization of these programming languages, it will becomes feasible to implement symbolic AI algorithms on top of LM.

At present, AutoCog offers Structured Thoughts Automaton (STA) as its sole Programming Model. STA's language is inherently low-level and may present challenges in terms of maintenance. For those interested in delving deeper, we have also made available a [preprint](https://arxiv.org/abs/2306.10196) of our submission to CGO-24. It is worth mentioning that the syntax presented in the publication is slightly outdated. The design of a proper language is one of our priority. To stay informed about our latest contributions, we will diligently curate a comprehensive [list of publications](./docs/PAPERS.md).

We are developing Finite Thought Automata (FTA) to act as the underlying Machine Model for AutoCog. In a nutshell, FTA enables to express a prompt as a finite automata over the alphabet of the LM. FTA is then used to enforce low-level syntax in the prompt. It ensures that the LM always provides completions that are parseable by the execution model. Initial work on FTA: [source](./autocog/automatons/fta) and [notebook](./share/fta.ipynb) (where we try to force untrained model to ouput numbers as "XX,XXX,XXX.XX").

As a research software, it is important to note that AutoCog undergoes continuous development, which may result in sudden and non-backward compatible changes. Nonetheless, we strive to maintain an up-to-date [Demo](./demo.ipynb), offering a glimpse into the capabilities of the framework. The [share](./share) directory also contains several notepads, particularly the notebooks for [searcher](./share/searcher.ipynb), [reader](./share/reader.ipynb), and [writer](./share/writer.ipynb).

## Getting started

### Install

As simple as `pip install -U git+https://github.com/LLNL/AutoCog`.

But, you'll probably want to clone the repository to get the library of programs:
```
git clone https://github.com/LLNL/AutoCog
pip install -U ./AutoCog
```

### Inside a Notebook

Most of the development is done inside Python notebook (jupiterlab).
To get started take a look at the [Demo](./demo.ipynb).
Eventually, several notebooks demonstrating various part of AutoCog will be provided in the [share](./share) folder.

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
