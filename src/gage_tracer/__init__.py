"""gage_tracer — Type 1 Gage Study analysis package.

Public API re-exported here for convenience:

- ``transform_ogp_data``: Parse raw OGP files into a structured TSV.
- ``calculate_type1_metrics``: Compute Cg, Cgk, bias, %Var, etc.
- ``create_dashboard``: Generate the interactive HTML dashboard.
"""

from src.gage_tracer.data_parser import transform_ogp_data
from src.gage_tracer.calculations import calculate_type1_metrics
from src.gage_tracer.visualization import create_dashboard

__all__ = ["transform_ogp_data", "calculate_type1_metrics", "create_dashboard"]
