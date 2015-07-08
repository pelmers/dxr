from cStringIO import StringIO

from os.path import basename, join, relpath, dirname
from flask import url_for

import dxr.indexers
from dxr.indexers import Ref
from dxr.utils import cd, search_url

# TODO next: import dynamically from a provided directory so we don't have to maintain this.
from idlparser.xpidl import IDLParser, Attribute
#  _____
# < lol >
#  -----
#         \   ^__^
#          \  (oo)\_______
#             (__)\       )\/\
#                 ||----w |
#                 ||     ||
from idlparser.header import idl_basename, header, include, jsvalue_include, \
    infallible_includes, header_end, forward_decl, write_interface, printComments


def start_extent(name, location):
    """Return the last byte position on which we can find name in the location's line."""
    return location._line.rfind(name) - location._colno + location._lexpos

def number_lines(text):
    return len(text.splitlines())

def header_line_numbers(idl, filename):
    """Map each production to its line number in the header."""
    # Basically I replace all fd.write in print_header with line increments
    production_map = {}
    line = number_lines(header % {'filename': filename,
                                  'basename': idl_basename(filename)}) + 1

    foundinc = False
    for inc in idl.includes():
        if not foundinc:
            foundinc = True
            line += 1
        line += number_lines(include % {'basename': idl_basename(inc.filename)})

    if idl.needsJSTypes():
        line += number_lines(jsvalue_include)

    # Include some extra files if any attributes are infallible.
    for iface in [p for p in idl.productions if p.kind == 'interface']:
        for attr in [m for m in iface.members if isinstance(m, Attribute)]:
            if attr.infallible:
                line += number_lines(infallible_includes)
                break

    line += number_lines(header_end) + 1

    for p in idl.productions:
        production_map[p] = line
        if p.kind == 'include': continue
        if p.kind == 'cdata':
            line += number_lines(p.data)
            continue

        if p.kind == 'forward':
            line += number_lines(forward_decl % {'name': p.name})
            continue
        if p.kind == 'interface':
            # Write_interface inserts a blank line at the start.
            production_map[p] += 1
            # Eh....
            fd = StringIO()
            write_interface(p, fd)
            line += len(fd.readlines())
            continue
        if p.kind == 'typedef':
            fd = StringIO()
            printComments(fd, p.doccomments, '')
            line += len(fd.readlines())
            line += number_lines("typedef %s %s;\n\n" % (p.realtype.nativeType('in'),
                                             p.name))

    return production_map


class FileToIndex(dxr.indexers.FileToIndex):

    def __init__(self, path, contents, plugin_name, tree):
        super(FileToIndex, self).__init__(path, contents, plugin_name, tree)
        # TODO next: expose in config option
        self.header_bucket = relpath(join(tree.object_folder, "dist", "include"), tree.source_folder)
        self.parser = IDLParser(self.tree.object_folder)
        # Hold on to the URL so we do not have to regenerate it everywhere.
        self.header_filename = basename(self.path.replace('.idl', '.h'))
        header_path = join(self.header_bucket, self.header_filename)
        self.generated_url = url_for('.browse',
                                     tree=self.tree.name,
                                     path=header_path)
        self._idl = None
        self._line_map = None

    @property
    def idl(self):
        """Return the AST."""

        if not self._idl:
            with cd(dirname(self.absolute_path())):
                self._idl = self.parser.parse(self.contents, basename(self.path))
                # TODO next: expose include dirs as config option
                self._idl.resolve(['.'], self.parser)
        return self._idl

    @property
    def line_map(self):
        if not self._line_map:
            self._line_map = header_line_numbers(self.idl, self.header_filename)
        return self._line_map

    def is_interesting(self):
        # TODO next: consider adding a link from generated headers back to the idl
        return self.path.endswith('.idl')

    def links(self):
        yield (3, 'IDL', [('idl-header', self.header_filename, self.generated_url)])

    def refs(self):
        def visit_interface(interface):
            # TODO next: anchor these to the right line number using header.py
            # TODO next: some sort of c++ source map?
            for member in interface.members:
                member.location.resolve()
                if member.kind == 'const':
                    start = start_extent(member.name, member.location)
                    yield start, start + len(member.name), Ref([{
                        'html': 'See generated source',
                        'title': 'Go to the definition in the C++ header file.',
                        'href': self.generated_url,
                        'icon': 'field'
                    }])
                elif member.kind == 'method':
                    start = member.location._lexpos
                    yield start, start + len(member.name), Ref([{
                        'html': 'See generated source',
                        'title': 'Go to the declaration in the C++ header file.',
                        'href': self.generated_url,
                        'icon': 'method'
                    }])

        # also create links for "include" etc.
        for item in self.idl.productions:
            if item.kind == 'include':
                filename = item.filename
                item.location.resolve()
                start = start_extent(filename, item.location)
                yield start, start + len(filename), Ref([{
                    'html':   'Jump to file',
                    'title':  'Go to the target of the include statement',
                    'href':   url_for('.browse', tree=self.tree.name, path=filename),
                    'icon':   'jump'
                }])
            elif item.kind == 'typedef':
                item.location.resolve()
                start = start_extent(item.name, item.location)
                yield start, start + len(item.name), Ref([{
                    'html':   'See generated source',
                    'title':  'Go to the typedef in the C++ header file',
                    'href':   self.generated_url + '#%d' % self.line_map[item],
                    'icon':   'type'
                }])
            elif item.kind == 'interface':
                # TODO next: yield for the extended class
                item.location.resolve()
                start = start_extent(item.name, item.location)
                if item.base:
                    base_start = start_extent(item.base, item.location)
                    print base_start
                    yield base_start, base_start + len(item.base), Ref([{
                        'html':   'Find declaration',
                        'title':  'Search for the declaration of this superclass',
                        'href':   search_url(self.tree, '"interface %s" ext:idl' % item.base),
                        'icon':   'type'
                    }])
                yield start, start + len(item.name), Ref([{
                    'html':   'See generated source',
                    'title':  'Go to the declaration in the C++ header file',
                    'href':   self.generated_url + '#%d' % self.line_map[item],
                    'icon':   'class'
                }])
                for ref in visit_interface(item):
                    yield ref
            elif item.kind == 'forward':
                item.location.resolve()
                start = start_extent(item.name, item.location)
                yield start, start + len(item.name), Ref([{
                    'html':   'See generated source',
                    'title':  'Go to the declaration in the C++ header file',
                    'href':   self.generated_url + '#%d' % self.line_map[item],
                    'icon':   'class'
                }])
            # TODO: can we do something useful for these?
            # Unhandled kinds: {'builtin', 'cdata', 'native', 'attribute', 'forward', 'attribute'}

# TODO next: expose plugin with option for configuring source directory.
