from unittest import TestCase

from nose.tools import eq_

from dxr.plugins.core import _find_iter, PathFilter


def list_eq(iterable, list_):
    """Reify an iterable into a list, and compare it to a second list."""
    eq_(list(iterable), list_)


def test_find_iter():
    list_eq(_find_iter('haystack', 'hay'), [0])
    list_eq(_find_iter('heyhey', 'hey'), [0, 3])
    list_eq(_find_iter('heyhey', ''), [])
    list_eq(_find_iter('hhhhh', 'hh'), [0, 2])  # Don't report overlaps.


class PathFilterTests(TestCase):
    """A few sanity checks for PathFilter

    More is covered in integration tests.

    """
    def filter_unicode(self):
        """Test that unicode(filter) works with different operators.
        """
        term = {'arg': "foo", 'name': 'path',
                'not': False, 'case_sensitive': False, 'qualified': False}
        a_filter = PathFilter(term, [])
        eq_(unicode(a_filter), u"path:foo")

        term['not'] = True
        eq_(unicode(a_filter), u"-path:foo")

        term['case_sensitive'] = True
        eq_(unicode(a_filter), u"-path:@foo")

        term['qualified'] = True
        term['not'] = False
        eq_(unicode(a_filter), u"+path:@foo")

        term['arg'] = 'Foo bar'
        eq_(unicode(a_filter), u'path:@"Foo bar"')

        term['arg'] = 'Foo "bar"'
        eq_(unicode(a_filter), u'path:@"Foo \\"bar\\"')

        accented_e = u'\u00E9'
        term['arg'] = u'readm' + accented_e
        eq_(unicode(a_filter), u'path:@readm' + accented_e)

    def test_bigrams_and_wildcards(self):
        """Make sure the right query shape is constructed and strings shorter
        than 3 chars are stripped out.

        """
        eq_(PathFilter({'name': 'path',
                        'arg': u'*hi*hork*.cp?',
                        'qualified': False,
                        'not': False,
                        'case_sensitive': False}, []).filter(),
            {
                'and': [
                    {
                        'and': [
                            {
                                'query': {
                                    'match_phrase': {
                                        'path.trigrams_lower': 'hork'
                                    }
                                }
                            },
                            {
                                'query': {
                                    'match_phrase': {
                                        'path.trigrams_lower': '.cp'
                                    }
                                }
                            }
                        ]
                    },
                    {
                        'script': {
                            'lang': 'js',
                            'script': '(new RegExp(pattern, flags)).test(doc["path"][0])',
                            'params': {
                                'pattern': r'.*hi.*hork.*\.cp.',
                                'flags': 'i'
                            }
                        }
                    }
                ]
            })

    def test_classes_and_capitals(self):
        """Make sure glob char classes aren't totally bungled and
        case-sensitivity is observed.

        They should be stripped out for now, but, when we implement the Cox
        method, they should be harnessed as prefixes and suffixes if next to
        something else.

        """
        eq_(PathFilter({'name': 'path',
                        'arg': u'fooba[rz]',
                        'qualified': False,
                        'not': False,
                        'case_sensitive': True}, []).filter(),
            {
                'and': [
                    {
                        'query': {
                            'match_phrase': {
                                'path.trigrams': 'fooba'
                            }
                        }
                    },
                    {
                        'script': {
                            'lang': 'js',
                            'script': '(new RegExp(pattern, flags)).test(doc["path"][0])',
                            'params': {
                                'pattern': r'fooba[rz]',
                                'flags': ''
                            }
                        }
                    }
                ]
            })
