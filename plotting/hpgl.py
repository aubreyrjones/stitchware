"""
Designed to handle CLO3D-specific HPGL outputs.
"""

from itertools import chain
from functools import reduce
import subprocess, io

from PIL import Image, ImagePalette
import shapely, shapely.geometry

def iterate_as_type(strings, t):
    return map(t, strings)

def parse_list_as_type(strings, t):
    return list(iterate_as_type(strings, t))

def iterate_as_coords(coords):
    return zip(iterate_as_type(coords[::2], int), iterate_as_type(coords[1::2], int))

def parse_list_as_coords(strings):
    return list(iterate_as_coords(strings))

def reduce_coord(f, coords, start, index):
    return reduce(f, map(lambda c : c[index], coords), start[index])

def reduce_coords(f, coords, start):
    return (reduce_coord(f, coords, start, 0), reduce_coord(f, coords, start, 1))

def flatten_coords(coords):
    retval = []
    for x, y in coords:
        retval.append(x)
        retval.append(y)
    return retval

def coord_extents(coords):
    maxes = reduce_coords(max, coords, (-2**32, -2**32))
    mins = reduce_coords(min, coords, (2**32, 2**32))
    return (mins, maxes)

def strip_endline(l):
    return l[:-2] if l.endswith(';\n') else l

def flatten_blocks_to_text(blocks: list):
    return "".join(map(str, blocks))


class Statement:
    def __init__(self, line: str):
        self.command = line[:2]
        self.tail = strip_endline(line[2:])
        self.split_tail = self.tail.split(',') if self.tail else []
        self.parsed_args = []
        self._parse_args()
    
    def _parse_args(self):
        if not self.split_tail: return
        if self.needs_coordinates():
            self.parsed_args = parse_list_as_coords(self.split_tail)
        elif self.command in ('SP'):
            self.parsed_args = parse_list_as_type(self.split_tail, int)

    def __str__(self):
        return f"{self.command}{self.tail};\n"

    def __repr__(self):
        which_args = self.parsed_args if self.parsed_args else self.split_tail
        return f"{self.command} {repr(which_args)}"
    
    def uncuttable(self):
        return self.command in ('LB', 'DT', 'DI')

    def needs_coordinates(self):
        return self.command in ('PU', 'PD', 'PA')

    def is_trace(self):
        return self.command in ('PD')

    def set_args(self, *args):
        self.parsed_args = list(args)
        self.rewrite()

    def rewrite(self):
        if not self.parsed_args: return
        self.split_tail = [str(a) for a in self.parsed_args]
        self.tail = ','.join(self.split_tail)


class Block:
    def __init__(self):
        self.commands = []
    
    def push_back(self, statement):
        self.commands.append(statement)
    
    def __repr__(self):
        return '***\n' + "\n".join(map(lambda s: "\t" + repr(s), self.commands))
    
    def __str__(self):
        return "".join(map(str, self.commands))

    def __iter__(self):
        return iter(self.commands)
    
    def uncuttable(self):
        return any(map(Statement.uncuttable, self.commands))
    
    def cuttable(self):
        return not self.uncuttable()
    
    def has_trace(self):
        return any(map(Statement.is_trace, self.commands))

    def has_coordinates(self):
        return any(map(Statement.needs_coordinates, self.commands))
    
    def extents(self):
        return coord_extents(list(chain(*map(lambda s: s.parsed_args, filter(Statement.needs_coordinates, self.commands)))))

    def get_pen(self):
        for s in self:
            if s.command == 'SP':
                return s.parsed_args[0]
        return None
    
    def set_pen(self, pen_number):
        for s in self:
            if s.command == 'SP':
                s.set_args(pen_number)
                break

    def trace(self):
        if not self.has_trace(): return None
        block_trace = []
        for cmd in self:
            if cmd.command == 'PU' and cmd.parsed_args:
                block_trace.append(cmd.parsed_args[0])
            if cmd.command == 'PD':
                block_trace.extend(cmd.parsed_args)
        return block_trace

    def distance_to_trace(self, point: tuple):
        if not self.has_trace(): return 2**31
        query_point = shapely.geometry.Point(*point)
        trace_string = shapely.geometry.LineString(self.trace())
        distance = trace_string.distance(query_point)
        return distance

class HPGLPlot:
    def __init__(self):
        self.blocks = []
        self.init_statements = {}
    
    def push_block(self):
        self.blocks.append(Block())
    
    def push_statement(self, statement: Statement):
        if statement.command in ('IP', 'SC'):
            self.init_statements[statement.command] = statement
        self.last_block().push_back(statement)

    def last_block(self):
        return self.blocks[-1]

    def __iter__(self):
        return iter(self.blocks)

    def linear(self):
        return chain(*self.blocks)

    def __repr__(self):
        return "\n".join(map(repr, iter(self)))
    
    def __str__(self):
        return "".join(map(str, iter(self)))
    
    def cuttable(self):
        return filter(Block.cuttable, self)

    def cuttable_repr(self):
        return "\n".join(map(lambda s: repr(s), self.cuttable()))
    
    def extents(self):
        return coord_extents(list(chain(*map(Block.extents, filter(Block.has_coordinates, self.blocks)))))

    def mirror(self):
        bounds = self.extents()
        self.init_statements['IP'].set_args(0, bounds[1][1], bounds[1][0], 0)
        self.init_statements['SC'].set_args(0, 1, 0, -1, 2)

    def find_passes(self):
        passes = {'init': self.blocks[0], 'coda': self.blocks[-1]}
        
        found_uncuttable = False
        work_passes = [[]]
        for b in self.blocks[1:-1]:
            if not b.cuttable(): 
                found_uncuttable = True
                continue
            if found_uncuttable and work_passes[-1]:
                work_passes.append([])
                found_uncuttable = False
            work_passes[-1].append(b)
        
        if len(work_passes) == 1:
            passes['work'] = {'knife': work_passes[0]}
        else:
            passes['work'] = {'pen': work_passes[0], 'knife': work_passes[1]}
        
        return passes



def parse_lines(lines):
    plot = HPGLPlot()
    plot.push_block()

    for l in lines:
        statement = Statement(l)
        if statement.command == 'PU' and not statement.tail:
            plot.push_block()
        plot.push_statement(statement)
    
    return plot

def parse_file(filename):
    with open(filename) as f:
        return parse_lines(f.readlines())

def render_preview(commands, outfile):
    subprocess.run(['hp2xx', '-q', '-t', '-x', '0', '-y', '0', '-m', 'png', '-f', outfile], input="".join(map(str, commands)).encode('ASCII'))

def image_preview(commands, rewrite_color=(0, 0, 0)):
    completed = subprocess.run(['hp2xx', '-q', '-t', '-x', '0', '-y', '0', '-m', 'png', '-f', '-'], input="".join(map(str, commands)).encode('ASCII'), stdout=subprocess.PIPE)
    img = Image.open(io.BytesIO(completed.stdout))
    img.palette.palette = b'\xff\xff\xff' + bytes(rewrite_color) + (b'\x00\x00\x00' * 254)
    img = img.convert('RGBA')
    newImage = []
    for px in img.getdata():
        if px[:3] == (255, 255, 255):
            newImage.append((255, 255, 255, 0))
        else:
            newImage.append(px)
    img.putdata(newImage)
    return img


def show_preview(commands, rewrite_color=(0, 0, 0)):
    image_preview(commands, rewrite_color).show()