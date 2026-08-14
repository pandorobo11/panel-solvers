# FMF solver

FMF evaluates free-molecular-flow panel loads with the Sentman model. Unlike a
pressure-only model, its local nondimensional traction retains both normal and
tangential/freestream contributions. The shared engine then applies panel area,
reference-area normalization, force/moment integration, and component totals.

## Flow inputs

Exactly one mode must be supplied:

- **Mode A:** positive molecular speed ratio
  `S = V_inf / sqrt(2 R Ti)` and positive free-stream incident translational
  (static) temperature `Ti_K`. `Ti_K` is not total or stagnation temperature;
  the supplied `S` and `Ti_K` must describe the same free-stream state.
- **Mode B:** positive `Mach` and `Altitude_km` in the bundled US1976 table's
  inclusive `0–1000 km` geometric-altitude range. The solver linearly
  interpolates static translational temperature, speed of sound, and mean
  molecular speed. It sets `V_inf = Mach * c`, converts mean molecular speed to
  most-probable speed with `V_mp = sqrt(pi) / 2 * V_mean`, and resolves
  `S = V_inf / V_mp` and `Ti_K` without a total-temperature conversion.

Both modes require positive wall temperature `Tw_K`. The reflected Sentman term
uses `sqrt(Tw_K / Ti_K)`; because there is no separate reflected-gas temperature
or accommodation input, FMF uses the wall temperature as the diffusely
reflected molecular temperature (`T_r = T_w`). Supplying both modes, only half a
pair, or neither mode is invalid.

## Outputs and scope

FMF VTP/NPZ data includes `Cp_n` and `theta_deg`; NPZ additionally includes the
resolved `S`, `Ti_K`, and `Tw_K`. Summary CSV includes resolved mode, `out_S`, and
`out_Ti_K`.

Use this model only when the free-molecular/Sentman assumptions are appropriate
for the intended regime and surface interaction. Mode B is tied to the bundled,
pinned atmosphere table and does not accept extrapolation beyond its altitude
range. It does not become a continuum-flow model merely because Mach is used to
derive speed ratio.

See the [FMF input reference](../reference/fmfsolver-input.md) and
[numerical conventions](../reference/numerical-conventions.md).
