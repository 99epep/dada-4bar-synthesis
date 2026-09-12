"""Read target laws using dada-engine-solver's current TOML conventions."""

from __future__ import annotations

from pathlib import Path
import tomllib

from .contracts import FreeKinematicsTarget, FreeMotionTarget


def load_solver_free_kinematics_target(
    path: str | Path,
) -> FreeKinematicsTarget:
    """Load a free target from a normal dada-engine-solver TOML file.

    Reads the same source fields used by
    dada_solver.configuration._load_free_kinematics().
    No motor-direction or phase transformation is performed here.
    """

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
            "dada-4bar-synthesis initially accepts only "
            "[kinematics] type = 'free'."
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
            maximum_absolute_first_derivative=(
                None if first is None else float(first)
            ),
            maximum_absolute_second_derivative=(
                None if second is None else float(second)
            ),
        )

    return FreeKinematicsTarget(
        small=motion("small"),
        large=motion("large"),
    )
