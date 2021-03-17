"""
Designed to handle CLO3D-specific HPGL outputs.
"""

from itertools import chain
from functools import reduce

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


class Statement:
    def __init__(self, line):
        self.command = line[:2]
        self.tail = line[2:-2] # drop the ';\n'
        self.split_tail = self.tail.split(',') if self.tail else []
        self.parsed_args = []
        self._parse_args()
    
    def _parse_args(self):
        if not self.split_tail: return
        if self.command in ('PU', 'PD', 'PA'):
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

    def __iter__(self):
        return iter(self.commands)
    
    def uncuttable(self):
        return any(map(Statement.uncuttable, self.commands))
    
    def cuttable(self):
        return not self.uncuttable()


class HPGLPlot:
    def __init__(self):
        self.blocks = []
        self.init_statements = {}
    
    def push_block(self):
        self.blocks.append(Block())
    
    def push_statement(self, statement):
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
        return "\n".join(map(lambda s: repr(s), iter(self)))
    
    def no_cuttable(self):
        return filter(Block.cuttable, self)

    def cuttable_repr(self):
        return "\n".join(map(lambda s: repr(s), self.no_cuttable()))


def parse_lines(lines):
    plot = HPGLPlot()
    plot.push_block()

    for l in lines:
        statement = Statement(l)
        if statement.command == 'PU' and not statement.tail:
            plot.push_block()
        plot.push_statement(statement)
    
    return plot
