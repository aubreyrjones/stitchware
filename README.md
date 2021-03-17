stitchware
----------

These are tools I use to manage a digital design workflow for garment
and bag making. These tools may be useful if you are trying to deal
with any *modern* HPGL-compatible plotter/cutter. At the time of
writing, this project does not plan to offer general HPGL parsing,
comprehension, or emulation. I use the excellent `hp2xx` software
during development and testing to transform HPGL to something
viewable. If you want rasterization or format transforms, I recommend
that.

The majority of my tools are designed to work with the `.plt` plotter
output from the CLO3D softgoods CAD program, and are not tested with
any other inputs. This means that I rely inherently on the
indiosyncrasies of that output, especially for effects such as
transformations, repetitions, and rewriting. While the `.plt` files
certainly appear to contain standard HPGL, these tools are _not_
written as general HPGL processors, and may require adaptation to
function with your input files.

Finally, the tools that interact directly with the cutter/plotter are
*not* appropriate for use with vintage plotters. They assume modern
machines with relatively large buffer memories compared to both
vintage machines and the actual HPGL input files processed.


Tech Requirements
-----------------

These tools are written mostly in python3, and exclusively for
Linux. Some of them are OS-agnostic and will probably work anywhere,
but many have dependencies you may find annoying to fulfill on a
Windows machine. Tools interacting with plotter hardware are most
assuredly not cross-platform, as they work with serial ports in a
naively unix-centric way.

If a script errors out trying to find a package, use `pip3` to satisfy
the dependency.

If you have no idea what I'm talking about and can't find out with
google, I'm afraid these tools are probably not friendly enough for
you to use without assistance. I would recommend finding a tech to
help you.


My Process
----------

[Note: This process is under development, and some aspects of this
description are... uh... aspirational.]

So that the context of these tools is clear, I will describe my
process for working with fabric.

I first design the item in pattern-making software. In particular, I
use CLO3D; but in principle there's nothing prohibiting another CAD
program, or even image capture with a vectorization pass run on
it. The key point is that the design software will output a text file
containing HPGL plotter commands describing the pattern pieces to be
cut from fabric.

I then use a wide-format "vinyl cutter" for the rest of the
process. Typically used in signmaking shops, this is effectively a
very large, roll-fed plotter designed to drag a blade like an X-Acto
knife across a thin sheet material with a very controllable pressure
to cut the film but leave the carrier paper. These cutters are
incredibly precise and repeatable, and can exactly retrace their path
over and over again without perceptible error. This can allow tougher
materials to be cut with several light passes, reducing the chance of
the material wrinkling or dragging with the knife.

Instead of dragging the knife, the machine can be easily refit to
carry an inkpen insert, making a mark instead of a cut. In general,
the pen carriers are designed to fit ballpoint style refills. But they
can often be modified to accomodate popular fabric pens of different
designs.

Given a sufficiently wide vinyl cutter, fabric can be marked for
cutting on the whole cloth, unrolled directly from the bolt. This makes
it quite convenient to cut the pattern just by following the lines
with shears. When working with CLO3D outputs, I use `mirror_plot` to
flip the pattern and plot it on the wrong side of the fabric so that I
can leave guidelines and panel outlines inside of the seam allowance
cutlines.

Fabric can also be cut with the machine, although this requires
substantially more prep work. A length of fabric long enough to
contain the entire pattern must be cut, then glued to a backing
material with a temporary adhesive. At present, I'm experimenting with
embroidery stabilizer and kraft paper as potential backings and
basting spray as the adhesive. The entire laminate stack is then fed
into the machine, with the blade pressure tuned so that the fabric is
cut but the backing is only lightly scored. Some fabrics may work
better than others, and some fabrics may work better with multiple
light cutting passes. Pattern pieces are then peeled off the backing
for assembly.

