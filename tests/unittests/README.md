Unit-tests
==========

Each group of unit-tests has one directory and one python file with the same name.
The python file implements specific testing logic while the directory contains the test-cases.

## STA's Dataflow

[![STA Dataflow](https://github.com/LLNL/AutoCog/workflows/dataflow/badge.svg)](https://github.com/LLNL/AutoCog/actions)

This tests the dataflow within STA's language and execution.
These tests do not require to instantiate any Language Model at the moment.
When a LM become required, we will use a `FakeLM` to permit testing without dependency on a real LLM.

The test are run by [dataflow.py](./dataflow.py) and the test programs are in [dataflow/](./dataflow/).

### Identity

Loading, displaying, and extracting the same data.

Currently, we only test a single correct use case for each test-case.
We need more valid data samples. Especially:
 - lists with:
   - single element
   - more elements than the limit in the program (currently undefined behavior)
 - dictionnary with:
   - additional fields
   - missing fields (would need FakeLM to provide completion)

The base cases correspond to different data:
- `text`: a simple string
- `list`: a list of string
- `item`: a dictionary with two text fields
- `item-list`: list of dictionary with text fields
- `nested`: list of dictionary with one text and one list of text fields
- `double-nested`: list of dictionary with one text and one list of dictionary of list of text fields

For each base case, there are variations:
 - `input`: single prompt, `data` from `inputs`, written as-is to output
 - `call`: single prompt, `data` from a call to a `DataSource` tool, written as-is to output
 - `flow`: **TODO** two prompts, `data` from `inputs`, read from first prompt into second prompt, written as-is to output

### Parallel flow

- identity-texts-mapped-input
- identity-double-mapped-flow
- filter-aggregate-list-text-bool

### Iteration

- iteration-text-call
- iteration-text-flow
