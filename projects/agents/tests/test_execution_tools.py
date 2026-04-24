import os
import unittest
from pathlib import Path
from unittest.mock import patch


class TestExecutionToolPaths(unittest.TestCase):
    def test_validate_write_path_allows_writable_implementation_authority(self):
        from athanor_agents.tools.execution import _validate_write_path

        with patch.dict(os.environ, {"ATHANOR_IMPLEMENTATION_AUTHORITY": "/implementation"}, clear=False):
            resolved = _validate_write_path("/implementation/projects/dashboard/src/file.tsx")

        self.assertEqual(Path("/implementation/projects/dashboard/src/file.tsx").resolve(), resolved)

    def test_validate_write_path_rejects_workspace_even_when_marked_as_implementation_authority(self):
        from athanor_agents.tools.execution import _validate_write_path

        with patch.dict(os.environ, {"ATHANOR_IMPLEMENTATION_AUTHORITY": "/workspace"}, clear=False):
            with self.assertRaises(ValueError):
                _validate_write_path("/workspace/projects/dashboard/src/file.tsx")
