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

    def generate_report(self):
        try:
            # 1. Read the file
            # Tab-Separated format from data prep.py
            df = pd.read_csv(self.watch_file, sep='\t')

            summary = []
            # K = 6  # Total study variation constant (99.73%) - removed, using standard formulas

            # 2. Identify Dimension Columns
            # Measurement columns are C# tags at the start
            # Stats section has columns: Dimension, Average, Max diff,
            # Nominal, Upper Tol, Lower Tol
            for col in df.columns:
                # Only process C# measurement columns
                if col.startswith('C') and not any(
                    x in col for x in ['tol', 'Avg', 'Max', 'Nominal']
                ):
                    
                    measurements = df[col].dropna().astype(float)
                    if measurements.empty:
                        continue

                    # 3. Dynamic Extraction of Specs
                    # Find the spec row matching this dimension
                    try:
                        spec_row = df[df['Dimension'] == col].iloc[0]
                        
                        nominal = float(spec_row['Nominal'])
                        u_tol = float(spec_row['Upper Tol'])
                        l_tol = float(spec_row['Lower Tol'])
                        tol_range = u_tol - l_tol
                    except (KeyError, IndexError, ValueError, TypeError):
                        # Skip if specs not found
                        continue

                    # 4. Statistical Calculations (Standard Gage Capability Formulas)
                    mean = measurements.mean()
                    std_dev = measurements.std()
                    # Guard against NaN (single measurement) or zero std
                    if pd.isna(std_dev) or std_dev == 0:
                        std_dev = 0.0
                    
                    # Reference = calculated average (not nominal)
                    reference = mean
                    tolerance = u_tol  # Matches Minitab input convention
                    
                    # Minitab Type 1 formulas (k=20%, c=6)
                    # Cg = (0.2 * T) / (6 * sg)
                    cg = (0.2 * tolerance) / (6 * std_dev) if std_dev > 0 else 0
                    
                    # Cgk = (0.1 * T - |Xbar - Ref|) / (3 * sg)
                    bias = abs(mean - reference)
                    cgk = (0.1 * tolerance - bias) / (3 * std_dev) if std_dev > 0 else 0

                    summary.append({
                        "Gage Item": col,
                        "Mean": round(mean, 8),
                        "StdDev": round(std_dev, 8),
                        "Cg": round(cg, 4),
                        "Cgk": round(cgk, 4),
                        "Status": "ACCEPT" if cgk >= 1.33 else "REJECT"
                    })

            # 5. Export the Minitab-style Summary
            if summary:
                report_df = pd.DataFrame(summary)
                with open(self.report_output, 'w') as f:
                    f.write("==============================================\n")
                    f.write("AUTOMATED TYPE 1 GAGE STUDY (GENERIC)\n")
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
            summary_data: List of dicts with keys: Gage Item, Mean, StdDev, Cg, Cgk, Status.
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
                spec_row = df[df['Dimension'] == dim].iloc[0] if len(df[df['Dimension'] == dim]) > 0 else None

                nominal = u_tol = l_tol = usl = lsl = None
                if spec_row is not None:
                    try:
                        nominal = float(spec_row['Nominal'])
                        u_tol = float(spec_row['Upper Tol'])
                        l_tol = float(spec_row['Lower Tol'])
                    except (ValueError, TypeError, KeyError):
                        pass

                fig, axes = plt.subplots(2, 1, figsize=(13.2, 12),
                                         gridspec_kw={'height_ratios': [1, 1]})
                fig.patch.set_facecolor('#0d1117')
                fig.suptitle(f'Type 1 Gage Study for {dim}', fontsize=16, fontweight='bold', color='#c9d1d9', y=0.98)

                # ── Compute y-axis range: average always at center ──
                mean_val = measurements.mean()
                std_val = measurements.std()
                # Guard against NaN (single measurement) or zero std
                if pd.isna(std_val) or std_val == 0:
                    std_val = 0.0
                data_min = float(measurements.min())
                data_max = float(measurements.max())
                data_span = data_max - data_min
                # Fallback span when all values are identical
                if data_span == 0:
                    data_span = abs(mean_val) * 1e-4 if mean_val != 0 else 1e-6

                # Tolerance lines: average + 10% of each tolerance value
                if u_tol is not None and l_tol is not None:
                    usl = mean_val + (u_tol * 0.1)
                    lsl = mean_val + (l_tol * 0.1)

                # Max distance from mean to any point we want to show
                max_dist = max(abs(data_max - mean_val), abs(data_min - mean_val))
                if usl is not None and lsl is not None:
                    max_dist = max(max_dist, abs(usl - mean_val), abs(lsl - mean_val))
                # Add 10% padding; guarantee a minimum visible range
                half_range = max_dist * 1.1
                if std_val > 0:
                    half_range = max(half_range, 5 * std_val)
                if half_range == 0:
                    half_range = data_span * 2
                y_lo = mean_val - half_range
                y_hi = mean_val + half_range

                # ── Top: Individual Value Plot ──
                ax1 = axes[0]
                x_vals = list(range(1, len(measurements) + 1))

                # Draw tolerance lines FIRST (behind data points)
                if usl is not None and lsl is not None:
                    ax1.axhline(y=usl, color='#e8836a', linestyle='--', linewidth=1.3,
                                label=f'avg+0.10*tol = {usl:.8f}', zorder=1)
                    ax1.axhline(y=lsl, color='#e8836a', linestyle='--', linewidth=1.3,
                                label=f'avg-0.10*tol = {lsl:.8f}', zorder=1)

                # Draw average line
                ax1.axhline(y=mean_val, color='#8cc68a', linestyle='-', linewidth=2,
                            alpha=0.8, label=f'Avg = {mean_val:.8f}', zorder=2)

                # Data points ON TOP of lines
                ax1.plot(x_vals, measurements.values, '-o', markersize=4, linewidth=1.1,
                         color='#58a6c9', markerfacecolor='#79c0db', markeredgecolor='#58a6c9',
                         markeredgewidth=0.5, zorder=3)

                ax1.set_facecolor('#161b22')
                ax1.set_xlabel('Observation', fontsize=11, color='#8b949e')
                ax1.set_ylabel('Value', fontsize=11, color='#8b949e')
                ax1.set_title('Individual Value Plot', fontsize=13, fontweight='bold', color='#c9d1d9')
                ax1.tick_params(labelsize=10, colors='#8b949e')
                ax1.grid(True, alpha=0.12, color='#484f58', linestyle='-', zorder=0)
                for spine in ax1.spines.values(): spine.set_color('#30363d')
                ax1.set_ylim(y_lo, y_hi)
                leg1 = ax1.legend(fontsize=9, loc='upper right', facecolor='#161b22',
                                  edgecolor='#30363d', labelcolor='#c9d1d9')

                # ── Bottom: Standard Vertical Histogram ──
                ax2 = axes[1]
                # Use ~10 evenly spaced bins across the data range for clear bars
                n_bins = min(12, max(5, int(np.sqrt(len(measurements)))))
                ax2.hist(measurements.values, bins=n_bins, color='#58a6c9',
                         edgecolor='#161b22', linewidth=0.8, rwidth=0.85, alpha=0.85)
                ax2.set_facecolor('#161b22')
                ax2.set_xlabel('Value', fontsize=11, color='#8b949e')
                ax2.set_ylabel('Frequency', fontsize=11, color='#8b949e')
                ax2.set_title('Histogram', fontsize=13, fontweight='bold', color='#c9d1d9')
                ax2.tick_params(labelsize=10, colors='#8b949e')
                ax2.grid(True, alpha=0.12, color='#484f58', linestyle='-', axis='y')
                for spine in ax2.spines.values(): spine.set_color('#30363d')
                # Pad x-axis so bars aren't jammed to edges
                hist_pad = data_span * 0.3 if data_span > 0 else (abs(mean_val) * 1e-4 if mean_val != 0 else 1e-6)
                ax2.set_xlim(data_min - hist_pad, data_max + hist_pad)

                if usl is not None and lsl is not None:
                    ax2.axvline(x=mean_val, color='#8cc68a', linestyle='-', linewidth=2, alpha=0.8, label='Avg')
                    ax2.legend(fontsize=9, loc='best', facecolor='#161b22',
                               edgecolor='#30363d', labelcolor='#c9d1d9')

                # ── Collect stats for HTML table ──
                avg_val = spec_row['Average'] if spec_row is not None and 'Average' in spec_row else row['Mean']
                max_diff_val = spec_row['Max diff'] if spec_row is not None and 'Max diff' in spec_row else 0
                status = row['Status']

                plt.tight_layout(rect=[0, 0, 1, 0.95])

                # Save to base64
                buf = BytesIO()
                fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#0d1117')
                plt.close(fig)
                buf.seek(0)
                img_b64 = base64.b64encode(buf.read()).decode('utf-8')
                chart_images.append({
                    'dim': dim, 'img': img_b64, 'status': status,
                    'avg': avg_val, 'max_diff': max_diff_val,
                    'cg': row['Cg'], 'cgk': row['Cgk'], 'stddev': row['StdDev'],
                    'nominal': nominal, 'usl': usl, 'lsl': lsl,
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
                avg_fmt = f"{d['avg']:.8f}" if isinstance(d['avg'], (int, float)) else str(d['avg'])
                md_fmt = f"{d['max_diff']:.8f}" if isinstance(d['max_diff'], (int, float)) else str(d['max_diff'])

                charts_html += f"""
                <div style="display:flex; gap:12px; background:{CARD_BG}; border-left:4px solid {border_color}; border-radius:8px; margin-bottom:16px; padding:12px; align-items:flex-start; flex-wrap:wrap;">
                    <div style="flex:2; min-width:400px; max-width:999px;">
                        <img src="data:image/png;base64,{d['img']}" style="width:100%; display:block; border-radius:4px;">
                    </div>
                    <div style="flex:1; min-width:220px;">
                        <table style="width:100%; border-collapse:collapse; font-size:13px; border-radius:6px; overflow:hidden;">
                            <tr style="background:{TABLE_HEADER_BG};">
                                <th style="padding:10px 14px; text-align:left; color:{ACCENT_BLUE}; font-size:11px; text-transform:uppercase; letter-spacing:1px; border-bottom:1px solid {GRID_COLOR};">Metric</th>
                                <th style="padding:10px 14px; text-align:left; color:{ACCENT_BLUE}; font-size:11px; text-transform:uppercase; letter-spacing:1px; border-bottom:1px solid {GRID_COLOR};">Value</th>
                            </tr>
                            <tr><td style="padding:8px 14px; color:{LABEL_COLOR};">Average</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{avg_fmt}</td></tr>
                            <tr style="background:rgba(255,255,255,0.02);"><td style="padding:8px 14px; color:{LABEL_COLOR};">Max diff</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{md_fmt}</td></tr>
                            <tr><td style="padding:8px 14px; color:{LABEL_COLOR};">Cg</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{d['cg']:.4f}</td></tr>
                            <tr style="background:rgba(255,255,255,0.02);"><td style="padding:8px 14px; color:{LABEL_COLOR};">Cgk</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{d['cgk']:.4f}</td></tr>
                            <tr><td style="padding:8px 14px; color:{LABEL_COLOR};">StdDev</td><td style="padding:8px 14px; color:{TEXT_COLOR}; font-family:'Consolas',monospace;">{d['stddev']:.8f}</td></tr>
                            <tr style="background:rgba(255,255,255,0.02);"><td style="padding:8px 14px; color:{LABEL_COLOR};">Status</td><td style="padding:8px 14px; background:{status_bg}; color:{status_fg}; font-weight:700; border-radius:4px; text-align:center;">{d['status']}</td></tr>
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

if __name__ == "__main__":
    FILE = "gage data.txt"
    OUT = "Gage_Study_Summary.txt"
    
    event_handler = SimplifiedGageReporter(FILE, OUT)
    
    # Generate initial report from existing measurements
    print("Generating initial report from existing measurements...")
    event_handler.generate_report()
    print(f"[OK] Report saved to {OUT}")
    print("[OK] Starting file monitor (Ctrl+C to stop)...")
    
    # Monitor for changes and update report
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[OK] Monitoring stopped.")
    finally:
        observer.stop()
        observer.join()