import numpy as np
import pandas as pd

from plant_intelligence.data.maize_prospective_environment import HORIZONS, _parse_sda_table, aggregate_weather, build_forward_year_manifest, build_safe_states, historical_climatology, horizon_audit


def _weather(start, end):
    idx = pd.date_range(start, end, freq='D')
    n = len(idx)
    return pd.DataFrame({'T2M': np.linspace(10.0,30.0,n), 'T2M_MIN': np.linspace(4.0,14.0,n), 'T2M_MAX': np.linspace(16.0,38.0,n), 'PRECTOTCORR': np.ones(n), 'ALLSKY_SFC_SW_DWN': np.full(n,20.0), 'RH2M': np.full(n,60.0), 'WS2M': np.full(n,2.5)}, index=idx)


def test_historical_climatology_excludes_current_year():
    frame = _weather('2010-01-01','2020-12-31')
    frame.loc['2020-05-01':'2020-06-30','T2M'] = 999.0
    summary, years_used = historical_climatology(frame, pd.Timestamp('2020-05-01'), 2020)
    assert years_used == 10
    assert summary['wx_t2m'] < 100.0
    assert summary['wx_n_days'] == 610


def test_forward_year_manifest_is_strictly_temporal():
    envs = pd.DataFrame({'environment':['2014-A','2015-A','2016-A','2017-A','2017-B'], 'year':[2014,2015,2016,2017,2017]})
    manifest = build_forward_year_manifest(envs, min_prior_years=2)
    assert set(manifest['test_year']) == {2016,2017}
    assert (manifest['train_year_max'] < manifest['test_year']).all()


def test_ssurgo_columnname_payload_parser():
    payload={'Table':[['mukey','muname','compname','comppct_r'],['123','Example soil','Example component',70]]}
    row=_parse_sda_table(payload)
    assert row['mukey']=='123'
    assert row['comppct_r']==70
    assert _parse_sda_table({'Table':[]}) is None


def test_horizon_lock_is_time_safe():
    audit=horizon_audit()
    assert list(audit['horizon']) == [h.name for h in HORIZONS]
    cols=['uses_future_realized_weather','uses_observed_anthesis','uses_observed_silking','uses_observed_harvest','uses_observed_yield']
    assert not audit[cols].astype(bool).any().any()


def test_safe_state_windows_stop_at_issuance_date():
    environments=pd.DataFrame([{'environment':'2020-TEST','year':2020,'city':'TEST','planting_date':'2020-05-01','latitude':40.0,'longitude':-90.0,'plant_population_proxy':8.0}])
    weather={'40.0000_-90.0000':_weather('2010-01-01','2020-12-31')}
    soil=pd.DataFrame([{'coordinate_key':'40.0000_-90.0000','ssurgo_available':True,'mukey':'1','muname':'Soil','compname':'Component'}])
    states=build_safe_states(environments,weather,soil)
    assert not states['uses_future_weather'].astype(bool).any()
    assert not states['uses_observed_phenology'].astype(bool).any()
    t1=states[states['horizon']=='T1_30DAP'].iloc[0]
    t2=states[states['horizon']=='T2_60DAP_reproductive_window_proxy'].iloc[0]
    assert t1.max_current_year_weather_date_used=='2020-05-31'
    assert t2.max_current_year_weather_date_used=='2020-06-30'
    assert int(t1.wx_n_days)==31
    assert int(t2.wx_n_days)==61


def test_weather_aggregation_fluxes_and_extrema():
    frame=pd.DataFrame({'T2M':[20.0,22.0],'T2M_MIN':[10.0,9.0],'T2M_MAX':[30.0,32.0],'PRECTOTCORR':[1.0,2.0],'ALLSKY_SFC_SW_DWN':[15.0,16.0],'RH2M':[50.0,70.0],'WS2M':[2.0,4.0]})
    out=aggregate_weather(frame)
    assert np.isclose(out['wx_t2m'],21.0)
    assert np.isclose(out['wx_t2m_min'],9.0)
    assert np.isclose(out['wx_t2m_max'],32.0)
    assert np.isclose(out['wx_prectotcorr'],3.0)
    assert np.isclose(out['wx_allsky_sfc_sw_dwn'],31.0)
