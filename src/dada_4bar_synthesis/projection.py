"""Projection-only inverse synthesis for a normalized four-bar loop."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Literal

import numpy as np
from scipy.optimize import differential_evolution

OutputType = Literal["rocker", "coupler"]


@dataclass(frozen=True, slots=True)
class NormalizedFourBarGeometry:
    """Scale-free four-bar geometry with crank radius fixed to one."""

    ground_ratio: float
    coupler_ratio: float
    rocker_ratio: float
    phase_rad: float = 0.0
    assembly_branch: int = 1

    def __post_init__(self) -> None:
        for name, value in (
            ("ground_ratio", self.ground_ratio),
            ("coupler_ratio", self.coupler_ratio),
            ("rocker_ratio", self.rocker_ratio),
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive.")
        if not math.isfinite(self.phase_rad):
            raise ValueError("phase_rad must be finite.")
        if self.assembly_branch not in (-1, 1):
            raise ValueError("assembly_branch must be -1 or 1.")

    @property
    def ground_pivot_angle_rad(self) -> float:
        """Equivalent pivot angle when the shared crank phase is set to zero."""

        return -self.phase_rad

    @property
    def rocker_pivot_x_ratio(self) -> float:
        return self.ground_ratio * math.cos(self.ground_pivot_angle_rad)

    @property
    def rocker_pivot_y_ratio(self) -> float:
        return self.ground_ratio * math.sin(self.ground_pivot_angle_rad)

    def to_dict(self) -> dict[str, object]:
        raw = asdict(self)
        raw.update(
            ground_pivot_angle_rad=self.ground_pivot_angle_rad,
            rocker_pivot_x_ratio=self.rocker_pivot_x_ratio,
            rocker_pivot_y_ratio=self.rocker_pivot_y_ratio,
        )
        return raw


@dataclass(frozen=True, slots=True)
class FourBarMotion:
    """Vector basis functions and analytic derivatives over one sampled cycle."""

    crank_xy: np.ndarray
    crank_dxy_dtheta: np.ndarray
    coupler_unit: np.ndarray
    coupler_unit_derivative: np.ndarray
    rocker_unit: np.ndarray
    rocker_unit_derivative: np.ndarray
    minimum_cross_product: float
    outer_closure_margin: float
    inner_closure_margin: float


@dataclass(frozen=True, slots=True)
class ProjectionRecovery:
    """One physical representative of a projection fit in crank-radius units."""

    axis_angle_canonical_rad: float
    axis_angle_shared_crank_rad: float
    output_along_ratio: float
    output_normal_ratio: float
    normalized_projection_scale: float

    @property
    def output_radius_ratio(self) -> float:
        return math.hypot(self.output_along_ratio, self.output_normal_ratio)

    def to_dict(self) -> dict[str, float]:
        raw = asdict(self)
        raw["output_radius_ratio"] = self.output_radius_ratio
        return raw


@dataclass(frozen=True, slots=True)
class ProjectionFit:
    output_type: OutputType
    coefficients: tuple[float, ...]
    position_rms: float
    derivative_rms: float | None
    maximum_absolute_position_error: float
    objective_rms: float
    recovery: ProjectionRecovery | None

    def to_dict(self) -> dict[str, object]:
        raw = asdict(self)
        if self.recovery is not None:
            raw["recovery"] = self.recovery.to_dict()
        return raw


@dataclass(frozen=True, slots=True)
class ProjectionSearchResult:
    geometry: NormalizedFourBarGeometry
    fit: ProjectionFit
    minimum_cross_product: float
    outer_closure_margin: float
    inner_closure_margin: float
    optimizer_success: bool
    optimizer_message: str
    function_evaluations: int

    def to_dict(self) -> dict[str, object]:
        return {
            "geometry": self.geometry.to_dict(),
            "fit": self.fit.to_dict(),
            "minimum_cross_product": self.minimum_cross_product,
            "outer_closure_margin": self.outer_closure_margin,
            "inner_closure_margin": self.inner_closure_margin,
            "optimizer_success": self.optimizer_success,
            "optimizer_message": self.optimizer_message,
            "function_evaluations": self.function_evaluations,
        }


def evaluate_four_bar(
    theta_rad: np.ndarray | tuple[float, ...],
    geometry: NormalizedFourBarGeometry,
    *,
    singularity_tolerance: float = 1.0e-10,
) -> FourBarMotion:
    """Evaluate one complete-rotation four-bar with crank radius normalized to 1."""

    theta = np.asarray(theta_rad, dtype=float)
    if theta.ndim != 1 or theta.size < 1 or not np.all(np.isfinite(theta)):
        raise ValueError("theta_rad must be a one-dimensional finite non empty sample array.")
    if not math.isfinite(singularity_tolerance) or singularity_tolerance <= 0.0:
        raise ValueError("singularity_tolerance must be finite and positive.")

    g = geometry.ground_ratio
    c = geometry.coupler_ratio
    r = geometry.rocker_ratio
    scale = max(1.0, g, c, r)
    tolerance = singularity_tolerance * scale

    minimum_center_distance = abs(g - 1.0)
    maximum_center_distance = g + 1.0
    outer_margin = c + r - maximum_center_distance
    inner_margin = minimum_center_distance - abs(c - r)
    if minimum_center_distance <= tolerance:
        raise ValueError("Four-bar circle centers coincide or nearly coincide during the cycle.")
    if outer_margin <= tolerance:
        raise ValueError("Four-bar cannot complete a crank revolution: outer closure limit.")
    if inner_margin <= tolerance:
        raise ValueError("Four-bar cannot complete a crank revolution: inner closure limit.")

    crank_angle = theta + geometry.phase_rad
    crank = np.column_stack((np.cos(crank_angle), np.sin(crank_angle)))
    crank_derivative = np.column_stack((-np.sin(crank_angle), np.cos(crank_angle)))
    pivot = np.array((g, 0.0), dtype=float)

    delta = pivot - crank
    distance = np.linalg.norm(delta, axis=1)
    direction = delta / distance[:, None]
    along = (c * c - r * r + distance * distance) / (2.0 * distance)
    height_squared = c * c - along * along
    if np.any(height_squared <= tolerance * tolerance):
        raise ValueError("Four-bar reaches a toggle singularity.")
    height = np.sqrt(height_squared)
    left_normal = np.column_stack((-direction[:, 1], direction[:, 0]))
    joint = (
        crank
        + along[:, None] * direction
        + geometry.assembly_branch * height[:, None] * left_normal
    )

    coupler_vector = joint - crank
    rocker_vector = joint - pivot
    determinant = (
        coupler_vector[:, 0] * rocker_vector[:, 1]
        - coupler_vector[:, 1] * rocker_vector[:, 0]
    )
    if np.any(np.abs(determinant) <= singularity_tolerance * scale * scale):
        raise ValueError("Four-bar velocity closure is singular.")

    velocity_rhs = np.sum(coupler_vector * crank_derivative, axis=1)
    joint_derivative = np.column_stack(
        (
            velocity_rhs * rocker_vector[:, 1] / determinant,
            -velocity_rhs * rocker_vector[:, 0] / determinant,
        )
    )

    coupler_unit = coupler_vector / c
    rocker_unit = rocker_vector / r
    coupler_unit_derivative = (joint_derivative - crank_derivative) / c
    rocker_unit_derivative = joint_derivative / r
    minimum_cross = float(np.min(np.abs(determinant) / (c * r)))

    return FourBarMotion(
        crank_xy=crank,
        crank_dxy_dtheta=crank_derivative,
        coupler_unit=coupler_unit,
        coupler_unit_derivative=coupler_unit_derivative,
        rocker_unit=rocker_unit,
        rocker_unit_derivative=rocker_unit_derivative,
        minimum_cross_product=minimum_cross,
        outer_closure_margin=outer_margin,
        inner_closure_margin=inner_margin,
    )


def projection_basis(
    motion: FourBarMotion,
    output_type: OutputType,
) -> tuple[np.ndarray, np.ndarray]:
    """Return the linear position basis and its analytic angular derivative."""

    count = motion.crank_xy.shape[0]
    ones = np.ones(count)
    zeros = np.zeros(count)
    if output_type == "rocker":
        position = np.column_stack(
            (ones, motion.rocker_unit[:, 0], motion.rocker_unit[:, 1])
        )
        derivative = np.column_stack(
            (
                zeros,
                motion.rocker_unit_derivative[:, 0],
                motion.rocker_unit_derivative[:, 1],
            )
        )
    elif output_type == "coupler":
        position = np.column_stack(
            (
                ones,
                motion.crank_xy[:, 0],
                motion.crank_xy[:, 1],
                motion.coupler_unit[:, 0],
                motion.coupler_unit[:, 1],
            )
        )
        derivative = np.column_stack(
            (
                zeros,
                motion.crank_dxy_dtheta[:, 0],
                motion.crank_dxy_dtheta[:, 1],
                motion.coupler_unit_derivative[:, 0],
                motion.coupler_unit_derivative[:, 1],
            )
        )
    else:
        raise ValueError("output_type must be 'rocker' or 'coupler'.")
    return position, derivative


def _recover_projection(
    coefficients: np.ndarray,
    output_type: OutputType,
    phase_rad: float,
) -> ProjectionRecovery | None:
    if output_type == "rocker":
        x, y = float(coefficients[1]), float(coefficients[2])
        scale = math.hypot(x, y)
        if scale <= 64.0 * np.finfo(float).eps:
            return None
        axis = math.atan2(y, x)
        # Gauge choice: place E one crank radius along the rocker. Any radial
        # scaling is equivalent in projection-only synthesis and is absorbed by
        # normalized_projection_scale.
        return ProjectionRecovery(
            axis_angle_canonical_rad=axis,
            axis_angle_shared_crank_rad=axis - phase_rad,
            output_along_ratio=1.0,
            output_normal_ratio=0.0,
            normalized_projection_scale=scale,
        )

    crank_x, crank_y = float(coefficients[1]), float(coefficients[2])
    scale = math.hypot(crank_x, crank_y)
    if scale <= 64.0 * np.finfo(float).eps:
        return None
    axis = math.atan2(crank_y, crank_x)
    coupler_x, coupler_y = float(coefficients[3]), float(coefficients[4])
    along = (coupler_x * math.cos(axis) + coupler_y * math.sin(axis)) / scale
    normal = (coupler_x * math.sin(axis) - coupler_y * math.cos(axis)) / scale
    return ProjectionRecovery(
        axis_angle_canonical_rad=axis,
        axis_angle_shared_crank_rad=axis - phase_rad,
        output_along_ratio=along,
        output_normal_ratio=normal,
        normalized_projection_scale=scale,
    )


def fit_projection(
    motion: FourBarMotion,
    target_q: np.ndarray | tuple[float, ...],
    *,
    output_type: OutputType,
    target_dq_dtheta: np.ndarray | tuple[float, ...] | None = None,
    derivative_weight: float = 0.0,
    phase_rad: float = 0.0,
) -> ProjectionFit:
    """Solve analytically for the best output point/projection coefficients."""

    q = np.asarray(target_q, dtype=float)
    if q.ndim != 1 or not np.all(np.isfinite(q)):
        raise ValueError("target_q must be a one-dimensional finite array.")
    position_basis, derivative_basis = projection_basis(motion, output_type)
    if len(q) != position_basis.shape[0]:
        raise ValueError("target_q sample count does not match the four-bar motion.")
    if not math.isfinite(derivative_weight) or derivative_weight < 0.0:
        raise ValueError("derivative_weight must be finite and non-negative.")

    dq = None
    if target_dq_dtheta is not None:
        dq = np.asarray(target_dq_dtheta, dtype=float)
        if dq.shape != q.shape or not np.all(np.isfinite(dq)):
            raise ValueError("target_dq_dtheta must match target_q with finite values.")
    if derivative_weight > 0.0 and dq is None:
        raise ValueError("A derivative target is required when derivative_weight is positive.")

    if derivative_weight > 0.0:
        root_weight = math.sqrt(derivative_weight)
        matrix = np.vstack((position_basis, root_weight * derivative_basis))
        rhs = np.concatenate((q, root_weight * dq))
    else:
        matrix = position_basis
        rhs = q

    coefficients, *_ = np.linalg.lstsq(matrix, rhs, rcond=None)
    predicted = position_basis @ coefficients
    position_error = predicted - q
    position_rms = float(np.sqrt(np.mean(position_error * position_error)))
    maximum_error = float(np.max(np.abs(position_error)))

    derivative_rms = None
    derivative_term = 0.0
    if dq is not None:
        derivative_error = derivative_basis @ coefficients - dq
        derivative_rms = float(np.sqrt(np.mean(derivative_error * derivative_error)))
        derivative_term = derivative_weight * derivative_rms * derivative_rms
    objective_rms = math.sqrt(position_rms * position_rms + derivative_term)

    return ProjectionFit(
        output_type=output_type,
        coefficients=tuple(float(value) for value in coefficients),
        position_rms=position_rms,
        derivative_rms=derivative_rms,
        maximum_absolute_position_error=maximum_error,
        objective_rms=objective_rms,
        recovery=_recover_projection(coefficients, output_type, phase_rad),
    )


def search_projection(
    theta_rad: np.ndarray | tuple[float, ...],
    target_q: np.ndarray | tuple[float, ...],
    *,
    output_type: OutputType,
    assembly_branch: int,
    target_dq_dtheta: np.ndarray | tuple[float, ...] | None = None,
    derivative_weight: float = 0.0,
    ratio_minimum: float = 0.2,
    ratio_maximum: float = 6.0,
    maximum_output_to_coupler_ratio: float | None = None,
    maximum_iterations: int = 80,
    population_size: int = 10,
    seed: int = 27,
) -> ProjectionSearchResult:
    """Search three link ratios and phase; solve output coordinates analytically."""

    if assembly_branch not in (-1, 1):
        raise ValueError("assembly_branch must be -1 or 1.")
    for name, value in (("ratio_minimum", ratio_minimum), ("ratio_maximum", ratio_maximum)):
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name} must be finite and positive.")
    if ratio_maximum <= ratio_minimum:
        raise ValueError("ratio_maximum must exceed ratio_minimum.")
    if maximum_output_to_coupler_ratio is not None:
        if (
            not math.isfinite(maximum_output_to_coupler_ratio)
            or maximum_output_to_coupler_ratio <= 0.0
        ):
            raise ValueError(
                "maximum_output_to_coupler_ratio must be finite and positive."
            )
    if maximum_iterations <= 0 or population_size < 4:
        raise ValueError("Search iteration and population limits are too small.")

    theta = np.asarray(theta_rad, dtype=float)
    q = np.asarray(target_q, dtype=float)
    dq = None if target_dq_dtheta is None else np.asarray(target_dq_dtheta, dtype=float)
    invalid_penalty = 1.0e6

    def objective(vector: np.ndarray) -> float:
        geometry = NormalizedFourBarGeometry(
            ground_ratio=math.exp(float(vector[0])),
            coupler_ratio=math.exp(float(vector[1])),
            rocker_ratio=math.exp(float(vector[2])),
            phase_rad=float(vector[3]),
            assembly_branch=assembly_branch,
        )
        try:
            motion = evaluate_four_bar(theta, geometry)
            fit = fit_projection(
                motion,
                q,
                output_type=output_type,
                target_dq_dtheta=dq,
                derivative_weight=derivative_weight,
                phase_rad=geometry.phase_rad,
            )
        except (ValueError, FloatingPointError, np.linalg.LinAlgError):
            return invalid_penalty

        if (
            output_type == "coupler"
            and maximum_output_to_coupler_ratio is not None
        ):
            recovery = fit.recovery
            if recovery is None:
                return invalid_penalty
            output_to_coupler = (
                recovery.output_radius_ratio / geometry.coupler_ratio
            )
            if output_to_coupler > maximum_output_to_coupler_ratio:
                excess = (
                    output_to_coupler / maximum_output_to_coupler_ratio - 1.0
                )
                return fit.objective_rms + 100.0 * excess * excess

        return fit.objective_rms

    logarithmic_bounds = (math.log(ratio_minimum), math.log(ratio_maximum))
    result = differential_evolution(
        objective,
        bounds=(
            logarithmic_bounds,
            logarithmic_bounds,
            logarithmic_bounds,
            (-math.pi, math.pi),
        ),
        maxiter=maximum_iterations,
        popsize=population_size,
        seed=seed,
        polish=True,
        tol=1.0e-7,
        updating="immediate",
        workers=1,
    )
    if not math.isfinite(float(result.fun)) or float(result.fun) >= invalid_penalty:
        raise ValueError("Search did not find a complete-rotation four-bar geometry.")

    geometry = NormalizedFourBarGeometry(
        ground_ratio=math.exp(float(result.x[0])),
        coupler_ratio=math.exp(float(result.x[1])),
        rocker_ratio=math.exp(float(result.x[2])),
        phase_rad=float(result.x[3]),
        assembly_branch=assembly_branch,
    )
    motion = evaluate_four_bar(theta, geometry)
    fit = fit_projection(
        motion,
        q,
        output_type=output_type,
        target_dq_dtheta=dq,
        derivative_weight=derivative_weight,
        phase_rad=geometry.phase_rad,
    )
    if (
        output_type == "coupler"
        and maximum_output_to_coupler_ratio is not None
    ):
        recovery = fit.recovery
        if recovery is None:
            raise ValueError("Search result has no physical coupler-point recovery.")
        output_to_coupler = recovery.output_radius_ratio / geometry.coupler_ratio
        if output_to_coupler > maximum_output_to_coupler_ratio * (1.0 + 1.0e-5):
            raise ValueError(
                "Search did not satisfy maximum_output_to_coupler_ratio."
            )

    return ProjectionSearchResult(
        geometry=geometry,
        fit=fit,
        minimum_cross_product=motion.minimum_cross_product,
        outer_closure_margin=motion.outer_closure_margin,
        inner_closure_margin=motion.inner_closure_margin,
        optimizer_success=bool(result.success),
        optimizer_message=str(result.message),
        function_evaluations=int(result.nfev),
    )
