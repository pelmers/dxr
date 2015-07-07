from os.path import basename, dirname

import dxr.indexers
from dxr.utils import cd
from idlparser.xpidl import IDLParser

class FileToIndex(dxr.indexers.FileToIndex):

    def __init__(self, path, contents, plugin_name, tree):
        super(FileToIndex, self).__init__(path, contents, plugin_name, tree)
        # TODO next: put this in TreeToIndex so we stop regenerating all the files each time
        self.parser = IDLParser(self.tree.object_folder)
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
        return self.path.endswith('.idl')

    def links(self):
        # TODO next: Read options list to find out where to link
        v = self.idl
        print v
        return []

    def refs(self):
        # TODO next: walk the idl visitor and use header.py to create ref links
        # also create links for "include" etc.
        return []
