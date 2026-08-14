# Environment-variable reference

An explicit API/configuration argument has highest precedence. The neutral name
then wins over the prefix for the selected product. Core never reads both legacy
product prefixes for one run.

| Neutral variable | Selected-product fallback | Domain | Default |
|---|---|---|---:|
| `PANELSOLVER_SHIELD_CACHE_MAX` | `FMFSOLVER_SHIELD_CACHE_MAX` or `NEWTSOLVER_SHIELD_CACHE_MAX` | integer ≥ 0 | `1`; `0` disables mask cache |
| `PANELSOLVER_SHIELD_BATCH_SIZE` | `FMFSOLVER_SHIELD_BATCH_SIZE` or `NEWTSOLVER_SHIELD_BATCH_SIZE` | integer ≥ 1 | Embree `64`; rtree `8` |
| `PANELSOLVER_PARALLEL_CHUNK_CASES` | `FMFSOLVER_PARALLEL_CHUNK_CASES` or `NEWTSOLVER_PARALLEL_CHUNK_CASES` | integer ≥ 1 | `8` |

Invalid or blank-domain values are errors; blank/unset variables are ignored.
Cache and batch variables matter only when ray shielding is used. Chunk size is a
scheduling/reuse hint and does not change the input-ordered final result schema.
