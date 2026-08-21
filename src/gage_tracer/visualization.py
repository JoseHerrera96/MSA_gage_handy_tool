"""Chart generation and HTML dashboard builder.

Handles all visual output: matplotlib Run Charts and Histograms,
and the self-contained HTML dashboard with embedded base-64 images.
"""

from __future__ import annotations

import math
from io import BytesIO
from html import escape
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
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
        figsize=(9, 7),
        gridspec_kw={"height_ratios": [1.1, 0.9]},
    )
    fig.patch.set_facecolor("#FEFEFE")  # Match page background

    # Chart palette — 3-color rule:
    #   #FF6135 (brand orange) = highlight / attention data
    #   #3A3A44 (dark gray) = primary data line
    #   #B0B0BA (light gray) = context / grid / secondary info
    CLR_DATA = "#3A3A44"       # Measurement line & dots
    CLR_REF = "#1A8754"        # Reference line (green = good)
    CLR_LIMIT = "#FF6135"      # Tolerance limits (brand orange = attention)
    CLR_MEAN = "#FF420D"       # Mean line when offset from ref (accent orange)
    CLR_GRID = "#E0E0E4"      # Grid lines — very light, non-competing
    CLR_LABEL = "#5A5A66"      # Axis labels
    CLR_TITLE = "#010101"      # Titles
    CLR_SPINE = "#D1D1D6"      # Axis borders
    CLR_CARD = "#FFFFFF"       # Plot area background

    ax1 = axes[0]
    x_vals = list(range(1, len(measurements) + 1))
    ax1.axhline(y=ref_upper, color=CLR_LIMIT, ls="--", lw=1.2, zorder=1, label="Ref+0.10·Tol")
    ax1.axhline(y=reference_val, color=CLR_REF, ls="-", lw=2, alpha=0.9, zorder=2, label="Ref")
    ax1.axhline(y=ref_lower, color=CLR_LIMIT, ls="--", lw=1.2, zorder=1, label="Ref−0.10·Tol")
    if abs(mean_val - reference_val) > 1e-12:
        ax1.axhline(y=mean_val, color=CLR_MEAN, ls=":", lw=1.4, alpha=0.9, zorder=2, label="Mean")
    ax1.plot(
        x_vals,
        measurements.values,
        "-o",
        ms=3,
        lw=0.9,
        color=CLR_DATA,
        markerfacecolor=CLR_DATA,
        markeredgecolor=CLR_DATA,
        markeredgewidth=0.4,
        zorder=3,
    )
    ax1.set_facecolor(CLR_CARD)
    ax1.set_xlabel("Observation", fontsize=9, color=CLR_LABEL)
    ax1.set_ylabel(dim, fontsize=10, color=CLR_TITLE, fontweight="bold")
    ax1.set_title(f"Run Chart of {dim}", fontsize=11, fontweight="bold", color=CLR_TITLE, pad=6)
    ax1.tick_params(labelsize=8, colors=CLR_LABEL)
    ax1.grid(True, alpha=0.5, color=CLR_GRID)
    for sp in ax1.spines.values():
        sp.set_color(CLR_SPINE)
    ax1.set_ylim(center_line - half_range, center_line + half_range)
    ax1.legend(fontsize=7, loc="upper right", facecolor=CLR_CARD, edgecolor=CLR_SPINE, labelcolor=CLR_LABEL, framealpha=0.95)

    # --- Bottom panel: Histogram ---
    ax2 = axes[1]
    n_bins: int = min(12, max(5, int(np.sqrt(len(measurements)))))
    ax2.hist(measurements.values, bins=n_bins, color="#B0B0BA", edgecolor=CLR_CARD, lw=0.6, rwidth=0.85, alpha=0.85)
    ax2.set_facecolor(CLR_CARD)
    ax2.set_xlabel("Value", fontsize=9, color=CLR_LABEL)
    ax2.set_ylabel("Freq", fontsize=9, color=CLR_LABEL)
    ax2.tick_params(labelsize=8, colors=CLR_LABEL)
    ax2.grid(True, alpha=0.5, color=CLR_GRID, axis="y")
    for sp in ax2.spines.values():
        sp.set_color(CLR_SPINE)
    hp: float = data_span * 0.3 if data_span > 0 else 1e-6
    ax2.set_xlim(data_min - hp, data_max + hp)
    ax2.axvline(x=reference_val, color=CLR_REF, ls="-", lw=1.6, alpha=0.7, label="Ref")
    if abs(mean_val - reference_val) > 1e-12:
        ax2.axvline(x=mean_val, color=CLR_MEAN, ls=":", lw=1.3, alpha=0.8, label="Mean")
    ax2.legend(fontsize=7, loc="best", facecolor=CLR_CARD, edgecolor=CLR_SPINE, labelcolor=CLR_LABEL, framealpha=0.95)

    plt.tight_layout(pad=1.2)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor="#FEFEFE")
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
        measurements = pd.to_numeric(df[dim], errors="coerce").dropna()
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
      <div class="metric-group-title" style="color:var(--color-text-secondary);">Basic Statistics</div>
      <div class="metric-row"><span class="metric-label">Reference</span><span class="metric-value">{ref_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">Mean</span><span class="metric-value">{mean_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">StdDev</span><span class="metric-value">{std_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">6×StdDev (SV)</span><span class="metric-value">{sv_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">Tolerance</span><span class="metric-value">{tol_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">Max diff</span><span class="metric-value">{md_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">Observations</span><span class="metric-value">{d['observations']}</span></div>
    </div>
    <div class="metric-group">
      <div class="metric-group-title" style="color:var(--color-status-accept);">Bias Analysis</div>
      <div class="metric-row"><span class="metric-label">Bias</span><span class="metric-value">{bias_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">T</span><span class="metric-value">{t_fmt}</span></div>
      <div class="metric-row"><span class="metric-label">PValue (Bias=0)</span><span class="metric-value">{p_fmt}</span></div>
    </div>
    <div class="metric-group">
      <div class="metric-group-title" style="color:var(--color-brand-primary);">Capability</div>
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
/* Neutral light theme — semantic design tokens */
:root {
  /* Brand colors */
  --color-brand-primary:  #FF6135;  /* Vibrant orange — CTAs, primary KPI emphasis */
  --color-brand-accent:   #FF420D;  /* Intense orange — critical alerts, danger states */

  /* Backgrounds */
  --color-bg-page:        #FEFEFE;  /* Page background — reduces eye fatigue */
  --color-bg-surface:     #FFFFFF;  /* Card/widget background */
  --color-bg-elevated:    #F5F5F7;  /* Grouped content, table headers */
  --color-bg-hover:       #FFF3EF;  /* Hover state — warm orange tint */

  /* Borders & shadows */
  --color-border-subtle:  #E8E8EC;  /* Card edges, section dividers */
  --color-border-default: #D1D1D6;  /* Active borders, inputs */
  --shadow-card:          0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --shadow-card-hover:    0 4px 12px rgba(0,0,0,0.08);

  /* Text (WCAG 2.2 AA compliant on #FEFEFE) */
  --color-text-primary:   #010101;  /* KPI values, section titles — max legibility */
  --color-text-secondary: #5A5A66;  /* Labels, descriptions — 7.4:1 on white */
  --color-text-muted:     #8E8E99;  /* Tertiary info, timestamps — 4.6:1 on white */
  --color-text-inverse:   #FFFFFF;  /* Text on colored backgrounds */

  /* Semantic status — green/red kept for accept/reject meaning */
  --color-status-accept:  #1A8754;  /* Accessible green — 4.6:1 on white */
  --color-status-reject:  #D42B2B;  /* Accessible red — 5.9:1 on white */

  /* Spacing & typography */
  --space-xs: 4px; --space-sm: 8px; --space-md: 16px;
  --space-lg: 24px; --space-xl: 32px; --space-container: 28px 32px;
  --font-sans:  'Inter', 'Segoe UI', system-ui, sans-serif;
  --font-mono:  'Cascadia Code', 'Consolas', 'Fira Code', monospace;
  --font-kpi:   clamp(36px, 5vw, 48px);
  --font-body:  13px; --font-small: 11px;
  --radius-sm: 6px; --radius-md: 10px; --radius-lg: 14px;
}

/* Reset */
*, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
html { font-size: 16px; }
body {
  background: var(--color-bg-page); color: var(--color-text-primary);
  font-family: var(--font-sans); padding: var(--space-container);
  line-height: 1.55; -webkit-font-smoothing: antialiased;
}

/* Header — title and timestamp */
.dash-header {
  display:flex; align-items:center; gap:var(--space-md);
  padding-bottom:var(--space-md); border-bottom:2px solid var(--color-border-subtle);
  margin-bottom:var(--space-lg);
}
.dash-title {
  font-size:20px; font-weight:600; color:var(--color-text-primary);
  letter-spacing:.2px; flex:1;
}
.dash-title em {
  font-style:normal; color:var(--color-brand-primary); /* Brand orange on title keyword */
}
.dash-date { color:var(--color-text-muted); font-size:var(--font-small); flex-shrink:0; }

/* KPI strip */
.kpi-row {
  display:grid; grid-template-columns:1.7fr repeat(4,1fr);
  gap:var(--space-md); margin-bottom:var(--space-lg);
}
.kpi-card {
  background:var(--color-bg-surface); box-shadow:var(--shadow-card);
  border-radius:var(--radius-md); padding:var(--space-md) var(--space-lg);
  transition:box-shadow .15s, transform .15s;
}
.kpi-card:hover { box-shadow:var(--shadow-card-hover); transform:translateY(-1px); }
.kpi-label {
  color:var(--color-text-secondary); font-size:var(--font-small);
  text-transform:uppercase; letter-spacing:1.2px; font-weight:500; margin-bottom:2px;
}
.kpi-value { color:var(--color-text-primary); font-weight:700; letter-spacing:-.5px; line-height:1.1; }
.kpi-primary .kpi-value { font-size:var(--font-kpi); }  /* Pass rate = largest number on screen */
.kpi-secondary .kpi-value { font-size:clamp(26px,3.5vw,34px); }
.kpi-sub { color:var(--color-text-muted); font-size:var(--font-small); margin-top:2px; }

/* Summary table */
.summary-table {
  width:100%; border-collapse:collapse; font-size:var(--font-body);
  margin-bottom:var(--space-lg); border-radius:var(--radius-md);
  overflow:hidden; box-shadow:var(--shadow-card);
}
.summary-table th {
  background:var(--color-bg-elevated); color:var(--color-text-secondary);
  font-size:10px; text-transform:uppercase; letter-spacing:1px; font-weight:600;
  padding:10px 14px; text-align:left; border-bottom:1px solid var(--color-border-default);
  position:sticky; top:0; z-index:2;
}
.summary-table td {
  padding:9px 14px; border-bottom:1px solid var(--color-border-subtle);
  transition:background .12s;
}
.summary-row { cursor:pointer; }
.summary-row:hover td { background:var(--color-bg-hover); }
.cell-dim { color:var(--color-text-primary); font-weight:600; }
.cell-mono { font-family:var(--font-mono); font-size:12px; color:var(--color-text-primary); }
.cell-expand { text-align:center; color:var(--color-text-muted); font-size:12px; transition:transform .2s; }
.row-open .cell-expand { transform:rotate(90deg); color:var(--color-brand-primary); }

/* Status badges */
.status-accept { color:var(--color-status-accept); font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:.5px; }
.status-reject { color:var(--color-status-reject); font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:.5px; }
.kpi-good { color:var(--color-status-accept); font-family:var(--font-mono); font-weight:600; }
.kpi-bad  { color:var(--color-status-reject); font-family:var(--font-mono); font-weight:600; }

/* Detail cards */
.detail-card {
  background:var(--color-bg-surface); border-left:4px solid var(--color-status-accept);
  border-radius:var(--radius-md); margin-bottom:var(--space-md); padding:var(--space-md);
  gap:var(--space-md); display:flex; flex-wrap:wrap; box-shadow:var(--shadow-card);
}
.detail-card.highlight { animation:fadeSlide .25s ease-out; border-left-color:var(--color-brand-primary) !important; }
@keyframes fadeSlide { from{opacity:0;transform:translateY(-8px)} to{opacity:1;transform:translateY(0)} }
.detail-chart { flex:2; min-width:380px; }
.detail-chart img { width:100%; display:block; border-radius:var(--radius-sm); }
.detail-metrics { flex:1; min-width:250px; display:flex; flex-direction:column; gap:var(--space-sm); }
.metric-group { background:var(--color-bg-elevated); border-radius:var(--radius-sm); padding:var(--space-sm) var(--space-md); }
.metric-group-title { font-size:10px; text-transform:uppercase; letter-spacing:1px; font-weight:700; margin-bottom:var(--space-xs); }
.metric-row { display:flex; justify-content:space-between; padding:3px 0; font-size:12px; }
.metric-label { color:var(--color-text-secondary); }
.metric-value { color:var(--color-text-primary); font-family:var(--font-mono); font-size:12px; }
.metric-status {
  align-self:stretch; text-align:center; font-weight:800; font-size:13px;
  padding:8px; border-radius:var(--radius-sm); color:var(--color-text-inverse);
  letter-spacing:1px; text-transform:uppercase;
}

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
    output_path: Path | None = None,
) -> str:
    """Generate a self-contained HTML dashboard with embedded charts.

    Produces a single HTML string containing embedded Base64 chart images.
    If ``output_path`` is provided, the rendered HTML is also written to disk.

    Args:
        df: Full measurement DataFrame.
        summary_data: List of metric dicts produced by
            ``calculate_type1_metrics``.
        output_path: Optional destination path for the ``.html`` file.

    Returns:
        The rendered HTML content.
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

    pr_color = "var(--color-status-accept)" if pass_rate >= 75 else "var(--color-brand-accent)"

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
  <div class="kpi-card kpi-secondary" style="border-left:3px solid var(--color-brand-primary);">
    <div class="kpi-label">Best Cgk</div>
    <div class="kpi-value" style="color:var(--color-text-primary);">{best['Cgk']:.2f}</div>
    <div class="kpi-sub">{best['Gage Item']}</div>
  </div>
  <div class="kpi-card kpi-secondary" style="border-left:3px solid var(--color-brand-accent);">
    <div class="kpi-label">Worst Cgk</div>
    <div class="kpi-value" style="color:var(--color-text-primary);">{worst['Cgk']:.2f}</div>
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

    if output_path is not None:
        output_path.write_text(html, encoding="utf-8")
        print(f"Dashboard created: {output_path}")

    return html


# ---------------------------------------------------------------------------
# Gage R&R Crossed Dashboard (6-Panel Minitab Standard)
# ---------------------------------------------------------------------------

# Control chart constants for n=3 (subgroup size)
_D2 = 1.693  # Constant for R chart
_D3 = 0.0    # Lower control limit factor for R chart
_D4 = 2.574  # Upper control limit factor for R chart
_A2 = 1.023  # Constant for Xbar chart


def create_gage_rr_dashboard(
    df: pd.DataFrame,
    results_dict: dict[str, object],
    part_col: str = "Part",
    op_col: str = "Operator",
    resp_col: str = "Measurement",
  dark_mode: bool = False,
) -> plt.Figure:
    """Generate 6-panel Gage R&R Crossed dashboard following Minitab standards.

    Creates a 2x3 grid of charts:
    1. Components of Variation (bar chart)
    2. Measurement by Part (scatter + line)
    3. R Chart by Operator (control chart)
    4. Measurement by Operator (boxplots)
    5. Xbar Chart by Operator (control chart)
    6. Part * Operator Interaction (line plot)

    Args:
        df: DataFrame with Part, Operator, Measurement columns.
        results_dict: Results dictionary from calculate_gage_rr_crossed.
        part_col: Name of part column (default "Part").
        op_col: Name of operator column (default "Operator").
        resp_col: Name of measurement column (default "Measurement").
        dark_mode: Use the dark Streamlit preview palette when ``True``.

    Returns:
        matplotlib Figure object with 6 panels.
    """
    # Color palette (consistent with project)
    CLR_DATA = "#D8DEE9" if dark_mode else "#3A3A44"       # Primary data
    CLR_REF = "#1A8754"        # Reference/good
    CLR_LIMIT = "#FF6135"      # Control limits/attention
    CLR_MEAN = "#FF420D"       # Mean/accent
    CLR_GRID = "#334155" if dark_mode else "#E0E0E4"      # Grid
    CLR_LABEL = "#CBD5E1" if dark_mode else "#5A5A66"      # Labels
    CLR_TITLE = "#F8FAFC" if dark_mode else "#010101"      # Titles
    CLR_SPINE = "#475569" if dark_mode else "#D1D1D6"      # Borders
    CLR_CARD = "#0E1826" if dark_mode else "#FFFFFF"       # Background
    CLR_FIGURE = "#0B1220" if dark_mode else "#FEFEFE"

    # Extract variance components for chart 1
    var_df = results_dict["variance_components"]
    gage_eval_df = results_dict["gage_evaluation"]

    # Create 2x3 figure
    figure_height = 14 if dark_mode else 12
    fig, axes = plt.subplots(2, 3, figsize=(18, figure_height))
    fig.patch.set_facecolor(CLR_FIGURE)
    if "Characteristic" in df.columns and df["Characteristic"].nunique() == 1:
      fig.suptitle(
        f"Gage R&R (Crossed) - Characteristic: {df['Characteristic'].iloc[0]}",
        fontsize=14,
        fontweight="bold",
        color=CLR_TITLE,
      )

    # Panel 1: Components of Variation (Bar Chart)
    ax1 = axes[0, 0]
    sources = ["Total Gage R&R", "Repeatability", "Reproducibility", "Operator", "Part-to-Part"]
    contribution_values = []
    study_var_values = []
    tolerance_values = []
    for source in sources:
        row = var_df[var_df["Source"] == source].iloc[0]
        contribution_values.append(float(row["%Contribution"]))
        study_var_values.append(float(row["%StudyVar"]))
        tolerance_values.append(float(row["%Tolerance"]))

    x_positions = np.arange(len(sources))
    bar_width = 0.25
    ax1.bar(
      x_positions - bar_width,
      contribution_values,
      bar_width,
      color=CLR_LIMIT,
      alpha=0.85,
      label="% Contribution",
    )
    ax1.bar(
      x_positions,
      study_var_values,
      bar_width,
      color=CLR_DATA,
      alpha=0.85,
      label="% Study Var",
    )
    ax1.bar(
      x_positions + bar_width,
      tolerance_values,
      bar_width,
      color=CLR_REF,
      alpha=0.85,
      label="% Tolerance",
    )
    ax1.set_xticks(x_positions)
    ax1.set_xticklabels(sources, rotation=45, ha="right")
    ax1.set_ylabel("Percent", fontsize=9, color=CLR_LABEL)
    ax1.set_title("Components of Variation", fontsize=10, fontweight="bold", color=CLR_TITLE)
    ax1.tick_params(labelsize=8, colors=CLR_LABEL)
    ax1.grid(True, alpha=0.3, color=CLR_GRID, axis="y")
    ax1.legend(fontsize=7, loc="upper left", facecolor=CLR_CARD, edgecolor=CLR_SPINE)
    for spine in ax1.spines.values():
        spine.set_color(CLR_SPINE)

    # Panel 2: Measurement by Part (all trials grouped by physical part)
    ax2 = axes[0, 1]
    parts = sorted(df[part_col].unique())
    part_positions = np.arange(len(parts))
    for operator in sorted(df[op_col].unique()):
      operator_means = []
      for part in parts:
        values = df[(df[op_col] == operator) & (df[part_col] == part)][resp_col]
        operator_means.append(float(values.mean()))
      ax2.plot(
        part_positions,
        operator_means,
        "-o",
        markersize=4,
        linewidth=1.2,
        alpha=0.8,
        label=operator,
      )

    ax2.set_xlabel("Part", fontsize=9, color=CLR_LABEL)
    ax2.set_xticks(part_positions)
    ax2.set_xticklabels(parts, rotation=45, ha="right")
    ax2.set_ylabel(resp_col, fontsize=9, color=CLR_LABEL)
    ax2.set_title("Measurement by Part", fontsize=10, fontweight="bold", color=CLR_TITLE)
    ax2.tick_params(labelsize=8, colors=CLR_LABEL)
    ax2.grid(True, alpha=0.3, color=CLR_GRID)
    ax2.legend(fontsize=7, loc="best", facecolor=CLR_CARD, edgecolor=CLR_SPINE, labelcolor=CLR_LABEL)
    for spine in ax2.spines.values():
        spine.set_color(CLR_SPINE)

    # Panel 3: R Chart by Operator (one subgroup range per part)
    ax3 = axes[0, 2]
    operator_labels = sorted(df[op_col].unique())
    r_values_by_operator: dict[str, list[float]] = {}

    for operator in operator_labels:
      op_data = df[df[op_col] == operator]
      part_ranges = []
      for part in parts:
        part_trials = op_data[op_data[part_col] == part][resp_col].values
        part_ranges.append(float(part_trials.max() - part_trials.min()))
      r_values_by_operator[operator] = part_ranges

    all_ranges = [value for values in r_values_by_operator.values() for value in values]
    r_bar = float(np.mean(all_ranges)) if all_ranges else 0.0
    ucl_r = _D4 * r_bar
    lcl_r = _D3 * r_bar
    for operator in operator_labels:
      ax3.plot(
        part_positions,
        r_values_by_operator[operator],
        "-o",
        markersize=3,
        linewidth=1,
        label=operator,
      )
    ax3.axhline(y=ucl_r, color=CLR_LIMIT, ls="--", lw=1.5, label=f"UCL ({ucl_r:.4f})")
    ax3.axhline(y=r_bar, color=CLR_REF, ls="-", lw=1.5, label=f"R-bar ({r_bar:.4f})")
    if lcl_r > 0:
      ax3.axhline(y=lcl_r, color=CLR_LIMIT, ls="--", lw=1.5, label=f"LCL ({lcl_r:.4f})")

    ax3.set_xticks(part_positions)
    ax3.set_xticklabels(parts, rotation=45, ha="right", fontsize=8)
    ax3.set_ylabel("Range (R)", fontsize=9, color=CLR_LABEL)
    ax3.set_title("R Chart by Operator", fontsize=10, fontweight="bold", color=CLR_TITLE)
    ax3.tick_params(labelsize=8, colors=CLR_LABEL)
    ax3.grid(True, alpha=0.3, color=CLR_GRID, axis="y")
    ax3.legend(fontsize=7, loc="best", facecolor=CLR_CARD, edgecolor=CLR_SPINE, labelcolor=CLR_LABEL)
    for spine in ax3.spines.values():
        spine.set_color(CLR_SPINE)

    # Panel 4: Measurement by Operator (Boxplots)
    ax4 = axes[1, 0]
    box_data = [df[df[op_col] == op][resp_col].values for op in sorted(df[op_col].unique())]
    bp = ax4.boxplot(
      box_data,
      labels=sorted(df[op_col].unique()),
      patch_artist=True,
      flierprops={
        "marker": "o",
        "markerfacecolor": CLR_LIMIT,
        "markeredgecolor": CLR_LIMIT,
        "markersize": 5,
        "alpha": 0.95,
      },
      whiskerprops={"color": CLR_DATA, "linewidth": 1.2},
      capprops={"color": CLR_DATA, "linewidth": 1.2},
    )

    for patch in bp["boxes"]:
        patch.set_facecolor(CLR_DATA)
        patch.set_alpha(0.6)
        patch.set_edgecolor(CLR_SPINE)

    for median in bp["medians"]:
        median.set_color(CLR_MEAN)
        median.set_linewidth(2)

    # Minitab overlays individual observations on this panel. Highlight only
    # observations outside the standard 1.5*IQR whisker limits.
    for position, operator in enumerate(operator_labels, start=1):
      values = df[df[op_col] == operator][resp_col].to_numpy(dtype=float)
      if values.size == 0:
        continue
      quartile_1, quartile_3 = np.percentile(values, [25, 75])
      iqr = quartile_3 - quartile_1
      lower_fence = quartile_1 - 1.5 * iqr
      upper_fence = quartile_3 + 1.5 * iqr
      outlier_mask = (values < lower_fence) | (values > upper_fence)
      jitter = np.linspace(-0.12, 0.12, values.size)
      ax4.scatter(
        np.full(values.size, position) + jitter,
        values,
        s=16,
        color=CLR_DATA,
        alpha=0.7,
        zorder=3,
      )
      if outlier_mask.any():
        ax4.scatter(
          np.full(outlier_mask.sum(), position) + jitter[outlier_mask],
          values[outlier_mask],
          s=34,
          color=CLR_LIMIT,
          edgecolors=CLR_LIMIT,
          zorder=4,
          label="Outlier" if position == 1 else "_nolegend_",
        )

    ax4.set_ylabel(resp_col, fontsize=9, color=CLR_LABEL)
    ax4.set_title("Measurement by Operator", fontsize=10, fontweight="bold", color=CLR_TITLE)
    ax4.tick_params(labelsize=8, colors=CLR_LABEL)
    ax4.grid(True, alpha=0.3, color=CLR_GRID, axis="y")
    for spine in ax4.spines.values():
        spine.set_color(CLR_SPINE)

    # Panel 5: Xbar Chart by Operator (one subgroup mean per part)
    ax5 = axes[1, 1]
    xbar_values_by_operator: dict[str, list[float]] = {}
    for operator in operator_labels:
      op_data = df[df[op_col] == operator]
      part_means = []
      for part in parts:
        part_trials = op_data[op_data[part_col] == part][resp_col].values
        part_means.append(float(np.mean(part_trials)))
      xbar_values_by_operator[operator] = part_means

    all_xbars = [value for values in xbar_values_by_operator.values() for value in values]
    x_double_bar = float(np.mean(all_xbars)) if all_xbars else 0.0
    ucl_x = x_double_bar + _A2 * r_bar
    lcl_x = x_double_bar - _A2 * r_bar
    for operator in operator_labels:
        ax5.plot(
            part_positions,
            xbar_values_by_operator[operator],
            "-o",
            markersize=3,
            linewidth=1,
            label=operator,
        )
    ax5.axhline(y=ucl_x, color=CLR_LIMIT, ls="--", lw=1.5, label=f"UCL ({ucl_x:.4f})")
    ax5.axhline(y=x_double_bar, color=CLR_REF, ls="-", lw=1.5, label=f"X-bar ({x_double_bar:.4f})")
    ax5.axhline(y=lcl_x, color=CLR_LIMIT, ls="--", lw=1.5, label=f"LCL ({lcl_x:.4f})")

    ax5.set_xticks(part_positions)
    ax5.set_xticklabels(parts, rotation=45, ha="right", fontsize=8)
    ax5.set_ylabel("X-bar", fontsize=9, color=CLR_LABEL)
    ax5.set_title("Xbar Chart by Operator", fontsize=10, fontweight="bold", color=CLR_TITLE)
    ax5.tick_params(labelsize=8, colors=CLR_LABEL)
    ax5.grid(True, alpha=0.3, color=CLR_GRID, axis="y")
    ax5.legend(fontsize=7, loc="best", facecolor=CLR_CARD, edgecolor=CLR_SPINE, labelcolor=CLR_LABEL)
    for spine in ax5.spines.values():
        spine.set_color(CLR_SPINE)

    # Panel 6: Part * Operator Interaction
    ax6 = axes[1, 2]
    for operator in operator_labels:
        op_data = df[df[op_col] == operator]
        part_means = []
        for part in parts:
            part_trials = op_data[op_data[part_col] == part][resp_col].values
            part_means.append(np.mean(part_trials))
        ax6.plot(part_positions, part_means, "-o", markersize=4, linewidth=1.5, alpha=0.8, label=operator)

    ax6.set_xlabel("Part", fontsize=9, color=CLR_LABEL)
    ax6.set_xticks(part_positions)
    ax6.set_xticklabels(parts, rotation=45, ha="right")
    ax6.set_ylabel("Mean Measurement", fontsize=9, color=CLR_LABEL)
    ax6.set_title("Part * Operator Interaction", fontsize=10, fontweight="bold", color=CLR_TITLE)
    ax6.tick_params(labelsize=8, colors=CLR_LABEL)
    ax6.grid(True, alpha=0.3, color=CLR_GRID)
    ax6.legend(fontsize=7, loc="best", facecolor=CLR_CARD, edgecolor=CLR_SPINE, labelcolor=CLR_LABEL)
    for spine in ax6.spines.values():
        spine.set_color(CLR_SPINE)

    for axis in axes.flat:
        axis.set_facecolor(CLR_CARD)
        axis.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        axis.ticklabel_format(axis="y", style="plain", useOffset=False)

    fig.tight_layout(pad=2.0, rect=(0, 0, 1, 0.96))
    return fig


def create_gage_rr_html_dashboard(
    df: pd.DataFrame,
    results_dict: dict[str, Any],
    output_path: Path | None = None,
) -> str:
    """Generate a self-contained HTML dashboard for Gage R&R Crossed results.

    Embeds the 6-panel chart as a Base64 image and displays KPI cards, ANOVA table,
    variance components, and gage evaluation tables.

    """
    import base64
    import time
    from io import BytesIO

    # 1. Render 6-panel figure to Base64
    fig = create_gage_rr_dashboard(df, results_dict)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor="#FEFEFE")
    plt.close(fig)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode("utf-8")

    # 2. Extract key metrics
    grr_pct = float(results_dict["total_grr_pct"])
    ndc = int(results_dict["ndc"])
    sv_total = float(results_dict["study_variation"])
    n_parts = int(results_dict["n_parts"])
    n_ops = int(results_dict["n_operators"])
    n_trials = int(results_dict["n_trials"])
    characteristic = (
      str(df["Characteristic"].iloc[0])
      if "Characteristic" in df.columns and df["Characteristic"].nunique() == 1
      else "All characteristics"
    )
    characteristic_html = escape(characteristic)

    # Industrial verdict
    if grr_pct < 10 and ndc >= 5:
        verdict = "PASS"
        verdict_color = "var(--color-status-accept)"
        verdict_msg = "Excellent - Measurement system is acceptable"
    elif 10 <= grr_pct <= 30 and ndc >= 5:
        verdict = "MARGINAL"
        verdict_color = "var(--color-brand-primary)"
        verdict_msg = "Marginal - Measurement system may be acceptable depending on application"
    else:
        verdict = "FAIL"
        verdict_color = "var(--color-status-reject)"
        verdict_msg = "Unacceptable - Measurement system needs improvement"

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    anova_html = results_dict["anova_table"].to_html(index=False, classes="stats-table")
    var_html = results_dict["variance_components"].to_html(index=False, classes="stats-table")
    eval_html = results_dict["gage_evaluation"].to_html(index=False, classes="stats-table")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gage R&amp;R (Crossed) — {characteristic_html}</title>
<style>
{_CSS_TEMPLATE}
.stats-table {{
  width:100%; border-collapse:collapse; font-size:12px; margin-bottom:16px;
  background:#FFFFFF; border-radius:6px; overflow:hidden; box-shadow:var(--shadow-card);
}}
.stats-table th {{
  background:var(--color-bg-elevated); color:var(--color-text-secondary);
  font-size:10px; text-transform:uppercase; letter-spacing:1px; font-weight:600;
  padding:10px 14px; text-align:left; border-bottom:1px solid var(--color-border-default);
}}
.stats-table td {{
  padding:8px 14px; border-bottom:1px solid var(--color-border-subtle);
  color:var(--color-text-primary); font-family:var(--font-mono);
}}
.stats-table tr:nth-child(even) td {{
  background:var(--color-bg-elevated);
}}
.section-card {{
  background:var(--color-bg-surface); border-radius:var(--radius-md);
  padding:var(--space-md) var(--space-lg); margin-bottom:var(--space-lg);
  box-shadow:var(--shadow-card); border:1px solid var(--color-border-subtle);
}}
.chart-section {{
  background:var(--color-bg-elevated); border-radius:var(--radius-md);
  padding:var(--space-md) var(--space-lg); margin-bottom:var(--space-lg);
  border:1px solid var(--color-border-subtle);
}}
.section-title {{
  font-size:14px; font-weight:700; color:var(--color-text-primary);
  margin-bottom:var(--space-md); text-transform:uppercase; letter-spacing:0.5px;
}}
.chart-container img {{
  width:100%; height:auto; border-radius:var(--radius-sm); display:block;
}}
</style>
</head>
<body>

<div class="dash-header">
  <h1 class="dash-title"><em>Gage R&amp;R (Crossed)</em> ANOVA Dashboard — {characteristic_html}</h1>
  <span class="dash-date">{timestamp}</span>
</div>

<div class="kpi-row">
  <div class="kpi-card kpi-secondary" style="border-left:3px solid var(--color-brand-primary);">
    <div class="kpi-label">Characteristic</div>
    <div class="kpi-value" style="font-size:20px;">{characteristic_html}</div>
    <div class="kpi-sub">Independent Gage R&amp;R report</div>
  </div>
  <div class="kpi-card kpi-primary" style="border-left:4px solid {verdict_color};">
    <div class="kpi-label">Verdict</div>
    <div class="kpi-value" style="color:{verdict_color}; font-size:32px;">{verdict}</div>
    <div class="kpi-sub">{verdict_msg}</div>
  </div>
  <div class="kpi-card kpi-secondary" style="border-left:3px solid var(--color-brand-primary);">
    <div class="kpi-label">% Total Gage R&amp;R</div>
    <div class="kpi-value">{grr_pct:.2f}%</div>
    <div class="kpi-sub">Target &lt; 10%</div>
  </div>
  <div class="kpi-card kpi-secondary" style="border-left:3px solid var(--color-status-accept);">
    <div class="kpi-label">NDC</div>
    <div class="kpi-value">{ndc}</div>
    <div class="kpi-sub">Target &ge; 5</div>
  </div>
  <div class="kpi-card kpi-secondary" style="border-left:3px solid var(--color-text-secondary);">
    <div class="kpi-label">Study Variation</div>
    <div class="kpi-value" style="font-size:20px;">{sv_total:.6f}</div>
    <div class="kpi-sub">6 &times; SD</div>
  </div>
  <div class="kpi-card kpi-secondary" style="border-left:3px solid var(--color-brand-accent);">
    <div class="kpi-label">Design</div>
    <div class="kpi-value" style="font-size:18px;">{n_parts}P &times; {n_ops}O &times; {n_trials}T</div>
    <div class="kpi-sub">{len(df)} measurements</div>
  </div>
</div>

<div class="chart-section">
  <div class="section-title">Gage R&amp;R Dashboard</div>
  <div class="chart-container">
    <img src="data:image/png;base64,{img_b64}" alt="Gage R&amp;R Dashboard">
  </div>
</div>

<div class="section-card">
  <div class="section-title">ANOVA Table</div>
  {anova_html}
</div>

<div class="section-card">
  <div class="section-title">Variance Components</div>
  {var_html}
</div>

<div class="section-card">
  <div class="section-title">Gage Evaluation</div>
  {eval_html}
</div>

</body>
</html>"""

    if output_path is not None:
        output_path.write_text(html, encoding="utf-8")
        print(f"Gage R&R Dashboard HTML created: {output_path}")

    return html
