# I/O contract with dada-engine-solver

## Principle

`dada-engine-solver` remains the reference implementation for thermodynamics,
`FreeKinematics`, and physical four-bar evaluation.

`dada-4bar-synthesis` is responsible only for inverse kinematic synthesis.

## Input: target law

The initial input is a standard solver TOML containing:

```toml
[geometry]
small_cylinder_minimum_volume = ...
small_cylinder_maximum_volume = ...
large_cylinder_minimum_volume = ...
large_cylinder_maximum_volume = ...

[kinematics]
type = "free"

[kinematics.small]
control_values = [...]

[kinematics.large]
control_values = [...]
```

Optional derivative limits use exactly the solver names:

```toml
maximum_absolute_first_derivative = ...
maximum_absolute_second_derivative = ...
```

The angle convention is the `FreeKinematics` study-angle convention:
theta in radians, period `2*pi`, with no implicit motor reversal.

## Output: realizable mechanism

The result maps one-to-one onto the low-level backend already present in
`dada-engine-solver`.

`loop` maps to `FourBarLoop`:
- `coupler_length`
- `rocker_length`
- `rocker_pivot_x`
- `rocker_pivot_y`
- `assembly_branch`

`output` maps to either `RockerOutputPoint` or `CouplerOutputPoint`:
- `type = "rocker" | "coupler"`
- `along`
- `normal`

`slider` maps to `SliderConstraint`:
- `axis_origin_x`
- `axis_origin_y`
- `axis_angle`
- `connecting_rod_length`
- `assembly_branch`

The shared result also contains:
- `crank_radius`
- `crank_angle_offset`
- `crank_direction`
- `small_volume_increases_with_coordinate`
- `large_volume_increases_with_coordinate`

## Why not SharedCrankRockerDesign?

That convenience design is currently narrower than the underlying backend:
it always constructs a rocker output and fixes `axis_angle=0`.

The synthesis result therefore targets the lower-level classes, which already
support coupler points and arbitrary slider-axis angles.

This should require only a small adapter in `dada-engine-solver`, not a new
four-bar implementation.

## Versioning

The output contract starts at `schema_version = 1`.
