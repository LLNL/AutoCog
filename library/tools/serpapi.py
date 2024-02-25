from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from .tool import SearchEngine

try:
    import serpapi
except:
    print("Warning: Package `serpapi` needed for Google Search (pip install google-search-results)")
    serpapi = None

class SerpAPI(SearchEngine):
    apikey:str
    numres:int = 10
    engine:str = "google" # "google_scholar"
    hl:str     = 'en'
    gl:str     = 'us'
    domain:str = 'google.com'

    async def __call__(self,
                 query:str,
                 start:int=0,
                 num:Optional[int]=None,
                 engine:Optional[str]=None,
                 hl:Optional[str]=None,
                 gl:Optional[str]=None,
                 domain:Optional[str]=None,
                 return_request:bool=False
                ):
        request = {
            "api_key":       self.apikey,
            "q":             query,
            "start":         str(start),
            "num":           str(self.numres if num    is None else num),
            "engine":        self.engine     if engine is None else engine,
            "hl":            self.hl         if hl     is None else hl,
            "gl":            self.gl         if gl     is None else gl,
            "google_domain": self.domain     if domain is None else domain
        }

        results = serpapi.GoogleSearch(request).get_dict()
        items = []
        if "organic_results" in results:
            items = [ { 'title' : r['title'], 'uid' : r['link'], 'content' : [ r['snippet'] if 'snippet' in r else '' ] } for r in results["organic_results"] if 'link' in r ]

        if return_request:
            request.update({ 'domain' : request['google_domain'] })
            request.update({ 'query' : query })
            del request['google_domain']
            del request["api_key"]
            del request["q"]
            request.update({ 'items' : items })
            return request
        elif len(items) == 0:
            return [ { 'title' : "No results", 'uid' : 'N/A', 'content' : [ "This search query did not return any results." ] } ]
        else:
            return items
