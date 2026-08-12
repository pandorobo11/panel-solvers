from __future__ import annotations

import importlib
import inspect
import math
import pickle
import unittest

import numpy as np
import pandas as pd

EXPECTED_SIGNATURES = {
    "fmfsolver.core.sentman_core": {
        "sentman_dC_dA_vector": (
            "(Vhat: 'np.ndarray', n_out: 'np.ndarray', S: 'float', Ti: 'float', "
            "Tw: 'float', Aref: 'float', shielded: 'bool' = False) -> 'np.ndarray'"
        ),
        "sentman_dC_dA_vectors": (
            "(Vhat: 'np.ndarray', n_out: 'np.ndarray', S: 'float', Ti: 'float', "
            "Tw: 'float', Aref: 'float', shielded: 'np.ndarray | bool' = False) "
            "-> 'np.ndarray'"
        ),
        "stl_to_body": "(v_stl: 'np.ndarray') -> 'np.ndarray'",
        "resolve_attitude_to_vhat": (
            "(alpha_deg: 'float', beta_deg: 'float', "
            "attitude_input: 'str | None' = None) -> "
            "'tuple[np.ndarray, float, float, str]'"
        ),
        "rot_y": "(alpha_rad: 'float') -> 'np.ndarray'",
    },
    "fmfsolver.physics.us1976": {
        "load_us1976_tables": "() -> 'tuple[pd.DataFrame, pd.DataFrame]'",
        "altitude_range_km": "() -> 'tuple[float, float]'",
        "sample_at_altitude_km": "(alt_km: 'float') -> 'dict'",
        "mean_to_most_probable_speed": "(v_mean: 'float') -> 'float'",
    },
    "newtsolver.core.attitude": {
        "_resolve_attitude_mode": "(attitude_input: 'str | None') -> 'str'",
        "stl_to_body": "(v_stl: 'np.ndarray') -> 'np.ndarray'",
        "resolve_attitude_to_vhat": (
            "(alpha_deg: 'float', beta_deg: 'float', "
            "attitude_input: 'str | None' = None) -> "
            "'tuple[np.ndarray, float, float, str]'"
        ),
        "rot_y": "(alpha_rad: 'float') -> 'np.ndarray'",
    },
    "newtsolver.core.panel_forces": {
        "panel_force_density": (
            "(Vhat: 'np.ndarray', n_out: 'np.ndarray', Aref: 'float', "
            "shielded: 'np.ndarray | bool' = False, "
            "face_stl_index: 'np.ndarray | None' = None, "
            "cp_max: 'float' = 2.0, windward_eq: 'str' = 'newtonian', "
            "leeward_eq: 'str' = 'shield', "
            "windward_eq_by_component: "
            "'list[str] | tuple[str, ...] | None' = None, "
            "leeward_eq_by_component: "
            "'list[str] | tuple[str, ...] | None' = None, "
            "Mach: 'float | None' = None, gamma: 'float | None' = None) "
            "-> 'np.ndarray'"
        ),
    },
    "newtsolver.surface_equations": {
        "normalize_windward_equation": "(value: 'str | None') -> 'str'",
        "normalize_leeward_equation": "(value: 'str | None') -> 'str'",
        "split_semicolon_tokens": "(value: 'str | None') -> 'list[str]'",
        "count_semicolon_entries": "(value: 'str | None') -> 'int'",
        "expand_equations_for_components": (
            "(raw_value: 'str | None', *, default_value: 'str', resolver, "
            "n_components: 'int', field_name: 'str') -> 'tuple[list[str], str]'"
        ),
    },
    "newtsolver.core.pressure_models.modified_newtonian": {
        "modified_newtonian_cp_max": "(Mach: 'float', gamma: 'float') -> 'float'",
    },
    "newtsolver.core.pressure_models.prandtl_meyer": {
        "_prandtl_meyer_nu": (
            "(Mach: 'np.ndarray', gamma: 'float') -> 'np.ndarray'"
        ),
        "_inverse_prandtl_meyer": (
            "(nu_target: 'np.ndarray', gamma: 'float') -> 'np.ndarray'"
        ),
        "prandtl_meyer_pressure_coefficient": (
            "(Mach: 'float', gamma: 'float', deltar: 'float | np.ndarray') "
            "-> 'np.ndarray'"
        ),
    },
    "newtsolver.core.pressure_models.tangent_wedge": {
        "_oblique_theta_from_beta": (
            "(Mach: 'float', gamma: 'float', beta: 'float') -> 'float'"
        ),
        "_tangent_wedge_detach_limit": (
            "(Mach: 'float', gamma: 'float') -> 'tuple[float, float]'"
        ),
        "_weak_oblique_shock_beta": (
            "(Mach: 'float', gamma: 'float', theta: 'np.ndarray') -> 'np.ndarray'"
        ),
        "tangent_wedge_pressure_coefficient": (
            "(Mach: 'float', gamma: 'float', deltar: 'float | np.ndarray', *, "
            "cp_cap: 'float | None' = None) -> 'np.ndarray'"
        ),
    },
    "newtsolver.core.pressure_models.tangent_cone": {
        "_tangent_cone_detach_limit": (
            "(Mach: 'float', gamma: 'float') -> 'tuple[float, float]'"
        ),
        "tangent_cone_pressure_coefficient": (
            "(Mach: 'float', gamma: 'float', deltar: 'float | np.ndarray', *, "
            "cp_cap: 'float | None' = None) -> 'np.ndarray'"
        ),
    },
}


class Phase8PublicCallableIdentityTests(unittest.TestCase):
    def test_exact_signatures_owner_identity_and_pickle_round_trip(self) -> None:
        for module_name, functions in EXPECTED_SIGNATURES.items():
            module = importlib.import_module(module_name)
            for name, signature in functions.items():
                with self.subTest(callable=f"{module_name}.{name}"):
                    function = getattr(module, name)
                    self.assertEqual(signature, str(inspect.signature(function)))
                    self.assertEqual(name, function.__name__)
                    self.assertEqual(name, function.__qualname__)
                    self.assertEqual(module_name, function.__module__)
                    self.assertIs(function, pickle.loads(pickle.dumps(function)))

    def test_newtsolver_reexports_reuse_the_owner_objects(self) -> None:
        attitude = importlib.import_module("newtsolver.core.attitude")
        panel_forces = importlib.import_module("newtsolver.core.panel_forces")
        selectors = importlib.import_module("newtsolver.surface_equations")
        panel_core = importlib.import_module("newtsolver.core.panel_core")
        pressure_package = importlib.import_module("newtsolver.core.pressure_models")

        owner_bindings = {
            "_resolve_attitude_mode": attitude,
            "stl_to_body": attitude,
            "panel_force_density": panel_forces,
            "normalize_windward_equation": selectors,
            "normalize_leeward_equation": selectors,
        }
        for name, owner in owner_bindings.items():
            with self.subTest(reexport=name):
                self.assertIs(getattr(owner, name), getattr(panel_core, name))

        for module_name, functions in EXPECTED_SIGNATURES.items():
            if not module_name.startswith("newtsolver.core.pressure_models."):
                continue
            owner = importlib.import_module(module_name)
            for name in functions:
                with self.subTest(package_reexport=name):
                    self.assertIs(getattr(owner, name), getattr(pressure_package, name))
                    if hasattr(panel_core, name):
                        self.assertIs(getattr(owner, name), getattr(panel_core, name))

    def test_pinned_keyword_spellings_and_return_values(self) -> None:
        fmf_frames = importlib.import_module("fmfsolver.core.sentman_core")
        atmosphere = importlib.import_module("fmfsolver.physics.us1976")
        newt_attitude = importlib.import_module("newtsolver.core.attitude")

        expected_sample = {"T_K": 288.15, "c_ms": 340.29, "Vmean_ms": 458.94}
        self.assertEqual(expected_sample, atmosphere.sample_at_altitude_km(alt_km=0.0))
        self.assertEqual(
            88.6226925452758,
            atmosphere.mean_to_most_probable_speed(v_mean=100.0),
        )
        source = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        expected_body = np.array([-1.0, 2.0, -3.0], dtype=np.float64)
        np.testing.assert_array_equal(expected_body, fmf_frames.stl_to_body(v_stl=source))
        np.testing.assert_array_equal(
            expected_body,
            newt_attitude.stl_to_body(v_stl=source),
        )
        self.assertEqual(
            "bank",
            newt_attitude._resolve_attitude_mode(attitude_input="BANK"),
        )

    def test_thin_wrappers_remain_numerically_identical_to_shared_owners(self) -> None:
        fmf = importlib.import_module("fmfsolver.core.sentman_core")
        shared_fmf = importlib.import_module("panelsolver.models.sentman")
        Vhat = np.array([1.0, 0.0, 0.0])
        normals = np.array([[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        kwargs = {
            "Vhat": Vhat,
            "n_out": normals,
            "S": 5.0,
            "Ti": 300.0,
            "Tw": 450.0,
            "Aref": 2.0,
        }
        np.testing.assert_array_equal(
            shared_fmf.sentman_dC_dA_vectors(**kwargs),
            fmf.sentman_dC_dA_vectors(**kwargs),
        )

        pressure_calls = (
            (
                "newtsolver.core.pressure_models.modified_newtonian",
                "panelsolver.models.hypersonic.modified_newtonian",
                "modified_newtonian_cp_max",
                {"Mach": 5.0, "gamma": 1.4},
            ),
            (
                "newtsolver.core.pressure_models.prandtl_meyer",
                "panelsolver.models.hypersonic.prandtl_meyer",
                "_prandtl_meyer_nu",
                {"Mach": np.array([2.0, 3.0]), "gamma": 1.4},
            ),
            (
                "newtsolver.core.pressure_models.tangent_wedge",
                "panelsolver.models.hypersonic.tangent_wedge",
                "tangent_wedge_pressure_coefficient",
                {
                    "Mach": 5.0,
                    "gamma": 1.4,
                    "deltar": np.array([0.0, math.radians(5.0)]),
                },
            ),
            (
                "newtsolver.core.pressure_models.tangent_cone",
                "panelsolver.models.hypersonic.tangent_cone",
                "tangent_cone_pressure_coefficient",
                {
                    "Mach": 5.0,
                    "gamma": 1.4,
                    "deltar": np.array([0.0, math.radians(5.0)]),
                },
            ),
        )
        for public_module, shared_module, name, call_kwargs in pressure_calls:
            with self.subTest(callable=f"{public_module}.{name}"):
                actual = getattr(importlib.import_module(public_module), name)(
                    **call_kwargs
                )
                expected = getattr(importlib.import_module(shared_module), name)(
                    **call_kwargs
                )
                np.testing.assert_array_equal(np.asarray(expected), np.asarray(actual))

        public_atmosphere = importlib.import_module("fmfsolver.physics.us1976")
        shared_atmosphere = importlib.import_module(
            "panelsolver.models.sentman_atmosphere"
        )
        for public_table, shared_table in zip(
            public_atmosphere.load_us1976_tables(),
            shared_atmosphere.load_us1976_tables(),
            strict=True,
        ):
            pd.testing.assert_frame_equal(public_table, shared_table, check_exact=True)

    def test_pinned_detach_cache_surface_is_product_owned(self) -> None:
        cases = (
            (
                "newtsolver.core.pressure_models.tangent_wedge",
                "_tangent_wedge_detach_limit",
                256,
            ),
            (
                "newtsolver.core.pressure_models.tangent_cone",
                "_tangent_cone_detach_limit",
                128,
            ),
        )
        for module_name, name, maxsize in cases:
            function = getattr(importlib.import_module(module_name), name)
            with self.subTest(callable=f"{module_name}.{name}"):
                self.assertEqual("_lru_cache_wrapper", type(function).__name__)
                self.assertEqual(
                    {"maxsize": maxsize, "typed": False},
                    function.cache_parameters(),
                )
                function.cache_clear()
                first = function(Mach=5.0, gamma=1.4)
                second = function(Mach=5.0, gamma=1.4)
                self.assertEqual(first, second)
                self.assertEqual(1, function.cache_info().hits)
                self.assertEqual(1, function.cache_info().misses)

    def test_product_detach_cache_counters_are_direct_call_only(self) -> None:
        wedge = importlib.import_module(
            "newtsolver.core.pressure_models.tangent_wedge"
        )
        wedge._tangent_wedge_detach_limit.cache_clear()
        wedge.tangent_wedge_pressure_coefficient(
            Mach=5.0,
            gamma=1.4,
            deltar=np.array([math.radians(5.0)]),
        )
        self.assertEqual(0, wedge._tangent_wedge_detach_limit.cache_info().currsize)

        wedge._tangent_wedge_detach_limit(Mach=5.0, gamma=1.4)
        self.assertEqual(1, wedge._tangent_wedge_detach_limit.cache_info().currsize)


if __name__ == "__main__":
    unittest.main()
