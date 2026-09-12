# dada-4bar-synthesis

Inverse kinematic synthesis of four-bar mechanisms for the DADA engine.

This repository is deliberately separate from `dada-engine-solver`.

Its role is:

1. read a mechanism-synthesis target exported by `dada-engine-solver`;
2. search for a realizable four-bar mechanism reproducing that law;
3. export a mechanical definition directly mappable to the existing
   `dada_solver.four_bar` classes.

The thermodynamic solver remains authoritative for thermodynamics. This project
does not duplicate its thermodynamic model.

## Canonical input

The primary input is the pair exported by the thermodynamic optimization:

- `motor_champion_motion_target.json`: provenance, angle convention, cylinder
  limits and recommended fit coordinates;
- `motor_champion_motion_target.csv`: sampled normalized motion and derivatives.

The loader fits the normalized shape first, as requested by the solver export.
The duplicated 360-degree CSV row is verified then removed before fitting, so
0 and 360 degrees are not counted twice.

A normal solver TOML using `FreeKinematics` remains supported as a secondary
compatibility input.

## Output

The synthesis result mirrors the low-level types already present in
`dada_solver.four_bar`:

- `FourBarLoop`;
- `RockerOutputPoint` or `CouplerOutputPoint`;
- `SliderConstraint`;
- `SharedCrankFourBarVolumeKinematics`.

No alternative mechanical convention is introduced here.
