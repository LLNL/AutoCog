
import os
import sys
import json
import tqdm
import random
import asyncio
import itertools

from autocog import CogArch
from autocog.lm import OpenAI, TfLM, Llama

mcq_checkers = {
  'select' : lambda r,d,i: int(r["answer"]) == i+1,
  'repeat' : lambda r,d,i: r["answer"] == d['choices'][i]
}

def mmlu_create_arch(library_path, patterns):
    arch = CogArch()
    scorers = {}
    for (tag,(pattern,mode,kwargs)) in patterns.items():
        arch.load(tag=tag, filepath=f'{library_path}/mmlu/{pattern}-{mode}.sta', **kwargs)
        scorers.update({ tag : mcq_checkers[mode] })
    return (arch, scorers)

def mmlu_register_openai(arch, text_length=30, **kwargs):
    arch.orchestrator.LMs.update({
      'text' : OpenAI(completion_kwargs={ 'max_tokens' : text_length }, **kwargs)
    })

def mmlu_register_tflm(arch, text_length=30, model_path='gpt2-medium', device='auto', **kwargs):
    model_kwargs = TfLM.create(model_path=model_path, device=device)
    arch.orchestrator.LMs.update({
      'text' : TfLM(completion_kwargs={ 'max_new_tokens' : text_length }, **model_kwargs, **kwargs)
    })

def mmlu_register_llama_cpp(arch, text_length=30, model_path='/workspace/models/llama/7B/ggml-model-q4_0.bin', n_ctx=2048, **kwargs):
    model_kwargs = Llama.create(model_path=model_path, n_ctx=n_ctx)
    arch.orchestrator.LMs.update({
      'text' : Llama(completion_kwargs={ 'max_tokens' : text_length }, **model_kwargs, **kwargs)
    })

def mmlu_register_local(arch, model, size=None, quant=None, use_path_length_normalization=False, text_length=30, model_basedir='/workspace/models', **kwargs):
    if quant is None:
        mmlu_register = mmlu_register_tflm
        if size is None:
            label = f'{model}-{text_length}'
            model_path = model
        else:
            label = f'{model}-{size}-{text_length}'
            model_path = f'{model_basedir}/{model}/{size}'
            assert os.path.exists(model_path)
    else:
        mmlu_register = mmlu_register_llama_cpp
        if size is None:
            label = f'{model}-{size}-{quant}-{text_length}'
            model_path = f'{model_basedir}/{model}/{size}/ggml-model-{quant}.bin'
        else:
            label = f'{model}-{quant}-{text_length}'
            model_path = f'{model_basedir}/{model}/ggml-model-{quant}.bin'
        assert os.path.exists(model_path)
    label = label.replace('/','_')
    if use_path_length_normalization:
        label += '-norm'
    mmlu_register(arch, model_path=model_path, use_path_length_normalization=use_path_length_normalization, text_length=text_length, **kwargs)
    return label

def mmlu_data(dataset_path=None):
    if os.path.exists('mmlu-data.json'):
        return json.load(open('mmlu-data.json'))
    if dataset_path is None:
        dataset_path = './mmlu-data'
    if not os.path.exists(dataset_path):
        raise NotImplementedError("Download MMLU dataset")
    raise NotImplementedError("Extract MMLU dataset to single JSON")

def mmlu_list(data):
    modes = list(set([ d['mode'] for d in data ]))
    print(f"By modes: ({len(modes)})")
    for mode in modes:
        mmlu_subset = [ d for d in data if d['mode'] == mode ]
        print(f" - {mode}: {len(mmlu_subset)}")

    topics = list(set([ d['topic'] for d in data ]))
    print(f"By topics: ({len(topics)})")
    for topic in topics:
        mmlu_subset = [ d for d in data if d['topic'] == topic ]
        print(f" - {topic}: {len(mmlu_subset)}")
        for mode in modes:
            mmlu_subsubset = [ d for d in mmlu_subset if d['mode'] == mode ]
            if len(mmlu_subsubset) > 0:
                print(f"   - {mode}: {len(mmlu_subsubset)}")

def mmlu_subset(dataset, topic=None, mode=None, limit=None, shuffle=True):
    data = []
    for d in dataset:
        on_topic = topic is None or ( isinstance(topic,str) and d['topic'] == topic ) or ( isinstance(topic,list) and d['topic'] in topic )
        on_mode  = mode  is None or ( isinstance(mode, str) and d['mode' ] == mode  ) or ( isinstance(mode, list) and d['mode' ] in mode )
        if on_topic and on_mode:
            data.append(d)
    if shuffle:
        random.shuffle(data)
    if limit is not None:
        data = data[:limit]
    return data

def mmlu_exec(arch, scorers, dataset):
    versions = scorers.keys()
    results = { v : [] for v in versions }
    workload = list(itertools.product(versions,dataset))
    random.shuffle(workload)
    for (version,data) in tqdm.tqdm(workload):
        idx = ord(data["answer"])-ord('A')
        res = asyncio.run(arch(version, question=data['question'], choices=data['choices']))
        results[version].append( (data, res, scorers[version](res,data,idx)) )
    return results