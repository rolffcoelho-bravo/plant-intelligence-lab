import pandas as pd

from plant_intelligence.diagnostics.maize_b18_t0_forecast_time_novelty_gate import (
    DECISION,
    NEXT_STAGE,
    next_gate_matrix,
    prior_art_matrix,
)


def test_broad_forecast_time_gxe_claim_has_direct_prior_art_collision():
    prior = prior_art_matrix()
    gillberg = prior.loc[prior['doi'].eq('10.1093/bioinformatics/btz197')].iloc[0]
    assert bool(gillberg['direct_collision'])
    assert 'historical weather' in gillberg['what_is_already_done'].lower()
    assert 'ideal in-season' in gillberg['what_is_already_done'].lower()


def test_partial_weather_prefix_is_not_promoted_as_method_novelty():
    gates = next_gate_matrix().set_index('gate')
    assert gates.loc['B18_PARTIAL_WEATHER_PREFIX_IS_NOVEL_BY_ITSELF', 'permitted'] == False
    assert gates.loc['B18_INFORMATION_PARITY_BENCHMARK_HYPOTHESIS', 'permitted'] == True
    assert gates.loc['B18_MODEL_FITTING_AFTER_T0', 'permitted'] == False


def test_t0_decision_routes_only_to_benchmark_kill_test():
    assert DECISION == 'B18_T0_BROAD_FORECAST_TIME_GXE_NOVELTY_REJECTED_INFORMATION_PARITY_BENCHMARK_HYPOTHESIS_SURVIVES_KILL_TEST_ONLY'
    assert NEXT_STAGE == 'B18_T1_INFORMATION_PARITY_BENCHMARK_NOVELTY_TEST'
