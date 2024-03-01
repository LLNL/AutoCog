
from ..sta.syntax import Syntax, syntax_kwargs as SyntaxKwargs
from ..lm import RLM
from ..lm import Llama

def loader(models_path=None, syntax=None, n_ctx=4096, **syntax_kwargs):
    if models_path is None:
        lm = RLM()
        syntax = Syntax(**syntax_kwargs)
    else:
        lm = Llama(model_path=models_path, n_ctx=n_ctx)

        if syntax is None:
            # TODO does llama.cpp (or GUFF) contains that info?
            model_name = models_path.split('/')[-1]
            if model_name.find('llama-2') >= 0 and model_name.find('chat') >= 0:
                syntax = 'Llama-2-Chat'
            elif model_name.find('capybarahermes') >= 0:
                syntax = 'ChatML'
            elif model_name.find('tinyllama') >= 0 and model_name.find('chat') >= 0:
                syntax = 'ChatML'
            elif model_name.find('tinyllama') >= 0 and model_name.find('miniguanaco') >= 0:
                syntax = 'Guanaco'
        else:
            assert syntax in SyntaxKwargs

        if syntax is None:
            syntax = syntax_kwargs
        else:
            syntax = SyntaxKwargs[syntax]
            syntax.update(syntax_kwargs)

        syntax = Syntax(**syntax)

    return (lm,syntax)