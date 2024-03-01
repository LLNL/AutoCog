#!/bin/bash -ex

# First argument should be a model path if missing and default is not found,
# testing will use the Random Language Model (generate random probablility 
# distribution over tokens). RLM is useful to test control and data flow as,
# by design, whatever the model says the system should never crash.
# One limitation of RLM testing is that it use printable ASCII tokens.
# Tokenizer for real models are much more annoying, especially as they
# have different (de)tokenization behavior (adding start/end token or 
# adding/deleting leading spaces or adding special marker to the string).
#
# While I write this, I am watching Andrej Karpathy video on Tokenization:
#          https://www.youtube.com/watch?v=zduSFxRajkE

model_path=$1
[ -z $model_path ] && model_path=/data/models/llama-2-7b-chat.Q4_K_M.gguf
if [ -e $model_path ]; then
  gguf_param="--gguf $model_path"
else
  gguf_param=''
fi

python3 -m autocog $gguf_param \
                   --syntax Llama-2-Chat \
                   --syntax '{ "prompt_with_format" : false, "prompt_with_index" : false, "prompt_indent" : "" }' \
                   --cogs mmlu.repeat.base:library/mmlu-exams/repeat.sta \
                   --cogs mmlu.repeat.cot:library/mmlu-exams/repeat-cot.sta \
                   --cogs mmlu.repeat.hyp:library/mmlu-exams/repeat-hyp.sta \
                   --cogs mmlu.repeat.iter:library/mmlu-exams/repeat-iter.sta \
                   --cogs mmlu.repeat.annot:library/mmlu-exams/repeat-annot.sta \
                   --cogs mmlu.select.base:library/mmlu-exams/select.sta \
                   --cogs mmlu.select.cot:library/mmlu-exams/select-cot.sta \
                   --cogs mmlu.select.hyp:library/mmlu-exams/select-hyp.sta \
                   --cogs mmlu.select.iter:library/mmlu-exams/select-iter.sta \
                   --cogs mmlu.select.annot:library/mmlu-exams/select-annot.sta \
                   --command '{ "__tag" : "mmlu.repeat.base",  "topic" : "arithmetic", "question" : "What is 3*4+9?", "choices" : [ "16", "21", "39", "42" ] }' \
                   --command '{ "__tag" : "mmlu.repeat.cot",   "topic" : "arithmetic", "question" : "What is 3*4+9?", "choices" : [ "16", "21", "39", "42" ] }' \
                   --command '{ "__tag" : "mmlu.repeat.hyp",   "topic" : "arithmetic", "question" : "What is 3*4+9?", "choices" : [ "16", "21", "39", "42" ] }' \
                   --command '{ "__tag" : "mmlu.repeat.iter",  "topic" : "arithmetic", "question" : "What is 3*4+9?", "choices" : [ "16", "21", "39", "42" ] }' \
                   --command '{ "__tag" : "mmlu.repeat.annot", "topic" : "arithmetic", "question" : "What is 3*4+9?", "choices" : [ "16", "21", "39", "42" ] }' \
                   --command '{ "__tag" : "mmlu.select.base",  "topic" : "arithmetic", "question" : "What is 3*4+9?", "choices" : [ "16", "21", "39", "42" ] }' \
                   --command '{ "__tag" : "mmlu.select.cot",   "topic" : "arithmetic", "question" : "What is 3*4+9?", "choices" : [ "16", "21", "39", "42" ] }' \
                   --command '{ "__tag" : "mmlu.select.hyp",   "topic" : "arithmetic", "question" : "What is 3*4+9?", "choices" : [ "16", "21", "39", "42" ] }' \
                   --command '{ "__tag" : "mmlu.select.iter",  "topic" : "arithmetic", "question" : "What is 3*4+9?", "choices" : [ "16", "21", "39", "42" ] }' \
                   --command '{ "__tag" : "mmlu.select.annot", "topic" : "arithmetic", "question" : "What is 3*4+9?", "choices" : [ "16", "21", "39", "42" ] }'
