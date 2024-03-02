
from autocog.sta.frontend import frontend

programs = ["""
""","""
define N=10;
argument M=$N;
argument P;
""","""
prompt main {
    is {
        question is text;
        answer is text<$N,K="test",f"another:{P}">;
    }
    channel {
        to .question from ?question;
    }
}
""","""
prompt main {
    is {
        question is text;
        choices[4] is {
            value is text;
            correct is enum("yes","no","maybe");
        }
        answer is repeat(.choices.value);
    }
}
""","""
prompt main {
    is {
        question is text;
    }
    channel {
        to .question.bar from another.question[3].foo[4:7];
    }
}
""","""
prompt main {
    is {
        question is text;
    }
    return .question;
}
""","""
prompt main {
    is {
        question is text;
    }
    return {
        as "ready";
        from .question;
        from .question as "another";
    }
}
""","""
prompt main {
    is {
        question is text;
    }
    flow {
        to main as "loop";
        to exit[3];
    }
}
""","""
prompt main {
    define annotation="some text";
    is {
        question is text;
    }
    annotate {
        .question as $annotation;
    }
}
""","""
struct a_choice {
    is {
        value   is text;
    }
}
""","""
format sentence {
    argument N=30;
    is text<$N>;
    annotate f"A grammatically correct sentence made of at most {N} tokens.";
}
""","""
flow {
    to mmlu_main as "main";
}
""","""
prompt main {
    is {
        topic is text;
    }
    channel {
        to .choices call {
            extern another_cog;
            entry mmlu_annot;
            kwarg question from ?question;
            kwarg choice   map  ?choices;
            bind choice.test as value;
        }
    }
}
"""
]

for program in programs:
    ast = frontend(program)
