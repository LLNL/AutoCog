#!/bin/bash -e

[ -z $AUTOCOG_HOME ] && echo "\$AUTOCOG_HOME must be set!" && exit 1

[ -z $LLAMA_CPP_MODEL_PATH ] && echo "\$LLAMA_CPP_MODEL_PATH must be set!" && exit 1

python3 -m autocog "test-openai-0" \
                   '{ "text" : { "cls" : "Llama", "model_path" : "'$LLAMA_CPP_MODEL_PATH'", "n_ctx" : 2048, "defaults" : { "max_tokens" : 20 } } }' \
                   '{ "fortune" : [ "'$AUTOCOG_HOME'/library/fortune.sta", {} ] }' \
                   '{}' \
                   '[ [ "fortune", { "question" : "Is Eureka, CA a good place for a computer scientist who love nature?" } ] ]'
