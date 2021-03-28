import shapely, shapely.geometry, shapely.ops, shapely.affinity
import cxf_font
import hpgl
import os.path
from shapely.affinity import rotate, scale, translate
from shapely.geometry import LineString, Point
from math import atan2
import glob
from typing import *

font_stash: Dict[str, Dict[str, Glyph]]
font_stash = {}

Coord = Tuple[float, float]

def map_glyph(f, strokes: List[LineString]):
    return [f(s) for s in strokes]

def map_glyph_vector(stroke_f, glyphs: List[List[LineString]]):
    return [map_glyph(stroke_f, g) for g in glyphs]

class Glyph:
    def __init__(self, strokes: List[LineString]):
        self.strokes = strokes
        glom = shapely.geometry.MultiLineString(self.strokes)
        bounds = glom.bounds
        bounds = [tuple(bounds[:2]), tuple(bounds[2:])]
        self.width = bounds[1][0] - bounds[0][0]
        self.height = bounds[1][1] - bounds[0][1]
        self.strokes = self.mapped(lambda s: translate(s, xoff=-bounds[0][0]))
        #self.strokes.append(LineString([Point(0, 0), Point(self.width, 0), Point(self.width, self.height), Point(0, self.height), Point(0, 0)]))
    
    def mapped(self, f: Callable) -> List[LineString]:
        return map_glyph(f, self.strokes)
    

def coords_list_to_points(coords: List[Coord]) -> List[Point]:
    return list(map(shapely.geometry.Point, coords))


def load_transformable_font(filename: str):
    raw_strokes = cxf_font.parse_cxf_font(filename)
    for k in raw_strokes.keys():
        conjoined = [raw_strokes[k][0]]
        for s in raw_strokes[k][1:]:
            extended = hpgl.extend_line(conjoined[-1], s, fuzzy=0.5)
            if extended:
                conjoined[-1] = extended
            else:
                conjoined.append(s)
        ls_strokes = [shapely.geometry.LineString(coords_list_to_points(stroke)) for stroke in conjoined]
        
        raw_strokes[k] = Glyph(ls_strokes)

    return raw_strokes


def calculate_font_scale(fontname: str, cm_size: Tuple[float, float]) -> Tuple[float, float]:
    glyph_size = font_stash[fontname]['X'].width, font_stash[fontname]['X'].height
    return (cm_size[0] * 400 / glyph_size[0], cm_size[1] * 400 / glyph_size[1])


def glyph_string(font, text, t=(0.0, 0.0), r=0.0, fontscale=(1.0, 25.0)):
    kernwidth = font['X'].width * 0.2
    retval = []
    x_accum = 0.0
    for c in text:
        if c not in font:
            c = 'X'
        glyph = font[c]
        retval.append(glyph.mapped(lambda line: translate(scale(line, xfact=fontscale[0], yfact=fontscale[1], origin=(0, 0)), xoff=x_accum)))
        x_accum += (glyph.width + kernwidth) * fontscale[0] # kerning like a champ lol
    
    retval = map_glyph_vector(lambda s: translate(rotate(s, r, origin=(0, 0), use_radians=True), xoff=t[0], yoff=t[1]), retval)
    return retval


def label_to_traces(text_params: dict, fontname='courier'):
    dx, dy = text_params['direction']
    angle = atan2(dy, dx)

    fontscale = calculate_font_scale(fontname, text_params['size'])

    glyphs = glyph_string(font_stash[fontname], text_params['text'], t=text_params['origin'], r=angle, fontscale=fontscale)
    retval = []
    for g in glyphs:
        retval.extend([hpgl.line_to_block(stroke, 4) for stroke in g])
    return retval


def rewrite_first_label(plot: hpgl.HPGLPlot, fontname='courier'):
    for idx, b in enumerate(plot.blocks[:]):
        if not b.is_text(): continue
        print(idx)
        plot.blocks = plot.blocks[:idx] + label_to_traces(b.get_text_properties(), fontname) + plot.blocks[idx + 1:]
        return True
    return False    

def rewrite_labels(plot: hpgl.HPGLPlot, fontname='courier'):
    while rewrite_first_label(plot, fontname): pass


#font_stash['courier'] = load_transformable_font(os.path.expanduser('~/cxf_fonts/courier.cxf'))

font_files = glob.glob(os.path.expanduser('~/cxf_fonts/*.cxf'))
for ff in font_files:
    try:
        fontname = os.path.basename(os.path.splitext(ff)[0])
        print("Loading font: " + fontname)
        font_stash[fontname] = load_transformable_font(ff)
    except Exception as ex:
        print("Cannot load: " + ff)
        print(ex)
        raise ex