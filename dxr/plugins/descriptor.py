"""Descriptor - Provide useful descriptions for common file types.
Refer to https://mxr.mozilla.org/webtools-central/source/mxr/Local.pm#27
"""
import re
from os.path import splitext, basename

import dxr.indexers

class FileToIndex(dxr.indexers.FileToIndex):
    """Do lots of work to yield a description needle."""

    def needles(self):
        if self.contains_text():
            extension = splitext(self.path)[1]
            description = None
            if extension:
                try:
                    # Find the describer method, skipping the dot on extension.
                    describer = getattr(self, 'describe_' + extension[1:])
                except AttributeError:
                    # Don't have a descriptor function for this file type, try doing generic.
                    description = self.generic_describe()
                else:
                    description = describer()
            else:
                description = self.generic_describe()
            if description:
                yield 'description', description

    def describe_html(self):
        title_re = re.compile(r'<title>([^<]*)</title>')
        match = re.search(title_re, self.contents)
        if match:
            print self.path, match.groups()
            return match.group(1)

    def generic_describe(self):
        # TODO next: for things like readme?
        filename = basename(self.path)
        root, ext = splitext(filename)
        # Look at the first 60 lines for some text matching filename [delimiter] text
        delimiters = ':,-'
        lines = self.contents.splitlines()
        re_string = r'({}|description)({})?\s*([{}])\s*(?P<description>[\w\s-]+)'.format(root, ext, delimiters)
        description_re = re.compile(re_string, re.IGNORECASE)
        for line in lines[:60]:
            match = re.search(description_re, line)
            if match:
                print self.path, match.groups()
                return match.group('description')
