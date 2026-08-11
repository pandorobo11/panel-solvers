import ast
import unittest
from pathlib import Path

SRC_ROOT = Path(__file__).parents[2] / "src"


def imported_modules(path: Path) -> set[str]:
    relative = path.relative_to(SRC_ROOT).with_suffix("")
    module_parts = list(relative.parts)
    package_parts = module_parts if path.name == "__init__.py" else module_parts[:-1]
    imports: set[str] = set()

    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                keep = len(package_parts) - (node.level - 1)
                prefix = package_parts[: max(keep, 0)]
                target = ".".join([*prefix, *(node.module or "").split(".")])
            else:
                target = node.module or ""
            imports.add(target.rstrip("."))

    return imports


class DependencyBoundaryTests(unittest.TestCase):
    def assert_tree_avoids(self, tree: str, forbidden: tuple[str, ...]) -> None:
        violations: list[str] = []
        for path in sorted((SRC_ROOT / tree).rglob("*.py")):
            for imported in sorted(imported_modules(path)):
                if any(
                    imported == prefix or imported.startswith(f"{prefix}.")
                    for prefix in forbidden
                ):
                    violations.append(f"{path.relative_to(SRC_ROOT)} -> {imported}")
        self.assertEqual([], violations, "Forbidden dependencies:\n" + "\n".join(violations))

    def test_core_is_model_app_and_frontend_independent(self) -> None:
        self.assert_tree_avoids(
            "panelsolver/core",
            ("panelsolver.models", "panelsolver.app", "fmfsolver", "newtsolver"),
        )

    def test_models_are_app_and_frontend_independent(self) -> None:
        self.assert_tree_avoids(
            "panelsolver/models",
            ("panelsolver.app", "fmfsolver", "newtsolver"),
        )


if __name__ == "__main__":
    unittest.main()
