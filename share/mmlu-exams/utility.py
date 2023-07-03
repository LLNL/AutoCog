
import os
import sys
import json
import tqdm
import random
import asyncio
import itertools

from autocog import CogArch
from autocog.lm import OpenAI, TfLM, Llama

def mmlu_create_arch(library_path, patterns=['direct','cot']):
    arch = CogArch()
    scorers = {}
    check_select = lambda r,d,i: int(r["answer"]) == i+1
    check_repeat = lambda r,d,i: r["answer"] == d['choices'][i]
    for pattern in patterns:
        arch.load(tag=f'{pattern}-select', filepath=f'{library_path}/mmlu/{pattern}-select.sta')
        arch.load(tag=f'{pattern}-repeat', filepath=f'{library_path}/mmlu/{pattern}-repeat.sta')
        scorers.update({ f'{pattern}-select' : check_select, f'{pattern}-repeat' : check_repeat })
    return (arch, scorers)

def mmlu_register_openai(arch, model='text-davinci-003'):
    arch.orchestrator.LMs.update({
      'text' : OpenAI(completion_kwargs={ 'max_tokens' : 30 }, model=model)
    })

def mmlu_register_tflm(arch, model_path='gpt2-medium', device='cuda'):
    model_kwargs = TfLM.create(model_path=model_path, device=device)
    arch.orchestrator.LMs.update({
      'text' : TfLM(completion_kwargs={ 'max_new_tokens' : 30 }, **model_kwargs)
    })

def mmlu_register_llama_cpp(arch, model_path='/workspace/models/7B/ggml-model-q4_0.bin', n_ctx=2048):
    model_kwargs = Llama.create(model_path=model_path, n_ctx=n_ctx)
    arch.orchestrator.LMs.update({
      'text' : Llama(completion_kwargs={ 'max_tokens' : 30 }, **model_kwargs)
    })

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
        if (topic is None or d['topic'] == topic) and (mode is None or d['mode'] == mode):
            data.append(d)
    if shuffle:
        random.shuffle(data)
    if limit is not None:
        data = data[:limit]
    return data

def mmlu_exec(arch, scorers, dataset, versions=None):
    if versions is None:
        versions = scorers.keys()
    results = { v : [] for v in versions }
    workload = list(itertools.product(versions,dataset))
    random.shuffle(workload)
    for (version,data) in tqdm.tqdm(workload):
        idx = ord(data["answer"])-ord('A')
        res = asyncio.run(arch(version, question=data['question'], choices=data['choices']))
        results[version].append( (data, res, scorers[version](res,data,idx)) )
    return results