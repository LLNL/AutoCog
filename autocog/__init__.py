
# TODO cleaner way to do that
from .architecture.orchestrator import Orchestrator
from .automatons.base import Automaton
Automaton.update_forward_refs(Orchestrator=Orchestrator)

from .architecture.base import CognitiveArchitecture as CogArch
