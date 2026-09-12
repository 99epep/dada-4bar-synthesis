import math

import numpy as np
import pytest

from dada_4bar_synthesis.projection import (
    NormalizedFourBarGeometry,
    evaluate_four_bar,
    fit_projection,
    projection_basis,
    search_projection,
)


def angles(count=360):
    return np.linspace(0.0, 2.0 * math.pi, count, endpoint=False)


def geometry(branch=-1):
    return NormalizedFourBarGeometry(2.0, 1.7, 1.6, 0.4, branch)


def test_analytic_basis_derivatives_match_centered_difference():
    theta = angles(180)
    item = geometry()
    motion = evaluate_four_bar(theta, item)
    step = 1.0e-6
    before = evaluate_four_bar(theta - step, item)
    after = evaluate_four_bar(theta + step, item)

    np.testing.assert_allclose(
        motion.rocker_unit_derivative,
        (after.rocker_unit - before.rocker_unit) / (2.0 * step),
        rtol=2e-8,
        atol=2e-9,
    )
    np.testing.assert_allclose(
        motion.coupler_unit_derivative,
        (after.coupler_unit - before.coupler_unit) / (2.0 * step),
        rtol=2e-8,
        atol=2e-9,
    )


def test_rejects_geometry_that_cannot_complete_a_revolution():
    with pytest.raises(ValueError, match="outer closure"):
        evaluate_four_bar(angles(), NormalizedFourBarGeometry(2.0, 1.0, 1.0))


def test_rocker_projection_is_recovered_exactly():
    motion = evaluate_four_bar(angles(), geometry())
    position, derivative = projection_basis(motion, "rocker")
    exact = np.array((0.13, 0.72, -0.31))
    q = position @ exact
    dq = derivative @ exact

    fit = fit_projection(
        motion,
        q,
        output_type="rocker",
        target_dq_dtheta=dq,
        derivative_weight=0.3,
        phase_rad=geometry().phase_rad,
    )

    assert fit.position_rms < 1e-12
    assert fit.derivative_rms is not None and fit.derivative_rms < 1e-12
    assert fit.coefficients == pytest.approx(exact, abs=1e-12)
    assert fit.recovery is not None
    assert fit.recovery.output_along_ratio == pytest.approx(1.0)
    assert fit.recovery.output_normal_ratio == pytest.approx(0.0)


def test_coupler_projection_recovers_physical_point():
    motion = evaluate_four_bar(angles(), geometry())
    axis = 0.7
    scale = 0.8
    along = 1.25
    normal = -0.45
    coefficients = np.array(
        (
            -0.11,
            scale * math.cos(axis),
            scale * math.sin(axis),
            scale * (along * math.cos(axis) + normal * math.sin(axis)),
            scale * (along * math.sin(axis) - normal * math.cos(axis)),
        )
    )
    position, derivative = projection_basis(motion, "coupler")
    q = position @ coefficients
    dq = derivative @ coefficients

    fit = fit_projection(
        motion,
        q,
        output_type="coupler",
        target_dq_dtheta=dq,
        derivative_weight=0.2,
        phase_rad=geometry().phase_rad,
    )

    assert fit.position_rms < 1e-12
    assert fit.recovery is not None
    assert fit.recovery.axis_angle_canonical_rad == pytest.approx(axis)
    assert fit.recovery.axis_angle_shared_crank_rad == pytest.approx(axis - 0.4)
    assert fit.recovery.output_along_ratio == pytest.approx(along)
    assert fit.recovery.output_normal_ratio == pytest.approx(normal)
    assert fit.recovery.normalized_projection_scale == pytest.approx(scale)


def test_search_recovers_a_synthetic_coupler_target():
    theta = angles(240)
    true_geometry = geometry()
    motion = evaluate_four_bar(theta, true_geometry)
    position, derivative = projection_basis(motion, "coupler")
    coefficients = np.array((-0.1, 0.4, 0.7, 1.2, -0.5))
    q = position @ coefficients
    dq = derivative @ coefficients

    result = search_projection(
        theta,
        q,
        output_type="coupler",
        assembly_branch=-1,
        target_dq_dtheta=dq,
        ratio_minimum=1.0,
        ratio_maximum=2.6,
        maximum_iterations=35,
        population_size=8,
        seed=3,
    )

    assert result.fit.position_rms < 2e-5
