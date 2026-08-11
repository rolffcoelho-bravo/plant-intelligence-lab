"""Fetch the first public phenotype targets for Case Study A.

Run from the repository root:

    python scripts/fetch_case_study_a.py

The script writes source payloads and provenance sidecars under data/raw/arapheno.
"""

from pathlib import Path

from plant_intelligence.data.arapheno import PRIMARY_TARGETS, save_phenotype_json


def main() -> None:
    output_dir = Path("data/raw/arapheno")
    for target in PRIMARY_TARGETS:
        data_path, provenance_path = save_phenotype_json(
            target.phenotype_id,
            output_dir=output_dir,
        )
        print(
            f"saved phenotype={target.phenotype_id} "
            f"trait={target.trait} day={target.day} protocol={target.protocol} "
            f"data={data_path} provenance={provenance_path}"
        )


if __name__ == "__main__":
    main()
