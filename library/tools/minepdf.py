from typing import Any, Dict, List, Tuple, Union, Optional, Callable, NamedTuple
from .tool import Tool

try:
    import pdfminer.layout
    import pdfminer.high_level
except:
    print("Warning: Package `pdfminer` needed for PDF mining (pip install pdfminer.six)")
    pdfminer = None

def pdf_to_dict_rec(element):
    content = list(element.__dict__.keys())
    if isinstance(element, pdfminer.layout.LTTextLine):
        content = element.get_text()
    elif isinstance(element, pdfminer.layout.LTTextContainer):
        content = [ pdf_to_dict_rec(e) for e in element ]

    return {
        'class' : element.__class__.__name__,
        'bbox'  : element.bbox if 'bbox' in element.__dict__ else None,
        'content' : content
    }
    
def pdf_to_dict(filepath):
    return [ {
        'class'    : page.__class__.__name__,
        'id'       : page.pageid,
        'bbox'     : page.bbox,
        'elements' : [ pdf_to_dict_rec(element) for element in page ]
    } for page in pdfminer.high_level.extract_pages(filepath) ]

class PdfMiner(Tool):
    async def __call__(self, filepath:str):
        if pdfminer is None:
            raise Exception("Fatal: Package `pdfminer` needed for PDF mining (pip install pdfminer.six)")
        return pdf_to_dict(filepath)
