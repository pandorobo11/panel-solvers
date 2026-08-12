import unittest

import numpy as np

from fmfsolver.legacy_adapter import project_case
from panelsolver.app import LegacyPanelSnapshot, LegacyRunContext, adapt_legacy_panels
from panelsolver.core import CommonCasePayload, ContractValueError, ModelCasePayload


def common_case() -> CommonCasePayload:
    return CommonCasePayload(
        case_id="adapted",
        Aref_m2=1,
        moment_reference_stl_m=[0, 0, 0],
        Lref_Cl_m=1,
        Lref_Cm_m=1,
        Lref_Cn_m=1,
        alpha_t_deg=10,
        beta_t_deg=-5,
    )


def snapshot() -> LegacyPanelSnapshot:
    return LegacyPanelSnapshot(
        vertices_stl_m=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float),
        faces=np.array([[0, 1, 2]], dtype=np.int64),
        centers_stl_m=[[1 / 3, 1 / 3, 0]],
        normals_out_stl=[[0, 0, 1]],
        areas_m2=[0.5],
        component_ids=[0],
        component_sources=("plate.stl",),
        shielded=[False],
        traction_coeff_stl=[[2, 0, 0]],
        cell_scalars={"Cp_n": [0], "theta_deg": [90]},
    )


class LegacyAdapterTests(unittest.TestCase):
    def test_adapts_computed_panels_and_routes_all_phase3_projections(self) -> None:
        case = common_case()
        raw = snapshot()
        adapted = adapt_legacy_panels(case, raw)
        expected_velocity = np.array(
            [1.0, -np.tan(np.deg2rad(-5)), np.tan(np.deg2rad(10))]
        )
        expected_velocity /= np.linalg.norm(expected_velocity)
        np.testing.assert_allclose(
            adapted.flow_state.velocity_hat_stl,
            expected_velocity,
        )

        bundle = project_case(
            case=case,
            model_case=ModelCasePayload("fmfsolver"),
            snapshot=raw,
            input_row={"case_id": "adapted"},
            run=LegacyRunContext(
                attitude_input_used="beta_tan",
                case_signature="signature",
                ray_backend_used="rtree",
                solver_version="1.0",
                run_started_at_utc="start",
                run_finished_at_utc="finish",
                run_elapsed_s=1.0,
                vtp_path="adapted.vtp",
                npz_path="adapted.npz",
            ),
            mode="A",
            speed_ratio=5.0,
            translational_temperature_k=300.0,
            wall_temperature_k=300.0,
        )

        self.assertIs(bundle.mesh.geometry, bundle.results.geometry)
        self.assertEqual("total", bundle.csv.rows[0]["scope"])
        self.assertEqual(5.0, float(bundle.npz.arrays["S"]))
        self.assertEqual("adapted", bundle.vtp.field_data["case_id"][0])
        self.assertFalse(bundle.results.local_loads.traction_coeff_stl.flags.writeable)

    def test_contract_copy_and_component_alignment_remain_enforced(self) -> None:
        case = common_case()
        raw = snapshot()
        adapted = adapt_legacy_panels(case, raw)
        raw.vertices_stl_m[0, 0] = 99
        self.assertEqual(0, adapted.mesh.vertices_stl_m[0, 0])

        raw.component_sources = ("plate.stl", "unexpected.stl")
        with self.assertRaises(ContractValueError):
            adapt_legacy_panels(case, raw)


if __name__ == "__main__":
    unittest.main()
