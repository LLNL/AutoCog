from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from .cogs import Cog

import uuid

class AssociativeMemoryInterface(Cog):
    keys:       Dict[str,Tuple[Callable,Callable]]
    primary:    Optional[str]                      = None

    data:       Dict[str,Any]                      = {}
    idx:        Dict[str,Dict[str,int]]            = {}
    embeddings: Dict[str,List[Any]]                = {}

    last_read:  List[str]                          = []
    last_write: List[str]                          = []

    @abstractmethod
    def __store(self, **data):
        if self.primary is None:
            uid = str(uuid.uuid4())
        else:
            assert self.primary in data
            assert isinstance(data[self.primary], str)
            uid = data[self.primary]

        if uid in self.data:
            return f"Already exist: {uid}"

        self.data.update({ uid : data })
        self.idx.update({ uid : {} })
        for (key,(enc,dist)) in self.keys.items():
            if not key in data:
                raise Exception(f"Cannot store data without key={key}")
            if not key in self.embeddings:
                self.embeddings.update({ key : [] })
            self.idx[uid].update({ key : len(self.embeddings[key]) })
            self.embeddings[key].append(enc(data[key]))

        return f"Inserted as: {uid}"

    @abstractmethod
    def __search(self, num:int, cumul='harmonic', **keys):
        if len(keys) == 0:
            raise Exception("Cannot search without keys...")
        embs = { k : self.keys[k][0](d) for (k,d) in self.keys.items() }
        uids = []
        for uid in self.data:
            scores = {}
            for (key,(enc,dist)) in keys.items():
                idx = self.idx[uid][key]
                emb = self.embeddings[key][idx]
                scores.update({ key : dist(embs[key],emb) })

            if cumul == 'arithmetic':
                score = sum(scores.values())/len(scores)
                scores.update({ '*' : sum(scores.values())/len(scores) })
            elif cumul == 'harmonic':
                scores.update({ '*' : len(scores)/sum([1./s for s in scores.values()]) })
            else:
                raise Exception("Unknown cumul method: {cumul}")
            uids.append(( uid, scores ))
        uids = sorted(uids, key=lambda x: x[1]['*'])[:num]
        return [ { 'uid' : uid, 'item' : self.data[uid], 'scores': scores } for (uid, score, scores) in uids ]    

    @abstractmethod
    def __pull(self, num:int, clear:int, fog:int, cumul=None, **keys):
        pass

    @abstractmethod
    def __lookup(self, key:str):
        return self.data[key] 

    @abstractmethod
    def __call__(self, cogctx:Any=None, function: str, **data) -> Tuple[Any,Any]:
        if function == 'store':
            return ( self.__store(**data), None )
        elif function == 'search':
            return ( self.__search(**data), None )
        elif function == 'pull':
            return ( self.__pull(**data), None )
        else:
            raise Exception(f"Unrecognized function: {function}")
