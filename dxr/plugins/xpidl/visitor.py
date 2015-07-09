from cStringIO import StringIO
from dxr.indexers import Ref
from dxr.plugins.xpidl.idlparser.xpidl import Attribute

from flask import url_for
from os.path import relpath, join, basename, dirname

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

def start_extent(name, location):
    """Return the last byte position on which we can find name in the
    location's line, resolving if necessary."""

    location.resolve()
    return location._line.rfind(name) - location._colno + location._lexpos

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

class IdlVisitor(object):
    """Traverse an IDL syntax tree and collect refs and needles."""

    def __init__(self, parser, contents, rel_path, abs_path, include_folders, header_bucket, tree_config):
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
        # TODO next: needles
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
            # Unhandled kinds: {'builtin', 'cdata', 'native', 'attribute', 'forward', 'attribute'}

    def generated_menu(self, production):
        # Return a menu for jumping to corresponding C++ source using the line map.
        return {
            'html': 'See generated source',
            'title': 'Go to this line in the generated C++ header file',
            'href': self.generated_url + '#%d' % self.line_map[production],
            'icon': 'class'
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
                                         'Search for children that derive this interface.', 'class')

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
        start = start_extent(interface.name, interface.location)
        if interface.base:
            # The interface that this one extends.
            base_start = start_extent(interface.base, interface.location)
            self.refs.append((base_start, base_start + len(interface.base), Ref([
                self.filtered_search_menu('type-decl', interface.base, icon='type'),
                self.subclass_search_menu(interface.base)
            ])))

        self.refs.append((start, start + len(interface.name), Ref([
            self.subclass_search_menu(interface.name),
            self.generated_menu(interface)
        ])))

        for member in interface.members:
            if member.kind == 'const':
                start = start_extent(member.name, member.location)
                self.refs.append((start, start + len(member.name), Ref([
                    self.filtered_search_menu('var', member.name, icon='field')
                ])))
            elif member.kind == 'method':
                start = member.location._lexpos
                self.refs.append((start, start + len(member.name), Ref([
                    self.filtered_search_menu('function', member.name, 'Find implementations',
                                         'Search for implementations of this method', 'method')
                ])))

    def visit_include(self, item):
        filename = item.filename
        start = start_extent(filename, item.location)
        self.refs.append((start, start + len(filename), Ref([self.include_menu(item)])))

    def visit_typedef(self, item):
        start = start_extent(item.name, item.location)
        self.refs.append((start, start + len(item.name), Ref([self.generated_menu(item)])))

    def visit_forward(self, item):
        start = start_extent(item.name, item.location)
        self.refs.append((start, start + len(item.name), Ref([
            self.filtered_search_menu('type-decl', item.name, icon='type'),
            self.subclass_search_menu(item.name),
            self.generated_menu(item)
        ])))

