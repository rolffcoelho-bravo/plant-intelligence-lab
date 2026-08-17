"""B12A runner with a schema-only alias for the frozen B10-R support output.

B10-R calls its standardized nearest-environment distance `full_nearest_z`.
B12's published external artifact uses the clearer alias `full_nearest_distance`.
The values are identical; the B11 reliability boundary remains based on the
unchanged `full_nearest_percentile` field.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from plant_intelligence.uncertainty import maize_b12_authenticated_runner as authenticated
from plant_intelligence.uncertainty import maize_external_temporal_validation as b12

_ORIGINAL_SUPPORT_GEOMETRY = b12.support_geometry


def support_geometry_with_distance_alias(*args, **kwargs):
    frame, geometry = _ORIGINAL_SUPPORT_GEOMETRY(*args, **kwargs)
    prefix = str(kwargs.get("prefix", "full"))
    source = f"{prefix}_nearest_z"
    alias = f"{prefix}_nearest_distance"
    if source in frame.columns and alias not in frame.columns:
        frame = frame.copy()
        frame[alias] = frame[source]
    return frame, geometry


def run(root: Path):
    b12.support_geometry = support_geometry_with_distance_alias
    return authenticated.run(root)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run blind B12A with frozen support-column compatibility."
    )
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root.resolve())
    print("Case Study B12A sealed prediction stage complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
