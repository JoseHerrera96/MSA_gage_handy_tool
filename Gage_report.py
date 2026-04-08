import math
import pandas as pd
import numpy as np
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class SimplifiedGageReporter(FileSystemEventHandler):
    def __init__(self, watch_file, report_output):
        self.watch_file = watch_file
        self.report_output = report_output

    def on_modified(self, event):
        if event.src_path.endswith(self.watch_file):
            # Brief pause to let the OS finish the file write
            time.sleep(0.3)
            self.generate_report()

    @staticmethod
    def _compute_bias_significance(bias, std_dev, sample_size):
        """Return t-statistic and two-sided p-value for bias = 0."""
        if sample_size <= 1 or pd.isna(std_dev) or std_dev <= 0:
            if abs(bias) < 1e-12:
                return 0.0, 1.0
            return float('inf'), 0.0

        t_value = bias / (std_dev / math.sqrt(sample_size))
        try:
            from scipy import stats
            p_value = float(2 * stats.t.sf(abs(t_value), df=sample_size - 1))
        except Exception:
            # Fallback to a normal approximation if SciPy is unavailable.
            p_value = float(math.erfc(abs(t_value) / math.sqrt(2)))

        return float(t_value), float(p_value)

    def _calculate_type1_metrics(self, dim, measurements, spec_row):
        """Compute a Minitab-style Type 1 Gage Study metric set for one dimension."""
        nominal = float(spec_row['Nominal'])
        upper_tol = float(spec_row['Upper Tol'])
        lower_tol = float(spec_row['Lower Tol'])

        sample_size = int(len(measurements))
        mean = float(measurements.mean())
        std_dev = float(measurements.std()) if sample_size > 1 else 0.0
        if pd.isna(std_dev):
            std_dev = 0.0

        max_diff = float(measurements.max() - measurements.min()) if sample_size > 0 else 0.0
        # Minitab Type 1 uses the stated tolerance value, not the full span.
        tolerance = max(abs(upper_tol), abs(lower_tol))
        study_var = 6 * std_dev

        # Use an explicit reference if present; otherwise fall back to the
        # measured average as the best available proxy for the master value.
        if 'Reference' in spec_row and pd.notna(spec_row['Reference']):
            reference = float(spec_row['Reference'])
        elif 'Average' in spec_row and pd.notna(spec_row['Average']):
            reference = float(spec_row['Average'])
        else:
            reference = mean

        bias = mean - reference
        t_value, p_value = self._compute_bias_significance(bias, std_dev, sample_size)

        cg = ((0.2 * tolerance) / study_var) if study_var > 0 and tolerance > 0 else 0.0
        cgk = (
            (0.1 * tolerance - abs(bias)) / (3 * std_dev)
            if std_dev > 0 and tolerance > 0 else 0.0
        )

        repeatability_pct = (study_var / tolerance * 100) if tolerance > 0 else None
        repeatability_bias_pct = (
            6 * math.sqrt(std_dev ** 2 + bias ** 2) / tolerance * 100
            if tolerance > 0 else None
        )

        return {
            'Gage Item': dim,
            'Reference': reference,
            'Mean': mean,
            'Bias': bias,
            'T': t_value,
            'PValue': p_value,
            'StdDev': std_dev,
            '6 x StdDev (SV)': study_var,
            'Tolerance (Tol)': tolerance,
            'Max diff': max_diff,
            'Cg': cg,
            'Cgk': cgk,
            '%Var(Repeatability)': repeatability_pct,
            '%Var(Repeatability and Bias)': repeatability_bias_pct,
            'Observations': sample_size,
            'Nominal': nominal,
            'Upper Tol': upper_tol,
            'Lower Tol': lower_tol,
            'Ref + 0.10*Tol': reference + 0.1 * tolerance,
            'Ref - 0.10*Tol': reference - 0.1 * tolerance,
            'Status': 'ACCEPT' if cg >= 1.33 and cgk >= 1.33 else 'REJECT',
        }

    def generate_report(self):
        try:
            # 1. Read the file
            # Tab-Separated format from data prep.py
            df = pd.read_csv(self.watch_file, sep='\t')

            summary = []

            # 2. Identify Dimension Columns
            # Measurement columns are C# tags at the start.
            for col in df.columns:
                if col.startswith('C') and not any(
                    x in col for x in ['tol', 'Avg', 'Max', 'Nominal']
                ):
                    measurements = df[col].dropna().astype(float)
                    if measurements.empty:
                        continue

                    try:
                        spec_row = df[df['Dimension'] == col].iloc[0]
                        summary.append(
                            self._calculate_type1_metrics(col, measurements, spec_row)
                        )
                    except (KeyError, IndexError, ValueError, TypeError):
                        # Skip if specs or numeric values are not usable.
                        continue

            # 5. Export the Minitab-style Summary
            if summary:
                report_df = pd.DataFrame(summary)[[
                    'Gage Item', 'Reference', 'Mean', 'Bias', 'T', 'PValue',
                    'StdDev', '6 x StdDev (SV)', 'Tolerance (Tol)', 'Max diff',
                    'Cg', 'Cgk', '%Var(Repeatability)',
                    '%Var(Repeatability and Bias)', 'Status'
                ]].copy()

                for col in [
                    'Reference', 'Mean', 'Bias', 'StdDev',
                    '6 x StdDev (SV)', 'Tolerance (Tol)', 'Max diff'
                ]:
                    report_df[col] = report_df[col].map(lambda x: f'{x:.8f}')
                for col in ['T', 'PValue', 'Cg', 'Cgk']:
                    report_df[col] = report_df[col].map(lambda x: f'{x:.4f}')
                for col in ['%Var(Repeatability)', '%Var(Repeatability and Bias)']:
                    report_df[col] = report_df[col].map(
                        lambda x: f'{x:.2f}%' if pd.notna(x) else 'N/A'
                    )

                with open(self.report_output, 'w') as f:
                    f.write("==============================================\n")
                    f.write("AUTOMATED TYPE 1 GAGE STUDY (MINITAB-STYLE)\n")
                    f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("==============================================\n\n")
                    f.write(report_df.to_string(index=False))
                print(f"Report generated: {len(summary)} dimensions analyzed.")
                # Create dashboard with data already in memory
                self.create_dashboard(df, summary)
            else:
                print("No valid dimensions found in data.")

        except Exception as e:
            print(f"Error reading gage data: {e}")

    def create_dashboard(self, df, summary_data):
        """Create a high-density Type 1 Gage Study dashboard.

        Architecture: semantic design tokens, F-pattern layout, progressive
        disclosure (details hidden behind click), 80/20 KPI hierarchy.
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import base64
            from io import BytesIO

            summary_df = pd.DataFrame(summary_data)
            summary_df = summary_df.rename(columns={'Gage Item': 'Dimension'})
            num_dims = len(summary_df)
            accepted = sum(1 for s in summary_data if s['Status'] == 'ACCEPT')
            rejected = num_dims - accepted
            pass_rate = round(accepted * 100 / num_dims, 1) if num_dims else 0

            # ── Identify worst dimension (lowest Cgk) for KPI spotlight ──
            worst = min(summary_data, key=lambda s: s['Cgk'])
            best = max(summary_data, key=lambda s: s['Cgk'])

            # ── Generate charts ──
            chart_images = []
            for _, row in summary_df.iterrows():
                dim = row['Dimension']
                if dim not in df.columns:
                    continue
                measurements = df[dim].dropna().astype(float)
                reference_val = float(row['Reference'])
                mean_val = float(row['Mean'])
                std_val = float(row['StdDev'])
                ref_upper = float(row['Ref + 0.10*Tol'])
                ref_lower = float(row['Ref - 0.10*Tol'])

                if pd.isna(std_val) or std_val == 0:
                    std_val = 0.0
                data_min = float(measurements.min())
                data_max = float(measurements.max())
                data_span = data_max - data_min
                if data_span == 0:
                    data_span = abs(mean_val) * 1e-4 if mean_val != 0 else 1e-6

                center_line = reference_val
                max_dist = max(
                    abs(data_max - center_line), abs(data_min - center_line),
                    abs(ref_upper - center_line), abs(ref_lower - center_line),
                )
                half_range = max_dist * 1.1
                if std_val > 0:
                    half_range = max(half_range, 5 * std_val)
                if half_range == 0:
                    half_range = data_span * 2

                # ── matplotlib: Run Chart + Histogram ──
                fig, axes = plt.subplots(
                    2, 1, figsize=(11, 9),
                    gridspec_kw={'height_ratios': [1.2, 0.8]},
                )
                fig.patch.set_facecolor('#0b0e14')

                ax1 = axes[0]
                x_vals = list(range(1, len(measurements) + 1))
                ax1.axhline(y=ref_upper, color='#e8836a', ls='--', lw=1.2, zorder=1,
                            label=f'Ref+0.10·Tol')
                ax1.axhline(y=reference_val, color='#7dcea0', ls='-', lw=2, alpha=.9,
                            zorder=2, label='Ref')
                ax1.axhline(y=ref_lower, color='#e8836a', ls='--', lw=1.2, zorder=1,
                            label=f'Ref−0.10·Tol')
                if abs(mean_val - reference_val) > 1e-12:
                    ax1.axhline(y=mean_val, color='#d4a574', ls=':', lw=1.4, alpha=.9,
                                zorder=2, label='Mean')
                ax1.plot(x_vals, measurements.values, '-o', ms=3, lw=0.9,
                         color='#58a6c9', markerfacecolor='#79c0db',
                         markeredgecolor='#58a6c9', markeredgewidth=0.4, zorder=3)
                ax1.set_facecolor('#11151c')
                ax1.set_xlabel('Observation', fontsize=9, color='#6e7681')
                ax1.set_ylabel(dim, fontsize=10, color='#8b949e', fontweight='bold')
                ax1.set_title(f'Run Chart of {dim}', fontsize=11, fontweight='bold',
                              color='#c9d1d9', pad=6)
                ax1.tick_params(labelsize=8, colors='#6e7681')
                ax1.grid(True, alpha=0.08, color='#484f58')
                for sp in ax1.spines.values():
                    sp.set_color('#21262d')
                ax1.set_ylim(center_line - half_range, center_line + half_range)
                ax1.legend(fontsize=7, loc='upper right', facecolor='#11151c',
                           edgecolor='#21262d', labelcolor='#8b949e', framealpha=.85)

                ax2 = axes[1]
                n_bins = min(12, max(5, int(np.sqrt(len(measurements)))))
                ax2.hist(measurements.values, bins=n_bins, color='#58a6c9',
                         edgecolor='#11151c', lw=0.6, rwidth=0.85, alpha=0.85)
                ax2.set_facecolor('#11151c')
                ax2.set_xlabel('Value', fontsize=9, color='#6e7681')
                ax2.set_ylabel('Freq', fontsize=9, color='#6e7681')
                ax2.tick_params(labelsize=8, colors='#6e7681')
                ax2.grid(True, alpha=0.08, color='#484f58', axis='y')
                for sp in ax2.spines.values():
                    sp.set_color('#21262d')
                hp = data_span * 0.3 if data_span > 0 else 1e-6
                ax2.set_xlim(data_min - hp, data_max + hp)
                ax2.axvline(x=reference_val, color='#7dcea0', ls='-', lw=1.6,
                            alpha=0.7, label='Ref')
                if abs(mean_val - reference_val) > 1e-12:
                    ax2.axvline(x=mean_val, color='#d4a574', ls=':', lw=1.3,
                                alpha=0.8, label='Mean')
                ax2.legend(fontsize=7, loc='best', facecolor='#11151c',
                           edgecolor='#21262d', labelcolor='#8b949e', framealpha=.85)

                plt.tight_layout(pad=1.2)
                buf = BytesIO()
                fig.savefig(buf, format='png', dpi=140, bbox_inches='tight',
                            facecolor='#0b0e14')
                plt.close(fig)
                buf.seek(0)
                img_b64 = base64.b64encode(buf.read()).decode('utf-8')

                chart_images.append({
                    'dim': dim,
                    'img': img_b64,
                    'status': row['Status'],
                    'reference': reference_val,
                    'mean': mean_val,
                    'max_diff': float(row['Max diff']),
                    'stddev': std_val,
                    'study_var': float(row['6 x StdDev (SV)']),
                    'tolerance': float(row['Tolerance (Tol)']),
                    'bias': float(row['Bias']),
                    't_value': float(row['T']),
                    'p_value': float(row['PValue']),
                    'cg': float(row['Cg']),
                    'cgk': float(row['Cgk']),
                    'var_repeat': row['%Var(Repeatability)'],
                    'var_repeat_bias': row['%Var(Repeatability and Bias)'],
                    'observations': int(row['Observations']),
                    'ref_upper': ref_upper,
                    'ref_lower': ref_lower,
                })

            # ── Build dimension summary table rows ──
            summary_rows = ""
            for i, d in enumerate(chart_images):
                st_cls = 'status-accept' if d['status'] == 'ACCEPT' else 'status-reject'
                cg_cls = 'kpi-good' if d['cg'] >= 1.33 else 'kpi-bad'
                cgk_cls = 'kpi-good' if d['cgk'] >= 1.33 else 'kpi-bad'
                vr = f"{d['var_repeat']:.1f}" if pd.notna(d['var_repeat']) else '—'
                summary_rows += f"""<tr class="summary-row" data-idx="{i}">
  <td class="cell-dim">{d['dim']}</td>
  <td class="{st_cls}">{d['status']}</td>
  <td class="{cg_cls}">{d['cg']:.2f}</td>
  <td class="{cgk_cls}">{d['cgk']:.2f}</td>
  <td class="cell-mono">{vr}%</td>
  <td class="cell-mono">{d['bias']:+.6f}</td>
  <td class="cell-dim cell-expand">▸</td>
</tr>\n"""

            # ── Build expandable detail cards ──
            detail_cards = ""
            for i, d in enumerate(chart_images):
                ref_fmt = f"{d['reference']:.8f}"
                mean_fmt = f"{d['mean']:.8f}"
                std_fmt = f"{d['stddev']:.8f}"
                sv_fmt = f"{d['study_var']:.8f}"
                tol_fmt = f"{d['tolerance']:.8f}"
                md_fmt = f"{d['max_diff']:.8f}"
                bias_fmt = f"{d['bias']:.8f}"
                t_fmt = f"{d['t_value']:.4f}" if math.isfinite(d['t_value']) else '∞'
                p_fmt = f"{d['p_value']:.4f}"
                vr_fmt = f"{d['var_repeat']:.2f}%" if pd.notna(d['var_repeat']) else 'N/A'
                vrb_fmt = f"{d['var_repeat_bias']:.2f}%" if pd.notna(d['var_repeat_bias']) else 'N/A'
                border = 'var(--color-status-accept)' if d['status'] == 'ACCEPT' else 'var(--color-status-reject)'
                status_bg = border

                detail_cards += f"""
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

            # ── Write HTML ──
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            dashboard_file = self.report_output.replace('.txt', '_dashboard.html')
            with open(dashboard_file, 'w', encoding='utf-8') as f:
                f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Type 1 Gage Study — Dashboard</title>
<style>
/* ═══════════════════════════════════════════════
   DESIGN TOKENS — Semantic, purpose-based
   ═══════════════════════════════════════════════ */
:root {{
  /* color.background */
  --color-bg-base:        #0b0e14;
  --color-bg-surface:     #131720;
  --color-bg-elevated:    #1a1f2b;
  --color-bg-hover:       #1e2533;

  /* color.border */
  --color-border-subtle:  #1e2430;
  --color-border-default: #2a3140;

  /* color.text */
  --color-text-primary:   #d1d5db;
  --color-text-secondary: #6e7681;
  --color-text-muted:     #484f58;
  --color-text-inverse:   #0b0e14;

  /* color.accent */
  --color-accent-blue:    #58a6c9;
  --color-accent-amber:   #d4a574;

  /* color.status */
  --color-status-accept:  #7dcea0;
  --color-status-reject:  #e07070;
  --color-status-warn:    #d4a574;

  /* spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-container: 28px 32px;

  /* typography */
  --font-sans:  'Inter', 'Segoe UI', system-ui, sans-serif;
  --font-mono:  'Cascadia Code', 'Consolas', 'Fira Code', monospace;
  --font-kpi:   clamp(36px, 5vw, 48px);
  --font-body:  13px;
  --font-small: 11px;

  /* radius */
  --radius-sm:  6px;
  --radius-md:  10px;
  --radius-lg:  14px;
}}

/* ═══════════════════════════════════════════════
   RESET + BASE
   ═══════════════════════════════════════════════ */
*, *::before, *::after {{ margin:0; padding:0; box-sizing:border-box; }}
html {{ font-size: 16px; }}
body {{
  background: var(--color-bg-base);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
  padding: var(--space-container);
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}}

/* ═══════════════════════════════════════════════
   HEADER — F-pattern entry point
   ═══════════════════════════════════════════════ */
.dash-header {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding-bottom: var(--space-md);
  border-bottom: 1px solid var(--color-border-subtle);
  margin-bottom: var(--space-lg);
}}
.dash-title {{
  font-size: 20px; font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: .2px;
}}
.dash-title em {{
  font-style: normal;
  background: linear-gradient(135deg, var(--color-accent-blue), #9b8ec4);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}}
.dash-date {{ color: var(--color-text-secondary); font-size: var(--font-small); }}

/* ═══════════════════════════════════════════════
   KPI ROW — 80/20: Pass Rate 40% larger, top-left
   ═══════════════════════════════════════════════ */
.kpi-row {{
  display: grid;
  grid-template-columns: 1.7fr repeat(4, 1fr);
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}}
.kpi-card {{
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-md) var(--space-lg);
  transition: border-color .15s;
}}
.kpi-card:hover {{ border-color: var(--color-accent-blue); }}
.kpi-label {{
  color: var(--color-text-secondary);
  font-size: var(--font-small);
  text-transform: uppercase;
  letter-spacing: 1.2px;
  font-weight: 500;
  margin-bottom: 2px;
}}
.kpi-value {{
  font-weight: 700;
  letter-spacing: -.5px;
  line-height: 1.1;
}}
.kpi-primary .kpi-value {{ font-size: var(--font-kpi); }}
.kpi-secondary .kpi-value {{ font-size: clamp(26px, 3.5vw, 34px); }}
.kpi-sub {{
  color: var(--color-text-muted);
  font-size: var(--font-small);
  margin-top: 2px;
}}

/* ═══════════════════════════════════════════════
   SUMMARY TABLE — cause-effect at a glance
   ═══════════════════════════════════════════════ */
.summary-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-body);
  margin-bottom: var(--space-lg);
  border-radius: var(--radius-md);
  overflow: hidden;
}}
.summary-table th {{
  background: var(--color-bg-elevated);
  color: var(--color-text-secondary);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 600;
  padding: 10px 14px;
  text-align: left;
  border-bottom: 1px solid var(--color-border-default);
  position: sticky; top: 0; z-index: 2;
}}
.summary-table td {{
  padding: 9px 14px;
  border-bottom: 1px solid var(--color-border-subtle);
  transition: background .12s;
}}
.summary-row {{ cursor: pointer; }}
.summary-row:hover td {{ background: var(--color-bg-hover); }}

.cell-dim {{ color: var(--color-text-primary); font-weight: 600; }}
.cell-mono {{ font-family: var(--font-mono); font-size: 12px; color: var(--color-text-primary); }}
.cell-expand {{ text-align:center; color:var(--color-text-muted); font-size:12px; transition:transform .2s; }}
.row-open .cell-expand {{ transform: rotate(90deg); color:var(--color-accent-blue); }}

.status-accept {{
  color: var(--color-status-accept);
  font-weight: 700; font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .5px;
}}
.status-reject {{
  color: var(--color-status-reject);
  font-weight: 700; font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .5px;
}}
.kpi-good {{ color: var(--color-status-accept); font-family: var(--font-mono); font-weight:600; }}
.kpi-bad  {{ color: var(--color-status-reject); font-family: var(--font-mono); font-weight:600; }}

/* ═══════════════════════════════════════════════
   DETAIL CARD — Progressive Disclosure
   ═══════════════════════════════════════════════ */
.detail-card {{
  background: var(--color-bg-surface);
  border-left: 4px solid var(--color-status-accept);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-md);
  padding: var(--space-md);
  gap: var(--space-md);
  display: flex;
  flex-wrap: wrap;
}}
.detail-card.highlight {{
  animation: fadeSlide .25s ease-out;
  border-color: var(--color-accent-blue) !important;
}}
@keyframes fadeSlide {{
  from {{ opacity: 0; transform: translateY(-8px); }}
  to   {{ opacity: 1; transform: translateY(0); }}
}}
.detail-chart {{
  flex: 2; min-width: 380px;
}}
.detail-chart img {{
  width: 100%; display: block; border-radius: var(--radius-sm);
}}
.detail-metrics {{
  flex: 1; min-width: 250px;
  display: flex; flex-direction: column; gap: var(--space-sm);
}}
.metric-group {{
  background: var(--color-bg-elevated);
  border-radius: var(--radius-sm);
  padding: var(--space-sm) var(--space-md);
}}
.metric-group-title {{
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 700;
  margin-bottom: var(--space-xs);
}}
.metric-row {{
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  font-size: 12px;
}}
.metric-label {{ color: var(--color-text-secondary); }}
.metric-value {{ color: var(--color-text-primary); font-family: var(--font-mono); font-size: 12px; }}
.metric-status {{
  align-self: stretch;
  text-align: center;
  font-weight: 800;
  font-size: 13px;
  padding: 8px;
  border-radius: var(--radius-sm);
  color: var(--color-text-inverse);
  letter-spacing: 1px;
  text-transform: uppercase;
}}

/* ═══════════════════════════════════════════════
   RESPONSIVE
   ═══════════════════════════════════════════════ */
@media (max-width: 900px) {{
  .kpi-row {{ grid-template-columns: 1fr 1fr; }}
  .detail-card {{ flex-direction: column; }}
}}
</style>
</head>
<body>

<!-- ─── HEADER ─── -->
<div class="dash-header">
  <h1 class="dash-title"><em>Type 1 Gage Study</em> Dashboard</h1>
  <span class="dash-date">{timestamp}</span>
</div>

<!-- ─── KPI ROW: F-pattern, primary KPI top-left, 40% larger ─── -->
<div class="kpi-row">
  <div class="kpi-card kpi-primary" style="border-left:4px solid {'var(--color-status-accept)' if pass_rate >= 75 else 'var(--color-status-reject)'};">
    <div class="kpi-label">Pass Rate</div>
    <div class="kpi-value" style="color:{'var(--color-status-accept)' if pass_rate >= 75 else 'var(--color-status-reject)'};">{pass_rate:.0f}%</div>
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

<!-- ─── SUMMARY TABLE: cause-effect at a glance ─── -->
<table class="summary-table">
  <thead>
    <tr>
      <th>Dimension</th><th>Status</th><th>Cg</th><th>Cgk</th>
      <th>%Var(R)</th><th>Bias</th><th></th>
    </tr>
  </thead>
  <tbody>
    {summary_rows}
  </tbody>
</table>

<!-- ─── DETAIL CARDS: Progressive Disclosure (hidden by default) ─── -->
<div id="detail-container">
{detail_cards}
</div>

<!-- ─── JS: Toggle disclosure ─── -->
<script>
document.querySelectorAll('.summary-row').forEach(function(row) {{
  row.addEventListener('click', function() {{
    var idx = this.dataset.idx;
    var card = document.getElementById('detail-' + idx);

    // Remove highlight from all
    document.querySelectorAll('.detail-card').forEach(function(c) {{ c.classList.remove('highlight'); }});
    document.querySelectorAll('.summary-row').forEach(function(r) {{ r.classList.remove('row-open'); }});

    // Highlight and scroll to clicked
    card.classList.add('highlight');
    this.classList.add('row-open');
    card.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }});
}});
</script>

</body>
</html>""")
            print(f"Dashboard created: {dashboard_file}")

        except Exception as e:
            print(f"Error creating dashboard: {e}")
            import traceback
            traceback.print_exc()

