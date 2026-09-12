import math

import pytest

from dada_4bar_synthesis.contracts import (
    AssemblyContract,
    FourBarLoopContract,
    OutputPointContract,
    SharedCrankFourBarContract,
    SliderConstraintContract,
)
from dada_4bar_synthesis.io import load_solver_free_kinematics_target


def test_loads_current_solver_free_kinematics_format(tmp_path):
    path = tmp_path / "solver.toml"
    path.write_text(
        """
[geometry]
small_cylinder_minimum_volume = 1.0e-5
small_cylinder_maximum_volume = 4.0e-5
large_cylinder_minimum_volume = 2.0e-5
large_cylinder_maximum_volume = 1.2e-4

[kinematics]
type = "free"

[kinematics.small]
control_values = [0.2, 0.85, 1.0, 0.6, 0.1, 0.0]

[kinematics.large]
control_values = [1.0, 0.7, 0.1, 0.0, 0.3, 0.9]
maximum_absolute_first_derivative = 0.001
""",
        encoding="utf-8",
    )

    target = load_solver_free_kinematics_target(path)

    assert target.small.control_values == (0.2, 0.85, 1.0, 0.6, 0.1, 0.0)
    assert target.small.minimum_volume == pytest.approx(1.0e-5)
    assert target.small.maximum_volume == pytest.approx(4.0e-5)
    assert target.large.minimum_volume == pytest.approx(2.0e-5)
    assert target.large.maximum_volume == pytest.approx(1.2e-4)
    assert target.large.maximum_absolute_first_derivative == pytest.approx(0.001)
    assert target.cycle_angle == pytest.approx(2.0 * math.pi)


def test_rejects_non_free_solver_kinematics(tmp_path):
    path = tmp_path / "solver.toml"
    path.write_text(
        """
[geometry]
small_cylinder_minimum_volume = 1.0e-5
small_cylinder_maximum_volume = 4.0e-5
large_cylinder_minimum_volume = 2.0e-5
large_cylinder_maximum_volume = 1.2e-4

[kinematics]
type = "shared_crank_rocker"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="type = 'free'"):
        load_solver_free_kinematics_target(path)


def test_output_contract_matches_low_level_solver_concepts():
    assembly = AssemblyContract(
        loop=FourBarLoopContract(
            coupler_length=0.12,
            rocker_length=0.14,
            rocker_pivot_x=0.10,
            rocker_pivot_y=0.0,
            assembly_branch=1,
        ),
        output=OutputPointContract(
            type="coupler",
            along=0.09,
            normal=-0.04,
        ),
        slider=SliderConstraintContract(
            axis_origin_x=0.0,
            axis_origin_y=-0.02,
            axis_angle=0.37,
            connecting_rod_length=0.30,
            assembly_branch=1,
        ),
    )

    result = SharedCrankFourBarContract(
        schema_version=1,
        crank_radius=0.045,
        small_assembly=assembly,
        large_assembly=assembly,
        crank_angle_offset=0.2,
        crank_direction=-1,
    )

    raw = result.to_dict()
    assert raw["schema_version"] == 1
    assert raw["small_assembly"]["output"]["type"] == "coupler"
    assert raw["small_assembly"]["slider"]["axis_angle"] == pytest.approx(0.37)
    assert raw["crank_direction"] == -1
