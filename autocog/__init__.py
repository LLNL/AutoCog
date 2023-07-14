
# TODO cleaner way to do that
from .architecture.orchestrator import Orchestrator
from .automatons.automaton import Automaton
Automaton.model_rebuild(force=True)

from .architecture.base import CognitiveArchitecture as CogArch
