import shapely, shapely.geometry, shapely.ops
import cxf_font

def coords_list_to_points(coords):
    return list(map(shapely.geometry.Point, coords))


def load_transformable_font(filename):
    raw_strokes = cxf_font.parse_cxf_font(filename)
    for k in raw_strokes.keys():
        raw_strokes[k] = [shapely.geometry.LineString(coords_list_to_points(stroke)) for stroke in raw_strokes[k]]

    return raw_strokes
