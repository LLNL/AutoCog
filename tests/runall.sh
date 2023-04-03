#!/bin/bash -e
#!/bin/bash -e

export AUTOCOG_HOME=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )

tmpdir=$(mktemp -d -t autocog-tests-XXX)
cd $tmpdir

git clone $AUTOCOG_HOME autocog
pip install -r autocog/requirements.txt
pip install autocog

[ ! -z $OPENAI_API_KEY ] && pip install openai tiktoken
[ ! -z $LLAMA_CPP_MODEL_PATH ] && pip install git+https://github.com/tristanvdb/llama-cpp-python@choice-dev

if [ -z $SKIP_AUTOCOG_UNITTESTS ]; then
  pushd autocog/tests/unittests
    python3 dataflow.py
  popd
fi

if [ ! -z $OPENAI_API_KEY ]; then
  autocog/tests/test-openai-0.sh
fi

if [ ! -z $LLAMA_CPP_MODEL_PATH ]; then
  autocog/tests/test-llama-0.sh 
fi

# TODO transformers