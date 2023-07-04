MMLU Exams
==========

Multiple programs that let a LLM decide the best of 4 answers. Uses the MMLU dataset.

## Clone and install AutoCog

```
git clone https://github.com/LLNL/AutoCog $HOME/AutoCog
pip install -U ./AutoCog
export AUTOCOG_LIB=$HOME/AutoCog/library
```

## Download some models

```
sudo apt install git-lfs
export MODEL_PATH=$HOME/models
mkdir -p $MODEL_PATH/openalpaca $MODEL_PATH/openalpaca
git lfs clone https://huggingface.co/openlm-research/open_llama_3b $MODEL_PATH/openllama/3B
git lfs clone https://huggingface.co/openlm-research/open_llama_7b $MODEL_PATH/models/openllama/7B
git lfs clone https://huggingface.co/openllmplayground/openalpaca_3b_600bt_preview $MODEL_PATH/openalpaca/3B
```

### Convert for LLaMa.cpp

TODO

## Download Dataset

TODO

## Diagnostic

### Llama.cpp
```
python3 exam.py ./results \
    '{ "s_direct" : [ "direct", "select", {} ] }' \
    '[ { "model" : "llama", "size" : "7B", "quant" : "q4_0" } ]' \
    '{ "topic" : ["elementary_mathematics"], "mode" : null, "limit" : 10, "shuffle" : true }'
```

### Transformers

```
pip install -U transformers
pip install -U sentencepiece
pip install protobuf==3.20
```

```
python3 exam.py ./results \
    '{ "s_mapeval" : [ "mapeval", "select", {} ], "r_mapeval" : [ "mapeval", "repeat", {} ] }' \
    '[ { "model" : "llama", "size" : "7B" } ]' \
    '{ "topic" : null, "mode" : "dev", "limit" : 10, "shuffle" : true }'
```