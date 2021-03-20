"""
Designed to handle CLO3D-specific HPGL outputs.
"""

from itertools import chain
from functools import reduce
import subprocess, io

from PIL import Image, ImagePalette
import shapely, shapely.geometry, shapely.ops
import random

def extend_line(a, b):
    if a[-1] == b[0]:
        return a + b[1:]
    if b[-1] == a[0]:
        return b + a[1:]
    if a[0] == b[0]:
        return list(reversed(a)) + b[1:]
    if a[-1] == b[-1]:
        return a[:-1] + list(reversed(b))
    return None

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
    def __init__(self, line: str, *args):
        self.command = line[:2]
        self.tail = ''
        self.split_tail = []
        self.parsed_args = []
        if args:
            if type(args[0]) is list:
                self.set_args(*args[0])
            else:
                self.set_args(*args)
        else:
            self.tail = strip_endline(line[2:])
            self.split_tail = self.tail.split(',') if self.tail else []
            self.parsed_args = []
            self._parse_args()
    
    def clone(self):
        return Statement(str(self))
    
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
        if self.needs_coordinates():
            self.split_tail = [str(a) for a in flatten_coords(self.parsed_args)]
        else:
            self.split_tail = [str(a) for a in self.parsed_args]
        self.tail = ','.join(self.split_tail)

class Block:
    def __init__(self):
        self.commands = []
        self.jitter = (random.randrange(200), random.randrange(200))
    
    def clone(self):
        o = Block()
        o.commands = [c.clone() for c in self.commands]
        o.jitter = self.jitter
        return o
    
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

    def trace(self, do_jitter=False):
        if not self.has_trace(): return None
        block_trace = []
        for cmd in self:
            if cmd.command == 'PU' and cmd.parsed_args:
                block_trace.append(cmd.parsed_args[0])
            if cmd.command == 'PD':
                block_trace.extend(cmd.parsed_args)
        if do_jitter:
            block_trace = [(x + self.jitter[0], y + self.jitter[1]) for x, y in block_trace]
        return block_trace

    def linestring(self, do_jitter=False):
        if not self.has_trace(): return None
        return shapely.geometry.LineString([shapely.geometry.Point(p) for p in self.trace(do_jitter)])

    def distance_to_trace(self, point: tuple, do_jitter=False):
        if not self.has_trace(): return 2**31
        query_point = shapely.geometry.Point(*point)
        trace_string = self.linestring(do_jitter)
        distance = trace_string.distance(query_point)
        return distance
    
    def connects_to(self, other_trace: list, retval=[]):
        if not self.has_trace(): return False
        if extend_line(self.trace(), other_trace):
            return True
        return False

class HPGLPlot:
    def __init__(self):
        self.blocks = []
        self.init_statements = {}
    
    def clone(self):
        o = HPGLPlot()
        o.blocks = [b.clone() for b in self.blocks]
        o.find_inits()
        return o
    
    def find_inits(self):
        for statement in self.linear():
            if statement.command in ('IP', 'SC'):
                self.init_statements[statement.command] = statement        

    def push_block(self):
        self.blocks.append(Block())
    
    def push_statement(self, statement: Statement):
        if statement.command in ('IP', 'SC'):
            self.init_statements[statement.command] = statement
        self.last_block().push_back(statement)

    def last_block(self):
        return self.blocks[-1]

    def connectivity(self, block, retval=None):
        if not retval:
            retval = []
        retval.append(block)
        for b in self:
            if b in retval: continue
            if b.connects_to(block.trace(), retval):
                self.connectivity(b, retval)
        return retval

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
        return coord_extents(list(chain(*map(Block.extents, filter(Block.has_coordinates, self.blocks[1:]))))) # this is just a bandaid, skipping the init

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
        plot.push_statement(statement)
        if statement.command == 'PU' and not statement.tail:
            plot.push_block()
    
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

class CutSorter:
    def __init__(self):
        self.ends = {}
        self.rings = []
    
    def add_unconnected(self, line: shapely.geometry.LineString):
        if not line: 
            print("Ummm, that's not a line.")
            return

        if line.is_ring:# and line.is_closed:
            print("Inserted ring.")
            self.rings.append(line)
            return
        
        for c in (line.coords[0], line.coords[-1]):
            if c in self.ends:
                o = self.ends[c]
                if c is o:
                    print("Self intersection")
                    continue
                extended = extend_line(list(line.coords), list(o.coords))
                merged_line = shapely.geometry.LineString(coordinates=extended)
                start, end = o.coords[0], o.coords[-1]
                if start in self.ends: del self.ends[start]
                if end in self.ends: del self.ends[end]
                self.add_unconnected(merged_line)
                return
        
        for c in (line.coords[0], line.coords[-1]):
            print("end")
            self.ends[c] = line
    
    def get_cuts(self):
        return chain(self.rings, set(self.ends.values()))

def line_to_block(line: shapely.geometry.LineString):
    b = Block()
    b.push_back(Statement('SP', [3 if line.is_ring else 2]))
    b.push_back(Statement('PU', [line.coords[0]]))
    b.push_back(Statement('PD', [c for c in line.coords[1:]]))
    b.push_back(Statement('PU', []))
    return b


def organize_cuts(plot):
    sorter = CutSorter()
    intake_count = 0
    for b in plot.blocks[:]:
        trace = b.linestring()
        if trace and b.get_pen() == 2:
            plot.blocks.remove(b)
            sorter.add_unconnected(trace)
            intake_count += 1
    print(f"Optimizing {intake_count} cut blocks.")

    for r in sorter.rings:
        print(list(r.coords))
        plot.blocks.append(line_to_block(r))
    print(f"Added {len(sorter.rings)} rings.")
    
    seen = []
    for l in sorter.ends.values():
        if l in seen: continue
        seen.append(l)
        plot.blocks.append(line_to_block(l))
    print(f"Added {len(seen)} non-rings.")
    return plot
        

