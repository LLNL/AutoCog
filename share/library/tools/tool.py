
from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from abc import abstractmethod

from ..cogs import Cog

class Tool(Cog):
    """Base class for a Tool. No specialization yet..."""

class SearchEngine(Tool):
    """Base interface for a search engine"""
    @abstractmethod
    async def __call__(self, query:str, start:int=0, num:Optional[int]=None) -> Tuple[Dict[str,Any],None]:
        return ( [ # None stands in for strings
                   { 'title' : None, 'uid' : None, 'content' : [ None, None ] },
                   { 'title' : None, 'uid' : None, 'content' : [ None, None, None ] }
                 ], None )

class Command(Tool):
    """Command line: takes `argv` returns (stdout, stderr, returncode)"""

    def __init__(self, command):
        self.command = command

    async def __call__(self, argv):
        # TODO exec [ self.command ] + argv
        return None # TODO return (out,err,rc)

class Endpoint(Tool):
    """Tool that communicate with HTTP ressources"""

    def __init__(self, url):
        self.url = url

    def __get(self, **kwargs):
        return None # TODO

    def __put(self, **kwargs):
        return None # TODO

    def __post(self, **kwargs):
        return None # TODO
    
    async def __call__(self, method, **kwargs):
        if method.lower() == 'get':
            return self.__get(**kwargs)
        elif method.lower() == 'put':
            return self.__put(**kwargs)
        elif method.lower() == 'post':
            return self.__post(**kwargs)
        else:
            raise Exception("Method not supported!")

class Stream(Cog):
    """Cog that implements open, close, read, and write (abstract)"""

    def __init__(self):
        pass # TODO

    def __open(self, **kwargs):
        return None # TODO

    def __close(self, **kwargs):
        return None # TODO

    def __read(self, **kwargs):
        return None # TODO

    def __write(self, **kwargs):
        return None # TODO

    async def __call__(self, operation):
        if operation.lower() == 'open':
            return self.__open(**kwargs)
        elif operation.lower() == 'close':
            return self.__close(**kwargs)
        elif operation.lower() == 'read':
            return self.__read(**kwargs)
        elif operation.lower() == 'write':
            return self.__write(**kwargs)
        else:
            raise Exception("Operation not supported!")
