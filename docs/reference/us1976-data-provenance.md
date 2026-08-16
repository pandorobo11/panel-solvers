# US1976 Sentman atmosphere data provenance

## Canonical dataset

FMF/Sentman Mode B uses one generated table containing exactly four physical
quantities:

| Column | Unit | Meaning |
|---|---|---|
| geometric altitude | km | geometric altitude above mean sea level |
| temperature | K | kinetic/static translational temperature |
| speed of sound | m/s | PDAS Big Tables sound speed |
| mean molecular speed | m/s | PDAS Big Tables mean particle speed |

The grid is 201 rows from 0 through 1000 km inclusive in 5 km steps. The
package-internal table is
`src/panelsolver/models/_sentman_atmosphere_data.py`; runtime sampling in
`src/panelsolver/models/sentman_atmosphere.py` linearly interpolates that table.
Runtime and installed-wheel use require neither filesystem data files nor
network access.

Pressure, density, viscosity, gravity, number density, mean free path,
molecular weight, and the other PDAS output fields are not part of the
canonical dataset because the solver does not use them.

## Scientific source

The technical definition is
[*U.S. Standard Atmosphere, 1976*](https://ntrs.nasa.gov/api/citations/19770009539/downloads/19770009539.pdf),
jointly issued under these identifiers:

- NOAA-S/T-76-1562;
- NASA-TM-X-74335;
- NASA Technical Reports Server document ID
  [19770009539](https://ntrs.nasa.gov/citations/19770009539).

The NTRS record describes the main atmosphere tables through 1000 km, marks
distribution as public, and identifies the report as a U.S. Government work
for which public use is permitted. This scientific publication establishes the
technical basis. A scientific citation alone is not a software or data license.

## Regeneration software and public-domain basis

The primary regeneration implementation is PDAS `bigtables.py` version 1.5
(2022-03-18), distributed in the official
[atmosphere package](https://www.pdas.com/atmosdownload.html). PDAS identifies
`bigtables.py` as the Python program that creates its 0--1000 km Big Tables
output. The source used here was obtained on 2026-08-15 from:

`https://www.pdas.com/packages/atmos.zip`

Pinned SHA-256 values:

| Object | SHA-256 |
|---|---|
| downloaded `atmos.zip` | `6ede29f1e4f104ad3d5cbe990071682fd903ab04d7d47b168a4c17817714365a` |
| upstream `bigtables.py` | `eca87577139ac3b2845d1d4eca91604ac278a491918979f2d2316bf88a9a3a28` |
| repository minimal calculation snapshot | `11e82d35d66a61c4326acf04fcad0c9ab471112721151b65cfdf4faff43f9994` |

The [PDAS legal statement](https://www.pdas.com/legal.html) distinguishes its
copyright in the collection as a compilation from the individual programs. It
states that the individual programs are not copyrighted and are public domain,
and also dedicates PDAS-added program value to the public domain. That statement
is the software/right provenance basis for using `bigtables.py`; it is separate
from the scientific report citation above.

Panel Solver does not claim copyright in the underlying U.S. Government data
or the PDAS public-domain program and does not relicense either as Apache-2.0.
The project license covers the project-authored generator, integration, tests,
documentation, and original selection or arrangement to the extent those
elements are copyrightable.

`tools/reference/pdas/bigtables_v1_5.py` is a development-only, minimal snapshot
of the upstream constants and calculation functions needed for these four
quantities. HTML generation, unused properties, and the upstream program's
unconditional HTML-writing entry point are deliberately omitted. The retained
numeric constants and calculations are unchanged. Neither the snapshot nor the
generator is imported by application runtime.

## Deterministic transformation

The provenance chain is:

```text
U.S. Standard Atmosphere, 1976
  -> PDAS public-domain bigtables.py v1.5
  -> pinned minimal calculation snapshot
  -> scripts/generate_us1976_sentman_table.py
  -> one generated Z / T / c / V_mean table
  -> panelsolver.models.sentman_atmosphere
```

The generator evaluates geometric altitudes `0, 5, ..., 1000` km and reproduces
the published-value formatting in the PDAS program:

- altitude: integer kilometers (`WriteIntegerCell`);
- temperature: three digits after the decimal (`WriteF3Cell`);
- speed of sound: two digits after the decimal (`WriteF2Cell`);
- mean molecular speed: two digits after the decimal (`WriteF2Cell`).

This explicit formatting is part of the compatibility contract. The generated
table intentionally does not substitute higher-precision binary results for the
previously shipped tabulated values.

Regenerate or verify without network access:

```bash
python scripts/generate_us1976_sentman_table.py
python scripts/generate_us1976_sentman_table.py --check
```

CI runs the check form to detect hand-edited drift.

## Previous-value verification

The previous current implementation transcribed four arrays from two CSV files
at pinned legacy `fmfsolver` commit
`b62bc844d02a8f5212e62a53dea3238a1414317d`. Those historical CSV files remain
read-only migration evidence and are not runtime or generator inputs:

| Legacy file | Used columns | SHA-256 |
|---|---|---|
| `us1976_table1.csv` | `Z`, `T`, `c` | `4afc36572b2126818d777e3e92fa33ec2440c1a6ad2f61aef5f65c0966f2a491` |
| `us1976_table2.csv` | `Z`, `V` | `7afe3132cd59836c77cdc32be6e0821de20027f9cf41974d3a337769ec7a534a` |

Before replacing the storage layout, every generated grid point was compared
independently with the previous altitude, temperature, sound-speed, and
mean-speed arrays. Each column had 201/201 exact matches, zero nonzero
differences, and maximum absolute difference `0.0`. Unit tests preserve
per-column SHA-256 evidence for that full-grid comparison in addition to known
points and interpolation samples. No golden fixture or tolerance was changed.

The expected supported numerical delta is therefore zero: Mode B speed ratio,
translational temperature, most-probable molecular speed, Sentman panel loads,
integrated coefficients, signatures, Summary CSV, VTP, and Phase 1 FMF goldens
remain unchanged.

## Packaging and scope

The generated Python module is ordinary `panelsolver` package source and is
included in wheel and sdist. The generator, PDAS reference snapshot, and this
development provenance material are outside the configured wheel package roots
and are not included in the wheel. The reference snapshot may be included in the
source distribution so an sdist checkout can regenerate the table offline.

Project licensing and the consolidated third-party rights boundary are recorded
in the root `LICENSE` and `THIRD_PARTY_NOTICES.md` files.
