
import os, sys, json

autocog_home = os.getenv('AUTOCOG_HOME', '/workspace/projects/autocog')
sys.path.append(autocog_home)

from autocog.architecture.utility import PromptTee

library_path = os.getenv('AUTOCOG_LIB', f'{autocog_home}/library')

from utility import mmlu_create_arch
from utility import mmlu_register_openai, mmlu_register_tflm, mmlu_register_llama_cpp
from utility import mmlu_data, mmlu_list, mmlu_subset, mmlu_exec

dataset = mmlu_data()
dataset = mmlu_subset(dataset=dataset, topic='elementary_mathematics', mode=None, limit=100, shuffle=True)

(arch, scorers) = mmlu_create_arch(library_path=library_path, patterns=['direct','cot'])

# arch.orchestrator.pipe = PromptTee(prefix='mmlu-openai', fmt='{p}/{c}/{t}-{i}.txt')
# mmlu_register_openai(arch)
# results = mmlu_exec(arch=arch, scorers=scorers, dataset=dataset)
# for (version,result) in results.items():
#     if len(result) > 0:
#         print(f"{version}: {len(list(filter(lambda x: x, result)))*100./len(result)}%")

arch.orchestrator.pipe = PromptTee(prefix='mmlu-llama', fmt='{p}/{c}/{t}-{i}.txt')
mmlu_register_llama_cpp(arch)
results = mmlu_exec(arch=arch, scorers=scorers, dataset=dataset)
json.dump(results, open('results.json','w'), indent=4)
for (version,result) in results.items():
    if len(result) > 0:
        print(f"{version}: {len(list(filter(lambda x: x[-1], result)))*100./len(result)}%")
