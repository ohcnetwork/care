import subprocess
import unittest

class TestTypstInstallation(unittest.TestCase):
    def test_typst_installed(self):
        try:
            subprocess.run(['typst', '--version'], check=True)
            typst_installed = True
        except subprocess.CalledProcessError:
            typst_installed = False

        self.assertTrue(typst_installed, "Typst is not installed or not accessible")
