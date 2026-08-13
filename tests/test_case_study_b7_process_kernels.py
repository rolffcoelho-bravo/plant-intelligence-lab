import numpy as np
import pandas as pd

from plant_intelligence.models.maize_environment_process_kernels import (
    STAGE_GROUPS,
    build_ec_audit,
    combine_maps,
    group_columns,
    process_block,
    split_ec_name,
)
from plant_intelligence.models.maize_environment_transfer import FeatureMap


def test_target_proximal_yield_outputs_are_excluded():
    ecov = pd.DataFrame(
        {
            "yield_FlaFlw": [1.0, 2.0],
            "TT_GerEme": [3.0, 4.0],
            "SW_StGEnG": [5.0, 6.0],
        },
        index=["e1", "e2"],
    )
    audit = build_ec_audit(ecov)
    row = audit[audit.covariate == "yield_FlaFlw"].iloc[0]
    assert bool(row.target_proximal)
    assert not bool(row.included_in_b7_candidates)
    groups = group_columns(audit)
    assert "yield_FlaFlw" not in groups["nonleaky"]
    assert "TT_GerEme" in groups["nonleaky"]


def test_process_blocks_match_predeclared_biology():
    assert process_block("TT") == "thermal"
    assert process_block("CumHI30") == "thermal"
    assert process_block("SW") == "water_soil"
    assert process_block("Eos") == "water_soil"
    assert process_block("LAI") == "canopy_growth"
    assert process_block("biomass") == "canopy_growth"
    assert process_block("yield") == "target_proximal"


def test_stage_parser_and_groups_are_deterministic():
    prefix, stage = split_ec_name("CumTT_EnJFlo")
    assert prefix == "CumTT"
    assert stage == "EnJFlo"
    assert stage in STAGE_GROUPS["vegetative"]
    prefix, stage = split_ec_name("LAI_StGEnG")
    assert prefix == "LAI"
    assert stage in STAGE_GROUPS["grain_fill_maturity"]


def test_equal_weight_multiple_kernel_map_identity():
    ids = ("e1", "e2")
    a = FeatureMap(ids, np.asarray([[1.0, 0.0], [0.5, 0.5]], dtype=np.float32), {})
    b = FeatureMap(ids, np.asarray([[0.0, 1.0], [1.0, 0.0]], dtype=np.float32), {})
    combined = combine_maps([a, b], "test")
    observed = combined.values @ combined.values.T
    expected = 0.5 * (a.values @ a.values.T + b.values @ b.values.T)
    assert np.allclose(observed, expected)


def test_nonleaky_stage_groups_exclude_target_proximal_columns():
    cols = {
        "yield_MatHar": [1.0, 2.0],
        "TT_GerEme": [1.0, 2.0],
        "SW_FlaFlw": [1.0, 2.0],
        "LAI_MatHar": [1.0, 2.0],
    }
    audit = build_ec_audit(pd.DataFrame(cols, index=["e1", "e2"]))
    groups = group_columns(audit)
    assert "yield_MatHar" not in groups["grain_fill_maturity"]
    assert "TT_GerEme" in groups["vegetative"]
    assert "SW_FlaFlw" in groups["reproductive_transition"]
    assert "LAI_MatHar" in groups["grain_fill_maturity"]
