# newtsolver

newtsolver evaluates pressure-only panel traction for Newtonian-family flow
models. The local load is `-Cp` times the outward panel normal; the shared engine
owns geometry scaling, shielding, integration, components, and artifacts.

## Surface equations

`windward_eq` accepts:

- `newtonian`;
- `modified_newtonian`;
- `tangent_wedge`;
- `tangent_cone`.

`leeward_eq` accepts:

- `shield`: zero leeward pressure;
- `prandtl_meyer`: expansion pressure/suction model.

A single selector applies to every STL. With multiple STL components, provide
exactly one semicolon-separated selector per component to choose equations
independently. Empty entries and mismatched counts are invalid.

## Flow inputs and constraints

`Mach` must be positive and `gamma` must be greater than 1. Modified Newtonian,
tangent wedge, tangent cone, and Prandtl–Meyer require `Mach > 1`. The implemented
Newtonian + leeward `shield` path accepts positive subsonic Mach because its
formula does not use a supersonic relation; that acceptance should not be read as
a claim that the hypersonic approximation is physically suitable there.

Tangent-wedge and tangent-cone paths retain their accepted detached/limited
branches, and Prandtl–Meyer retains its bounded numerical inversion. These panel
approximations do not model viscous effects, full shock interaction, or general
three-dimensional CFD physics. Select them only within a justified engineering
approximation regime.

See the [newtsolver input reference](../reference/newtsolver-input.md) and
[numerical conventions](../reference/numerical-conventions.md).
