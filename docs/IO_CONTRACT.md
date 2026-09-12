# I/O contract with dada-engine-solver

## Principle

`dada-engine-solver` remains the reference implementation for thermodynamics,
free target generation, and physical four-bar evaluation.

`dada-4bar-synthesis` is responsible only for inverse kinematic synthesis.

## Canonical input: sampled champion target

The canonical interface is the JSON + CSV pair exported by the solver for
mechanism synthesis.

The JSON is authoritative for:

- provenance;
- study-angle convention;
- cylinder physical volume limits;
- sampling metadata;
- recommended normalized fit coordinates.

The CSV is authoritative for the sampled law. The initial synthesis uses:

- `theta_rad`;
- the JSON-recommended small normalized coordinate;
- the JSON-recommended large normalized coordinate;
- their first derivatives with respect to theta.

Second derivatives are loaded when present and retained for diagnostics or a
future acceleration term in the objective.

The current solver champion recommends:

- `small_centered_minus1_plus1`;
- `large_centered_minus1_plus1`;
- `small_dq_dtheta_per_rad`;
- `large_dq_dtheta_per_rad`.

### Periodic endpoint

Solver exports contain both 0 and 360 degrees. They represent the same physical
state. The loader verifies that values and derivatives agree at both endpoints,
then removes the 360-degree row before least-squares fitting.

Thus a 0.25-degree export with 1441 rows becomes 1440 unique samples.

### Angle convention

The target stays in the solver study-angle convention. No motor-direction
transformation is performed at the I/O boundary. Mechanism synthesis may later
choose crank direction and phase explicitly.

## Secondary input: FreeKinematics TOML

A standard solver TOML with `[kinematics] type = "free"` remains supported for
compatibility, but it is not the preferred mechanism-synthesis interface.

## Output: realizable mechanism

The result maps one-to-one onto the low-level backend already present in
`dada-engine-solver`.

`loop` maps to `FourBarLoop`:

- `coupler_length`;
- `rocker_length`;
- `rocker_pivot_x`;
- `rocker_pivot_y`;
- `assembly_branch`.

`output` maps to either `RockerOutputPoint` or `CouplerOutputPoint`:

- `type = "rocker" | "coupler"`;
- `along`;
- `normal`.

`slider` maps to `SliderConstraint`:

- `axis_origin_x`;
- `axis_origin_y`;
- `axis_angle`;
- `connecting_rod_length`;
- `assembly_branch`.

The shared result also contains:

- `crank_radius`;
- `crank_angle_offset`;
- `crank_direction`;
- `small_volume_increases_with_coordinate`;
- `large_volume_increases_with_coordinate`.

## Why not SharedCrankRockerDesign?

That convenience design is currently narrower than the underlying backend: it
always constructs a rocker output and fixes `axis_angle=0`.

The synthesis result therefore targets the lower-level classes, which already
support coupler points and arbitrary slider-axis angles.

## Versioning

The mechanical output contract starts at `schema_version = 1`.
