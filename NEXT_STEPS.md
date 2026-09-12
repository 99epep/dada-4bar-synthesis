# Current state and next steps

## Repository role

`dada-4bar-synthesis` performs inverse kinematic synthesis only.

- Input: normalized motion target exported by `dada-engine-solver`.
- Output: four-bar geometry approximating that target.
- Thermodynamics remain in `dada-engine-solver`.
- Do not add a thermodynamic solver or a second physical model here.

## Current synthesis stage

The implemented method is a **projection-only four-bar fit**.

For a fixed four-bar geometry, the output point and projection axis are fitted
linearly. Rocker-point and coupler-point outputs are supported. A finite piston
connecting rod has **not** yet been included.

The best practical solutions found so far are coupler-point (`F`) outputs.

### Large cylinder — compact candidate to preserve

Source result:
`outputs/champion_projection_BF_over_BC_4.json`

- output: coupler point `F`
- assembly branch: `+1`
- ground / crank: `8.359076059286378`
- coupler / crank: `1.8978981818881382`
- rocker / crank: `8.562558314779313`
- phase: `-0.6741270855205765 rad`
- fixed pivot / crank:
  - x = `6.5305460224395135`
  - y = `5.217865580266911`
- projection axis in shared-crank frame:
  `0.40824128311504243 rad`
- F local coordinates from crank pin B:
  - along coupler / crank = `1.8306390741406238`
  - normal to coupler / crank = `0.33169924587809335`
- |BF| / |BC| = `0.9802671316129091`
- normalized position RMS = `0.003139916965537827`
- normalized derivative RMS = `0.017814897701556507`
- minimum four-bar cross product = `0.713775533495472`

### Small cylinder — compact candidate to preserve

Source result:
`outputs/champion_projection_BF_over_BC_4.json`

- output: coupler point `F`
- assembly branch: `-1`
- ground / crank: `5.022706788451722`
- coupler / crank: `1.6563469344036357`
- rocker / crank: `5.1468443338063725`
- phase: `2.7064039666740163 rad`
- fixed pivot / crank:
  - x = `-4.554542857952098`
  - y = `-2.117480304002033`
- projection axis in shared-crank frame:
  `-2.3048052319993504 rad`
- F local coordinates from crank pin B:
  - along coupler / crank = `1.5159800513453636`
  - normal to coupler / crank = `-0.4124220620237704`
- |BF| / |BC| = `0.9485201500558249`
- normalized position RMS = `0.004552238459089386`
- normalized derivative RMS = `0.024907510954867273`
- minimum four-bar cross product = `0.6434636799793059`

## Important corrected input contract

The fitted centered coordinate is

`x = 2*q - 1`

therefore its derivatives are

`dx/dtheta = 2*dq/dtheta`

and

`d2x/dtheta2 = 2*d2q/dtheta2`.

The exporter in `dada-engine-solver` and this repository's loader were corrected
accordingly. Do not reintroduce the old factor-of-two mismatch.

## Known optimizer limitations

These are not urgent unless synthesis is resumed:

1. Differential evolution can miss the compact basin.
2. A constrained search can terminate slightly outside the `|BF|/|BC|` bound
   and currently raise at final validation.
3. Multiple restarts should eventually be added.
4. One failed branch should not abort an entire CLI campaign.
5. `output_radius/coupler` should remain a first-class diagnostic.

For the immediate project, the two compact candidates above are sufficient.

## Next mechanical stage

Add the finite piston connecting rod only after the projection-only candidate
has been thermodynamically assessed.

Suggested sequence:

1. keep the four-bar ratios and coupler point close to the current candidates;
2. add slider axis origin and finite connecting-rod length;
3. locally refine geometry against position and derivative;
4. choose physical crank radius / piston stroke / piston area;
5. export the final mechanism to the low-level mechanism backend in
   `dada-engine-solver`.

## Thermodynamic handoff

The temporary thermo bridge that lived in this repository is obsolete.

`dada-engine-solver` now contains the native experimental
`shared_crank_coupler_projection` kinematics path and the thermodynamic TOML
belongs there.

The latest native thermo attempt reached:

`maximum_cycle_count_reached`

rather than periodic convergence. Investigate that in `dada-engine-solver`;
do not duplicate the fix here.
