Structured Thoughts
===================

In the Structured Thoughts programming model, prompts are akin to the building blocks of traditional computer programs.
Prompts are compiled to automaton that ensure that the resulting completion can be parsed to extract structured data.
Branching between prompts is controlled by the language model.
The dataflow is statically defined and executed when instantiating the automaton of each prompt.
Calls (to other prompts or python tools) are executed during the dataflow phase.

Below, we show a single prompt program which implement Chain-of-Thoughts (CoT) to answer a multiple choice question.
In this examples, the language model is presented with the `topic`, the `question`, and four `choices`.
It can then think using one to ten `thought` (up 20 tokens for each).
Eventually, the model must indicate the index of the correct choice.

```
format thought {
    is text<20>;
    annotate f"a short text representing a single thought, it does not have to be a proper sentence.";
}

prompt main {
    is {
        topic is text<20>;
        question is text<50>;
        choices[4] is text<40>;
        work[1:10] is thought;
        answer is select(.choices);
    }
    channel {
        to .topic    from ?topic;
        to .question from ?question;
        to .choices  from ?choices;
    }
    return {
        from .answer;
    }
    annotate {
        _ as "You are answering a multiple choice questionnaire.";
        .topic           as "the general category from which the question was taken";
        .question        as "the question that you have to answer";
        .choices         as "the four possible choices to answer the question, only one is correct";
        .work            as "show your work step-by-step";
        .answer          as "you pick the index of the choice that best answer the question";
    }
}
```

We are developing the [MCQ](./library/mcq) library of program to illustrate thought patterns that are achievable using Structured Thoughts.