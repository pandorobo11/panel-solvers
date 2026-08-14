# Current case-table fixtures

These one-case fixtures exercise the supported case schema independently of the
read-only Phase 1 evidence. The CSV files are the generation sources for the
matching BIFF8 `.xls` files and intentionally omit the retired `save_npz_on`
field.

The CSV sources were imported with bundled `@oai/artifact-tool`, exported as
temporary XLSX workbooks, and converted once to Excel 97–2003 BIFF8 with
LibreOfficeDev 26.8.0.0.alpha0
(`2c87e51eeaa2b413ff4ae097b2705eea1995d8e5`). The committed `.xls` files are
read-only test inputs; no workbook-generation dependency is required by the
package or test suite.

Both tables refer to `../phase1/inputs/stl/plate.stl` so the readers exercise
relative path resolution without copying or changing historical geometry.
