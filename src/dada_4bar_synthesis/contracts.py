"""Versioned I/O contracts aligned with dada-engine-solver conventions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Literal


def _finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")


def _positive(name: str, value: float) -> None:
    _finite(name, value)
    if value <= 0.0:
        raise ValueError(f"{name} must be positive.")


@dataclass(frozen=True, slots=True)
class CylinderTargetLimits:
    """Physical cylinder-volume limits carried by a synthesis target."""

    minimum_m3: float
    maximum_m3: float

    def __post_init__(self) -> None:
        _positive("minimum volume", self.minimum_m3)
        _positive("maximum volume", self.maximum_m3)
        if self.maximum_m3 <= self.minimum_m3:
            raise ValueError("Maximum volume must exceed minimum volume.")

    @property
    def swept_m3(self) -> float:
        return self.maximum_m3 - self.minimum_m3


@dataclass(frozen=True, slots=True)
class SampledMotionTarget:
    """Sampled two-cylinder target emitted by dada-engine-solver.

    The shape coordinates are dimensionless centered motions, normally in the
    solver's -1..+1 convention. Angles are study angles in radians. A duplicated
    2*pi endpoint must already have been removed by the loader.
    """

    theta_rad: tuple[float, ...]
    small_q: tuple[float, ...]
    large_q: tuple[float, ...]
    small_dq_dtheta: tuple[float, ...]
    large_dq_dtheta: tuple[float, ...]
    small_limits: CylinderTargetLimits
    large_limits: CylinderTargetLimits
    small_d2q_dtheta2: tuple[float, ...] | None = None
    large_d2q_dtheta2: tuple[float, ...] | None = None
    angle_convention: str = "study_angle_radians"
    source_purpose: str | None = None
    sample_step_deg: float | None = None

    def __post_init__(self) -> None:
        n = len(self.theta_rad)
        if n < 4:
            raise ValueError("At least four unique angular samples are required.")

        required = (
            ("small_q", self.small_q),
            ("large_q", self.large_q),
            ("small_dq_dtheta", self.small_dq_dtheta),
            ("large_dq_dtheta", self.large_dq_dtheta),
        )
        optional = (
            ("small_d2q_dtheta2", self.small_d2q_dtheta2),
            ("large_d2q_dtheta2", self.large_d2q_dtheta2),
        )
        for name, values in required:
            if len(values) != n:
                raise ValueError(f"{name} must contain {n} samples.")
            if not all(math.isfinite(value) for value in values):
                raise ValueError(f"{name} samples must be finite.")
        for name, values in optional:
            if values is not None:
                if len(values) != n:
                    raise ValueError(f"{name} must contain {n} samples.")
                if not all(math.isfinite(value) for value in values):
                    raise ValueError(f"{name} samples must be finite.")

        if not all(math.isfinite(value) for value in self.theta_rad):
            raise ValueError("theta_rad samples must be finite.")
        if not math.isclose(self.theta_rad[0], 0.0, abs_tol=1.0e-12):
            raise ValueError("The target must start at study angle 0 rad.")
        if any(right <= left for left, right in zip(self.theta_rad, self.theta_rad[1:])):
            raise ValueError("theta_rad samples must be strictly increasing.")
        if self.theta_rad[-1] >= 2.0 * math.pi - 1.0e-12:
            raise ValueError("The duplicated 2*pi endpoint must not be stored in the target.")

        if self.angle_convention != "study_angle_radians":
            raise ValueError("Unsupported angle convention.")
        if self.sample_step_deg is not None:
            _positive("sample step", self.sample_step_deg)

    @property
    def sample_count(self) -> int:
        return len(self.theta_rad)


@dataclass(frozen=True, slots=True)
class FreeMotionTarget:
    """Legacy/secondary input: one FreeKinematics motion definition."""

    control_values: tuple[float, ...]
    minimum_volume: float
    maximum_volume: float
    maximum_absolute_first_derivative: float | None = None
    maximum_absolute_second_derivative: float | None = None

    def __post_init__(self) -> None:
        if len(self.control_values) < 4:
            raise ValueError("At least four control values are required.")
        if not all(math.isfinite(v) for v in self.control_values):
            raise ValueError("Control values must be finite.")
        _positive("minimum volume", self.minimum_volume)
        _positive("maximum volume", self.maximum_volume)
        if self.maximum_volume <= self.minimum_volume:
            raise ValueError("Maximum volume must exceed minimum volume.")
        for name, value in (
            ("maximum absolute first derivative", self.maximum_absolute_first_derivative),
            ("maximum absolute second derivative", self.maximum_absolute_second_derivative),
        ):
            if value is not None:
                _finite(name, value)
                if value < 0.0:
                    raise ValueError(f"{name} must be non-negative.")


@dataclass(frozen=True, slots=True)
class FreeKinematicsTarget:
    """Secondary two-cylinder target in the solver study-angle convention."""

    small: FreeMotionTarget
    large: FreeMotionTarget
    angle_convention: str = "study_angle_radians"
    cycle_angle: float = 2.0 * math.pi
    source_kinematics_type: str = "free"

    def __post_init__(self) -> None:
        if self.angle_convention != "study_angle_radians":
            raise ValueError("Unsupported angle convention.")
        if not math.isclose(self.cycle_angle, 2.0 * math.pi):
            raise ValueError("A DADA kinematic cycle must be 2*pi radians.")
        if self.source_kinematics_type != "free":
            raise ValueError("Free-kinematics target must have source type 'free'.")


@dataclass(frozen=True, slots=True)
class FourBarLoopContract:
    """Direct counterpart of dada_solver.four_bar.FourBarLoop."""

    coupler_length: float
    rocker_length: float
    rocker_pivot_x: float
    rocker_pivot_y: float
    assembly_branch: int = 1

    def __post_init__(self) -> None:
        _positive("coupler length", self.coupler_length)
        _positive("rocker length", self.rocker_length)
        _finite("rocker pivot x", self.rocker_pivot_x)
        _finite("rocker pivot y", self.rocker_pivot_y)
        if self.assembly_branch not in (-1, 1):
            raise ValueError("assembly_branch must be -1 or 1.")


@dataclass(frozen=True, slots=True)
class OutputPointContract:
    """Counterpart of RockerOutputPoint or CouplerOutputPoint."""

    type: Literal["rocker", "coupler"]
    along: float
    normal: float = 0.0

    def __post_init__(self) -> None:
        if self.type not in ("rocker", "coupler"):
            raise ValueError("Output type must be 'rocker' or 'coupler'.")
        _finite("output along coordinate", self.along)
        _finite("output normal coordinate", self.normal)


@dataclass(frozen=True, slots=True)
class SliderConstraintContract:
    """Direct counterpart of dada_solver.four_bar.SliderConstraint."""

    axis_origin_x: float
    axis_origin_y: float
    axis_angle: float
    connecting_rod_length: float
    assembly_branch: int = 1

    def __post_init__(self) -> None:
        _finite("slider axis origin x", self.axis_origin_x)
        _finite("slider axis origin y", self.axis_origin_y)
        _finite("slider axis angle", self.axis_angle)
        _positive("connecting rod length", self.connecting_rod_length)
        if self.assembly_branch not in (-1, 1):
            raise ValueError("slider assembly_branch must be -1 or 1.")


@dataclass(frozen=True, slots=True)
class AssemblyContract:
    """One complete four-bar plus slider assembly."""

    loop: FourBarLoopContract
    output: OutputPointContract
    slider: SliderConstraintContract


@dataclass(frozen=True, slots=True)
class SharedCrankFourBarContract:
    """Mechanical result directly mappable to the solver four-bar backend."""

    schema_version: int
    crank_radius: float
    small_assembly: AssemblyContract
    large_assembly: AssemblyContract
    small_volume_increases_with_coordinate: bool = True
    large_volume_increases_with_coordinate: bool = True
    crank_angle_offset: float = 0.0
    crank_direction: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("Only schema_version=1 is supported.")
        _positive("crank radius", self.crank_radius)
        _finite("crank angle offset", self.crank_angle_offset)
        if self.crank_direction not in (-1, 1):
            raise ValueError("crank_direction must be -1 or 1.")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
