MMLU Exams
==========

> DEPRECATED: the content of this folder is from v0.3 and code examples are not valid.
> The codes of the MMLU-Exams for AutoCog v0.4+ is located in `library/mmlu-exams`.

The Massive Multitask Language Understanding dataset is made of a large number of multiple choices questions on a variety of subjects.
The MMLU Exams form a collection of programs to guide language models in there search of the correct answer.

At this point, there are two main goals for this project:
 - demonstrate programmatic patterns for LM
 - figure out large jobs: capture, reliability and performance

## Design

We identified various patterns that can be used to implement a MCQ application.
We differentiate between patterns specific to the application and generic "cognitive patterns".

We are limiting these patterns to:
 - not call other program (no recursion and no parrallel CFG)
 - not use the `filter` clauses of channels
 - only produce native formats (`thought` or `bool`) in addition to `choice`

### MCQ Patterns

In the simplest case, a single prompt is used.
It receives the topic, question, and four choices.
The prompt makes the LM either repeat the correct choice or select the index of that choice.
This is the basic **prompt** of any MMLU Exams, either `repeat` or `select`.

The `hypothesis` and `annotate` **prompts** are optional.
Both permits the LM to produce intermediate thoughts from different point of view.

The former, `hypothesis`, let the LM emit an hypothesis given only the topic and question.
This hypothesis is then shown before the choices in next prompt.

The latter, `annotate`, considers each choice seperately and provide an annotation.
It receives the topic, question, one of the choices, and (if available) the hypothesis.
The next prompt is provided with the annotation for each choice.

Finally, a variation `annotate` first asks the LM if the result is correct, then it produces the annotation.
We use a boolean meaning that the model can only produce variations of yes/no and true/false.

Below is the skeleton for the application with all prompts:
```
formats:
- choice(repeat=.choices.candidate):

prompt(mmlu_hypothesis):
- target(topic)
- target(question)
> topic:
> question:
> hypothesis(thought):
__next(mmlu_annotate):

prompt(mmlu_annotate):
- target(topic)
- target(question)
- target(hypothesis) prompt(mmlu_hypothesis)
- target(candidate) source(choices) mapped
> topic:
> question:
> hypothesis(thought):
> candidate:
> correct(bool):
> annotation(thought):
__next(mmlu_choice):

prompt(mmlu_choice):
- target(topic)
- target(question)
- target(hypothesis) prompt(mmlu_hypothesis)
- target(choices) prompt(mmlu_annotate) source(candidate,annotation)
> topic:
> question:
> hypothesis(thought):
> choices[4]:
> > candidate:
> > annotation(thought):
> answer(choice):
__exit(answer):
```

### Cognitive Patterns

We define a set of composable cognitive patterns meant to give the LM "space to think".
These are used to introduce some form of "temporary variables" or "intermediate computations".
We included chain-of-thoughts, accumulation-of-thoughts, selection/repetition-of-thoughts (aka self-consistency), and reflexion.
We also propose an equivalent to tree-of-thoughts, implemented by composing the other patterns.

#### Chain-of-Thoughts

Chain-of-Thoughts let the LM enumerate thoughts within a prompt.
It is already a classic pattern for LLM prompting **cite**.

```
> work[5](thought): 
```

#### Accumulation-of-Thoughts

Accumulation-of-Thoughts is similar to `CoT`.
Thoughts are produced by iterating over the same prompts.
The next prompt can access the last thought and/or all the intermediate thoughts.

AoT is inherently more expensive than CoT as it iterates over the prompt.
However, composed with CoT for example, it permits to implement sequence of thought where intermediate results are discarded.

```
prompt(aot):
- target(intermediate) source(work) append prompt(aot)
> intermediate[20](thought):
> work(thought):
__next(aot,next):
```

#### Selection/Repetition-of-Thoughts

Pick one-or-more out of a list of thoughts (same pattern as first application pattern). List needs to be know when prompt is instantiated (could relax to list size for `SoT`).

Selection/Repetition-of-Thoughts permits us to reduce the information generated by `CoT` or `AoT`. It is similar to self-consistency **cite**.

```
formats:
- choice(select=.work):

prompt(sot):
- target(work) prompt(previous)
> work[20](thought):
> selection[3](choice):
__next(next):
```

#### Reflexion

Reflexion is an advanced version of AoT were the LM accumulates hints until it believe that the answer is correct.
The `valid` field is optional and it does not control the branch.
Boolean fields like `valid` enforce a finite choice for the completion and seem to help (experiments needed).

```
prompt(reflexion):
- target(question)
- target(hints) source(hint) prompt(reflexion)
> question:
> hints(thought):
> answer(thought):
> valid(bool): 
> hint(thought): 
__next(reflexion,next):
```

#### Tree-of-Thought

We propose a pattern that is similar to the Tree-of-Thoughts.

**TODO** need to figure out an implementation (will need changes to `mapped` and `append` clauses). Code below is not correct.

```
prompt(tot_1):
- target(steps) source(step) prompt(tot_2) mapped
> stack:
> > steps[100]:
> step[3](thought):
__next(tot_2):

prompt(tot_2):
- target(stacks) source(stack) prompt(tot_1)
- target(steps) source(step) prompt(tot_1) append
> stacks[20]:
> > steps[100]: 
__next(tot_1,next):
```

### Implementations

The application patterns yield 8 possible cases: `[hypo-][anno-](repeat|select)`.
By default, each **prompt** is `inout` (ToT paper terminology), meaning that the LM provide the answer directly without any intermediate work.
Four combinations can be aranged using the MCQ application patterns: [choice](programs/choice.sta), [hyp-choice](programs/hyp-choice.sta), [anno-choice](programs/anno-choice.sta), and [hyp-anno-choice](programs/hyp-anno-choice.sta).
In these files, we overuse the "macro" system to facilitate future tuning of the natural language parts of the program.
It has the added advantage to centralize all NL piece in [one JSON file](programs/descriptions.json).

We use cognitive patterns to introduce intermediate thoughts.
We have implemented:
 - [hyp-cot-anno-cot-choice-cot](programs/hyp-cot-anno-cot-choice-cot.sta) adding a simple Chain-of-Thoughts to each of the three prompts
 - [anno-cot2-rot-choice-reflex](programs/hyp-cot2-rot-anno-cot-choice-reflex.sta) adding a simple Chain-of-Thoughts to each of the three prompts

## Instructions

### Clone and install AutoCog

```
git clone https://github.com/LLNL/AutoCog $HOME/AutoCog
pip install -U ./AutoCog
export AUTOCOG_LIB=$HOME/AutoCog/library
```

### Download some models

```
sudo apt install git-lfs
export MODEL_PATH=$HOME/models
mkdir -p $MODEL_PATH/openalpaca $MODEL_PATH/openalpaca
git lfs clone https://huggingface.co/openlm-research/open_llama_3b $MODEL_PATH/openllama/3B
git lfs clone https://huggingface.co/openlm-research/open_llama_7b $MODEL_PATH/models/openllama/7B
git lfs clone https://huggingface.co/openllmplayground/openalpaca_3b_600bt_preview $MODEL_PATH/openalpaca/3B
```

#### Convert for LLaMa.cpp

TODO

### Download Dataset

TODO

## Tests

Llama 7B with 4 bits quantization running 18 versions on 10 elementary maths/scieance questions:
```
python3 exam.py ./results versions.json llama-7B-q4.json elementary.json
```
It tooks 15h on an Xeon E5-2670:
```
  s_direct: 30.0% (total: 10, correct: 3, error: 7, failed: 0)
  r_direct: 20.0% (total: 10, correct: 2, error: 8, failed: 0)
  s_cot_3: 20.0% (total: 10, correct: 2, error: 8, failed: 0)
  r_cot_3: 30.0% (total: 10, correct: 3, error: 7, failed: 0)
  s_cot_5: 20.0% (total: 10, correct: 2, error: 8, failed: 0)
  r_cot_5: 20.0% (total: 10, correct: 2, error: 8, failed: 0)
  s_cot_10: 30.0% (total: 10, correct: 3, error: 7, failed: 0)
  r_cot_10: 20.0% (total: 10, correct: 2, error: 8, failed: 0)
  s_mapeval: 50.0% (total: 10, correct: 5, error: 5, failed: 0)
  r_mapeval: 20.0% (total: 10, correct: 2, error: 8, failed: 0)
  s_mapcot_3_3: 40.0% (total: 10, correct: 4, error: 6, failed: 0)
  r_mapcot_3_3: 10.0% (total: 10, correct: 1, error: 9, failed: 0)
  s_mapcot_3_5: 40.0% (total: 10, correct: 4, error: 6, failed: 0)
  r_mapcot_3_5: 30.0% (total: 10, correct: 3, error: 7, failed: 0)
  s_mapcot_5_3: 30.0% (total: 10, correct: 3, error: 7, failed: 0)
  r_mapcot_5_3: 30.0% (total: 10, correct: 3, error: 7, failed: 0)
  s_mapcot_5_5: 40.0% (total: 10, correct: 4, error: 6, failed: 0)
  r_mapcot_5_5: 20.0% (total: 10, correct: 2, error: 8, failed: 0)
```



## Notes

### Llama.cpp

```
python3 exam.py ./results \
    '{ "s_direct" : [ "direct", "select", {} ] }' \
    '[ { "model" : "llama", "size" : "7B", "quant" : "q4_0" } ]' \
    '{ "topic" : ["elementary_mathematics"], "mode" : null, "limit" : 10, "shuffle" : true }'
```

### Transformers (pytorch)

```
pip install -U transformers
pip install -U sentencepiece
pip install protobuf==3.20
```

```
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

```
python3 exam.py ./results \
    '{ "s_mapeval" : [ "mapeval", "select", {} ], "r_mapeval" : [ "mapeval", "repeat", {} ] }' \
    '[ { "model" : "llama", "size" : "7B" } ]' \
    '{ "topic" : null, "mode" : "dev", "limit" : 10, "shuffle" : true }'
```

## Versions

```
{
  "s_direct"     : [ "direct",  "select", {} ],
  "r_direct"     : [ "direct",  "repeat", {} ],
  "s_cot_3"      : [ "cot",     "select", { "N" : 3  } ],
  "r_cot_3"      : [ "cot",     "repeat", { "N" : 3  } ],
  "s_cot_5"      : [ "cot",     "select", { "N" : 5  } ],
  "r_cot_5"      : [ "cot",     "repeat", { "N" : 5  } ],
  "s_cot_10"     : [ "cot",     "select", { "N" : 10 } ],
  "r_cot_10"     : [ "cot",     "repeat", { "N" : 10 } ],
  "s_mapeval"    : [ "mapeval", "select", {} ],
  "r_mapeval"    : [ "mapeval", "repeat", {} ],
  "s_mapcot_3_3" : [ "mapcot",  "select", { "N" : 3, "M" : 3 } ],
  "r_mapcot_3_3" : [ "mapcot",  "repeat", { "N" : 3, "M" : 3 } ],
  "s_mapcot_3_5" : [ "mapcot",  "select", { "N" : 3, "M" : 5 } ],
  "r_mapcot_3_5" : [ "mapcot",  "repeat", { "N" : 3, "M" : 5 } ],
  "s_mapcot_5_3" : [ "mapcot",  "select", { "N" : 5, "M" : 3 } ],
  "r_mapcot_5_3" : [ "mapcot",  "repeat", { "N" : 5, "M" : 3 } ],
  "s_mapcot_5_5" : [ "mapcot",  "select", { "N" : 5, "M" : 5 } ],
  "r_mapcot_5_5" : [ "mapcot",  "repeat", { "N" : 5, "M" : 5 } ]
}
```
