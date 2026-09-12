"""Load synthesis targets using dada-engine-solver output conventions."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import tomllib

from .contracts import (
    CylinderTargetLimits,
    FreeKinematicsTarget,
    FreeMotionTarget,
    SampledMotionTarget,
)


_DEFAULT_FIT_COLUMNS = {
    "small": "small_centered_minus1_plus1",
    "large": "large_centered_minus1_plus1",
    "derivative_small": "small_centered_dq_dtheta_per_rad",
    "derivative_large": "large_centered_dq_dtheta_per_rad",
}


def _float(row: dict[str, str], name: str) -> float:
    try:
        return float(row[name])
    except KeyError as error:
        raise ValueError(f"Missing required target CSV column: {name}") from error
    except ValueError as error:
        raise ValueError(f"Invalid floating-point value in target CSV column: {name}") from error


def _periodic_endpoint_matches(series: list[list[float]]) -> bool:
    return all(
        math.isclose(values[0], values[-1], rel_tol=1.0e-9, abs_tol=1.0e-10)
        for values in series
    )


def load_solver_motion_target(
    csv_path: str | Path,
    json_path: str | Path | None = None,
) -> SampledMotionTarget:
    """Load the canonical mechanism-synthesis target exported by the solver.

    The JSON file supplies provenance, physical cylinder limits, sampling
    metadata and the recommended normalized fit columns. The CSV supplies the
    sampled target law and analytic derivatives.

    Solver exports include both 0 and 2*pi. The latter is verified to be a
    periodic duplicate and removed so least-squares fitting does not give the
    cycle origin double weight.
    """

    csv_path = Path(csv_path)
    if json_path is None:
        json_path = csv_path.with_suffix(".json")
    json_path = Path(json_path)

    with json_path.open("r", encoding="utf-8") as stream:
        metadata = json.load(stream)

    recommended = dict(_DEFAULT_FIT_COLUMNS)
    recommended.update(metadata.get("recommended_mechanism_fit_coordinates", {}))
    column_small = str(recommended["small"])
    column_large = str(recommended["large"])
    column_dsmall = str(recommended["derivative_small"])
    column_dlarge = str(recommended["derivative_large"])

    if (
        column_small == "small_centered_minus1_plus1"
        and column_dsmall == "small_dq_dtheta_per_rad"
    ) or (
        column_large == "large_centered_minus1_plus1"
        and column_dlarge == "large_dq_dtheta_per_rad"
    ):
        raise ValueError(
            "Inconsistent legacy motion-target derivatives: centered motion "
            "requires centered derivative columns. Regenerate the target with "
            "the corrected dada-engine-solver exporter."
        )

    second_small = recommended.get("second_derivative_small")
    second_large = recommended.get("second_derivative_large")
    if (second_small is None) != (second_large is None):
        raise ValueError(
            "Target JSON must recommend both second-derivative columns or neither."
        )
    column_d2small = None if second_small is None else str(second_small)
    column_d2large = None if second_large is None else str(second_large)

    theta: list[float] = []
    small: list[float] = []
    large: list[float] = []
    dsmall: list[float] = []
    dlarge: list[float] = []
    d2small: list[float] = []
    d2large: list[float] = []

    with csv_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError("Target CSV has no header.")
        if column_d2small is not None:
            have_second = (
                column_d2small in reader.fieldnames
                and column_d2large in reader.fieldnames
            )
            if not have_second:
                raise ValueError(
                    "Target CSV is missing the second-derivative columns "
                    "recommended by the target JSON."
                )
        else:
            have_second = (
                "small_d2q_dtheta2_per_rad2" in reader.fieldnames
                and "large_d2q_dtheta2_per_rad2" in reader.fieldnames
            )
            if have_second:
                column_d2small = "small_d2q_dtheta2_per_rad2"
                column_d2large = "large_d2q_dtheta2_per_rad2"
        for row in reader:
            theta.append(_float(row, "theta_rad"))
            small.append(_float(row, column_small))
            large.append(_float(row, column_large))
            dsmall.append(_float(row, column_dsmall))
            dlarge.append(_float(row, column_dlarge))
            if have_second:
                assert column_d2small is not None
                assert column_d2large is not None
                d2small.append(_float(row, column_d2small))
                d2large.append(_float(row, column_d2large))

    if len(theta) < 5:
        raise ValueError("Target CSV must contain at least five rows including 2*pi.")

    expected_rows = metadata.get("csv_sampling", {}).get("rows_including_360_deg")
    if expected_rows is not None and len(theta) != int(expected_rows):
        raise ValueError(
            f"Target CSV row count {len(theta)} does not match JSON metadata "
            f"({int(expected_rows)})."
        )

    if not math.isclose(theta[0], 0.0, abs_tol=1.0e-12):
        raise ValueError("Target CSV must start at theta=0 rad.")
    if not math.isclose(theta[-1], 2.0 * math.pi, rel_tol=0.0, abs_tol=1.0e-10):
        raise ValueError("Target CSV must include the duplicated theta=2*pi endpoint.")

    periodic_series = [small, large, dsmall, dlarge]
    if d2small:
        periodic_series.extend((d2small, d2large))
    if not _periodic_endpoint_matches(periodic_series):
        raise ValueError("Target values at theta=0 and theta=2*pi are not periodic duplicates.")

    # Remove 2*pi: it is the same physical sample as theta=0.
    theta.pop()
    small.pop()
    large.pop()
    dsmall.pop()
    dlarge.pop()
    if d2small:
        d2small.pop()
        d2large.pop()

    try:
        small_meta = metadata["cylinder_limits"]["small"]
        large_meta = metadata["cylinder_limits"]["large"]
        small_limits = CylinderTargetLimits(
            minimum_m3=float(small_meta["minimum_m3"]),
            maximum_m3=float(small_meta["maximum_m3"]),
        )
        large_limits = CylinderTargetLimits(
            minimum_m3=float(large_meta["minimum_m3"]),
            maximum_m3=float(large_meta["maximum_m3"]),
        )
    except KeyError as error:
        raise ValueError(f"Missing required target JSON field: {error.args[0]}") from error

    for label, item, limits in (
        ("small", small_meta, small_limits),
        ("large", large_meta, large_limits),
    ):
        if "swept_m3" in item and not math.isclose(
            float(item["swept_m3"]), limits.swept_m3, rel_tol=1.0e-10, abs_tol=1.0e-15
        ):
            raise ValueError(f"{label} cylinder swept volume is inconsistent in target JSON.")

    raw_convention = str(metadata.get("angle_convention", ""))
    if "Study angle" not in raw_convention and "study angle" not in raw_convention:
        raise ValueError("Target JSON does not declare the solver study-angle convention.")

    step = metadata.get("csv_sampling", {}).get("step_deg")
    return SampledMotionTarget(
        theta_rad=tuple(theta),
        small_q=tuple(small),
        large_q=tuple(large),
        small_dq_dtheta=tuple(dsmall),
        large_dq_dtheta=tuple(dlarge),
        small_d2q_dtheta2=(tuple(d2small) if d2small else None),
        large_d2q_dtheta2=(tuple(d2large) if d2large else None),
        small_limits=small_limits,
        large_limits=large_limits,
        angle_convention="study_angle_radians",
        source_purpose=(None if "purpose" not in metadata else str(metadata["purpose"])),
        sample_step_deg=(None if step is None else float(step)),
    )


def load_solver_free_kinematics_target(
    path: str | Path,
) -> FreeKinematicsTarget:
    """Secondary compatibility loader for a solver FreeKinematics TOML."""

    path = Path(path)
    with path.open("rb") as stream:
        data = tomllib.load(stream)

    try:
        geometry = data["geometry"]
        kinematics = data["kinematics"]
    except KeyError as error:
        raise ValueError(
            f"Missing required solver configuration section: {error.args[0]}"
        ) from error

    if kinematics.get("type") != "free":
        raise ValueError(
            "FreeKinematics compatibility input requires [kinematics] type = 'free'."
        )

    def motion(side: str) -> FreeMotionTarget:
        try:
            definition = kinematics[side]
            controls = tuple(float(v) for v in definition["control_values"])
            minimum = float(geometry[f"{side}_cylinder_minimum_volume"])
            maximum = float(geometry[f"{side}_cylinder_maximum_volume"])
        except KeyError as error:
            raise ValueError(
                f"Missing required solver configuration field: {error.args[0]}"
            ) from error

        first = definition.get("maximum_absolute_first_derivative")
        second = definition.get("maximum_absolute_second_derivative")
        return FreeMotionTarget(
            control_values=controls,
            minimum_volume=minimum,
            maximum_volume=maximum,
            maximum_absolute_first_derivative=None if first is None else float(first),
            maximum_absolute_second_derivative=None if second is None else float(second),
        )

    return FreeKinematicsTarget(small=motion("small"), large=motion("large"))
