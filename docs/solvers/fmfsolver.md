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

## Sentman local-load equation

For each panel, the Sentman model computes a local nondimensional traction
vector. The model returns this vector without panel-area or reference-area
scaling; the shared engine applies those factors and performs force, moment, and
component integration. General frame transformations and moment conventions are
described in [Numerical conventions](../reference/numerical-conventions.md).

### Geometry and symbols

- $\hat{\boldsymbol V}$ is the unit flow direction in the STL frame.
- $\boldsymbol n_{\mathrm{out}}$ is the STL outward unit normal.
- $\boldsymbol n_{\mathrm{in}}=-\boldsymbol n_{\mathrm{out}}$ is the inward
  unit normal used in Sentman's original report.
- $\gamma=\boldsymbol n_{\mathrm{in}}\mathbin{\boldsymbol\cdot}
  \hat{\boldsymbol V}$ is the direction cosine between the flow and inward
  normal. Here, $\gamma$ is not the specific-heat ratio used by newtsolver.
- $S$ is the molecular speed ratio, $T_i$ is the incident translational
  temperature, and $T_w$ is the wall temperature. The input columns are `S`,
  `Ti_K`, and `Tw_K`.

### Auxiliary functions and local traction

Define

$$
h = \gamma S,
\qquad
\Phi = 1 + \operatorname{erf}(h),
\qquad
E = e^{-h^2}.
$$

The implemented coefficients are

$$
c_{\parallel}
=
\gamma\Phi
+
\frac{E}{S\sqrt{\pi}},
$$

$$
c_{n,i}
=
\frac{\Phi}{2S^2},
$$

and

$$
c_{n,r}
=
\frac{1}{2}
\sqrt{\frac{T_w}{T_i}}
\left[
\frac{\gamma\sqrt{\pi}}{S}\Phi
+
\frac{E}{S^2}
\right].
$$

The local traction coefficient is therefore

$$
\boldsymbol{\tau}
=
c_{\parallel}\hat{\boldsymbol V}
+
\left(c_{n,i}+c_{n,r}\right)\boldsymbol n_{\mathrm{in}}.
$$

In this local equation, $S$ enters the projected speed $h$ and the explicit
$1/S$ and $1/S^2$ terms. The incident temperature and wall temperature enter
the reflected coefficient through $\sqrt{T_w/T_i}$; $T_i$ also belongs to the
physical free-stream state used to define or resolve $S$. Consequently, `S`,
`Ti_K`, and `Tw_K` describe distinct parts of the implemented load rather than
three interchangeable temperature or velocity corrections.

The three terms have distinct roles. The
$c_{\parallel}\hat{\boldsymbol V}$ term is the incident-molecule load in the
flow direction and retains the component tangent to the panel.
$c_{n,i}\boldsymbol n_{\mathrm{in}}$ is the normal contribution from the
random thermal motion of incident molecules, while
$c_{n,r}\boldsymbol n_{\mathrm{in}}$ is the normal contribution from diffusely
reflected molecules. Under complete diffuse reflection, reflected tangential
momentum cancels statistically, so the reflected term appears only in the
normal direction. The error-function and exponential terms retain random
thermal motion, so this is not a simple windward-only pressure law.

For panel $j$, the common integrator forms

$$
\Delta\boldsymbol C_j
=
\boldsymbol{\tau}_j
\frac{A_j}{A_{\mathrm{ref}}}.
$$

This is algebraically the same as the original report's $dC/dA$ form. The
current model returns the local traction numerator, and the common integrator
applies $A_j/A_{\mathrm{ref}}$ exactly once before summing whole-vehicle forces
and moments.

### Assumptions and implementation scope

Sentman's Eq. (21) applies within kinetic theory, free-molecular flow, and
complete diffuse-reflection assumptions. Its general form uses reflected
molecular temperature $T_r$. FMF has no independent $T_r$ input or thermal
accommodation coefficient; the current implementation assumes complete thermal
accommodation and substitutes $T_r=T_w$, which produces the
$\sqrt{T_w/T_i}$ factor above.

This equation does not model specular reflection, mixed reflection, an arbitrary
thermal accommodation coefficient, or multiple reflections between surfaces.
Ray shielding is a separate geometric approximation that sets an occluded
panel's load to zero; see
[Shielding and parallel execution](../user-guide/shielding-and-parallel.md).

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

## Reference

Lee H. Sentman, *Free Molecule Flow Theory and Its Application to the
Determination of Aerodynamic Forces*, LMSC-448514, 1961, Section II-B,
especially Eq. (21).
