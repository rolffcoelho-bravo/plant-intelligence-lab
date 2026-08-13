"""Public entry point for Case Study B8 decision-horizon forecasting.

The computational engine is separated from the decision-time execution wrapper
so the public command always applies the availability/provenance checks.
"""

from pathlib import Path

from plant_intelligence.models import maize_environment_decision_horizons_core as core
from plant_intelligence.models.maize_environment_decision_horizon_execution import (
    availability_audit,
    historical_location_proxy,
    main,
    run,
)

HorizonSpec = core.HorizonSpec
HORIZONS = core.HORIZONS
HORIZON_ORDER = core.HORIZON_ORDER
PRE_FLOWERING_STAGES = core.PRE_FLOWERING_STAGES
AT_FLOWERING_STAGES = core.AT_FLOWERING_STAGES
REPRODUCTIVE_STAGES = core.REPRODUCTIVE_STAGES
FULL_STAGES = core.FULL_STAGES
location_code = core.location_code
horizon_columns = core.horizon_columns
load_selected_configs = core.load_selected_configs
summarize = core.summarize
paired_environment_bootstrap = core.paired_environment_bootstrap
history_summary = core.history_summary
make_figure = core.make_figure


def run_predictions(root: Path):
    core.historical_location_proxy = historical_location_proxy
    core.availability_audit = availability_audit
    return core.run_predictions(root)


if __name__ == "__main__":
    main()
