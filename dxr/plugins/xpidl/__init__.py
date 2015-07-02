import dxr.indexers
from idlparser.xpidl import IDLParser

class FileToIndex(dxr.indexers.FileToIndex):

    def __init__(self, path, contents, plugin_name, tree):
        super(FileToIndex, self).__init__(path, contents, plugin_name, tree)
        self.parser = IDLParser(self.tree.object_folder)
        self._idl = None

    @property
    def idl(self):
        """Return the AST visitor."""

        if not self._idl:
            self._idl = self.parser.parse(self.contents, self.absolute_path())
            self._idl.resolve('.', self.parser)
        return self._idl

    def is_interesting(self):
        return self.path.endswith('.idl')

    def refs(self):
        v = self.idl
        print v
        yield []
