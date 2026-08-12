from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from panelsolver.app import default_model_registry, request_from_registry
from panelsolver.core import (
    CaseExecutionRequest,
    CommonCasePayload,
    ExecutionError,
    ExecutionModelError,
    LocalLoads,
    ModelCasePayload,
    ResultCache,
    ShieldingConfig,
    execute_case,
)

from .test_mesh_loading import FIXTURE_STL


class _CountingModel:
    model_id = "synthetic"
    algorithm_version = "synthetic-v1"

    def __init__(self) -> None:
        self.evaluate_calls = 0

    def validate_case(self, case: ModelCasePayload) -> None:
        if case.payload.get("fail_validation"):
            raise RuntimeError("model validation failed")

    def signature_payload(self, case: ModelCasePayload):
        return dict(case.payload)

    def evaluate(self, geometry, flow_state, case):
        self.evaluate_calls += 1
        traction = np.ones((geometry.n_faces, 3), dtype=np.float64)
        traction[flow_state.shielded] = 0.0
        return LocalLoads(traction)


class _WrongOutputModel(_CountingModel):
    def evaluate(self, geometry, flow_state, case):
        return object()


class _FlowEchoModel(_CountingModel):
    def evaluate(self, geometry, flow_state, case):
        self.evaluate_calls += 1
        traction = np.tile(flow_state.velocity_hat_stl, (geometry.n_faces, 1))
        traction[flow_state.shielded] = 0.0
        flow_y = np.full(geometry.n_faces, flow_state.velocity_hat_stl[1])
        return LocalLoads(
            traction,
            {"flow_y": flow_y},
            {"flow_y": float(flow_state.velocity_hat_stl[1])},
        )


def _common_case(**updates) -> CommonCasePayload:
    values = {
        "case_id": "synthetic-case",
        "Aref_m2": 1.0,
        "moment_reference_stl_m": [0.0, 0.0, 0.0],
        "Lref_Cl_m": 1.0,
        "Lref_Cm_m": 1.0,
        "Lref_Cn_m": 1.0,
        "alpha_t_deg": 0.0,
        "beta_t_deg": 0.0,
    }
    values.update(updates)
    return CommonCasePayload(**values)


def _request(model=None, **updates) -> CaseExecutionRequest:
    model = _CountingModel() if model is None else model
    values = {
        "model": model,
        "common_case": _common_case(),
        "model_case": ModelCasePayload("synthetic", {"value": 1}),
        "stl_paths": [FIXTURE_STL / "plate.stl"],
        "scale_m_per_unit": 1.0,
        "velocity_hat_stl": np.array([1.0, 0.0, 0.0]),
        "shielding": ShieldingConfig(enabled=False),
    }
    values.update(updates)
    return CaseExecutionRequest(**values)


def _assert_array_semantics_equal(
    test_case: unittest.TestCase,
    actual: np.ndarray,
    expected: np.ndarray,
) -> None:
    test_case.assertEqual(expected.dtype, actual.dtype)
    test_case.assertEqual(expected.shape, actual.shape)
    np.testing.assert_array_equal(actual, expected)


def _assert_integrated_semantics_equal(test_case, actual, expected) -> None:
    for name in (
        "force_coeff_stl",
        "force_coeff_body",
        "force_coeff_stability",
        "moment_area_coeff_body_m",
        "moment_coeff_body",
    ):
        _assert_array_semantics_equal(
            test_case,
            getattr(actual, name),
            getattr(expected, name),
        )


def _assert_result_semantics_equal(test_case, actual, expected) -> None:
    test_case.assertEqual(actual.case, expected.case)
    test_case.assertEqual(actual.model_case, expected.model_case)
    for name in ("centers_stl_m", "normals_out_stl", "areas_m2", "component_ids"):
        _assert_array_semantics_equal(
            test_case,
            getattr(actual.geometry, name),
            getattr(expected.geometry, name),
        )
    _assert_array_semantics_equal(
        test_case,
        actual.flow_state.velocity_hat_stl,
        expected.flow_state.velocity_hat_stl,
    )
    _assert_array_semantics_equal(
        test_case,
        actual.flow_state.shielded,
        expected.flow_state.shielded,
    )
    _assert_array_semantics_equal(
        test_case,
        actual.local_loads.traction_coeff_stl,
        expected.local_loads.traction_coeff_stl,
    )
    test_case.assertEqual(
        set(actual.local_loads.cell_scalars),
        set(expected.local_loads.cell_scalars),
    )
    for name in expected.local_loads.cell_scalars:
        _assert_array_semantics_equal(
            test_case,
            actual.local_loads.cell_scalars[name],
            expected.local_loads.cell_scalars[name],
        )
    test_case.assertEqual(actual.local_loads.metadata, expected.local_loads.metadata)
    _assert_integrated_semantics_equal(test_case, actual.total, expected.total)
    test_case.assertEqual(len(actual.components), len(expected.components))
    for actual_component, expected_component in zip(
        actual.components,
        expected.components,
        strict=True,
    ):
        test_case.assertEqual(
            (
                actual_component.component_id,
                actual_component.face_count,
                actual_component.shielded_face_count,
                actual_component.metadata,
            ),
            (
                expected_component.component_id,
                expected_component.face_count,
                expected_component.shielded_face_count,
                expected_component.metadata,
            ),
        )
        _assert_integrated_semantics_equal(
            test_case,
            actual_component.integrated,
            expected_component.integrated,
        )
    test_case.assertEqual(actual.metadata, expected.metadata)


class ExecutionTests(unittest.TestCase):
    def test_one_engine_evaluates_and_integrates_a_protocol_model(self) -> None:
        model = _CountingModel()
        result = execute_case(_request(model))

        self.assertEqual(1, model.evaluate_calls)
        self.assertFalse(result.cache_hit)
        self.assertEqual("not_used", result.shielding.config.effective_backend)
        self.assertEqual("synthetic", result.results.model_id)
        self.assertEqual(result.signature.digest, result.results.metadata["case_signature"])
        self.assertEqual(
            result.mesh.n_faces,
            result.results.local_loads.traction_coeff_stl.shape[0],
        )

    def test_result_cache_skips_model_but_keeps_current_source_metadata(self) -> None:
        model = _CountingModel()
        cache = ResultCache(max_entries=1)
        first = execute_case(_request(model), result_cache=cache)

        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "renamed.stl"
            copied.write_bytes((FIXTURE_STL / "plate.stl").read_bytes())
            second = execute_case(
                _request(model, stl_paths=[copied]),
                result_cache=cache,
            )

        self.assertFalse(first.cache_hit)
        self.assertTrue(second.cache_hit)
        self.assertEqual(1, model.evaluate_calls)
        self.assertNotEqual(
            first.mesh.components[0].source,
            second.mesh.components[0].source,
        )
        self.assertEqual(first.signature.digest, second.signature.digest)

    def test_result_cache_isolates_every_accepted_exact_flow_direction(self) -> None:
        model = _FlowEchoModel()
        cache = ResultCache(max_entries=3)
        request_a = _request(
            model,
            velocity_hat_stl=np.array([1.0, 0.0, 0.0]),
        )
        request_b = _request(
            model,
            velocity_hat_stl=np.array([1.0, 1.0e-12, 0.0]),
        )
        next_float = np.nextafter(1.0, 2.0)
        request_c = _request(
            model,
            velocity_hat_stl=np.array([next_float, 0.0, 0.0]),
        )

        first_a = execute_case(request_a, result_cache=cache)
        first_b = execute_case(request_b, result_cache=cache)
        first_c = execute_case(request_c, result_cache=cache)
        cached_a = execute_case(request_a, result_cache=cache)
        cached_b = execute_case(request_b, result_cache=cache)
        cached_c = execute_case(request_c, result_cache=cache)
        fresh_b = execute_case(request_b)

        self.assertEqual(first_a.signature.digest, first_b.signature.digest)
        self.assertEqual(first_a.signature.digest, first_c.signature.digest)
        self.assertEqual(
            [False, False, False, True, True, True],
            [
                first_a.cache_hit,
                first_b.cache_hit,
                first_c.cache_hit,
                cached_a.cache_hit,
                cached_b.cache_hit,
                cached_c.cache_hit,
            ],
        )
        self.assertEqual(4, model.evaluate_calls)
        self.assertEqual(
            (3, 3, 3),
            (
                cache.stats().entries,
                cache.stats().hits,
                cache.stats().misses,
            ),
        )
        np.testing.assert_array_equal(
            cached_b.results.local_loads.traction_coeff_stl[:, 1],
            np.full(cached_b.mesh.n_faces, 1.0e-12),
        )
        np.testing.assert_array_equal(
            cached_c.results.local_loads.traction_coeff_stl[:, 0],
            np.full(cached_c.mesh.n_faces, next_float),
        )
        _assert_result_semantics_equal(self, cached_b.results, fresh_b.results)
        _assert_result_semantics_equal(self, cached_c.results, first_c.results)

    def test_execute_case_owns_private_result_cache_entries(self) -> None:
        model = _CountingModel()
        request = _request(model)
        baseline = execute_case(request)

        generic_cache = ResultCache(max_entries=1)
        generic_cache.put(baseline.signature, baseline.results)
        self.assertIsNotNone(generic_cache.get(baseline.signature))

        preseeded_cache = ResultCache(max_entries=2)
        preseeded_cache.put(baseline.signature, baseline.results)
        preseeded = execute_case(request, result_cache=preseeded_cache)
        self.assertFalse(preseeded.cache_hit)
        self.assertEqual(2, preseeded_cache.stats().entries)

        engine_cache = ResultCache(max_entries=1)
        first = execute_case(request, result_cache=engine_cache)
        self.assertFalse(first.cache_hit)
        self.assertIsNone(engine_cache.get(first.signature))
        repeated = execute_case(request, result_cache=engine_cache)
        self.assertTrue(repeated.cache_hit)
        self.assertEqual(3, model.evaluate_calls)

    def test_backend_request_isolates_cache_even_when_shielding_is_off(self) -> None:
        model = _CountingModel()
        cache = ResultCache(max_entries=2)
        first = execute_case(
            _request(
                model,
                shielding=ShieldingConfig(enabled=False, ray_backend="rtree"),
            ),
            result_cache=cache,
        )
        second = execute_case(
            _request(
                model,
                shielding=ShieldingConfig(enabled=False, ray_backend="embree"),
            ),
            result_cache=cache,
        )
        self.assertNotEqual(first.signature.digest, second.signature.digest)
        self.assertEqual(2, model.evaluate_calls)

    def test_model_failures_propagate_and_invalid_outputs_are_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "model validation failed"):
            execute_case(
                _request(
                    model_case=ModelCasePayload(
                        "synthetic", {"fail_validation": True}
                    )
                )
            )
        with self.assertRaisesRegex(ExecutionModelError, "LocalLoads"):
            execute_case(_request(_WrongOutputModel()))

    def test_request_rejects_mismatched_identity_and_flow_direction(self) -> None:
        with self.assertRaisesRegex(ExecutionModelError, "does not match"):
            _request(model_case=ModelCasePayload("other", {}))
        with self.assertRaisesRegex(ExecutionError, "tangent angles"):
            _request(velocity_hat_stl=np.array([0.0, 1.0, 0.0]))
        accepted = _request(
            velocity_hat_stl=np.array([1.0, 1.0e-12, 0.0]),
        )
        np.testing.assert_array_equal(
            accepted.velocity_hat_stl,
            np.array([1.0, 1.0e-12, 0.0]),
        )
        with self.assertRaisesRegex(ExecutionError, "tangent angles"):
            _request(velocity_hat_stl=np.array([1.0, 2.0e-12, 0.0]))

    def test_app_assembles_both_models_without_core_branching(self) -> None:
        registry = default_model_registry()
        self.assertEqual(("sentman", "hypersonic"), registry.model_ids)
        model_case = ModelCasePayload(
            "sentman",
            {"S": 5.0, "Ti_K": 300.0, "Tw_K": 400.0},
        )
        request = request_from_registry(
            registry,
            common_case=_common_case(),
            model_case=model_case,
            stl_paths=[FIXTURE_STL / "plate.stl"],
            scale_m_per_unit=1.0,
            velocity_hat_stl=np.array([1.0, 0.0, 0.0]),
            shielding=ShieldingConfig(enabled=False),
        )
        self.assertEqual("sentman", request.model.model_id)


if __name__ == "__main__":
    unittest.main()
