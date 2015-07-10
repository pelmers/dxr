from cStringIO import StringIO

from flask import url_for
from os.path import relpath, join, basename, dirname

from dxr.indexers import Ref, Extent, Position
from dxr.plugins.xpidl.idlparser.xpidl import Attribute
from dxr.utils import search_url

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


def start_pos(name, location):
    """Return the last byte position on which we can find name in the
    location's line, resolving if necessary."""

    location.resolve()
    return location._line.rfind(name) - location._colno + location._lexpos


def make_extent(name, location, offset=0):
    """Return an Extent for the given name in this Location, offset describes the line number
    offset. (TODO: figure out why.)"""

    location.resolve()
    start_col = location._line.rfind(name) - location._colno
    # the AST's line numbers are 0-based, but DXR expects 1-based lines.
    return Extent(Position(location._lineno + offset, start_col),
                  Position(location._lineno + offset, start_col + len(name)))


def header_line_numbers(idl, filename):
    """Map each production to its line number in the header."""
    # Basically I replace all fd.write in print_header with line increments
    def number_lines(text):
        return len(text.splitlines())

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
            # write_interface inserts a blank line at the start.
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


class IdlVisitor(object):
    """Traverse an IDL syntax tree and collect refs and needles."""

    def __init__(self, parser, contents, rel_path, abs_path, include_folders, header_bucket,
                 tree_config):
        self.tree = tree_config
        # Hold on to the URL so we do not have to regenerate it everywhere.
        self.header_filename = basename(rel_path.replace('.idl', '.h'))
        header_path = relpath(join(header_bucket, self.header_filename),
                              self.tree.source_folder)
        self.generated_url = url_for('.browse',
                                     tree=self.tree.name,
                                     path=header_path)
        self.ast = parser.parse(contents, basename(rel_path))
        # Might raise IdlError
        self.ast.resolve([dirname(abs_path)] + include_folders, parser)
        self.line_map = header_line_numbers(self.ast, self.header_filename)
        # List of (start, end, Ref) where start and end are byte offsets into the file.
        self.refs = []
        self.needles = []

        # Initiate visitations.
        for item in self.ast.productions:
            if item.kind == 'include':
                self.visit_include(item)
            elif item.kind == 'typedef':
                self.visit_typedef(item)
            elif item.kind == 'forward':
                self.visit_forward(item)
            elif item.kind == 'interface':
                self.visit_interface(item)
            # TODO: can we do something useful for these?
            # Unhandled: {'builtin', 'cdata', 'native', 'attribute', 'forward', 'attribute'}

    def yield_needle(self, name, mapping, extent):
        self.needles.append((PLUGIN_NAME + '_' + name, mapping, extent))

    def yield_name_needle(self, filter_name, name, location, offset=0):
        self.yield_needle(filter_name, {'name': name}, make_extent(name, location, offset))

    def yield_ref(self, start, end, menus):
        self.refs.append((start, end, Ref(menus)))

    def generated_menu(self, production):
        # Return a menu for jumping to corresponding C++ source using the line map.
        return {
            'html': 'See generated source',
            'title': 'Go to this line in the generated C++ header file',
            'href': self.generated_url + '#%d' % self.line_map[production],
            'icon': 'jump'
        }

    def filtered_search_menu(self, filter_name, name, html='Find declaration',
                             title='Search for declarations.', icon='class'):
        return {
            'html': html,
            'title': title,
            'href': search_url(self.tree, '%s:%s' % (filter_name, name)),
            'icon': icon
        }

    def subclass_search_menu(self, name):
        return self.filtered_search_menu('derived', name, 'Find subclasses',
                                         'Search for children that derive this interface.',
                                         'class')

    def include_menu(self, item):
        return {
            'html': 'Jump to file',
            'title': 'Go to the target of the include statement',
            'href': url_for('.browse', tree=self.tree.name,
                            path=relpath(item.resolved_path, self.tree.source_folder)),
            'icon': 'jump'
        }

    def visit_interface(self, interface):
        # Yield refs for the members, methods, etc. of an interface (and the interface itself).
        start = start_pos(interface.name, interface.location)
        if interface.base:
            # The interface that this one extends.
            base_start = start_pos(interface.base, interface.location)
            self.yield_ref(base_start, base_start + len(interface.base), [
                self.filtered_search_menu('type-decl', interface.base, icon='type'),
                self.subclass_search_menu(interface.base)
            ])
            self.yield_name_needle('derived', interface.base, interface.location)

        self.yield_ref(start, start + len(interface.name), [
            self.subclass_search_menu(interface.name),
            self.generated_menu(interface)
        ])
        self.yield_name_needle('type_decl', interface.name, interface.location, 1)

        for member in interface.members:
            if member.kind == 'const':
                start = start_pos(member.name, member.location)
                self.yield_ref(start, start + len(member.name), [
                    self.filtered_search_menu('var-decl', member.name, icon='field'),
                    self.filtered_search_menu('var', member.name, html='Find definition',
                                              title='Search for definitions', icon='field'),
                ])
                self.yield_name_needle('var_decl', member.name, member.location)

            elif member.kind == 'method':
                start = member.location._lexpos
                self.yield_ref(start, start + len(member.name), [
                    self.filtered_search_menu('function-decl', member.name, icon='method'),
                    self.filtered_search_menu('function', member.name, 'Find implementations',
                                              'Search for implementations of this method',
                                              'method')
                ])
                self.yield_name_needle('function_decl', member.name, member.location)

    def visit_include(self, item):
        filename = item.filename
        start = start_pos(filename, item.location)
        self.yield_ref(start, start + len(filename), [self.include_menu(item)])

    def visit_typedef(self, item):
        start = start_pos(item.name, item.location)
        self.yield_ref(start, start + len(item.name), [self.generated_menu(item)])

    def visit_forward(self, item):
        start = start_pos(item.name, item.location)
        self.yield_ref(start, start + len(item.name), [
            self.filtered_search_menu('type-decl', item.name, icon='type'),
            self.subclass_search_menu(item.name),
            self.generated_menu(item)
        ])
