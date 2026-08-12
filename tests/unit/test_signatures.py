from __future__ import annotations

import hashlib
import pickle
import unittest

from panelsolver.core import (
    CommonCasePayload,
    ResolvedShieldingConfig,
    ResultCache,
    ResultCacheError,
    SignatureError,
    SignatureMatchKind,
    build_case_signature,
    match_case_signature,
)


def _common_case(**updates) -> CommonCasePayload:
    values = {
        "case_id": "case-a",
        "Aref_m2": 2.0,
        "moment_reference_stl_m": [0.1, 0.2, 0.3],
        "Lref_Cl_m": 1.0,
        "Lref_Cm_m": 2.0,
        "Lref_Cn_m": 3.0,
        "alpha_t_deg": 10.0,
        "beta_t_deg": -2.0,
    }
    values.update(updates)
    return CommonCasePayload(**values)


def _shielding(**updates) -> ResolvedShieldingConfig:
    values = {
        "enabled": True,
        "requested_backend": "auto",
        "effective_backend": "embree",
        "batch_size": 64,
        "cache_max": 1,
    }
    values.update(updates)
    return ResolvedShieldingConfig(**values)


def _signature(**updates):
    values = {
        "geometry_fingerprint": "a" * 64,
        "common_case": _common_case(),
        "model_id": "sentman",
        "model_algorithm_version": "sentman-v1",
        "model_case_payload": {"S": 5.0, "nested": {"x": [1, 2]}},
        "shielding_config": _shielding(),
    }
    values.update(updates)
    return build_case_signature(**values)


class SignatureTests(unittest.TestCase):
    def test_canonical_payload_is_mapping_order_and_pickle_stable(self) -> None:
        first = _signature(
            model_case_payload={"S": 5.0, "nested": {"x": [1, 2]}},
        )
        second = _signature(
            model_case_payload={"nested": {"x": (1, 2)}, "S": 5.0},
        )
        restored = pickle.loads(pickle.dumps(first))

        self.assertEqual(first.digest, second.digest)
        self.assertEqual(first.canonical_payload, second.canonical_payload)
        self.assertEqual(first.digest, restored.digest)
        self.assertEqual(first.canonical_payload, restored.canonical_payload)
        self.assertNotIn("solver_version", first.canonical_payload)
        self.assertNotIn("application_version", first.canonical_payload)

    def test_every_numerical_identity_field_changes_the_digest(self) -> None:
        baseline = _signature().digest
        variants = (
            _signature(geometry_fingerprint="b" * 64),
            _signature(common_case=_common_case(Aref_m2=3.0)),
            _signature(model_id="hypersonic"),
            _signature(model_algorithm_version="sentman-v2"),
            _signature(model_case_payload={"S": 6.0}),
            _signature(
                shielding_config=_shielding(
                    enabled=False,
                    effective_backend="not_used",
                    batch_size=0,
                )
            ),
            _signature(shielding_config=_shielding(requested_backend="rtree")),
            _signature(shielding_config=_shielding(effective_backend="rtree")),
            _signature(shielding_config=_shielding(batch_size=8)),
            _signature(
                shielding_config=_shielding(algorithm_version="shielding-v2")
            ),
        )
        self.assertTrue(all(item.digest != baseline for item in variants))

    def test_cache_capacity_does_not_change_numerical_signature(self) -> None:
        first = _signature(shielding_config=_shielding(cache_max=1))
        second = _signature(shielding_config=_shielding(cache_max=99))
        self.assertEqual(first.digest, second.digest)

    def test_rejects_nonfinite_unsupported_and_invalid_identity(self) -> None:
        invalid_payloads = (
            {"value": float("nan")},
            {"value": float("inf")},
            {"value": object()},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(SignatureError):
                    _signature(model_case_payload=payload)
        with self.assertRaises(SignatureError):
            _signature(geometry_fingerprint="not-a-digest")
        with self.assertRaises(SignatureError):
            _signature(model_algorithm_version=" version ")

    def test_primary_precedes_opaque_legacy_fallbacks(self) -> None:
        primary = _signature()
        legacy = hashlib.sha256(b"legacy").hexdigest()
        duplicate = primary.digest

        match = match_case_signature(
            primary.digest,
            primary,
            legacy_signatures=(duplicate, legacy),
        )
        self.assertEqual(SignatureMatchKind.PRIMARY, match.kind)
        fallback = match_case_signature(
            legacy,
            primary,
            legacy_signatures=(duplicate, legacy),
        )
        self.assertEqual(SignatureMatchKind.LEGACY, fallback.kind)
        self.assertEqual(1, fallback.legacy_index)
        self.assertEqual(
            SignatureMatchKind.NONE,
            match_case_signature("<invalid-stored>", primary).kind,
        )

    def test_direct_and_file_legacy_variants_remain_distinct(self) -> None:
        primary = _signature()
        direct = hashlib.sha256(b"direct-defaults").hexdigest()
        normalized_file = hashlib.sha256(b"file-defaults").hexdigest()
        self.assertNotEqual(direct, normalized_file)
        self.assertEqual(
            0,
            match_case_signature(
                direct,
                primary,
                legacy_signatures=(direct, normalized_file),
            ).legacy_index,
        )
        self.assertEqual(
            1,
            match_case_signature(
                normalized_file,
                primary,
                legacy_signatures=(direct, normalized_file),
            ).legacy_index,
        )


class ResultCacheTests(unittest.TestCase):
    def test_cache_defensively_copies_values_and_tracks_hits(self) -> None:
        cache = ResultCache[dict[str, list[int]]](max_entries=1)
        signature = _signature()
        value = {"items": [1, 2]}
        cache.put(signature, value)
        value["items"].append(3)
        first = cache.get(signature)
        self.assertEqual({"items": [1, 2]}, first)
        first["items"].append(4)
        self.assertEqual({"items": [1, 2]}, cache.get(signature))
        self.assertEqual((1, 2, 0), (
            cache.stats().entries,
            cache.stats().hits,
            cache.stats().misses,
        ))

    def test_cache_eviction_disabled_mode_and_key_isolation(self) -> None:
        cache = ResultCache[str](max_entries=1)
        first = _signature()
        second = _signature(model_algorithm_version="sentman-v2")
        cache.put(first, "first")
        cache.put(second, "second")
        self.assertIsNone(cache.get(first))
        self.assertEqual("second", cache.get(second))
        self.assertEqual(1, cache.stats().evictions)

        disabled = ResultCache[str](max_entries=0)
        disabled.put(first, "value")
        self.assertIsNone(disabled.get(first))
        self.assertEqual(0, disabled.stats().entries)
        with self.assertRaises(ResultCacheError):
            ResultCache(max_entries=-1)


if __name__ == "__main__":
    unittest.main()
