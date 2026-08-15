from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from fmfsolver.app.cli_app import CLI_POLICY as LEGACY_FMF_CLI_POLICY
from fmfsolver.io.io_cases import read_cases as legacy_read_fmf_cases
from fmfsolver.runtime import RUNTIME_POLICY as LEGACY_FMF_RUNTIME_POLICY
from newtsolver.app.cli_app import CLI_POLICY as LEGACY_HYPERSONIC_CLI_POLICY
from newtsolver.io.io_cases import read_cases as legacy_read_hypersonic_cases
from newtsolver.runtime import RUNTIME_POLICY as LEGACY_HYPERSONIC_RUNTIME_POLICY
from panelsolver.domains import fmf, hypersonic

REPOSITORY_ROOT = Path(__file__).parents[2]


class DomainOwnershipTests(unittest.TestCase):
    def test_legacy_batch_surfaces_delegate_to_canonical_domain_objects(self) -> None:
        self.assertIs(fmf.read_cases, legacy_read_fmf_cases)
        self.assertIs(hypersonic.read_cases, legacy_read_hypersonic_cases)
        self.assertIs(fmf.RUNTIME_POLICY, LEGACY_FMF_RUNTIME_POLICY)
        self.assertIs(hypersonic.RUNTIME_POLICY, LEGACY_HYPERSONIC_RUNTIME_POLICY)
        self.assertIs(
            fmf.RUNTIME_POLICY,
            LEGACY_FMF_CLI_POLICY.runtime_policy,
        )
        self.assertIs(
            hypersonic.RUNTIME_POLICY,
            LEGACY_HYPERSONIC_CLI_POLICY.runtime_policy,
        )

    def test_canonical_domain_execution_does_not_load_legacy_or_compat(self) -> None:
        code = f"""
import sys
import tempfile
from pathlib import Path
from panelsolver.domains import fmf, hypersonic
from tests.current_case_fixtures import read_current_cases

inputs = Path({str(REPOSITORY_ROOT)!r}) / 'tests' / 'fixtures' / 'phase1' / 'inputs'
with tempfile.TemporaryDirectory() as temp_dir:
    for domain, filename, expected_version in (
        (fmf, 'fmfsolver_cases.csv', '1.3.8'),
        (hypersonic, 'newtsolver_cases.csv', '1.0.3'),
    ):
        row = read_current_cases(domain.read_cases, inputs / filename).iloc[0].to_dict()
        row.update(out_dir=temp_dir, save_vtp_on=0, shielding_on=0, ray_backend='rtree')
        result = domain.run_cases((row,))
        assert len(result.cases) == 1
        assert result.cases[0].csv.rows[0]['solver_version'] == expected_version
        candidates = domain.build_primary_signatures(row)
        assert candidates.legacy_signatures == ()

loaded = sorted(
    name for name in sys.modules
    if name.startswith(('fmfsolver', 'newtsolver', 'panelsolver._compat'))
)
assert loaded == [], loaded
"""
        subprocess.run([sys.executable, "-c", code], check=True)


if __name__ == "__main__":
    unittest.main()
