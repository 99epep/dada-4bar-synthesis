# dada-4bar-synthesis

Inverse kinematic synthesis of four-bar mechanisms for the DADA engine.

This repository is deliberately separate from `dada-engine-solver`.

Its role is:

1. read a target kinematic law produced/used by `dada-engine-solver`;
2. search for a realizable four-bar mechanism reproducing that law;
3. export a mechanical definition directly mappable to the existing
   `dada_solver.four_bar` classes.

The thermodynamic solver remains authoritative for thermodynamics. This project
does not duplicate its thermodynamic model.

## I/O contract

### Input

The first supported input is a normal `dada-engine-solver` TOML configuration
using `[kinematics] type = "free"` with `control_values` for the small and large
cylinders. Cylinder volume limits are read from the existing `[geometry]`
fields.

Angles use the solver study-angle convention: radians internally, one cycle is
`2*pi`.

### Output

The synthesis result mirrors the low-level types already present in
`dada_solver.four_bar`:

- `FourBarLoop`
- `RockerOutputPoint` or `CouplerOutputPoint`
- `SliderConstraint`
- `SharedCrankFourBarVolumeKinematics`

No alternative mechanical convention is introduced here.

Version 0.1 intentionally contains only target-law I/O, result-contract
dataclasses, validation, and tests. The mathematical synthesis is added on top
of this contract.
