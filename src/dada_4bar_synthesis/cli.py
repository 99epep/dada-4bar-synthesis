"""Command-line entry point for projection-only four-bar synthesis."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .io import load_solver_motion_target
from .projection import search_projection


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fit normalized DADA motion targets with a four-bar output in pure projection."
        )
    )
    parser.add_argument("target_csv", type=Path)
    parser.add_argument("--target-json", type=Path, default=None)
    parser.add_argument("--side", choices=("small", "large", "both"), default="both")
    parser.add_argument(
        "--output-type", choices=("rocker", "coupler", "both"), default="both"
    )
    parser.add_argument("--branch", choices=("-1", "1", "both"), default="both")
    parser.add_argument("--derivative-weight", type=float, default=0.0)
    parser.add_argument("--ratio-minimum", type=float, default=0.2)
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
    parser.add_argument("--population-size", type=int, default=10)
    parser.add_argument("--seed", type=int, default=27)
    parser.add_argument("--result-json", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    target = load_solver_motion_target(args.target_csv, args.target_json)

    sides = ("small", "large") if args.side == "both" else (args.side,)
    output_types = (
        ("rocker", "coupler") if args.output_type == "both" else (args.output_type,)
    )
    branches = (-1, 1) if args.branch == "both" else (int(args.branch),)

    records: list[dict[str, object]] = []
    search_index = 0
    for side in sides:
        q = target.small_q if side == "small" else target.large_q
        dq = target.small_dq_dtheta if side == "small" else target.large_dq_dtheta
        for output_type in output_types:
            for branch in branches:
                result = search_projection(
                    target.theta_rad,
                    q,
                    output_type=output_type,
                    assembly_branch=branch,
                    target_dq_dtheta=dq,
                    derivative_weight=args.derivative_weight,
                    ratio_minimum=args.ratio_minimum,
                    ratio_maximum=args.ratio_maximum,
                    maximum_output_to_coupler_ratio=args.max_output_to_coupler_ratio,
                    maximum_iterations=args.maximum_iterations,
                    population_size=args.population_size,
                    seed=args.seed + search_index,
                )
                search_index += 1
                record = {
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

    records.sort(key=lambda item: float(item["fit"]["objective_rms"]))

    for rank, record in enumerate(records, start=1):
        fit = record["fit"]
        geometry = record["geometry"]
        recovery = fit.get("recovery")
        derivative = fit["derivative_rms"]
        print(
            f"{rank:2d} {record['side']:5s} {record['output_type']:7s} "
            f"branch={record['assembly_branch']:+d} "
            f"RMS={fit['position_rms']:.8g} "
            f"dRMS={'-' if derivative is None else f'{derivative:.8g}'}"
        )
        print(
            "   "
            f"ground/crank={geometry['ground_ratio']:.8g} "
            f"coupler/crank={geometry['coupler_ratio']:.8g} "
            f"rocker/crank={geometry['rocker_ratio']:.8g} "
            f"pivot_angle={math.degrees(geometry['ground_pivot_angle_rad']):.4f} deg "
            f"min_cross={record['minimum_cross_product']:.6g}"
        )
        if recovery is not None:
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

    if args.result_json is not None:
        payload = {
            "schema_version": 1,
            "method": "projection_only_linear_output_fit",
            "target_csv": str(args.target_csv),
            "target_json": None if args.target_json is None else str(args.target_json),
            "settings": {
                "side": args.side,
                "output_type": args.output_type,
                "branch": args.branch,
                "derivative_weight": args.derivative_weight,
                "ratio_minimum": args.ratio_minimum,
                "ratio_maximum": args.ratio_maximum,
                "maximum_output_to_coupler_ratio": args.max_output_to_coupler_ratio,
                "maximum_iterations": args.maximum_iterations,
                "population_size": args.population_size,
                "seed": args.seed,
            },
            "results": records,
        }
        args.result_json.parent.mkdir(parents=True, exist_ok=True)
        args.result_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
