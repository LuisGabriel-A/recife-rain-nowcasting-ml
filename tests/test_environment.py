"""Explicit failures for incompatible environments, without installing packages."""

import unittest
from unittest.mock import patch

from src.check_environment import check_environment


class EnvironmentTests(unittest.TestCase):
    def test_runtime_versions_match_without_requiring_notebook_tools(self):
        self.assertEqual(check_environment()["python"], "3.14.6")
        self.assertEqual(check_environment()["packages"]["scikit-learn"], "1.9.1")
        self.assertNotIn("jupyter", check_environment()["packages"])

    def test_python_mismatch_is_reported(self):
        with patch("src.check_environment.platform.python_version", return_value="3.12.0"):
            with self.assertRaisesRegex(ValueError, "python: expected"):
                check_environment()

    def test_package_mismatch_is_reported(self):
        with patch("src.check_environment.version", return_value="0.0"):
            with self.assertRaisesRegex(ValueError, "scikit-learn: expected"):
                check_environment()


if __name__ == "__main__":
    unittest.main()
