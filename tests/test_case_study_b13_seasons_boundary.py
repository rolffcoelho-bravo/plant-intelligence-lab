from __future__ import annotations

import pandas as pd
import pytest

from plant_intelligence.uncertainty import maize_b13_seasons_runner as seasons


def test_documented_seasons_boundary_recovers_planting_date():
    dates = pd.date_range('2023-04-01', '2023-04-30', freq='D')
    weather = pd.DataFrame(
        {
            'Env': ['AAH1_2023'] * len(dates),
            'Date': [int(value.strftime('%Y%m%d')) for value in dates],
            'T2M': 20.0,
        }
    )
    result = seasons.planting_dates_from_seasons_weather(weather)
    assert len(result) == 1
    assert result.loc[0, 'environment'] == 'AAH1_2023'
    assert result.loc[0, 'seasons_only_start_date'] == '2023-04-01'
    assert result.loc[0, 'planting_date'] == '2023-04-15'
    assert result.loc[0, 'season_boundary_rule'] == seasons.SEASON_BOUNDARY_RULE
    assert result.loc[0, 'target_outcomes_used'] is False


def test_seasons_boundary_requires_complete_14_day_preplant_window():
    dates = list(pd.date_range('2023-04-01', '2023-04-20', freq='D'))
    dates.remove(pd.Timestamp('2023-04-07'))
    weather = pd.DataFrame(
        {
            'Env': ['AAH1_2023'] * len(dates),
            'Date': [value.strftime('%Y%m%d') for value in dates],
        }
    )
    with pytest.raises(ValueError):
        seasons.planting_dates_from_seasons_weather(weather)


def test_seasons_boundary_ignores_non_target_year_environments():
    rows = []
    for env, start in [('AAH1_2022', '2022-04-01'), ('BBH1_2023', '2023-05-01')]:
        for value in pd.date_range(start, periods=20, freq='D'):
            rows.append({'Env': env, 'Date': value.strftime('%Y%m%d')})
    result = seasons.planting_dates_from_seasons_weather(pd.DataFrame(rows))
    assert result['environment'].tolist() == ['BBH1_2023']
    assert result.loc[0, 'planting_date'] == '2023-05-15'
