import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tests.test_server as t
import unittest
suite = unittest.TestSuite()
suite.addTest(t.TestSanitizeFilename("test_strips_path_separators"))
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
