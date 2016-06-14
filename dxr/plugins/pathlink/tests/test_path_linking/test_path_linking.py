"""Test that the plugin produces correct needles and refs.

"""
from dxr.testing import DxrInstanceTestCase, menu_on


class PathLinkTests(DxrInstanceTestCase):
    def test_menus1(self):
        page = self.source_page('README')

        menu_on(page, 'Different', {'html': 'Go to Different',
                                    'href': '/code/source/Different'})
        menu_on(page, 'sub/green/blue', {'html': 'Go to sub/green/blue',
                                         'href': '/code/source/sub/green/blue'})
        menu_on(page, 'sub/red', {'html': 'Go to sub/red',
                                  'href': '/code/source/sub/red'})
        menu_on(page, '/sub/green', {'html': 'Go to sub/green',
                                     'href': '/code/source/sub/green'})

    def test_menus2(self):
        page = self.source_page('sub/red')

        menu_on(page, '/sub/green', {'html': 'Go to sub/green',
                                     'href': '/code/source/sub/green'})
        menu_on(page, 'green/blue', {'html': 'Go to sub/green/blue',
                                     'href': '/code/source/sub/green/blue'})
