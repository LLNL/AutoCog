import os, sys, json

# base_path='/home/ubuntu'
# repo_path=f'{base_path}/AutoCog'
# library_path=f'{repo_path}/library'

# os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
# os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512" # TODO does it actually reduce the chance of out of memory error...

from .ftt import Choice, Complete

from autocog.lm import TfLM, OpenAI, Llama

llama_path = lambda x: "/workspace/models/{}/ggml-model-{}.bin".format(*x)

def load_json(x):
    if x == '':
        return {}
    elif x.endswith('.json'):
        assert os.path.exists(x)
        return json.load(open(x))
    else:
        return json.loads(x)

if __name__ == '__main__':
    # model_path = lambda mtag: f"{base_path}/hf-{mtag}"
    # model_path = model_path('llama-7b')
    # model_path = 'gpt2-large'
    # llm = TfLM(
    #     completion_kwargs={ 'top_k' : 100, 'top_p' : 0.50, 'max_new_tokens' : 30 },
    #     **TfLM.create(model_path=model_path, device='cuda')
    # )

    # llm = OpenAI()

    llm = Llama(model_path=llama_path(('7B','q4_0')), n_ctx=2048, defaults={'max_tokens':20})

    tree = Choice.build(
        choices=['What purpose does'],
        successors=[ Complete.build(
            beams=4,
            length=5,
            successor=Choice.build(
                choices=['test','joke','error'],
                successors=[]
            ),
        ) ]
    )
    # print(json.dumps(tree.dict(), indent=4)
    results = tree.evaluate(llm=llm, prompt='', )
    print(json.dumps(tree.dict(), indent=4))
    for (text,proba,path) in sorted(results,key=lambda x: x[1]):
        print(f'> "{text}": {proba} ({path})')

[
f"""You are a helpful AI assistant. You are taking the MMLU exam. You are given one question and four choices for the answer. Only one of these choices is the correct answer.
You are using an interactive questionnaire. Follow this syntax after the start prompt:
```
> question(text): {states['question']}
> choices[4](text): {states['choices']}
> answer(choice): {states['answer']}
```
Each prompt expects one of the following formats:
- text: {formats['text']}
- choice: {formats['choice']}
Terminate each prompt with a newline.

start(record):
> question(text): {question}
> choices[1](text): {choice[0]}
> choices[2](text): {choice[1]}
> choices[3](text): {choice[2]}
> choices[4](text): {choice[3]}
> answer(choice): """, { 'choices' : ['1','2','3','4'] }
]

[
"""You are a helpful AI assistant. You are taking the MMLU exam. You are given one question and four choices for the answer. Only one of these choices is the correct answer.
You are using an interactive questionnaire. Follow this syntax after the start prompt:
```
> question(text): """, { 'beams' : 10, 'length' : 10 }, """
> choices[4](text): """, { 'beams' : 10, 'length' : 10 }, """
> answer(choice): """, { 'beams' : 10, 'length' : 10 }, """
```
Each prompt expects one of the following formats:
- text: """, { 'beams' : 10, 'length' : 10, }, """
- choice: """, { 'beams' : 10, 'length' : 10 }, f"""
Terminate each prompt with a newline.

start(record):
> question(text): {inputs['question']}
> choices[1](text): {inputs['choice'][0]}
> choices[2](text): {inputs['choice'][1]}
> choices[3](text): {inputs['choice'][2]}
> choices[4](text): {inputs['choice'][3]}
> answer(choice): {inputs['answer']}
"""
]
