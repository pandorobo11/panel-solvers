from __future__ import annotations

import math
import unittest

import numpy as np

from panelsolver.core import (
    CommonCasePayload,
    ModelCasePayload,
    PanelFlowState,
    PanelGeometry,
    PanelLoadModel,
    integrate_panel_loads,
)
from panelsolver.models import (
    ModelRegistry,
    SentmanCaseError,
    SentmanModel,
    sample_at_altitude_km,
)


def _geometry(normals: np.ndarray) -> PanelGeometry:
    n_faces = normals.shape[0]
    return PanelGeometry(
        centers_stl_m=np.zeros((n_faces, 3)),
        normals_out_stl=normals,
        areas_m2=np.ones(n_faces),
        component_ids=np.zeros(n_faces, dtype=np.int64),
    )


def _mode_a_case(**updates: object) -> ModelCasePayload:
    payload: dict[str, object] = {
        "S": 5.0,
        "Ti_K": 300.0,
        "Mach": None,
        "Altitude_km": None,
        "Tw_K": 450.0,
    }
    payload.update(updates)
    return ModelCasePayload("sentman", payload)


def _flat_plate_reference(
    speed_ratio: float,
    alpha_rad: float,
    wall_to_translation: float,
) -> tuple[float, float]:
    sin_alpha = math.sin(alpha_rad)
    cos_alpha = math.cos(alpha_rad)
    projected_speed = speed_ratio * cos_alpha
    erf_term = 1.0 + math.erf(projected_speed)
    exponential = math.exp(-(projected_speed * projected_speed))
    inverse_s = 1.0 / speed_ratio
    inverse_s_squared = inverse_s * inverse_s
    inverse_s_sqrt_pi = inverse_s / math.sqrt(math.pi)
    normal = sin_alpha * cos_alpha * erf_term
    normal += sin_alpha * inverse_s_sqrt_pi * exponential
    axial_incident = (cos_alpha * cos_alpha + 0.5 * inverse_s_squared)
    axial_incident *= erf_term
    axial_incident += cos_alpha * inverse_s_sqrt_pi * exponential
    axial_reflected = math.sqrt(wall_to_translation) * (
        (math.sqrt(math.pi) * 0.5 * inverse_s) * cos_alpha * erf_term
        + 0.5 * inverse_s_squared * exponential
    )
    return normal, axial_incident + axial_reflected


class SentmanModelTests(unittest.TestCase):
    def test_model_implements_protocol_and_preserves_tangential_load(self) -> None:
        model = SentmanModel()
        self.assertIsInstance(model, PanelLoadModel)
        alpha_rad = math.radians(30.0)
        velocity = np.array([math.cos(alpha_rad), 0.0, math.sin(alpha_rad)])
        geometry = _geometry(np.array([[-1.0, 0.0, 0.0]]))
        flow = PanelFlowState(velocity, np.array([False]))

        loads = ModelRegistry((model,)).evaluate(
            geometry,
            flow,
            _mode_a_case(S=10.0, Ti_K=1000.0, Tw_K=1000.0),
        )

        self.assertNotEqual(0.0, loads.traction_coeff_stl[0, 2])
        self.assertTrue(
            np.any(
                np.cross(loads.traction_coeff_stl, geometry.normals_out_stl)
                != 0.0
            )
        )

    def test_flat_plate_matches_independent_sentman_reference(self) -> None:
        model = SentmanModel()
        geometry = _geometry(np.array([[-1.0, 0.0, 0.0]]))
        for speed_ratio in (1.0, 10.0, 100.0):
            for alpha_deg in (0.0, 10.0, 30.0, 60.0):
                alpha_rad = math.radians(alpha_deg)
                flow = PanelFlowState(
                    np.array(
                        [math.cos(alpha_rad), 0.0, math.sin(alpha_rad)]
                    ),
                    np.array([False]),
                )
                loads = model.evaluate(
                    geometry,
                    flow,
                    _mode_a_case(
                        S=speed_ratio,
                        Ti_K=1000.0,
                        Tw_K=1000.0,
                    ),
                )
                common_case = CommonCasePayload(
                    case_id="flat-plate",
                    Aref_m2=1.0,
                    moment_reference_stl_m=np.zeros(3),
                    Lref_Cl_m=1.0,
                    Lref_Cm_m=1.0,
                    Lref_Cn_m=1.0,
                    alpha_t_deg=alpha_deg,
                    beta_t_deg=0.0,
                )
                integrated = integrate_panel_loads(geometry, loads, common_case)
                expected_cn, expected_ca = _flat_plate_reference(
                    speed_ratio,
                    alpha_rad,
                    1.0,
                )
                with self.subTest(S=speed_ratio, alpha_deg=alpha_deg):
                    self.assertAlmostEqual(integrated.total.CN, expected_cn, delta=1e-10)
                    self.assertAlmostEqual(integrated.total.CA, expected_ca, delta=1e-10)

    def test_shielded_faces_are_exact_zero_but_keep_geometry_scalar(self) -> None:
        geometry = _geometry(
            np.array([[-1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]])
        )
        flow = PanelFlowState(
            np.array([1.0, 0.0, 0.0]),
            np.array([False, True]),
        )
        loads = SentmanModel().evaluate(geometry, flow, _mode_a_case())

        np.testing.assert_array_equal(
            loads.traction_coeff_stl[1],
            np.zeros(3),
        )
        self.assertEqual(0.0, loads.cell_scalars["Cp_n"][1])
        self.assertEqual(180.0, loads.cell_scalars["theta_deg"][1])

    def test_mode_b_resolves_the_pinned_atmosphere_values(self) -> None:
        case = ModelCasePayload(
            "sentman",
            {
                "S": None,
                "Ti_K": None,
                "Mach": 25.0,
                "Altitude_km": 100.0,
                "Tw_K": 450.0,
            },
        )
        atmosphere = sample_at_altitude_km(100.0)
        self.assertEqual(
            {"T_K": 195.081, "c_ms": 280.0, "Vmean_ms": 381.36},
            atmosphere,
        )
        loads = SentmanModel().evaluate(
            _geometry(np.array([[-1.0, 0.0, 0.0]])),
            PanelFlowState(
                np.array([1.0, 0.0, 0.0]),
                np.array([False]),
            ),
            case,
        )
        self.assertEqual("B", loads.metadata["mode"])
        self.assertEqual(195.081, loads.metadata["Ti_K"])
        self.assertAlmostEqual(20.71180556342718, loads.metadata["S"], places=14)

    def test_signature_payload_preserves_raw_mode_fields(self) -> None:
        model = SentmanModel()
        case = ModelCasePayload(
            "sentman",
            {
                "S": None,
                "Ti_K": None,
                "Mach": 25,
                "Altitude_km": 100,
                "Tw_K": 450,
                "unrelated": "not-signed-by-model",
            },
        )
        expected = {
            "mode": "B",
            "S": None,
            "Ti_K": None,
            "Mach": 25.0,
            "Altitude_km": 100.0,
            "Tw_K": 450.0,
        }
        first = model.signature_payload(case)
        self.assertEqual(expected, first)
        first["Mach"] = 99.0
        self.assertEqual(expected, model.signature_payload(case))

    def test_case_validation_keeps_modes_separate_and_physical(self) -> None:
        invalid = (
            _mode_a_case(Ti_K=None),
            _mode_a_case(Mach=5.0, Altitude_km=100.0),
            _mode_a_case(S=0.0),
            _mode_a_case(Tw_K="not-a-number"),
            ModelCasePayload(
                "sentman",
                {
                    "S": None,
                    "Ti_K": None,
                    "Mach": 5.0,
                    "Altitude_km": 1001.0,
                    "Tw_K": 300.0,
                },
            ),
        )
        for case in invalid:
            with self.subTest(payload=dict(case.payload)), self.assertRaises(
                SentmanCaseError
            ):
                SentmanModel().validate_case(case)

        SentmanModel().validate_case(
            ModelCasePayload(
                "sentman",
                {
                    "S": None,
                    "Ti_K": None,
                    "Mach": 5.0,
                    "Altitude_km": 0.0,
                    "Tw_K": 300.0,
                },
            )
        )


if __name__ == "__main__":
    unittest.main()
