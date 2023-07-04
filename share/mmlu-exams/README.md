MMLU Exams
==========

Multiple programs that let a LLM decide the best of 4 answers. Uses the MMLU dataset.

At this time, the immediate goal is to figure out how to get **reliable** massive job with AutoCog.
Specifically: figuring out SLURM configs to run on HPC clusters.

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
