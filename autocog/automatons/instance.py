
from typing import Any, Dict, List, Tuple, Optional, NamedTuple
from abc import abstractmethod
from pydantic import BaseModel

class Instance(BaseModel):
    header: str
    prompt: str = ''
    idx: int = 0

    next: Optional[str] = None

    started: bool = False

    @abstractmethod
    def vstate(self):
        """"""

    @abstractmethod
    def need_prompt(self):
        """"""

    @abstractmethod
    def need_content(self):
        """"""

    @abstractmethod
    def build_astate(self):
        """"""

    @abstractmethod
    def astate(self):
        """"""

    @abstractmethod
    def get_content(self):
        """"""

    @abstractmethod
    def set_content(self):
        """"""

    @abstractmethod
    def known_choice(self):
        """"""

    @abstractmethod
    def write_content(self):
        """"""

    @abstractmethod
    def fork(self):
        """"""
