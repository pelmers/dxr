import cPickle
from os.path import join, relpath, dirname, exists, abspath
import re

import dxr.indexers
from dxr.build import unignored, ensure_folder
from dxr.lines import Ref
from dxr.utils import browse_file_url
from dxr.plugins import Plugin

# Names for temp files.
TEMP_RE_NAME = 're.pickle'
TEMP_PATHS_NAME = 'paths.txt'


class TreeToIndex(dxr.indexers.TreeToIndex):
    def __init__(self, plugin_name, tree, vcs_cache):
        super(TreeToIndex, self).__init__(plugin_name, tree, vcs_cache)
        self.temp_folder = join(self.tree.temp_folder, 'plugins/pathlink')
        self.all_paths = set()
        # Separately keep track of all folders to use on files in the source
        # root where the relative path regex will match absolute paths too.
        self.all_folders = set()

    def post_build(self):
        """Store the regular expression that finds the relative paths for the
        directory tree in files.

        """
        # Map folder path relative to source -> paths.txt file for that folder.
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
            rel_path = relpath(path, self.tree.source_folder)
            parent = dirname(rel_path)
            if parent not in open_stack:
                # Then we're visiting some new directory.
                self.all_paths.add('/' + parent)
                self.all_folders.add('/' + parent)
                # Close any paths that are not superfolders of the current.
                paths_to_finalize = (stored_path for stored_path in open_stack
                                     if not parent.startswith(stored_path))
                self.finalize_paths(open_stack, paths_to_finalize)
                # Ensure the path's relative directory exists under temp_folder.
                temp_parent = join(self.temp_folder, dirname(rel_path))
                ensure_folder(temp_parent)
                # Open a file for recording these paths.
                open_stack[parent] = open(join(temp_parent, TEMP_PATHS_NAME), 'w+')
            # Put an entry for this file in all the entries of the open stack.
            self.all_paths.add('/' + rel_path)
            add_entry(path)

        # Close any still-open files at the end.
        self.finalize_paths(open_stack, open_stack.keys())
        # Freeze path sets.
        self.all_paths = frozenset(self.all_paths)
        self.all_folders = frozenset(self.all_folders)

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
            regex = re.compile('|'.join(re.escape(line.strip().rstrip('/'))
                               for line in path_map[path]))
            temp = self.temp_path_for_source(path or '.')
            with open(join(temp, TEMP_RE_NAME), 'wb') as pickled:
                cPickle.dump(regex, pickled)
            path_map[path].close()
            del path_map[path]

    def file_to_index(self, path, contents):
        # If we're at the root, then the set of absolute paths to search for is
        # the set of all folders, since the relative path regexp will already
        # find all absolute-pathed files.
        if not dirname(path):
            return FileToIndex(path, contents, self.plugin_name, self.tree, self.all_folders)
        else:
            return FileToIndex(path, contents, self.plugin_name, self.tree, self.all_paths)


class FileToIndex(dxr.indexers.FileToIndex):
    # Regular expression that finds abspath-like things
    abspath_re = re.compile(r'(/[\w:_.-]+)+')

    def __init__(self, path, contents, plugin_name, tree, all_paths):
        super(FileToIndex, self).__init__(path, contents, plugin_name, tree)
        self.all_paths = all_paths
        temp_folder = join(self.tree.temp_folder, 'plugins/pathlink')
        temp_path = join(temp_folder, relpath(self.absolute_path(), self.tree.source_folder))
        regex_path = join(dirname(temp_path), TEMP_RE_NAME)
        if exists(regex_path):
            with open(regex_path, 'rb') as regex_pickle:
                self.regex = cPickle.load(regex_pickle)

    def is_interesting(self):
        # Skip files bigger than 100K for speed (mostly skiping generated files).
        return super(FileToIndex, self).is_interesting() and len(self.contents) < 102400

    def refs(self):
        for m in self.regex.finditer(self.contents):
            path = m.group()
            yield (m.start(), m.end(),
                   PathRef(self.tree, relpath(join(dirname(self.absolute_path()), path),
                                              self.tree.source_folder)))

        for m in self.abspath_re.finditer(self.contents):
            path = m.group()
            if path in self.all_paths:
                yield (m.start(), m.end(), PathRef(self.tree, path.lstrip('/')))


class PathRef(Ref):
    plugin = 'pathlink'

    def menu_items(self):
        yield {'html': 'Go to %s' % self.menu_data,
               'title': 'Go to %s' % self.menu_data,
               'href': browse_file_url(self.tree.name, self.menu_data),
               'icon': 'external_link'}


plugin = Plugin(tree_to_index=TreeToIndex, refs=[PathRef])
