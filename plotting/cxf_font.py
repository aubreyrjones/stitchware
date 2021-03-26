from math import *
import os
import re
import glob

#=======================================================================
# This routine parses the .cxf font file and builds a font dictionary of
# line segment strokes required to cut each character.
# Arcs (only used in some fonts) are converted to a number of line
# segemnts based on the angular length of the arc. Since the idea of
# this font description is to make it support independant x and y scaling,
# we can not use native arcs in the gcode.
#
# Copied from: https://github.com/LinuxCNC/simple-gcode-generators/, used under GPL.
#=======================================================================
def parse_cxf_font(filename):
    font = {}
    key = None
    num_cmds = 0
    line_num = 0
    with open(filename, 'r') as file:
        for text in file:
            #format for a typical letter (lowercase r):
            ##comment, with a blank line after it
            #
            #[r] 3
            #L 0,0,0,6
            #L 0,6,2,6
            #A 2,5,1,0,90
            #
            line_num += 1
            end_char = re.match('^$', text) #blank line
            if end_char and key: #save the character to our dictionary
                font[key] = stroke_list
                if (num_cmds != cmds_read):
                    print("(warning: discrepancy in number of commands %s, line %s, %s != %s )" % (fontfile, line_num, num_cmds, cmds_read))

            new_cmd = re.match('^\[(.*)\]\s(\d+)', text)
            if new_cmd: #new character
                key = new_cmd.group(1)
                num_cmds = int(new_cmd.group(2)) #for debug
                cmds_read = 0
                stroke_list = []

            line_cmd = re.match('^L (.*)', text)
            if line_cmd:
                cmds_read += 1
                coords = line_cmd.group(1)
                coords = [float(n) for n in coords.split(',')]
                stroke_list.append([tuple(coords[:2]), tuple(coords[2:])])

            arc_cmd = re.match('^A (.*)', text)
            if arc_cmd:
                segment_list = []
                cmds_read += 1
                coords = arc_cmd.group(1)
                coords = [float(n) for n in coords.split(',')]
                xcenter, ycenter, radius, start_angle, end_angle = coords
                # since font defn has arcs as ccw, we need some font foo
                if ( end_angle < start_angle ):
                    start_angle -= 360.0
                # approximate arc with line seg every 5 degrees
                segs = int((end_angle - start_angle) / 5) + 1
                angleincr = (end_angle - start_angle)/segs
                xstart = cos(start_angle * pi/180) * radius + xcenter
                ystart = sin(start_angle * pi/180) * radius + ycenter
                segment_list.append((xstart, ystart))
                angle = start_angle
                for i in range(segs):
                    angle += angleincr
                    xend = cos(angle * pi/180) * radius + xcenter
                    yend = sin(angle * pi/180) * radius + ycenter
                    #coords = [xstart,ystart,xend,yend]
                    segment_list.append((xend, yend))
                    xstart = xend
                    ystart = yend
                stroke_list.append(segment_list)
    return font

f = None

if __name__ == '__main__':
    f = parse_cxf_font("/home/netzapper/cxf_fonts/courier.cxf")
    print(f['a'])