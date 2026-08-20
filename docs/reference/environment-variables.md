# Environment-variable reference

An explicit API/configuration argument has highest precedence. The neutral name
then wins over the prefix for the selected product. The application or
compatibility boundary resolves only that selected prefix and passes
product-neutral values into core.

| Neutral variable | Selected-product fallback | Domain | Default |
|---|---|---|---:|
| `PANELSOLVER_SHIELD_BATCH_SIZE` | `FMFSOLVER_SHIELD_BATCH_SIZE` or `NEWTSOLVER_SHIELD_BATCH_SIZE` | integer ≥ 1 | Embree `64`; rtree `8` |
| `PANELSOLVER_PARALLEL_CHUNK_CASES` | `FMFSOLVER_PARALLEL_CHUNK_CASES` or `NEWTSOLVER_PARALLEL_CHUNK_CASES` | integer ≥ 1 | `8` |

Invalid or blank-domain values are errors; blank/unset variables are ignored.
The batch variable matters only when ray shielding is used. Chunk size is a
scheduling/reuse hint and does not change the input-ordered final result schema.
