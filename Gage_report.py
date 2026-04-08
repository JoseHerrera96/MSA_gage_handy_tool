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
        """Create a Minitab-style Type 1 Gage Study dashboard using matplotlib.
        
        Args:
            df: DataFrame with measurement data already loaded.
            summary_data: List of dicts with Minitab-style metrics such as
                reference, bias, tolerance, capability, and % variation.
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.ticker as ticker
            import base64
            from io import BytesIO

            summary_df = pd.DataFrame(summary_data)
            # Rename to match dashboard expectations
            summary_df = summary_df.rename(columns={'Gage Item': 'Dimension'})
            num_dims = len(summary_df)
            accepted = sum(1 for s in summary_data if s['Status'] == 'ACCEPT')
            rejected = num_dims - accepted

            # Generate one chart image per dimension (Minitab style)
            chart_images = []
            for i, (_, row) in enumerate(summary_df.iterrows()):
                dim = row['Dimension']
                if dim not in df.columns:
                    continue
                measurements = df[dim].dropna().astype(float)
                reference_val = float(row['Reference'])
                mean_val = float(row['Mean'])
                std_val = float(row['StdDev'])
                tolerance_val = float(row['Tolerance (Tol)'])
                ref_upper = float(row['Ref + 0.10*Tol'])
                ref_lower = float(row['Ref - 0.10*Tol'])
                max_diff_val = float(row['Max diff'])
                status = row['Status']

                fig, axes = plt.subplots(2, 1, figsize=(13.2, 12),
                                         gridspec_kw={'height_ratios': [1, 1]})
                fig.patch.set_facecolor('#0d1117')
                fig.suptitle(f'Type 1 Gage Study for {dim}', fontsize=16, fontweight='bold', color='#c9d1d9', y=0.98)

                # ── Compute y-axis range: reference at center, with mean shown for comparison ──
                if pd.isna(std_val) or std_val == 0:
                    std_val = 0.0
                data_min = float(measurements.min())
                data_max = float(measurements.max())
                data_span = data_max - data_min
                if data_span == 0:
                    data_span = abs(mean_val) * 1e-4 if mean_val != 0 else 1e-6

                center_line = reference_val
                max_dist = max(abs(data_max - center_line), abs(data_min - center_line))
                max_dist = max(max_dist, abs(ref_upper - center_line), abs(ref_lower - center_line))

                half_range = max_dist * 1.1
                if std_val > 0:
                    half_range = max(half_range, 5 * std_val)
                if half_range == 0:
                    half_range = data_span * 2
                y_lo = center_line - half_range
                y_hi = center_line + half_range

                # ── Top: Run Chart ──
                ax1 = axes[0]
                x_vals = list(range(1, len(measurements) + 1))

                ax1.axhline(y=ref_upper, color='#e8836a', linestyle='--', linewidth=1.3,
                            label=f'Ref + 0.10*Tol = {ref_upper:.8f}', zorder=1)
                ax1.axhline(y=reference_val, color='#8cc68a', linestyle='-', linewidth=2,
                            alpha=0.9, label=f'Ref = {reference_val:.8f}', zorder=2)
                ax1.axhline(y=ref_lower, color='#e8836a', linestyle='--', linewidth=1.3,
                            label=f'Ref - 0.10*Tol = {ref_lower:.8f}', zorder=1)

                if abs(mean_val - reference_val) > 1e-12:
                    ax1.axhline(y=mean_val, color='#d4a574', linestyle=':', linewidth=1.5,
                                alpha=0.9, label=f'Mean = {mean_val:.8f}', zorder=2)

                ax1.plot(x_vals, measurements.values, '-o', markersize=4, linewidth=1.1,
                         color='#58a6c9', markerfacecolor='#79c0db', markeredgecolor='#58a6c9',
                         markeredgewidth=0.5, zorder=3)

                ax1.set_facecolor('#161b22')
                ax1.set_xlabel('Observation', fontsize=11, color='#8b949e')
                ax1.set_ylabel('Value', fontsize=11, color='#8b949e')
                ax1.set_title('Run Chart', fontsize=13, fontweight='bold', color='#c9d1d9')
                ax1.tick_params(labelsize=10, colors='#8b949e')
                ax1.grid(True, alpha=0.12, color='#484f58', linestyle='-', zorder=0)
                for spine in ax1.spines.values():
                    spine.set_color('#30363d')
                ax1.set_ylim(y_lo, y_hi)
                ax1.legend(fontsize=9, loc='upper right', facecolor='#161b22',
                           edgecolor='#30363d', labelcolor='#c9d1d9')

                # ── Bottom: Standard Vertical Histogram ──
                ax2 = axes[1]
                n_bins = min(12, max(5, int(np.sqrt(len(measurements)))))
                ax2.hist(measurements.values, bins=n_bins, color='#58a6c9',
                         edgecolor='#161b22', linewidth=0.8, rwidth=0.85, alpha=0.85)
                ax2.set_facecolor('#161b22')
                ax2.set_xlabel('Value', fontsize=11, color='#8b949e')
                ax2.set_ylabel('Frequency', fontsize=11, color='#8b949e')
                ax2.set_title('Histogram', fontsize=13, fontweight='bold', color='#c9d1d9')
                ax2.tick_params(labelsize=10, colors='#8b949e')
                ax2.grid(True, alpha=0.12, color='#484f58', linestyle='-', axis='y')
                for spine in ax2.spines.values():
                    spine.set_color('#30363d')
                hist_pad = data_span * 0.3 if data_span > 0 else (abs(mean_val) * 1e-4 if mean_val != 0 else 1e-6)
                ax2.set_xlim(data_min - hist_pad, data_max + hist_pad)
                ax2.axvline(x=reference_val, color='#8cc68a', linestyle='-', linewidth=2, alpha=0.8, label='Reference')
                if abs(mean_val - reference_val) > 1e-12:
                    ax2.axvline(x=mean_val, color='#d4a574', linestyle=':', linewidth=1.5, alpha=0.9, label='Mean')
                ax2.legend(fontsize=9, loc='best', facecolor='#161b22',
                           edgecolor='#30363d', labelcolor='#c9d1d9')

                plt.tight_layout(rect=[0, 0, 1, 0.95])

                # Save to base64
                buf = BytesIO()
                fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#0d1117')
                plt.close(fig)
                buf.seek(0)
                img_b64 = base64.b64encode(buf.read()).decode('utf-8')
                chart_images.append({
                    'dim': dim,
                    'img': img_b64,
                    'status': status,
                    'reference': reference_val,
                    'mean': mean_val,
                    'max_diff': max_diff_val,
                    'stddev': std_val,
                    'study_var': float(row['6 x StdDev (SV)']),
                    'tolerance': tolerance_val,
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

            # ── Build HTML ──
            # 2026 UI: Midnight blue dark mode + muted earth tones
            BG_COLOR = '#0d1117'          # Deep midnight black
            CARD_BG = '#161b22'            # Dark navy card
            GRID_COLOR = '#21262d'         # Subtle separator
            TEXT_COLOR = '#c9d1d9'         # Soft cool gray text
            ACCENT_BLUE = '#58a6c9'        # Dusty ocean blue
            ACCENT_GREEN = '#7c9a6e'       # Muted moss green
            ACCENT_RED = '#c4655a'         # Soft terracotta
            ACCENT_AMBER = '#d4a574'       # Warm clay/sand
            TABLE_HEADER_BG = '#1c2633'    # Deep teal-navy
            LABEL_COLOR = '#768390'        # Muted cool gray labels

            charts_html = ""
            for d in chart_images:
                border_color = ACCENT_GREEN if d['status'] == 'ACCEPT' else ACCENT_RED
                status_bg = ACCENT_GREEN if d['status'] == 'ACCEPT' else ACCENT_RED
                status_fg = '#0d1117' if d['status'] == 'ACCEPT' else '#c9d1d9'

                ref_fmt = f"{d['reference']:.8f}"
                mean_fmt = f"{d['mean']:.8f}"
                md_fmt = f"{d['max_diff']:.8f}"
                std_fmt = f"{d['stddev']:.8f}"
                sv_fmt = f"{d['study_var']:.8f}"
                tol_fmt = f"{d['tolerance']:.8f}"
                bias_fmt = f"{d['bias']:.8f}"
                t_fmt = f"{d['t_value']:.4f}" if math.isfinite(d['t_value']) else '∞'
                p_fmt = f"{d['p_value']:.4f}"
                vr_fmt = f"{d['var_repeat']:.2f}%" if pd.notna(d['var_repeat']) else 'N/A'
                vrb_fmt = f"{d['var_repeat_bias']:.2f}%" if pd.notna(d['var_repeat_bias']) else 'N/A'

                charts_html += f"""
                <div style="display:flex; gap:12px; background:{CARD_BG}; border-left:4px solid {border_color}; border-radius:8px; margin-bottom:16px; padding:12px; align-items:flex-start; flex-wrap:wrap;">
                    <div style="flex:2; min-width:400px; max-width:999px;">
                        <img src="data:image/png;base64,{d['img']}" style="width:100%; display:block; border-radius:4px;">
                    </div>
                    <div style="flex:1; min-width:260px;">
                        <table style="width:100%; border-collapse:collapse; font-size:13px; border-radius:6px; overflow:hidden;">
                            <tr style="background:{TABLE_HEADER_BG};">
                                <th style="padding:10px 14px; text-align:left; color:{ACCENT_BLUE}; font-size:11px; text-transform:uppercase; letter-spacing:1px; border-bottom:1px solid {GRID_COLOR};">Metric</th>
                                <th style="padding:10px 14px; text-align:left; color:{ACCENT_BLUE}; font-size:11px; text-transform:uppercase; letter-spacing:1px; border-bottom:1px solid {GRID_COLOR};">Value</th>
                            </tr>
                            <tr style="background:rgba(88,166,201,0.10);"><td colspan="2" style="padding:8px 14px; color:{ACCENT_BLUE}; font-weight:700;">Basic Statistics</td></tr>
                            <tr><td style="padding:8px 14px; color:{LABEL_COLOR};">Reference</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{ref_fmt}</td></tr>
                            <tr style="background:rgba(255,255,255,0.02);"><td style="padding:8px 14px; color:{LABEL_COLOR};">Mean</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{mean_fmt}</td></tr>
                            <tr><td style="padding:8px 14px; color:{LABEL_COLOR};">StdDev</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{std_fmt}</td></tr>
                            <tr style="background:rgba(255,255,255,0.02);"><td style="padding:8px 14px; color:{LABEL_COLOR};">6 × StdDev (SV)</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{sv_fmt}</td></tr>
                            <tr><td style="padding:8px 14px; color:{LABEL_COLOR};">Tolerance (Tol)</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{tol_fmt}</td></tr>
                            <tr style="background:rgba(255,255,255,0.02);"><td style="padding:8px 14px; color:{LABEL_COLOR};">Max diff</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{md_fmt}</td></tr>
                            <tr><td style="padding:8px 14px; color:{LABEL_COLOR};">Observations</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{d['observations']}</td></tr>

                            <tr style="background:rgba(124,154,110,0.12);"><td colspan="2" style="padding:8px 14px; color:{ACCENT_GREEN}; font-weight:700;">Bias Study</td></tr>
                            <tr><td style="padding:8px 14px; color:{LABEL_COLOR};">Bias</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{bias_fmt}</td></tr>
                            <tr style="background:rgba(255,255,255,0.02);"><td style="padding:8px 14px; color:{LABEL_COLOR};">T</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{t_fmt}</td></tr>
                            <tr><td style="padding:8px 14px; color:{LABEL_COLOR};">PValue (Bias = 0)</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{p_fmt}</td></tr>

                            <tr style="background:rgba(212,165,116,0.12);"><td colspan="2" style="padding:8px 14px; color:{ACCENT_AMBER}; font-weight:700;">Capability</td></tr>
                            <tr><td style="padding:8px 14px; color:{LABEL_COLOR};">Cg</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{d['cg']:.4f}</td></tr>
                            <tr style="background:rgba(255,255,255,0.02);"><td style="padding:8px 14px; color:{LABEL_COLOR};">Cgk</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{d['cgk']:.4f}</td></tr>
                            <tr><td style="padding:8px 14px; color:{LABEL_COLOR};">%Var (Repeatability)</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{vr_fmt}</td></tr>
                            <tr style="background:rgba(255,255,255,0.02);"><td style="padding:8px 14px; color:{LABEL_COLOR};">%Var (Repeatability + Bias)</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{vrb_fmt}</td></tr>

                            <tr><td style="padding:8px 14px; color:{LABEL_COLOR};">Status</td><td style="padding:8px 14px; background:{status_bg}; color:{status_fg}; font-weight:700; border-radius:4px; text-align:center;">{d['status']}</td></tr>
                        </table>
                    </div>
                </div>
                """

            dashboard_file = self.report_output.replace('.txt', '_dashboard.html')
            with open(dashboard_file, 'w', encoding='utf-8') as f:
                f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Type 1 Gage Study Dashboard</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: {BG_COLOR};
    color: {TEXT_COLOR};
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    padding: 28px 36px;
    line-height: 1.5;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 18px;
    border-bottom: 1px solid {GRID_COLOR};
  }}
  .header h1 {{
    font-size: 24px;
    font-weight: 600;
    color: {TEXT_COLOR};
    letter-spacing: 0.3px;
  }}
  .header h1 span {{
    background: linear-gradient(135deg, {ACCENT_BLUE}, #7c6dab);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  .header .date {{
    color: {LABEL_COLOR};
    font-size: 13px;
    font-weight: 400;
  }}
  .stat-card {{
    background: {CARD_BG};
    border-radius: 10px;
    padding: 18px 28px;
    min-width: 150px;
    border: 1px solid {GRID_COLOR};
    transition: border-color 0.2s;
  }}
  .stat-card:hover {{ border-color: {ACCENT_BLUE}; }}
  .stat-label {{
    color: {LABEL_COLOR};
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    font-weight: 500;
    margin-bottom: 4px;
  }}
  .stat-value {{
    font-size: 34px;
    font-weight: 700;
    letter-spacing: -0.5px;
  }}
</style>
</head>
<body>
  <div class="header">
    <h1><span>Type 1 Gage Study</span> Dashboard</h1>
    <span class="date">{time.strftime('%Y-%m-%d %H:%M:%S')}</span>
  </div>
  <div style="display:flex; gap:16px; flex-wrap:wrap; margin-bottom:24px;">
    <div class="stat-card" style="border-left:3px solid {ACCENT_BLUE};">
      <div class="stat-label">Dimensions</div>
      <div class="stat-value" style="color:{ACCENT_BLUE};">{num_dims}</div>
    </div>
    <div class="stat-card" style="border-left:3px solid {ACCENT_GREEN};">
      <div class="stat-label">Accepted</div>
      <div class="stat-value" style="color:{ACCENT_GREEN};">{accepted}</div>
    </div>
    <div class="stat-card" style="border-left:3px solid {ACCENT_RED};">
      <div class="stat-label">Rejected</div>
      <div class="stat-value" style="color:{ACCENT_RED};">{rejected}</div>
    </div>
    <div class="stat-card" style="border-left:3px solid {ACCENT_AMBER};">
      <div class="stat-label">Pass Rate</div>
      <div class="stat-value" style="color:{ACCENT_AMBER};">{accepted*100//num_dims if num_dims else 0}%</div>
    </div>
  </div>
  {charts_html}
</body>
</html>""")
            print(f"Dashboard created: {dashboard_file}")

        except Exception as e:
            print(f"Error creating dashboard: {e}")
            import traceback
            traceback.print_exc()

