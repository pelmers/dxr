import cPickle
from os.path import join, relpath, dirname, exists
import re

import dxr.indexers
from dxr.build import unignored, ensure_folder
from dxr.lines import Ref
from dxr.utils import browse_file_url
from dxr.plugins import Plugin


class TreeToIndex(dxr.indexers.TreeToIndex):
    def __init__(self, plugin_name, tree, vcs_cache):
        super(TreeToIndex, self).__init__(plugin_name, tree, vcs_cache)
        self.temp_folder = join(self.tree.temp_folder, 'plugins/pathlink')

    def post_build(self):
        """Store the source directory tree in memory? or in a file to save memory space.
        probably put them in a file.
        """
        open_stack = {}

        def add_entry(path):
            """Add an entry for path in all the open logs of open_stack."""
            for (stored_path, log) in open_stack.iteritems():
                # Compute the relative path from the stored path to the current path.
                to_write = relpath(path, join(self.tree.source_folder, stored_path))
                log.write(to_write + '\n')

        for path in unignored(self.tree.source_folder,
                              self.tree.ignore_paths,
                              self.tree.ignore_filenames):
            # Ensure the path's relative directory exists under temp_folder.
            # Keep track of the file as being open now.
            # For each child, put parentdir - child path into the open files.
            rel_path = relpath(path, self.tree.source_folder)
            parent = dirname(rel_path)
            if parent not in open_stack:
                # Now we're visiting some new directory.
                # Close any paths that are not superfolders of the current.
                paths_to_finalize = {stored_path for stored_path in open_stack
                                     if stored_path not in parent}
                self.finalize_paths(open_stack, paths_to_finalize)
                temp_parent = join(self.temp_folder, dirname(rel_path))
                ensure_folder(temp_parent)
                # Open a file for recording in it.
                open_stack[parent] = open(join(temp_parent, "paths.txt"), "w+")
            # Put an entry for this file in all the entries of the open stack.
            add_entry(path)

        # Close any still-open files at the end.
        self.finalize_paths(open_stack, open_stack.keys())

    def temp_path_for_source(self, source_path):
        """Return the path under temp/plugins/pathlink that corresponds to
        source_path which is relative to tree.source_folder.
        """
        return join(self.temp_folder, source_path)

    def finalize_paths(self, path_map, to_finalize):
        """Finalize the given paths, by compiling and pickling the regex to path
        're.pickle' and closing the files.

        Delete to_finalize from path_map on completion.
        """
        for path in to_finalize:
            # Cursor back to the start before reading
            path_map[path].seek(0)
            regex = re.compile('|'.join(re.escape(line.strip()) for line in path_map[path].readlines()))
            temp = self.temp_path_for_source(path or '.')
            with open(join(temp, 're.pickle'), 'wb') as pickled:
                cPickle.dump(regex, pickled)
            path_map[path].close()
            del path_map[path]

    def file_to_index(self, path, contents):
        return FileToIndex(path, contents, self.plugin_name, self.tree)


class FileToIndex(dxr.indexers.FileToIndex):
    def __init__(self, path, contents, plugin_name, tree):
        super(FileToIndex, self).__init__(path, contents, plugin_name, tree)
        temp_folder = join(self.tree.temp_folder, 'plugins/pathlink')
        temp_path = join(temp_folder, relpath(self.absolute_path(), self.tree.source_folder))
        regex_path = join(dirname(temp_path), 're.pickle')
        if exists(regex_path):
            with open(regex_path, 'rb') as regex_pickle:
                self.regex = cPickle.load(regex_pickle)

    def is_interesting(self):
        # Skip files bigger than 100K for speed (mostly skiping generated files).
        return super(FileToIndex, self).is_interesting() and len(self.contents) < 102400

    def refs(self):
        for m in self.regex.finditer(self.contents):
            path = m.group(0)
            yield (m.start(0), m.end(0),
                   PathRef(self.tree, relpath(join(dirname(self.absolute_path()), path),
                                              self.tree.source_folder)))


class PathRef(Ref):
    plugin = 'pathlink'

    def menu_items(self):
        print self.menu_data
        yield {'html': 'Visit file %s' % self.menu_data,
               'title': 'Go to %s' % self.menu_data,
               'href': browse_file_url(self.tree.name, self.menu_data),
               'icon': 'external_link'}

plugin = Plugin(tree_to_index=TreeToIndex, refs=[PathRef])
