#!/bin/bash -e

[ -z $AUTOCOG_HOME ] && echo "\$AUTOCOG_HOME must be set!" && exit 1

python3 -m autocog --prefix "test-openai-0" --tee stdout \
                   --lm '{ "text"     : { "cls" : "OpenAI", "config" : { "max_tokens" : 20, "temperature" : 0.4 } } }' \
                   --lm '{ "thought"  : { "cls" : "OpenAI", "config" : { "max_tokens" : 15, "temperature" : 1.0 } } }' \
                   --lm '{ "sentence" : { "cls" : "OpenAI", "config" : { "max_tokens" : 30, "temperature" : 0.7 } } }' \
                   --program '{ "fortune" : { "filepath" : "'$AUTOCOG_HOME'/library/fortune.sta" } }' \
                   --command '{ "tag" : "fortune", "question" : "Is Eureka, CA a good place for a computer scientist who love nature?" }'