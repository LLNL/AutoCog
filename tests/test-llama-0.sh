#!/bin/bash -e

[ -z $AUTOCOG_HOME ] && echo "\$AUTOCOG_HOME must be set!" && exit 1

[ -z $LLAMA_CPP_MODEL_PATH ] && echo "\$LLAMA_CPP_MODEL_PATH must be set!" && exit 1

python3 -m autocog --prefix "test-llama-0" --tee stdout \
                   --lm '{ "text" : { "cls" : "LLaMa", "model" : { "model_path" : "'$LLAMA_CPP_MODEL_PATH'", "n_ctx" : 2048 }, "config" : { "max_tokens" : 20, "temperature" : 0.4 } } }' \
                   --program '{ "fortune" : { "filepath" : "'$AUTOCOG_HOME'/library/fortune.sta" } }' \
                   --command '{ "tag" : "fortune", "question" : "Is Eureka, CA a good place for a computer scientist who love nature?" }'
