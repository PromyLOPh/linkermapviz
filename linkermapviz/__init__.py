# vim: set fileencoding=utf8 :

import sys, re, os
from itertools import chain, groupby
import squarify

from bokeh.plotting import figure, show, output_file, ColumnDataSource
from bokeh.models import HoverTool, LabelSet
from bokeh.models.mappers import CategoricalColorMapper
from bokeh.palettes import Category10
from bokeh.layouts import column

class Objectfile:
    def __init__ (self, section, offset, size, comment):
        self.section = section.strip ()
        self.offset = offset
        self.size = size
        self.path = (None, None)
        self.basepath = None
        if comment:
            self.path = re.match (r'^(.+?)(?:\(([^\)]+)\))?$', comment).groups ()
            self.basepath = os.path.basename (self.path[0])
        self.children = []

    def __repr__ (self):
        return '<Objectfile {} {:x} {:x} {} {}>'.format (self.section, self.offset, self.size, self.path, repr (self.children))

def parseSections (fd):
    """
    Quick&Dirty parsing for GNU ld’s linker map output, needs LANG=C, because
    some messages are localized.
    """

    sections = []

    # skip until memory map is found
    found = False
    while True:
        l = sys.stdin.readline ()
        if not l:
            break
        if l.strip () == 'Memory Configuration':
            found = True
            break
    if not found:
        return None

    # long section names result in a linebreak afterwards
    sectionre = re.compile ('(?P<section>.+?|.{14,}\n)[ ]+0x(?P<offset>[0-9a-f]+)[ ]+0x(?P<size>[0-9a-f]+)(?:[ ]+(?P<comment>.+))?\n+', re.I)
    subsectionre = re.compile ('[ ]{16}0x(?P<offset>[0-9a-f]+)[ ]+(?P<function>.+)\n+', re.I)
    s = sys.stdin.read ()
    pos = 0
    while True:
        m = sectionre.match (s, pos)
        if not m:
            # skip that line
            try:
                nextpos = s.index ('\n', pos)+1
                pos = nextpos
                continue
            except ValueError:
                break
        pos = m.end ()
        section = m.group ('section')
        v = m.group ('offset')
        offset = int (v, 16) if v is not None else None
        v = m.group ('size')
        size = int (v, 16) if v is not None else None
        comment = m.group ('comment')
        if section != '*default*' and size > 0:
            of = Objectfile (section, offset, size, comment)
            if section.startswith (' '):
                sections[-1].children.append (of)
                while True:
                    m = subsectionre.match (s, pos)
                    if not m:
                        break
                    pos = m.end ()
                    offset, function = m.groups ()
                    offset = int (offset, 16)
                    if sections and sections[-1].children:
                        sections[-1].children[-1].children.append ((offset, function))
            else:
                sections.append (of)

    return sections

def main ():
    sections = parseSections (sys.stdin)
    if sections is None:
        print ('start of memory config not found, did you invoke the compiler/linker with LANG=C?')
        return

    sectionWhitelist = {'.text', '.data', '.bss', '.rodata'}
    plots = []
    whitelistedSections = list (filter (lambda x: x.section in sectionWhitelist, sections))
    allObjects = list (chain (*map (lambda x: x.children, whitelistedSections)))
    allFiles = list (set (map (lambda x: x.basepath, allObjects)))
    for s in whitelistedSections:
        objects = s.children
        groupsize = {}
        for k, g in groupby (sorted (objects, key=lambda x: x.basepath), lambda x: x.basepath):
            groupsize[k] = sum (map (lambda x: x.size, g))
        objects.sort (reverse=True, key=lambda x: x.size)
        values = list (map (lambda x: x.size, objects))
        totalsize = sum (values)

        x = 0
        y = 0
        width = 1000 
        height = 1000
        values = squarify.normalize_sizes (values, width, height)
        rects = squarify.squarify(values, x, y, width, height)
        padded_rects = squarify.padded_squarify(values, x, y, width, height)

        # plot with bokeh
        output_file('linkermap.html', title='Linker map')

        left = list (map (lambda x: x['x'], padded_rects))
        top = list (map (lambda x: x['y'], padded_rects))
        rectx = list (map (lambda x: x['x']+x['dx']/2, padded_rects))
        recty = list (map (lambda x: x['y']+x['dy']/2, padded_rects))
        rectw = list (map (lambda x: x['dx'], padded_rects))
        recth = list (map (lambda x: x['dy'], padded_rects))
        files = list (map (lambda x: x.basepath, objects))
        size = list (map (lambda x: x.size, objects))
        children = list (map (lambda x: ','.join (map (lambda x: x[1], x.children)) if x.children else x.section, objects))
        legend = list (map (lambda x: '{} ({})'.format (x.basepath, groupsize[x.basepath]), objects))
        source = ColumnDataSource(data=dict(
            left=left,
            top=top,
            x=rectx,
            y=recty,
            width=rectw,
            height=recth,
            file=files,
            size=size,
            children=children,
            legend=legend,
        ))

        hover = HoverTool(tooltips=[
            ("size", "@size"),
            ("file", "@file"),
            ("symbol", "@children"),
        ])


        p = figure(title='Linker map for section {} ({} bytes)'.format (s.section, totalsize),
                plot_width=width, plot_height=height,
                tools=[hover,'pan','wheel_zoom','box_zoom','reset'],
                x_range=(0, width), y_range=(0, height))

        p.xaxis.visible = False
        p.xgrid.visible = False
        p.yaxis.visible = False
        p.ygrid.visible = False

        palette = Category10[10]
        mapper = CategoricalColorMapper (palette=palette, factors=allFiles)
        p.rect (x='x', y='y', width='width', height='height', source=source, color={'field': 'file', 'transform': mapper}, legend='legend')

        # set up legend, must be done after plotting
        p.legend.location = "top_left"
        p.legend.orientation = "horizontal"

        plots.append (p)
    show (column (*plots, sizing_mode="scale_width"))

if __name__ == '__main__':
    main ()

