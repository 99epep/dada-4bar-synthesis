#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
if ROOT.name != "dada-4bar-synthesis":
    raise SystemExit("Run this script from the dada-4bar-synthesis repository root.")

projection = ROOT / "src" / "dada_4bar_synthesis" / "projection.py"
text = projection.read_text(encoding="utf-8")

replacements = [
(
'''    derivative_weight: float = 0.0,
    ratio_minimum: float = 0.2,
    ratio_maximum: float = 6.0,
    maximum_iterations: int = 80,
''',
'''    derivative_weight: float = 0.0,
    ratio_minimum: float = 0.2,
    ratio_maximum: float = 6.0,
    maximum_output_to_coupler_ratio: float | None = None,
    maximum_iterations: int = 80,
'''
),
(
'''    if ratio_maximum <= ratio_minimum:
        raise ValueError("ratio_maximum must exceed ratio_minimum.")
    if maximum_iterations <= 0 or population_size < 4:
''',
'''    if ratio_maximum <= ratio_minimum:
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
'''
),
(
'''        except (ValueError, FloatingPointError, np.linalg.LinAlgError):
            return invalid_penalty
        return fit.objective_rms
''',
'''        except (ValueError, FloatingPointError, np.linalg.LinAlgError):
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
'''
),
(
'''    fit = fit_projection(
        motion,
        q,
        output_type=output_type,
        target_dq_dtheta=dq,
        derivative_weight=derivative_weight,
        phase_rad=geometry.phase_rad,
    )
    return ProjectionSearchResult(
''',
'''    fit = fit_projection(
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
'''
),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit("Expected projection.py block not found:\n" + old[:200])
    text = text.replace(old, new, 1)

projection.write_text(text, encoding="utf-8")
print(f"patched {projection}")

cli = ROOT / "src" / "dada_4bar_synthesis" / "cli.py"
text = cli.read_text(encoding="utf-8")

replacements = [
(
'''    parser.add_argument("--ratio-minimum", type=float, default=0.2)
    parser.add_argument("--ratio-maximum", type=float, default=6.0)
    parser.add_argument("--maximum-iterations", type=int, default=80)
''',
'''    parser.add_argument("--ratio-minimum", type=float, default=0.2)
    parser.add_argument("--ratio-maximum", type=float, default=6.0)
    parser.add_argument(
        "--max-output-to-coupler-ratio",
        type=float,
        default=None,
        help=(
            "Optional physical bound on |BF|/BC for coupler-point outputs. "
            "Disabled by default."
        ),
    )
    parser.add_argument("--maximum-iterations", type=int, default=80)
'''
),
(
'''                    ratio_minimum=args.ratio_minimum,
                    ratio_maximum=args.ratio_maximum,
                    maximum_iterations=args.maximum_iterations,
''',
'''                    ratio_minimum=args.ratio_minimum,
                    ratio_maximum=args.ratio_maximum,
                    maximum_output_to_coupler_ratio=args.max_output_to_coupler_ratio,
                    maximum_iterations=args.maximum_iterations,
'''
),
(
'''                record = {
                    "side": side,
                    "output_type": output_type,
                    "assembly_branch": branch,
                    **result.to_dict(),
                }
                records.append(record)
''',
'''                record = {
                    "side": side,
                    "output_type": output_type,
                    "assembly_branch": branch,
                    **result.to_dict(),
                }
                recovery = record["fit"].get("recovery")
                if output_type == "coupler" and recovery is not None:
                    record["output_to_coupler_ratio"] = (
                        recovery["output_radius_ratio"]
                        / record["geometry"]["coupler_ratio"]
                    )
                else:
                    record["output_to_coupler_ratio"] = None
                records.append(record)
'''
),
(
'''        if recovery is not None:
            print(
                "   "
                f"axis={math.degrees(recovery['axis_angle_shared_crank_rad']):.4f} deg "
                f"output_along/crank={recovery['output_along_ratio']:.8g} "
                f"output_normal/crank={recovery['output_normal_ratio']:.8g} "
                f"output_radius/crank={recovery['output_radius_ratio']:.8g}"
            )
''',
'''        if recovery is not None:
            extra = ""
            if record["output_to_coupler_ratio"] is not None:
                extra = (
                    f" output_radius/coupler="
                    f"{record['output_to_coupler_ratio']:.8g}"
                )
            print(
                "   "
                f"axis={math.degrees(recovery['axis_angle_shared_crank_rad']):.4f} deg "
                f"output_along/crank={recovery['output_along_ratio']:.8g} "
                f"output_normal/crank={recovery['output_normal_ratio']:.8g} "
                f"output_radius/crank={recovery['output_radius_ratio']:.8g}"
                f"{extra}"
            )
'''
),
(
'''                "ratio_minimum": args.ratio_minimum,
                "ratio_maximum": args.ratio_maximum,
                "maximum_iterations": args.maximum_iterations,
''',
'''                "ratio_minimum": args.ratio_minimum,
                "ratio_maximum": args.ratio_maximum,
                "maximum_output_to_coupler_ratio": args.max_output_to_coupler_ratio,
                "maximum_iterations": args.maximum_iterations,
'''
),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit("Expected cli.py block not found:\n" + old[:200])
    text = text.replace(old, new, 1)

cli.write_text(text, encoding="utf-8")
print(f"patched {cli}")

tests = ROOT / "tests" / "test_projection.py"
text = tests.read_text(encoding="utf-8")
if "test_search_respects_output_to_coupler_bound" not in text:
    text += '''

def test_search_respects_output_to_coupler_bound():
    theta = angles(180)
    true_geometry = geometry()
    motion = evaluate_four_bar(theta, true_geometry)
    position, derivative = projection_basis(motion, "coupler")

    axis = 0.5
    scale = 0.7
    along = 1.1
    normal = 0.2
    coefficients = np.array(
        (
            0.05,
            scale * math.cos(axis),
            scale * math.sin(axis),
            scale * (along * math.cos(axis) + normal * math.sin(axis)),
            scale * (along * math.sin(axis) - normal * math.cos(axis)),
        )
    )
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
        maximum_output_to_coupler_ratio=1.5,
        maximum_iterations=30,
        population_size=8,
        seed=5,
    )

    assert result.fit.recovery is not None
    ratio = (
        result.fit.recovery.output_radius_ratio
        / result.geometry.coupler_ratio
    )
    assert ratio <= 1.5 * (1.0 + 1.0e-5)
'''
    tests.write_text(text, encoding="utf-8")
    print(f"updated {tests}")

print()
print("Next:")
print("  python -m pytest")
print("  for r in 1 1.5 2 3 4; do")
print("    python -m dada_4bar_synthesis \\")
print("      ../dada-engine-solver/outputs/motor_champion_motion_target.csv \\")
print("      --output-type coupler --ratio-maximum 12 \\")
print('      --max-output-to-coupler-ratio "$r" \\')
print('      --result-json "outputs/champion_projection_BF_over_BC_${r}.json"')
print("  done")
