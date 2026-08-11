import importlib
import unittest


class PackageSkeletonTests(unittest.TestCase):
    def test_all_top_level_packages_are_importable(self) -> None:
        for package_name in ("panelsolver", "fmfsolver", "newtsolver"):
            with self.subTest(package_name=package_name):
                self.assertIsNotNone(importlib.import_module(package_name))

    def test_shared_layers_are_importable(self) -> None:
        for package_name in (
            "panelsolver.core",
            "panelsolver.models",
            "panelsolver.app",
        ):
            with self.subTest(package_name=package_name):
                self.assertIsNotNone(importlib.import_module(package_name))


if __name__ == "__main__":
    unittest.main()
