
import io, os, uuid, json, pathlib

import graphviz

from IPython.display import display, HTML, IFrame

from typing import List

def wrap_svg(
    svg_txt,
    element_styles="height:800px",
    container_styles="overflow:hidden",
    pan_zoom_json = "{controlIconsEnabled: true, zoomScaleSensitivity: 0.4, minZoom: 0.01, maxZoom: 1000.}"):
    """
    Embeds SVG object into Jupyter cell with ability to pan and zoom.
    @param  g: digraph object
    @param  element_styles: CSS styles for embedded SVG element.
    @param  container_styles: CSS styles for container div element.
    @param  pan_zoom_json: pan and zoom settings, see https://github.com/bumbu/svg-pan-zoom
    """
    html_container_class_name = F"svg_container_{str(uuid.uuid4()).replace('-','_')}"
    html = F'''
        <div class="{html_container_class_name}">
            <style>
                .{html_container_class_name} {{
                    {container_styles}
                }}
                .{html_container_class_name} SVG {{
                    {element_styles}
                }}
            </style>
            <script src="https://bumbu.me/svg-pan-zoom/dist/svg-pan-zoom.min.js"></script>
            <script type="text/javascript">
                attempts = 5;
                var existCondition = setInterval(function() {{
                  console.log(attempts);
                  svg_el = document.querySelector(".{html_container_class_name} svg");
                  if (svg_el != null) {{
                      console.log("Exists!");
                      clearInterval(existCondition);
                      svgPanZoom(svg_el, {pan_zoom_json});
                  }}
                  if (--attempts == 0) {{
                      console.warn("SVG element not found, zoom wont work");
                      clearInterval(existCondition);
                  }}
                }}, 100); // check every 100ms
            </script>
            {svg_txt}
        </div>
    '''
    return HTML(html)

def wrap_graphviz(dot, **kwargs):
    svg = graphviz.Digraph(body=dot).pipe(format='svg').decode("utf-8")
    return wrap_svg(svg, **kwargs)
 
def wrap_frame(
    body:str,
    scripts:List[str]=[],
    path:str='frame-wraps',
    width:str="100%",
    height:str="500px",
    **kwargs
):
    # Import provided body inside the template
    open_if_file = lambda s: open(s).read() if os.path.exists(s) else s
    template = "<!DOCTYPE html><html lang=\"en\"><body>\n{scripts}\n{body}\n</body></html>".format(
        scripts='{scripts}', body=open_if_file(body)
    )

    # Format the scripts and kwargs (include height and width of the iframe)
    stringify = lambda v: v if isinstance(v,str) else json.dumps(v)
    kwargs = { k : stringify(v) for (k,v) in kwargs.items() }
    template = template.format(
        scripts='\n'.join([f"<script>{open_if_file(s)}</script>" for s in scripts ]),
        iframe_width=width, iframe_height=height, **kwargs
    )

    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    filepath=f"{path}/{uuid.uuid4()}.html"
    with io.open(filepath, 'wt', encoding='utf8') as F:
        F.write(template)

    return IFrame(src=filepath, width=width, height=height)