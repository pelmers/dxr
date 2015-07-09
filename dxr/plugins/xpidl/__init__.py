from functools import partial

from os.path import join, abspath
from schema import Optional, Use, And

from dxr.config import AbsPath
from dxr.filters import LINE
import dxr.indexers
from dxr.indexers import STRING_PROPERTY, iterable_per_line, split_into_lines, with_start_and_end
from dxr.plugins import Plugin, AdHocTreeToIndex, filters_from_namespace
from dxr.plugins.xpidl import filters
from dxr.plugins.xpidl.visitor import IdlVisitor
from idlparser.xpidl import IDLParser, IDLError

PLUGIN_NAME = 'xpidl'

# Like qualified line needle, but has no qualname
LINE_NEEDLE = {
    'type': 'object',
    'properties': {
        'name': STRING_PROPERTY,
        'start': {
            'type': 'integer',
            'index': 'no'  # just for highlighting
        },
        'end': {
            'type': 'integer',
            'index': 'no'
        }
    }
}



class FileToIndex(dxr.indexers.FileToIndex):

    def __init__(self, path, contents, plugin_name, tree):
        super(FileToIndex, self).__init__(path, contents, plugin_name, tree)
        self.temp_folder = join(self.tree.temp_folder, 'plugins', PLUGIN_NAME)
        self.parser = IDLParser(self.temp_folder)
        self._idl = None
        self._idl_exception = False

    @property
    def idl(self):
        """Parse the IDL file and resolve deps."""
        # Don't try again if we already excepted.
        if not self._idl and not self._idl_exception:
            try:
                self._idl = IdlVisitor(self.parser, self.contents, self.path, self.absolute_path(),
                                       self.plugin_config.include_folders,
                                       self.plugin_config.header_bucket, self.tree)
            except IDLError as e:
                print e
                self._idl_exception = True
        return self._idl

    def is_interesting(self):
        # TODO next next: consider adding a link from generated headers back to the idl
        return self.path.endswith('.idl')

    def links(self):
        if self.idl:
            yield (3, 'IDL', [('idl-header', self.idl.header_filename, self.idl.generated_url)])

    def refs(self):
        return self.idl.refs if self.idl else []

    def needles_by_line(self):
        return iterable_per_line(
            with_start_and_end(split_into_lines(self.idl.needles if self.idl else [])))

ColonPathList = And(basestring,
                    Use(lambda value: value.strip().split(':')),
                    Use(lambda paths: map(abspath, paths)),
                    error='This should be a colon-separated list of paths.')

mappings = {
    LINE: {
        'properties': {
            'xpidl_var_decl': LINE_NEEDLE,
            'xpidl_function_decl': LINE_NEEDLE,
            'xpidl_derived': LINE_NEEDLE,
            'xpidl_type_decl': LINE_NEEDLE
        }
    }
}

plugin = Plugin(
    tree_to_index=partial(AdHocTreeToIndex,
                          file_to_index_class=FileToIndex),
    filters=filters_from_namespace(filters.__dict__),
    mappings=mappings,
    config_schema={
        'header_bucket': AbsPath,
        Optional('include_folders', default=[]): ColonPathList})


# TODO next: export needles definitions so we can do a structured queries
# TODO next: structured query ideas -- interface and method declarations, deriving interfaces
# TODO next: create a real python module out of idlparser/
# TODO next next: automatically read moz.build files to get include directories
