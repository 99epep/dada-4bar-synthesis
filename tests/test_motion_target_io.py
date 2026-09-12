import csv
import json
import math

import pytest

from dada_4bar_synthesis.io import load_solver_motion_target


def write_target(tmp_path, *, periodic=True):
    json_path = tmp_path / "target.json"
    csv_path = tmp_path / "target.csv"
    metadata = {
        "purpose": "test mechanism target",
        "angle_convention": "Study angle before motor-operation direction transformation; physical crank direction/sign may be chosen later.",
        "cylinder_limits": {
            "small": {"minimum_m3": 1e-5, "maximum_m3": 4e-5, "swept_m3": 3e-5},
            "large": {"minimum_m3": 2e-5, "maximum_m3": 1.2e-4, "swept_m3": 1e-4},
        },
        "csv_sampling": {"step_deg": 90.0, "rows_including_360_deg": 5},
        "recommended_mechanism_fit_coordinates": {
            "small": "sq",
            "large": "lq",
            "derivative_small": "sdq",
            "derivative_large": "ldq",
        },
    }
    json_path.write_text(json.dumps(metadata), encoding="utf-8")

    rows = []
    for index, theta in enumerate((0.0, math.pi/2, math.pi, 3*math.pi/2, 2*math.pi)):
        q = math.cos(theta)
        last_small = q if periodic or index != 4 else q + 0.1
        rows.append({
            "theta_rad": theta,
            "sq": last_small,
            "lq": -q,
            "sdq": -math.sin(theta),
            "ldq": math.sin(theta),
            "small_d2q_dtheta2_per_rad2": -q,
            "large_d2q_dtheta2_per_rad2": q,
        })
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return csv_path, json_path


def test_loads_solver_motion_target_and_removes_duplicate_endpoint(tmp_path):
    csv_path, json_path = write_target(tmp_path)
    target = load_solver_motion_target(csv_path, json_path)

    assert target.sample_count == 4
    assert target.theta_rad == pytest.approx((0.0, math.pi/2, math.pi, 3*math.pi/2))
    assert target.small_q == pytest.approx((1.0, 0.0, -1.0, 0.0), abs=1e-12)
    assert target.large_q == pytest.approx((-1.0, 0.0, 1.0, 0.0), abs=1e-12)
    assert target.small_d2q_dtheta2 is not None
    assert target.small_limits.swept_m3 == pytest.approx(3e-5)
    assert target.large_limits.swept_m3 == pytest.approx(1e-4)
    assert target.sample_step_deg == pytest.approx(90.0)


def test_infers_sibling_json_path(tmp_path):
    csv_path, _ = write_target(tmp_path)
    target = load_solver_motion_target(csv_path)
    assert target.source_purpose == "test mechanism target"


def test_rejects_nonperiodic_duplicate_endpoint(tmp_path):
    csv_path, json_path = write_target(tmp_path, periodic=False)
    with pytest.raises(ValueError, match="not periodic duplicates"):
        load_solver_motion_target(csv_path, json_path)


def test_rejects_legacy_centered_motion_with_uncentered_derivative(tmp_path):
    csv_path, json_path = write_target(tmp_path)
    metadata = json.loads(json_path.read_text(encoding="utf-8"))
    metadata["recommended_mechanism_fit_coordinates"] = {
        "small": "small_centered_minus1_plus1",
        "large": "large_centered_minus1_plus1",
        "derivative_small": "small_dq_dtheta_per_rad",
        "derivative_large": "large_dq_dtheta_per_rad",
    }
    json_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match="Inconsistent legacy motion-target derivatives"):
        load_solver_motion_target(csv_path, json_path)
