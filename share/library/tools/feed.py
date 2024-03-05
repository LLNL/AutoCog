from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from .tool import Tool

try:
    import feedparser
except:
    print("Warning: Package `feedparser` needed for (RSS) feeds reader (pip install feedparser)")
    feedparser = None

# TODO https://www.tutorialspoint.com/python_text_processing/python_reading_rss_feed.htm

class RssFeed(Tool):
    async def __call__(self, feedurl:str):
        if feedparser is None:
            raise Exception("Fatal: Package `feedparser` needed for PDF mining (pip install feedparser)")
        raise NotImplementedError()