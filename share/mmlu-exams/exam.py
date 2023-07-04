
import os, sys, json

autocog_home = os.getenv('AUTOCOG_HOME', '/workspace/projects/autocog')
try:
    import autocog
except:
    sys.path.append(autocog_home)

from autocog.architecture.utility import PromptTee
from autocog.utility.args2arch import parse_json

library_path = os.getenv('MMLU_LIB', './programs')
model_basedir = os.getenv('MODEL_PATH', '/workspace/models')

from utility import mmlu_create_arch, mmlu_register_local
from utility import mmlu_data, mmlu_list, mmlu_subset, mmlu_exec

resdir   = sys.argv[1]
patterns = parse_json(sys.argv[2])
models   = parse_json(sys.argv[3])
datacfg  = parse_json(sys.argv[4])

dataset = mmlu_subset(dataset=mmlu_data(), **datacfg)
# mmlu_list(dataset)

(arch, scorers) = mmlu_create_arch(library_path=library_path, patterns=patterns)
for model in models:
    label = mmlu_register_local(arch, model_basedir=model_basedir, **model)
    print(f"label: {label}")
    arch.orchestrator.pipe = PromptTee(prefix=label, fmt=resdir + '/{p}/{c}/{t}-{i}.txt')
    results = mmlu_exec(arch=arch, scorers=scorers, dataset=dataset)
    json.dump(results, open(f'{resdir}/{label}.json','w'), indent=4)
    for (version,result) in results.items():
        if len(result) > 0:
            num_total   = len(result)
            num_correct = len(list(filter(lambda x: x is not None and x[-1], result)))
            num_error   = len(list(filter(lambda x: x is not None and not x[-1], result)))
            num_failed  = len(list(filter(lambda x: x is None, result)))
            percentage  = int(num_correct * 10e4 / (num_correct+num_error))*10e-2
            print(f"  {version}: {percentage}% (total: {num_total}, correct: {num_correct}, error: {num_error}, failed: {num_failed})")
