from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from panelsolver.core import MeshComponent, PanelGeometry, PanelMesh

GOLDEN_ROOT = Path(__file__).parents[1] / "fixtures" / "phase1" / "golden"


def _array(case: dict, name: str) -> np.ndarray:
    record = case["npz"]["arrays"][name]
    return np.asarray(record["values"]).reshape(record["shape"])


class Phase3MeshGoldenTests(unittest.TestCase):
    def test_all_phase1_topology_is_representable_without_normalization(self) -> None:
        paths = sorted(GOLDEN_ROOT.glob("*/*.json"))
        paths = [path for path in paths if path.name != "contracts.json"]
        self.assertEqual(15, len(paths))

        for path in paths:
            with self.subTest(solver=path.parent.name, case_id=path.stem):
                case = json.loads(path.read_text(encoding="utf-8"))
                geometry = PanelGeometry(
                    centers_stl_m=_array(case, "centers_stl_m"),
                    normals_out_stl=_array(case, "normals_out_stl"),
                    areas_m2=_array(case, "areas_m2"),
                    component_ids=_array(case, "face_stl_index"),
                )
                sources = _array(case, "stl_paths").tolist()
                components = [
                    MeshComponent(component_id, source)
                    for component_id, source in enumerate(sources)
                ]
                mesh = PanelMesh(
                    vertices_stl_m=_array(case, "vertices"),
                    faces=_array(case, "faces"),
                    geometry=geometry,
                    components=components,
                )

                np.testing.assert_array_equal(
                    mesh.vertices_stl_m,
                    _array(case, "vertices"),
                )
                np.testing.assert_array_equal(mesh.faces, _array(case, "faces"))
                np.testing.assert_array_equal(
                    mesh.face_component_ids,
                    _array(case, "face_stl_index"),
                )
                self.assertEqual(sources, [item.source for item in mesh.components])


if __name__ == "__main__":
    unittest.main()
