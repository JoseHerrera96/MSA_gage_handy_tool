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
