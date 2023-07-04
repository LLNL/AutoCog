MMLU Exams
==========

Multiple programs that let a LLM decide the best of 4 answers.

Uses the MMLU dataset.

```
 python3 exam.py ./results \
    '{ "s_direct" : [ "direct", "select", {} ] }' \
    '[ { "model" : "llama", "size" : "7B", "quant" : "q4_0" } ]' \
    '{ "topic" : ["elementary_mathematics"], "mode" : null, "limit" : 10, "shuffle" : true }'
```

```
python3 exam.py ./results \
    '{ "s_mapeval" : [ "mapeval", "select", {} ], "r_mapeval" : [ "mapeval", "repeat", {} ] }' \
    '[ { "model" : "llama", "size" : "7B" } ]' \
    '{ "topic" : null, "mode" : "dev", "limit" : 10, "shuffle" : true }'
```