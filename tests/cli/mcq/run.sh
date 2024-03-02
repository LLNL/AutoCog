#!/bin/bash -e

model=$1
[ -z $model ] && model=none

COGS="repeat.base:@mcq/repeat.sta \
repeat.cot:@mcq/repeat-cot.sta \
repeat.hyp:@mcq/repeat-hyp.sta \
repeat.iter:@mcq/repeat-iter.sta \
repeat.annot:@mcq/repeat-annot.sta \
select.base:@mcq/select.sta \
select.cot:@mcq/select-cot.sta \
select.hyp:@mcq/select-hyp.sta \
select.iter:@mcq/select-iter.sta \
select.annot:@mcq/select-annot.sta"

for cog in $COGS; do
    tag=$(echo $cog | cut -d: -f1 | tr '.' '-')
    if [ $model == 'none' ]; then
        model_path=
        kind=random
        quant=none
    else
        model_path=$model
        kind=$(basename $model | cut -d. -f1)
        quant=$(basename $model | cut -d. -f2)
    fi
    python3 -m autocog --model "$model_path" --prefix $tag-$kind-$quant --cog $cog --command data.json \
                       --syntax '{ "prompt_with_format" : false, "prompt_with_index" : false, "prompt_indent" : "  " }'
done
