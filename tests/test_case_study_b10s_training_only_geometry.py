import pandas as pd

from plant_intelligence.models.maize_forecast_time_prediction import FROZEN_CONFIG
from plant_intelligence.models.maize_training_only_geometry_selection import CANDIDATES, MIN_INNER_YEARS, inner_years_for_outer, select_candidate


def _evidence():
    rows=[]
    for i,cfg in enumerate(CANDIDATES):
        for j,year in enumerate([2015,2016,2017]):
            rmse=3+i*.01+j*.001-(.5 if cfg.name=='diagnostic_rank8_gamma4' else 0)
            n=100+j
            rows.append({'inner_test_year':year,'config':cfg.name,'n':n,'rmse':rmse,'mae':rmse*.8,'sse':rmse*rmse*n,'sae':rmse*.8*n})
    return pd.DataFrame(rows)


def test_b10s_candidate_grid_is_frozen():
    assert len(CANDIDATES)==12
    assert {c.e_rank for c in CANDIDATES}=={8,16,32}
    assert {c.gamma_multiplier for c in CANDIDATES}=={0.5,1.0,2.0,4.0}


def test_b10s_2016_is_insufficient_history_fallback():
    assert MIN_INNER_YEARS==2
    assert inner_years_for_outer([2014,2015,2016],2016)==[2015]
    out=select_candidate(_evidence(),2016)
    assert out['selection_status']=='INSUFFICIENT_HISTORY_FALLBACK'
    assert out['selected_config']==FROZEN_CONFIG.name
    assert out['outer_outcome_used_for_selection'] is False


def test_b10s_2017_uses_only_pre_outer_years():
    out=select_candidate(_evidence(),2017)
    assert out['selection_status']=='TRAINING_ONLY_SELECTED'
    assert out['inner_years']=='2015;2016'
    assert out['selected_config']=='diagnostic_rank8_gamma4'


def test_b10s_future_inner_row_cannot_change_2017_selection():
    ev=_evidence()
    first=select_candidate(ev,2017)
    changed=ev.copy()
    changed.loc[changed.inner_test_year.eq(2017),'rmse']=999.0
    changed.loc[changed.inner_test_year.eq(2017),'sse']=999.0**2*changed.loc[changed.inner_test_year.eq(2017),'n']
    second=select_candidate(changed,2017)
    assert first['selected_config']==second['selected_config']
    assert first['mean_inner_year_rmse']==second['mean_inner_year_rmse']
