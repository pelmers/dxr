# Index a big idl file.

from nose import SkipTest
from nose.tools import eq_,ok_
from dxr.testing import DxrInstanceTestCase
import os

class IdlTests(DxrInstanceTestCase):
    """Test indexing of Rust projects"""

    def test_nothing(self):
        """A null test just to make the setup method run"""
