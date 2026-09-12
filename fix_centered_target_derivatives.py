#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
SYNTH = ROOT
ENGINE = ROOT.parent / "dada-engine-solver"

if SYNTH.name != "dada-4bar-synthesis":
    raise SystemExit("Run this script from the dada-4bar-synthesis repository root.")
if not ENGINE.exists():
    raise SystemExit(f"Sibling engine repository not found: {ENGINE}")

engine_path = ENGINE / "examples" / "export_motor_champion_motion_target.py"
text = engine_path.read_text(encoding="utf-8")

old_rows = '''                "small_centered_minus1_plus1": 2.0 * q_s - 1.0,
                "large_centered_minus1_plus1": 2.0 * q_l - 1.0,
                "small_dq_dtheta_per_rad": dq_s,
                "large_dq_dtheta_per_rad": dq_l,
                "small_d2q_dtheta2_per_rad2": d2q_s,
                "large_d2q_dtheta2_per_rad2": d2q_l,
'''
new_rows = '''                "small_centered_minus1_plus1": 2.0 * q_s - 1.0,
                "large_centered_minus1_plus1": 2.0 * q_l - 1.0,
                "small_dq_dtheta_per_rad": dq_s,
                "large_dq_dtheta_per_rad": dq_l,
                "small_d2q_dtheta2_per_rad2": d2q_s,
                "large_d2q_dtheta2_per_rad2": d2q_l,
                "small_centered_dq_dtheta_per_rad": 2.0 * dq_s,
                "large_centered_dq_dtheta_per_rad": 2.0 * dq_l,
                "small_centered_d2q_dtheta2_per_rad2": 2.0 * d2q_s,
                "large_centered_d2q_dtheta2_per_rad2": 2.0 * d2q_l,
'''
if old_rows not in text:
    raise SystemExit("Could not find expected CSV row block in engine exporter.")
text = text.replace(old_rows, new_rows, 1)

old_meta = '''        "recommended_mechanism_fit_coordinates": {
            "small": "small_centered_minus1_plus1",
            "large": "large_centered_minus1_plus1",
            "derivative_small": "small_dq_dtheta_per_rad",
            "derivative_large": "large_dq_dtheta_per_rad",
            "note": (
'''
new_meta = '''        "recommended_mechanism_fit_coordinates": {
            "small": "small_centered_minus1_plus1",
            "large": "large_centered_minus1_plus1",
            "derivative_small": "small_centered_dq_dtheta_per_rad",
            "derivative_large": "large_centered_dq_dtheta_per_rad",
            "second_derivative_small": "small_centered_d2q_dtheta2_per_rad2",
            "second_derivative_large": "large_centered_d2q_dtheta2_per_rad2",
            "note": (
'''
if old_meta not in text:
    raise SystemExit("Could not find expected metadata block in engine exporter.")
text = text.replace(old_meta, new_meta, 1)
engine_path.write_text(text, encoding="utf-8")
print(f"patched {engine_path}")

io_path = SYNTH / "src" / "dada_4bar_synthesis" / "io.py"
text = io_path.read_text(encoding="utf-8")

old_defaults = '''_DEFAULT_FIT_COLUMNS = {
    "small": "small_centered_minus1_plus1",
    "large": "large_centered_minus1_plus1",
    "derivative_small": "small_dq_dtheta_per_rad",
    "derivative_large": "large_dq_dtheta_per_rad",
}
'''
new_defaults = '''_DEFAULT_FIT_COLUMNS = {
    "small": "small_centered_minus1_plus1",
    "large": "large_centered_minus1_plus1",
    "derivative_small": "small_centered_dq_dtheta_per_rad",
    "derivative_large": "large_centered_dq_dtheta_per_rad",
}
'''
if old_defaults not in text:
    raise SystemExit("Could not find expected defaults block in synthesis loader.")
text = text.replace(old_defaults, new_defaults, 1)

old_columns = '''    column_small = str(recommended["small"])
    column_large = str(recommended["large"])
    column_dsmall = str(recommended["derivative_small"])
    column_dlarge = str(recommended["derivative_large"])

    theta: list[float] = []
'''
new_columns = '''    column_small = str(recommended["small"])
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
'''
if old_columns not in text:
    raise SystemExit("Could not find expected column selection block in synthesis loader.")
text = text.replace(old_columns, new_columns, 1)

old_second = '''        have_second = (
            "small_d2q_dtheta2_per_rad2" in reader.fieldnames
            and "large_d2q_dtheta2_per_rad2" in reader.fieldnames
        )
'''
new_second = '''        if column_d2small is not None:
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
'''
if old_second not in text:
    raise SystemExit("Could not find expected second-derivative detection block.")
text = text.replace(old_second, new_second, 1)

old_load_second = '''            if have_second:
                d2small.append(_float(row, "small_d2q_dtheta2_per_rad2"))
                d2large.append(_float(row, "large_d2q_dtheta2_per_rad2"))
'''
new_load_second = '''            if have_second:
                assert column_d2small is not None
                assert column_d2large is not None
                d2small.append(_float(row, column_d2small))
                d2large.append(_float(row, column_d2large))
'''
if old_load_second not in text:
    raise SystemExit("Could not find expected second-derivative load block.")
text = text.replace(old_load_second, new_load_second, 1)

io_path.write_text(text, encoding="utf-8")
print(f"patched {io_path}")

test_path = SYNTH / "tests" / "test_motion_target_io.py"
text = test_path.read_text(encoding="utf-8")
if "test_rejects_legacy_centered_motion_with_uncentered_derivative" not in text:
    text += '''

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
'''
    test_path.write_text(text, encoding="utf-8")
    print(f"updated {test_path}")

print()
print("Patch complete.")
print("Next:")
print("  1. Regenerate the champion target in ../dada-engine-solver")
print("  2. Back here, run: python -m pytest")
print("  3. Re-run the projection search")
