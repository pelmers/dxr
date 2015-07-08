from cStringIO import StringIO
from functools import partial

from os.path import basename, join, relpath, dirname, abspath
from flask import url_for

from schema import Optional, Use, And

from dxr.config import AbsPath
import dxr.indexers
from dxr.indexers import Ref
from dxr.plugins import Plugin, AdHocTreeToIndex
from dxr.utils import cd, search_url
from idlparser.xpidl import IDLParser, Attribute, IDLError


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

PLUGIN_NAME = 'xpidl'

def start_extent(name, location):
    """Return the last byte position on which we can find name in the
    location's line, resolving if necessary."""

    location.resolve()
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
        if p.kind == 'cdata':
            line += number_lines(p.data)
        elif p.kind == 'forward':
            line += number_lines(forward_decl % {'name': p.name})
        elif p.kind == 'interface':
            # Write_interface inserts a blank line at the start.
            production_map[p] += 1
            # Eh....
            fd = StringIO()
            write_interface(p, fd)
            line += len(fd.readlines())
        elif p.kind == 'typedef':
            fd = StringIO()
            printComments(fd, p.doccomments, '')
            line += len(fd.readlines())
            line += number_lines("typedef %s %s;\n\n" % (p.realtype.nativeType('in'),
                                             p.name))

    return production_map


class FileToIndex(dxr.indexers.FileToIndex):

    def __init__(self, path, contents, plugin_name, tree):
        super(FileToIndex, self).__init__(path, contents, plugin_name, tree)
        self.temp_folder = join(self.tree.temp_folder, 'plugins', PLUGIN_NAME)
        self.parser = IDLParser(self.temp_folder)
        self.dirname = dirname(self.absolute_path())
        # Hold on to the URL so we do not have to regenerate it everywhere.
        self.header_filename = basename(self.path.replace('.idl', '.h'))
        header_path = relpath(join(self.plugin_config.header_bucket, self.header_filename),
                              self.tree.source_folder)
        self.generated_url = url_for('.browse',
                                     tree=self.tree.name,
                                     path=header_path)
        self.idl = None
        self.line_map = None

    def resolve(self):
        """Parse the IDL file and resolve deps."""

        self.idl = self.parser.parse(self.contents, basename(self.path))
        try:
            self.idl.resolve([self.dirname] + self.plugin_config.include_folders, self.parser)
        except IDLError as e:
            print e
        self.line_map = header_line_numbers(self.idl, self.header_filename)

    def is_interesting(self):
        # TODO next next: consider adding a link from generated headers back to the idl
        return self.path.endswith('.idl')

    def links(self):
        yield (3, 'IDL', [('idl-header', self.header_filename, self.generated_url)])

    def refs(self):
        def generated_menu(production):
            # Return a menu for jumping to corresponding C++ source using the line map.
            return {
                'html':   'See generated source',
                'title':  'Go to this line in the generated C++ header file',
                'href':   self.generated_url + '#%d' % self.line_map[production],
                'icon':   'class'
            }

        def visit_interface(interface):
            # Yield refs for the members, methods, etc. of an interface (and the interface itself).
            start = start_extent(interface.name, interface.location)
            if interface.base:
                # The interface that this one extends.
                base_start = start_extent(interface.base, interface.location)
                yield base_start, base_start + len(interface.base), Ref([{
                    'html':   'Find declaration',
                    'title':  'Search for the declaration of this class',
                    'href':   search_url(self.tree, 'type-decl:%s' % interface.base),
                    'icon':   'type'
                }])
            yield start, start + len(interface.name), Ref([{
                'html':   'Find subclasses',
                'title':  'Search for children that derive this interface.',
                'href':   search_url(self.tree, 'derived:%s' % interface.name),
                'icon':   'class'
            }, generated_menu(interface)])
            for member in interface.members:
                if member.kind == 'const':
                    start = start_extent(member.name, member.location)
                    yield start, start + len(member.name), Ref([{
                        'html': 'Find declarations',
                        'title': 'Search for declarations of this constant.',
                        'href': search_url(self.tree, "var:%s" % member.name),
                        'icon': 'field'
                    }])
                elif member.kind == 'method':
                    start = member.location._lexpos
                    yield start, start + len(member.name), Ref([{
                        'html': 'Find implementations',
                        'title': 'Search for implementations of this method',
                        'href': search_url(self.tree, "function:%s" % member.name),
                        'icon': 'method'
                    }])

        self.resolve()
        if not self.idl:
            # Then we could not resolve the idl file, do not continue.
            raise StopIteration
        for item in self.idl.productions:
            if item.kind == 'include':
                filename = item.filename
                start = start_extent(filename, item.location)
                yield start, start + len(filename), Ref([{
                    'html':   'Jump to file',
                    'title':  'Go to the target of the include statement',
                    'href': url_for('.browse', tree=self.tree.name,
                                    path=relpath(item.resolved_path, self.tree.source_folder)),
                    'icon': 'jump'
                }])
            elif item.kind == 'typedef':
                start = start_extent(item.name, item.location)
                yield start, start + len(item.name), Ref([generated_menu(item)])
            elif item.kind == 'forward':
                start = start_extent(item.name, item.location)
                yield start, start + len(item.name), Ref([generated_menu(item)])
            elif item.kind == 'interface':
                for ref in visit_interface(item):
                    yield ref
            # TODO: can we do something useful for these?
            # Unhandled kinds: {'builtin', 'cdata', 'native', 'attribute', 'forward', 'attribute'}

ColonPathList = And(basestring,
                    Use(lambda value: value.strip().split(':')),
                    Use(lambda paths: map(abspath, paths)),
                    error='This should be a colon-separated list of paths.')

plugin = Plugin(
    tree_to_index=partial(AdHocTreeToIndex,
                          file_to_index_class=FileToIndex),
    config_schema={
        'header_bucket': AbsPath,
        Optional('include_folders', default=[]): ColonPathList})


# TODO next: export needles definitions so we can do a structured queries
# TODO next: structured query ideas -- interface and method declarations, deriving interfaces
# TODO next: create a real python module out of idlparser/
# TODO next next: automatically read moz.build files to get include directories
