"""Chart generation and HTML dashboard builder.

Handles all visual output: matplotlib Run Charts and Histograms,
and the self-contained HTML dashboard with embedded base-64 images.
"""

from __future__ import annotations

import math
from io import BytesIO
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------

def _render_dimension_chart(
    dim: str,
    measurements: pd.Series,
    reference_val: float,
    mean_val: float,
    std_val: float,
    ref_upper: float,
    ref_lower: float,
) -> str:
    """Draw a Run Chart + Histogram for a single dimension.

    Both charts are stacked vertically in one figure and rendered to a
    base-64 encoded PNG that can be embedded directly in HTML.

    Args:
        dim: Dimension name (used in titles and axis labels).
        measurements: Numeric series of repeated measurements.
        reference_val: Reference (master/nominal) value.
        mean_val: Sample mean.
        std_val: Sample standard deviation.
        ref_upper: Upper reference line (Ref + 0.10·Tolerance).
        ref_lower: Lower reference line (Ref − 0.10·Tolerance).

    Returns:
        Base-64 encoded PNG string (ready for an ``<img>`` src).
    """
    import base64

    if pd.isna(std_val) or std_val == 0:
        std_val = 0.0
    data_min: float = float(measurements.min())
    data_max: float = float(measurements.max())
    data_span: float = data_max - data_min
    if data_span == 0:
        data_span = abs(mean_val) * 1e-4 if mean_val != 0 else 1e-6

    # Figure out a good Y-axis range so all reference lines and data
    # points are visible with some breathing room.
    center_line: float = reference_val
    max_dist: float = max(
        abs(data_max - center_line),
        abs(data_min - center_line),
        abs(ref_upper - center_line),
        abs(ref_lower - center_line),
    )
    half_range: float = max_dist * 1.1
    if std_val > 0:
        half_range = max(half_range, 5 * std_val)
    if half_range == 0:
        half_range = data_span * 2

    # --- Top panel: Run Chart (observations over time) ---
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(11, 9),
        gridspec_kw={"height_ratios": [1.2, 0.8]},
    )
    fig.patch.set_facecolor("#0b0e14")

    ax1 = axes[0]
    x_vals = list(range(1, len(measurements) + 1))
    ax1.axhline(y=ref_upper, color="#e8836a", ls="--", lw=1.2, zorder=1, label="Ref+0.10·Tol")
    ax1.axhline(y=reference_val, color="#7dcea0", ls="-", lw=2, alpha=0.9, zorder=2, label="Ref")
    ax1.axhline(y=ref_lower, color="#e8836a", ls="--", lw=1.2, zorder=1, label="Ref−0.10·Tol")
    if abs(mean_val - reference_val) > 1e-12:
        ax1.axhline(y=mean_val, color="#d4a574", ls=":", lw=1.4, alpha=0.9, zorder=2, label="Mean")
    ax1.plot(
        x_vals,
        measurements.values,
        "-o",
        ms=3,
        lw=0.9,
        color="#58a6c9",
        markerfacecolor="#79c0db",
        markeredgecolor="#58a6c9",
        markeredgewidth=0.4,
        zorder=3,
    )
    ax1.set_facecolor("#11151c")
    ax1.set_xlabel("Observation", fontsize=9, color="#6e7681")
    ax1.set_ylabel(dim, fontsize=10, color="#8b949e", fontweight="bold")
    ax1.set_title(f"Run Chart of {dim}", fontsize=11, fontweight="bold", color="#c9d1d9", pad=6)
    ax1.tick_params(labelsize=8, colors="#6e7681")
    ax1.grid(True, alpha=0.08, color="#484f58")
    for sp in ax1.spines.values():
        sp.set_color("#21262d")
    ax1.set_ylim(center_line - half_range, center_line + half_range)
    ax1.legend(fontsize=7, loc="upper right", facecolor="#11151c", edgecolor="#21262d", labelcolor="#8b949e", framealpha=0.85)

    ax2 = axes[1]
    n_bins: int = min(12, max(5, int(np.sqrt(len(measurements)))))
    ax2.hist(measurements.values, bins=n_bins, color="#58a6c9", edgecolor="#11151c", lw=0.6, rwidth=0.85, alpha=0.85)
    ax2.set_facecolor("#11151c")
    ax2.set_xlabel("Value", fontsize=9, color="#6e7681")
    ax2.set_ylabel("Freq", fontsize=9, color="#6e7681")
    ax2.tick_params(labelsize=8, colors="#6e7681")
    ax2.grid(True, alpha=0.08, color="#484f58", axis="y")
    for sp in ax2.spines.values():
        sp.set_color("#21262d")
    hp: float = data_span * 0.3 if data_span > 0 else 1e-6
    ax2.set_xlim(data_min - hp, data_max + hp)
    ax2.axvline(x=reference_val, color="#7dcea0", ls="-", lw=1.6, alpha=0.7, label="Ref")
    if abs(mean_val - reference_val) > 1e-12:
        ax2.axvline(x=mean_val, color="#d4a574", ls=":", lw=1.3, alpha=0.8, label="Mean")
    ax2.legend(fontsize=7, loc="best", facecolor="#11151c", edgecolor="#21262d", labelcolor="#8b949e", framealpha=0.85)

    plt.tight_layout(pad=1.2)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor="#0b0e14")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# Dashboard assembly
# ---------------------------------------------------------------------------

def _build_chart_data(
    df: pd.DataFrame,
    summary_data: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Render charts and collect per-dimension display data.

    Iterates over every dimension in the summary, generates a chart
    image, and packs all the numeric fields the HTML template needs.

    Args:
        df: Full measurement DataFrame (columns = dimensions).
        summary_data: Metric dicts from ``calculate_type1_metrics``.

    Returns:
        List of dicts (one per dimension) with the base-64 chart image
        and all associated metrics.
    """
    summary_df = pd.DataFrame(summary_data).rename(columns={"Gage Item": "Dimension"})
    chart_images: list[dict[str, Any]] = []

    for _, row in summary_df.iterrows():
        dim: str = row["Dimension"]
        if dim not in df.columns:
            continue
        measurements = df[dim].dropna().astype(float)
        reference_val = float(row["Reference"])
        mean_val = float(row["Mean"])
        std_val = float(row["StdDev"])
        ref_upper = float(row["Ref + 0.10*Tol"])
        ref_lower = float(row["Ref - 0.10*Tol"])

        img_b64 = _render_dimension_chart(
            dim, measurements, reference_val, mean_val, std_val, ref_upper, ref_lower,
        )

        chart_images.append(
            {
                "dim": dim,
                "img": img_b64,
                "status": row["Status"],
                "reference": reference_val,
                "mean": mean_val,
                "max_diff": float(row["Max diff"]),
                "stddev": std_val,
                "study_var": float(row["6 x StdDev (SV)"]),
                "tolerance": float(row["Tolerance (Tol)"]),
                "bias": float(row["Bias"]),
                "t_value": float(row["T"]),
                "p_value": float(row["PValue"]),
                "cg": float(row["Cg"]),
                "cgk": float(row["Cgk"]),
                "var_repeat": row["%Var(Repeatability)"],
                "var_repeat_bias": row["%Var(Repeatability and Bias)"],
                "observations": int(row["Observations"]),
                "ref_upper": ref_upper,
                "ref_lower": ref_lower,
            }
        )

    return chart_images


def _build_summary_rows(chart_images: list[dict[str, Any]]) -> str:
    """Build the ``<tr>`` rows for the overview summary table.

    Each row is clickable — it highlights the matching detail card below.

    Args:
        chart_images: Per-dimension data dicts from ``_build_chart_data``.

    Returns:
        HTML string with all table rows.
    """
    rows = ""
    for i, d in enumerate(chart_images):
        st_cls = "status-accept" if d["status"] == "ACCEPT" else "status-reject"
        cg_cls = "kpi-good" if d["cg"] >= 1.33 else "kpi-bad"
        cgk_cls = "kpi-good" if d["cgk"] >= 1.33 else "kpi-bad"
        vr = f"{d['var_repeat']:.1f}" if pd.notna(d["var_repeat"]) else "—"
        rows += (
            f'<tr class="summary-row" data-idx="{i}">\n'
            f'  <td class="cell-dim">{d["dim"]}</td>\n'
            f'  <td class="{st_cls}">{d["status"]}</td>\n'
            f'  <td class="{cg_cls}">{d["cg"]:.2f}</td>\n'
            f'  <td class="{cgk_cls}">{d["cgk"]:.2f}</td>\n'
            f'  <td class="cell-mono">{vr}%</td>\n'
            f'  <td class="cell-mono">{d["bias"]:+.6f}</td>\n'
            f'  <td class="cell-dim cell-expand">▸</td>\n'
            f"</tr>\n"
        )
    return rows


def _build_detail_cards(chart_images: list[dict[str, Any]]) -> str:
    """Build the detail cards that show chart + metrics for each dimension.

    Every card includes the Run Chart/Histogram image on the left and
    three metric groups (Basic Stats, Bias, Capability) on the right.

    Args:
        chart_images: Per-dimension data dicts.

    Returns:
        HTML string with all detail cards.
    """
    cards = ""
    for i, d in enumerate(chart_images):
        ref_fmt = f"{d['reference']:.8f}"
        mean_fmt = f"{d['mean']:.8f}"
        std_fmt = f"{d['stddev']:.8f}"
        sv_fmt = f"{d['study_var']:.8f}"
        tol_fmt = f"{d['tolerance']:.8f}"
        md_fmt = f"{d['max_diff']:.8f}"
        bias_fmt = f"{d['bias']:.8f}"
        t_fmt = f"{d['t_value']:.4f}" if math.isfinite(d["t_value"]) else "∞"
        p_fmt = f"{d['p_value']:.4f}"
        vr_fmt = f"{d['var_repeat']:.2f}%" if pd.notna(d["var_repeat"]) else "N/A"
        vrb_fmt = f"{d['var_repeat_bias']:.2f}%" if pd.notna(d["var_repeat_bias"]) else "N/A"
        border = "var(--color-status-accept)" if d["status"] == "ACCEPT" else "var(--color-status-reject)"
        status_bg = border

        cards += f"""
<div class="detail-card open" id="detail-{i}" style="border-left-color:{border};">
  <div class="detail-chart">
    <img src="data:image/png;base64,{d['img']}" alt="Chart {d['dim']}">
  </div>
  <div class="detail-metrics">
    <div class="metric-group">
      <div class="metric-group-title" style="color:var(--color-accent-blue);">Basic Statistics</div>
      <div class="metric-row"><span class="metric-label">Reference</span><span class="metric-value">{ref_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">Mean</span><span class="metric-value">{mean_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">StdDev</span><span class="metric-value">{std_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">6×StdDev (SV)</span><span class="metric-value">{sv_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">Tolerance</span><span class="metric-value">{tol_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">Max diff</span><span class="metric-value">{md_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">Observations</span><span class="metric-value">{d['observations']}</span></div>
    </div>
    <div class="metric-group">
      <div class="metric-group-title" style="color:var(--color-status-accept);">Bias</div>
      <div class="metric-row"><span class="metric-label">Bias</span><span class="metric-value">{bias_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">T</span><span class="metric-value">{t_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">PValue (Bias=0)</span><span class="metric-value">{p_fmt}</span></div>
    </div>
    <div class="metric-group">
      <div class="metric-group-title" style="color:var(--color-accent-amber);">Capability</div>
      <div class="metric-row"><span class="metric-label">Cg</span><span class="metric-value" style="font-size:15px;font-weight:600;">{d['cg']:.4f}</span></div>
      <div class="metric-row"><span class="metric-label">Cgk</span><span class="metric-value" style="font-size:15px;font-weight:600;">{d['cgk']:.4f}</span></div>
      <div class="metric-row"><span class="metric-label">%Var(Repeat)</span><span class="metric-value">{vr_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">%Var(R+Bias)</span><span class="metric-value">{vrb_fmt}</span></div>
    </div>
    <div class="metric-status" style="background:{status_bg};">{d['status']}</div>
  </div>
</div>\n"""

    return cards


# ---------------------------------------------------------------------------
# HTML template (CSS + JS)
# ---------------------------------------------------------------------------

_CSS_TEMPLATE = """\
/* Dark-theme dashboard — uses CSS custom properties for easy theming */:root {
  --color-bg-base:        #0b0e14;
  --color-bg-surface:     #131720;
  --color-bg-elevated:    #1a1f2b;
  --color-bg-hover:       #1e2533;
  --color-border-subtle:  #1e2430;
  --color-border-default: #2a3140;
  --color-text-primary:   #d1d5db;
  --color-text-secondary: #6e7681;
  --color-text-muted:     #484f58;
  --color-text-inverse:   #0b0e14;
  --color-accent-blue:    #58a6c9;
  --color-accent-amber:   #d4a574;
  --color-status-accept:  #7dcea0;
  --color-status-reject:  #e07070;
  --color-status-warn:    #d4a574;
  --space-xs: 4px; --space-sm: 8px; --space-md: 16px;
  --space-lg: 24px; --space-xl: 32px; --space-container: 28px 32px;
  --font-sans:  'Inter', 'Segoe UI', system-ui, sans-serif;
  --font-mono:  'Cascadia Code', 'Consolas', 'Fira Code', monospace;
  --font-kpi:   clamp(36px, 5vw, 48px);
  --font-body:  13px; --font-small: 11px;
  --radius-sm: 6px; --radius-md: 10px; --radius-lg: 14px;
}
*, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
html { font-size: 16px; }
body {
  background: var(--color-bg-base); color: var(--color-text-primary);
  font-family: var(--font-sans); padding: var(--space-container);
  line-height: 1.55; -webkit-font-smoothing: antialiased;
}
.dash-header { display:flex; justify-content:space-between; align-items:baseline;
  padding-bottom:var(--space-md); border-bottom:1px solid var(--color-border-subtle);
  margin-bottom:var(--space-lg); }
.dash-title { font-size:20px; font-weight:600; color:var(--color-text-primary); letter-spacing:.2px; }
.dash-title em { font-style:normal; background:linear-gradient(135deg,var(--color-accent-blue),#9b8ec4);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.dash-date { color:var(--color-text-secondary); font-size:var(--font-small); }
.kpi-row { display:grid; grid-template-columns:1.7fr repeat(4,1fr); gap:var(--space-md); margin-bottom:var(--space-lg); }
.kpi-card { background:var(--color-bg-surface); border:1px solid var(--color-border-subtle);
  border-radius:var(--radius-md); padding:var(--space-md) var(--space-lg); transition:border-color .15s; }
.kpi-card:hover { border-color:var(--color-accent-blue); }
.kpi-label { color:var(--color-text-secondary); font-size:var(--font-small); text-transform:uppercase;
  letter-spacing:1.2px; font-weight:500; margin-bottom:2px; }
.kpi-value { font-weight:700; letter-spacing:-.5px; line-height:1.1; }
.kpi-primary .kpi-value { font-size:var(--font-kpi); }
.kpi-secondary .kpi-value { font-size:clamp(26px,3.5vw,34px); }
.kpi-sub { color:var(--color-text-muted); font-size:var(--font-small); margin-top:2px; }
.summary-table { width:100%; border-collapse:collapse; font-size:var(--font-body);
  margin-bottom:var(--space-lg); border-radius:var(--radius-md); overflow:hidden; }
.summary-table th { background:var(--color-bg-elevated); color:var(--color-text-secondary);
  font-size:10px; text-transform:uppercase; letter-spacing:1px; font-weight:600;
  padding:10px 14px; text-align:left; border-bottom:1px solid var(--color-border-default);
  position:sticky; top:0; z-index:2; }
.summary-table td { padding:9px 14px; border-bottom:1px solid var(--color-border-subtle); transition:background .12s; }
.summary-row { cursor:pointer; }
.summary-row:hover td { background:var(--color-bg-hover); }
.cell-dim { color:var(--color-text-primary); font-weight:600; }
.cell-mono { font-family:var(--font-mono); font-size:12px; color:var(--color-text-primary); }
.cell-expand { text-align:center; color:var(--color-text-muted); font-size:12px; transition:transform .2s; }
.row-open .cell-expand { transform:rotate(90deg); color:var(--color-accent-blue); }
.status-accept { color:var(--color-status-accept); font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:.5px; }
.status-reject { color:var(--color-status-reject); font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:.5px; }
.kpi-good { color:var(--color-status-accept); font-family:var(--font-mono); font-weight:600; }
.kpi-bad  { color:var(--color-status-reject); font-family:var(--font-mono); font-weight:600; }
.detail-card { background:var(--color-bg-surface); border-left:4px solid var(--color-status-accept);
  border-radius:var(--radius-md); margin-bottom:var(--space-md); padding:var(--space-md);
  gap:var(--space-md); display:flex; flex-wrap:wrap; }
.detail-card.highlight { animation:fadeSlide .25s ease-out; border-color:var(--color-accent-blue) !important; }
@keyframes fadeSlide { from{opacity:0;transform:translateY(-8px)} to{opacity:1;transform:translateY(0)} }
.detail-chart { flex:2; min-width:380px; }
.detail-chart img { width:100%; display:block; border-radius:var(--radius-sm); }
.detail-metrics { flex:1; min-width:250px; display:flex; flex-direction:column; gap:var(--space-sm); }
.metric-group { background:var(--color-bg-elevated); border-radius:var(--radius-sm); padding:var(--space-sm) var(--space-md); }
.metric-group-title { font-size:10px; text-transform:uppercase; letter-spacing:1px; font-weight:700; margin-bottom:var(--space-xs); }
.metric-row { display:flex; justify-content:space-between; padding:3px 0; font-size:12px; }
.metric-label { color:var(--color-text-secondary); }
.metric-value { color:var(--color-text-primary); font-family:var(--font-mono); font-size:12px; }
.metric-status { align-self:stretch; text-align:center; font-weight:800; font-size:13px;
  padding:8px; border-radius:var(--radius-sm); color:var(--color-text-inverse);
  letter-spacing:1px; text-transform:uppercase; }
@media (max-width:900px) { .kpi-row{grid-template-columns:1fr 1fr;} .detail-card{flex-direction:column;} }
"""

_JS_TEMPLATE = """\
// When a summary row is clicked, scroll to its detail card and highlight it.
document.querySelectorAll('.summary-row').forEach(function(row) {
  row.addEventListener('click', function() {
    var idx = this.dataset.idx;
    var card = document.getElementById('detail-' + idx);
    document.querySelectorAll('.detail-card').forEach(function(c) { c.classList.remove('highlight'); });
    document.querySelectorAll('.summary-row').forEach(function(r) { r.classList.remove('row-open'); });
    card.classList.add('highlight');
    this.classList.add('row-open');
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});
"""


def create_dashboard(
    df: pd.DataFrame,
    summary_data: list[dict[str, Any]],
    output_path: Path,
) -> None:
    """Generate a self-contained HTML dashboard with embedded charts.

    Produces a single ``.html`` file with no external dependencies —
    all charts are base-64 encoded PNGs, and all styles/scripts are
    inlined.  Just open it in any browser.

    Args:
        df: Full measurement DataFrame.
        summary_data: List of metric dicts produced by
            ``calculate_type1_metrics``.
        output_path: Destination path for the ``.html`` file.
    """
    import time

    num_dims: int = len(summary_data)
    accepted: int = sum(1 for s in summary_data if s["Status"] == "ACCEPT")
    rejected: int = num_dims - accepted
    pass_rate: float = round(accepted * 100 / num_dims, 1) if num_dims else 0

    worst = min(summary_data, key=lambda s: s["Cgk"])
    best = max(summary_data, key=lambda s: s["Cgk"])

    chart_images = _build_chart_data(df, summary_data)
    summary_rows = _build_summary_rows(chart_images)
    detail_cards = _build_detail_cards(chart_images)

    timestamp: str = time.strftime("%Y-%m-%d %H:%M:%S")

    pr_color = "var(--color-status-accept)" if pass_rate >= 75 else "var(--color-status-reject)"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Type 1 Gage Study — Dashboard</title>
<style>
{_CSS_TEMPLATE}
</style>
</head>
<body>

<div class="dash-header">
  <h1 class="dash-title"><em>Type 1 Gage Study</em> Dashboard</h1>
  <span class="dash-date">{timestamp}</span>
</div>

<div class="kpi-row">
  <div class="kpi-card kpi-primary" style="border-left:4px solid {pr_color};">
    <div class="kpi-label">Pass Rate</div>
    <div class="kpi-value" style="color:{pr_color};">{pass_rate:.0f}%</div>
    <div class="kpi-sub">{accepted}/{num_dims} dimensions</div>
  </div>
  <div class="kpi-card kpi-secondary" style="border-left:3px solid var(--color-status-accept);">
    <div class="kpi-label">Accepted</div>
    <div class="kpi-value" style="color:var(--color-status-accept);">{accepted}</div>
  </div>
  <div class="kpi-card kpi-secondary" style="border-left:3px solid var(--color-status-reject);">
    <div class="kpi-label">Rejected</div>
    <div class="kpi-value" style="color:var(--color-status-reject);">{rejected}</div>
  </div>
  <div class="kpi-card kpi-secondary" style="border-left:3px solid var(--color-status-accept);">
    <div class="kpi-label">Best Cgk</div>
    <div class="kpi-value" style="color:var(--color-status-accept);">{best['Cgk']:.2f}</div>
    <div class="kpi-sub">{best['Gage Item']}</div>
  </div>
  <div class="kpi-card kpi-secondary" style="border-left:3px solid var(--color-status-reject);">
    <div class="kpi-label">Worst Cgk</div>
    <div class="kpi-value" style="color:var(--color-status-reject);">{worst['Cgk']:.2f}</div>
    <div class="kpi-sub">{worst['Gage Item']}</div>
  </div>
</div>

<table class="summary-table">
  <thead>
    <tr><th>Dimension</th><th>Status</th><th>Cg</th><th>Cgk</th><th>%Var(R)</th><th>Bias</th><th></th></tr>
  </thead>
  <tbody>
    {summary_rows}
  </tbody>
</table>

<div id="detail-container">
{detail_cards}
</div>

<script>
{_JS_TEMPLATE}
</script>

</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard created: {output_path}")
