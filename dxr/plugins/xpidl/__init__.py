from os.path import basename, dirname, join, relpath

from flask import url_for

import dxr.indexers
from dxr.indexers import Ref
from dxr.utils import cd
# TODO next: import dynamically from a provided directory so we don't have to maintain this.
from idlparser.xpidl import IDLParser


class FileToIndex(dxr.indexers.FileToIndex):

    def __init__(self, path, contents, plugin_name, tree):
        super(FileToIndex, self).__init__(path, contents, plugin_name, tree)
        # TODO next: expose in config option
        self.header_bucket = relpath(join(tree.object_folder, "dist", "include"), tree.source_folder)
        # TODO next: put this in TreeToIndex so we stop regenerating all the files each time
        # or are we? is the cache taking care of things? should check.
        self.parser = IDLParser(self.tree.object_folder)
        # Hold on to the URL so we do not have to regenerate it everywhere.
        header_filename = basename(self.path.replace('.idl', '.h'))
        header_path = join(self.header_bucket, header_filename)
        self.generated_url = url_for('.browse',
                                     tree=self.tree.name,
                                     path=header_path)
        self._idl = None

    @property
    def idl(self):
        """Return the AST."""

        if not self._idl:
            with cd(dirname(self.absolute_path())):
                self._idl = self.parser.parse(self.contents, basename(self.path))
                self._idl.resolve('.', self.parser)
        return self._idl

    def is_interesting(self):
        # TODO next: consider adding a link from generated headers back to the idl
        return self.path.endswith('.idl')

    def links(self):
        header_filename = basename(self.path.replace('.idl', '.h'))
        yield (3, 'IDL', [('idl-header', header_filename, self.generated_url)])

    def refs(self):
        def visit_interface(interface):
            # TODO next: anchor these to the right line number using header.py
            # TODO next: some sort of c++ source map?
            for member in interface.members:
                member.location.resolve()
                if member.kind == 'const':
                    start = member.location._lexpos + member.location._line.rfind(member.name)
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
                start = item.location._lexpos + item.location._line.rfind(filename)
                yield start, start + len(filename), Ref([{
                    'html':   'Jump to file',
                    'title':  'Go to the target of the include statement',
                    'href':   url_for('.browse', tree=self.tree.name, path=filename),
                    'icon':   'jump'
                }])
            elif item.kind == 'typedef':
                item.location.resolve()
                start = item.location._lexpos + item.location._line.rfind(item.name)
                yield start, start + len(item.name), Ref([{
                    'html':   'See generated source',
                    'title':  'Go to the typedef in the C++ header file',
                    'href':   self.generated_url,
                    'icon':   'type'
                }])
            elif item.kind == 'interface':
                for ref in visit_interface(item):
                    yield ref
            elif item.kind in {'builtin', 'cdata', 'native', 'attribute', 'forward', 'attribute'}:
                # Don't do anything for these kinds of items.
                # TODO: can we do something useful for these?
                continue

# TODO next: expose plugin with option for configuring source directory.
