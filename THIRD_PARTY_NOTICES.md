# Third-party and public-domain notices

This file records material and dependencies that are not relicensed by the
Panel Solver Apache License 2.0. It is informational and is not an Apache
`NOTICE` file.

## U.S. Standard Atmosphere, 1976

- Title: *U.S. Standard Atmosphere, 1976*
- Report identifiers: NOAA-S/T-76-1562 and NASA-TM-X-74335
- NASA Technical Reports Server document ID:
  [19770009539](https://ntrs.nasa.gov/citations/19770009539)
- NTRS rights record: `Distribution Limits: Public`; `Copyright: Work of the
  US Gov. Public Use Permitted`

Panel Solver uses a generated 201-row table of geometric altitude,
temperature, speed of sound, and mean molecular speed for the FMF/Sentman Mode
B atmosphere calculation. The underlying U.S. Government report and physical
data are not claimed as copyright of pandorobo11. The complete transformation,
rounding, source hashes, and equivalence evidence are documented in
[US1976 Sentman atmosphere data provenance](docs/reference/us1976-data-provenance.md).

## Public Domain Aeronautical Software

The regeneration source is the `bigtables.py` program version 1.5 from the
Public Domain Aeronautical Software (PDAS) atmosphere package:

- upstream package: `https://www.pdas.com/packages/atmos.zip` (retrieved
  2026-08-15);
- package SHA-256:
  `6ede29f1e4f104ad3d5cbe990071682fd903ab04d7d47b168a4c17817714365a`;
- upstream `bigtables.py` SHA-256:
  `eca87577139ac3b2845d1d4eca91604ac278a491918979f2d2316bf88a9a3a28`;
- repository minimal calculation snapshot:
  `tools/reference/pdas/bigtables_v1_5.py`;
- snapshot SHA-256:
  `11e82d35d66a61c4326acf04fcad0c9ab471112721151b65cfdf4faff43f9994`.

The [PDAS legal statement](https://www.pdas.com/legal.html) distinguishes the
compilation copyright in the collection from its individual programs. It
states that the individual programs are public domain and that PDAS-added
program value is donated to the public domain. The repository uses and
redistributes only the minimal calculation snapshot needed for deterministic
regeneration. It does not vendor the PDAS Web site, `bigtables.html`, or the
PDAS collection as a whole.

The underlying PDAS program is not claimed as copyright of pandorobo11 and is
not relicensed under Apache-2.0.

## Scientific methods and citations

The Sentman, Newtonian, Modified Newtonian, tangent-wedge, tangent-cone,
Taylor--Maccoll, and Prandtl--Meyer implementations use mathematical equations,
physical methods, and algorithms described by the technical sources cited in
the solver documentation. Those citations are technical provenance; they are
not third-party software licenses. The project does not redistribute source
publication figures or publication prose.

## Offline documentation static assets

The wheel and standalone documentation ZIP redistribute the generated MkDocs
site, including theme CSS, JavaScript, images, and webfonts. This content is a
vendored release-artifact exception to the separately installed dependency
boundary described below. The site uses the built-in `mkdocs` theme from the
locked MkDocs 1.6.1 distribution; it does not include the ReadTheDocs/Sphinx
RTD theme, Lato, Roboto Slab, jQuery, or HTML5 Shiv assets.

| Redistributed content | Copyright holder | License | Required preservation |
|---|---|---|---|
| MkDocs 1.6.1 templates, base CSS/JS, favicon, and grid image | Copyright © 2014-present Tom Christie | BSD-2-Clause | copyright, conditions, and disclaimer |
| Bootswatch 5.3.2 Cerulean CSS | Copyright © 2013 Thomas Park | MIT | copyright and permission notice |
| Bootstrap 5.3.2 CSS and JavaScript | Copyright © 2011-2023 The Bootstrap Authors | MIT | copyright and permission notice |
| Popper 2.11.8 code embedded in the Bootstrap JavaScript bundle | Copyright © 2019 Federico Zivolo | MIT | copyright and permission notice |
| Font Awesome Free 6.5.1 CSS and webfonts | Copyright © 2023 Fonticons, Inc. | MIT for code; SIL OFL 1.1 for webfonts | MIT notice and complete OFL text; reserved font name retained |

The required copyright notices and license texts are preserved under
`THIRD_PARTY_LICENSES/`. That directory and this notice are copied into
`panelsolver/_docs_site/` in the wheel and therefore into the byte-equivalent
documentation ZIP. The same files are also recorded as wheel metadata license
files. They are not covered or relicensed by Panel Solver's project
Apache-2.0 `LICENSE`.

## Runtime dependencies

The runtime dependencies declared in `pyproject.toml`--NetworkX, NumPy,
openpyxl, pandas, PySide6, PyVista, pyvistaqt, Rtree, SciPy, and Trimesh--and
the optional Embree bindings are installed as separate distributions. They
remain subject to their respective upstream licenses and are not relicensed by
Panel Solver. Consult each installed distribution and its upstream project for
its applicable license and notices.

Except for the audited offline-documentation assets above, the panelsolver
wheel does not contain runtime-dependency source or binaries. In particular,
it declares `PySide6==6.9.3` as an external dependency and does not contain
PySide6 or Qt binaries. A future standalone application bundle, for example one
produced with PyInstaller, would require a separate license and notice audit
for every bundled dependency and binary.
