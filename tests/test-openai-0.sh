#!/bin/bash -e

[ -z $AUTOCOG_HOME ] && echo "\$AUTOCOG_HOME must be set!" && exit 1

python3 -m autocog "test-openai-0" \
                   '{ "text" : { "cls" : "OpenAI", "max_tokens" : 20, "temperature" : 0.4 } }' \
                   '{ "fortune" : [ "'$AUTOCOG_HOME'/library/fortune.sta", {} ] }' \
                   '{}' \
                   '[ [ "fortune", { "question" : "Is Eureka, CA a good place for a computer scientist who love nature?" } ] ]'
