Multiple Choices Question Library
=================================

A collection of "solvers" for Multiple Choices Questions.
It is meant to illustrate the utilization of various thought-patterns to solve the same problem.

Evenetually, it should provide a library of thought-patterns that can be compose into complex MCP solvers.
It will probably require to evolve the language a lot to arrive there...

There are two basic patterns `select` and `repeat` whether the LM is ask the pick the index of the correct answer or to repeat the correct answer verbatim.
We provide five versions of each basic case:
 - `base`: no extra step either select or repeat
 - `cot`: uses Chain-of-Thought before answering
 - `hyp`: uses two prompts, in the first one the choices are not provided instead the LM must make an hypothesis. In the second prompt it see the hypothesis alongside the choices
 - `annot`: the LM individually annotate the choices, it judge their correctness as yes, no, maybe. 
 - `iter`: the LM can iterate over its answer until it believe it to be correct

For `v0.5.4`, we will look at more complex composition of these patterns and any other patterns we can imagine at that time.