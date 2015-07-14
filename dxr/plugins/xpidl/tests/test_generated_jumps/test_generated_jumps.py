from dxr.testing import DxrInstanceTestCase

class IdlJumpTest(DxrInstanceTestCase):
    """Test that `generated` links jump to the right line/file."""

    def test_nothing(self):
        """A null test just to make the setup method run"""
