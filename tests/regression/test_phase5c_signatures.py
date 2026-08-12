from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from panelsolver.core import (
    CommonCasePayload,
    ModelCasePayload,
    ResolvedShieldingConfig,
    build_case_signature,
    clear_mesh_cache,
    load_panel_mesh,
)
from panelsolver.models import HypersonicModel, SentmanModel

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "phase1"
GOLDEN_ROOT = FIXTURE_ROOT / "golden"


def _array(case: dict, name: str) -> np.ndarray:
    record = case["npz"]["arrays"][name]
    return np.asarray(record["values"]).reshape(record["shape"])


class Phase5cSignatureGoldenTests(unittest.TestCase):
    def test_all_phase1_cases_have_isolated_deterministic_signatures(self) -> None:
        signatures: set[str] = set()
        paths = sorted(GOLDEN_ROOT.glob("*/*.json"))
        paths = [path for path in paths if path.name != "contracts.json"]
        self.assertEqual(15, len(paths))

        for path in paths:
            with self.subTest(solver=path.parent.name, case_id=path.stem):
                golden = json.loads(path.read_text(encoding="utf-8"))
                normalized = golden["normalized_input"]
                source_names = [
                    Path(value).name
                    for value in str(normalized["stl_path"]).split(";")
                ]
                clear_mesh_cache()
                loaded = load_panel_mesh(
                    [FIXTURE_ROOT / "inputs" / "stl" / name for name in source_names],
                    normalized["stl_scale_m_per_unit"],
                )
                common_case = CommonCasePayload(
                    case_id=normalized["case_id"],
                    Aref_m2=normalized["Aref_m2"],
                    moment_reference_stl_m=[
                        normalized["ref_x_m"],
                        normalized["ref_y_m"],
                        normalized["ref_z_m"],
                    ],
                    Lref_Cl_m=normalized["Lref_Cl_m"],
                    Lref_Cm_m=normalized["Lref_Cm_m"],
                    Lref_Cn_m=normalized["Lref_Cn_m"],
                    alpha_t_deg=float(_array(golden, "alpha_t_deg_resolved")),
                    beta_t_deg=float(_array(golden, "beta_t_deg_resolved")),
                )
                if path.parent.name == "fmfsolver":
                    model = SentmanModel()
                else:
                    model = HypersonicModel()
                model_case = ModelCasePayload(model.model_id, normalized)
                effective_backend = golden["provenance"]["effective_backend"]
                shielding_enabled = bool(normalized["shielding_on"])
                shielding = ResolvedShieldingConfig(
                    enabled=shielding_enabled,
                    requested_backend=normalized["ray_backend"],
                    effective_backend=effective_backend,
                    batch_size=(64 if effective_backend == "embree" else 8)
                    if shielding_enabled
                    else 0,
                    cache_max=1 if shielding_enabled else 0,
                )
                signature = build_case_signature(
                    geometry_fingerprint=loaded.geometry_fingerprint,
                    common_case=common_case,
                    model_id=model.model_id,
                    model_algorithm_version=model.algorithm_version,
                    model_case_payload=model.signature_payload(model_case),
                    shielding_config=shielding,
                )
                repeated = build_case_signature(
                    geometry_fingerprint=loaded.geometry_fingerprint,
                    common_case=common_case,
                    model_id=model.model_id,
                    model_algorithm_version=model.algorithm_version,
                    model_case_payload=model.signature_payload(model_case),
                    shielding_config=shielding,
                )

                self.assertRegex(signature.digest, r"^[0-9a-f]{64}$")
                self.assertEqual(signature.digest, repeated.digest)
                self.assertNotIn(signature.digest, signatures)
                signatures.add(signature.digest)

        self.assertEqual(15, len(signatures))


if __name__ == "__main__":
    unittest.main()
