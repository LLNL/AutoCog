
from .architecture.orchestrator import Orchestrator
from .automatons.base import Automaton
Automaton.update_forward_refs(Orchestrator=Orchestrator)
#StructuredThoughtAutomaton.update_forward_refs()

from .architecture.base import CognitiveArchitecture as CogArch
