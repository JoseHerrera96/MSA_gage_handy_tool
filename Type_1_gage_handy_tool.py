"""Type 1 Gage Study — Streamlit Web Application.

Retro/Pixel Art UI with Drag & Drop file upload for processing
Type 1 Gage Study data (Cg, Cgk, %Var calculations).

Run with: streamlit run Type_1_gage_handy_tool.py
"""

from __future__ import annotations

import sys
import io
import base64
from pathlib import Path
from typing import Any
from tempfile import NamedTemporaryFile

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

# Root directory — everything is resolved relative to where this script lives.
PROJECT_ROOT: Path = Path(__file__).resolve().parent

# Add src/ to the import path so we can use the gage_tracer package
# without needing a pip install.
_src_dir = str(PROJECT_ROOT / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from gage_tracer.data_parser import _parse_ogp_data, _compute_dimension_statistics, _build_interleaved_output, _format_output_dataframe
from gage_tracer.calculations import calculate_type1_metrics

# =============================================================================
# PALETA DE COLORES CORPORATIVA (V5 - STRICT)
# =============================================================================
TANGO = "#F37021"
WHITE = "#FFFFFF"
BLACK = "#000000"
DARK_GRAY = "#121212"

# =============================================================================
# CSS INYECTADO — TEMA RETRO/PIXEL ART
# =============================================================================
RETRO_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap');

/* ============================================================
   LAYOUT WIDE - FULL WIDTH CONFIGURATION
   ============================================================ */

/* Eliminar max-width del contenedor principal */
.block-container {{
    max-width: 100% !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
}}

/* Ocultar elementos nativos de Streamlit */
#MainMenu {{visibility: hidden !important;}}
footer {{visibility: hidden !important;}}
header {{visibility: hidden !important;}}

/* Fondo principal - Negro puro */
.stApp {{
    background-color: #000000 !important;
}}

/* Sidebar */
.stSidebar, [data-testid="stSidebar"] {{
    background-color: #121212 !important;
}}

/* ============================================================
   TIPOGRAFÍA RESPONSIVA - ESCALADO DINÁMICO
   ============================================================ */
h1, h2, h3, h4 {{
    font-family: 'Press Start 2P', cursive !important;
    color: #FFFFFF !important;
    border-radius: 0px !important;
    text-shadow: none !important;
}}

/* Escalado fluido para headers */
h1 {{ font-size: clamp(1rem, 2vw, 1.6rem) !important; }}
h2 {{ font-size: clamp(0.8rem, 1.5vw, 1.2rem) !important; }}
h3 {{ font-size: clamp(0.7rem, 1.2vw, 1rem) !important; }}

p, span, label {{
    font-family: 'VT323', monospace !important;
    color: #FFFFFF !important;
    font-size: clamp(1rem, 1.5vw, 1.3rem) !important;
}}

/* ============================================================
   SELECTBOX - V1.0 COMPACTO CON ANCHO LIMITADO
   ============================================================ */

[data-testid="stSelectbox"] {{
    max-width: 350px !important;
    width: 100% !important;
}}

[data-testid="stSelectbox"] > div {{
    min-height: 40px !important;
}}

[data-testid="stSelectbox"] div[role="listbox"] {{
    background-color: #121212 !important;
    border: 2px solid #FFFFFF !important;
    border-radius: 0px !important;
    color: #FFFFFF !important;
    font-family: 'VT323', monospace !important;
    font-size: 1rem !important;
}}

[data-testid="stSelectbox"]:focus-within div[role="listbox"] {{
    border-color: #F37021 !important;
}}

/* ============================================================
   FILE UPLOADER - V3.5 HACK INVISIBLE (BOTÓN OCULTO, TEXTO VISIBLE)
   ============================================================ */

[data-testid="stFileUploader"] {{
    background-color: #000000 !important;
    border: 4px solid #FFFFFF !important;
    border-radius: 0px !important;
    padding: 24px !important;
    width: 100% !important;
    position: relative !important;
}}

/* Sección como fondo naranja pixel-art con texto ::before */
[data-testid="stFileUploader"] section {{
    background-color: #F37021 !important;
    border: 3px solid #FFFFFF !important;
    border-radius: 0px !important;
    padding: 20px 40px !important;
    min-height: 60px !important;
    position: relative !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}}

/* Inyectar "UPLOAD FILE" en el contenedor section vía ::before */
[data-testid="stFileUploader"] section::before {{
    content: "UPLOAD FILE";
    display: block !important;
    color: #FFFFFF !important;
    font-family: 'Press Start 2P', cursive !important;
    font-size: 12px !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    white-space: nowrap !important;
    pointer-events: none !important;
    z-index: 10 !important;
}}

/* Botón INVISIBLE pero clickeable */
[data-testid="stFileUploader"] button {{
    opacity: 0 !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: 100% !important;
    cursor: pointer !important;
    z-index: 20 !important;
}}

/* Hover: cambiar color de fondo del section */
[data-testid="stFileUploader"]:hover section {{
    background-color: #FFFFFF !important;
    border-color: #F37021 !important;
}}

[data-testid="stFileUploader"]:hover section::before {{
    color: #F37021 !important;
}}

/* Textos de apoyo */
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] p {{
    color: #FFFFFF !important;
    font-family: 'VT323', monospace !important;
    font-size: clamp(0.9rem, 1.5vw, 1.1rem) !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}}

/* ============================================================
   BENTO GRID V3.1 - ANTI-OVERLAP & AUTO-SCALING
   ============================================================ */

/* Contenedor principal de columnas */
[data-testid="stHorizontalBlock"] {{
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 12px !important;
    align-items: stretch !important;
}}

/* Forzar que cada columna de KPI sea un contenedor rígido */
[data-testid="stHorizontalBlock"] > div {{
    flex: 1 1 180px !important;
    min-width: 150px !important;
    max-width: 100% !important;
    overflow: hidden !important;
}}

/* Ajuste específico de la tarjeta de Métrica */
[data-testid="stMetric"] {{
    background-color: #121212 !important;
    border: 2px solid #FFFFFF !important;
    border-radius: 0px !important;
    padding: 12px !important;
    height: 100% !important;
    min-height: 100px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    box-shadow: none !important;
    overflow: hidden !important;
}}

/* Prevención de traslape en la Etiqueta */
[data-testid="stMetricLabel"] {{
    font-family: 'Press Start 2P', cursive !important;
    color: #FFFFFF !important;
    font-size: clamp(0.5rem, 0.8vw, 0.6rem) !important;
    margin-bottom: 8px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    text-transform: uppercase !important;
}}

/* Prevención de traslape en el Valor (Cg, Cgk, etc) */
[data-testid="stMetricValue"] {{
    font-family: 'Press Start 2P', cursive !important;
    color: #F37021 !important;
    font-size: clamp(0.8rem, 1.8vw, 1.2rem) !important;
    line-height: 1.2 !important;
    word-break: break-all !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}}

[data-testid="stMetricDelta"] {{
    font-family: 'VT323', monospace !important;
    color: #FFFFFF !important;
    font-size: clamp(0.7rem, 1vw, 0.9rem) !important;
    margin-top: 4px !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
}}

/* ============================================================
   BOTONES GLOBALES - BORDES PIXEL LIMPIOS
   ============================================================ */
.stButton > button {{
    background-color: #F37021 !important;
    color: #FFFFFF !important;
    font-family: 'Press Start 2P', cursive !important;
    font-size: clamp(0.6rem, 1vw, 0.8rem) !important;
    border: 2px solid #F37021 !important;
    border-radius: 0px !important;
    padding: 12px 20px !important;
    box-shadow: none !important;
    text-shadow: none !important;
}}

.stButton > button:hover {{
    background-color: #FFFFFF !important;
    color: #F37021 !important;
    border: 2px solid #F37021 !important;
}}

/* (Bento Grid CSS movido arriba para orden jerárquico) */

/* ============================================================
   TABLAS / DATAFRAMES - FULL WIDTH
   ============================================================ */
[data-testid="stDataFrame"] {{
    background-color: #121212 !important;
    border: 2px solid #FFFFFF !important;
    border-radius: 0px !important;
    width: 100% !important;
}}

/* ============================================================
   INPUTS Y SELECTBOX
   ============================================================ */
.stSelectbox > div > div,
.stNumberInput > div > div,
.stTextInput > div > div {{
    background-color: #121212 !important;
    border: 2px solid #FFFFFF !important;
    border-radius: 0px !important;
    color: #FFFFFF !important;
}}

/* ============================================================
   EXPANDER - SIN SOMBRAS
   ============================================================ */
.streamlit-expanderHeader {{
    font-family: 'Press Start 2P', cursive !important;
    font-size: clamp(0.55rem, 1vw, 0.7rem) !important;
    color: #FFFFFF !important;
    background-color: #121212 !important;
    border: 2px solid #FFFFFF !important;
    border-radius: 0px !important;
    box-shadow: none !important;
}}

.streamlit-expanderContent {{
    background-color: #000000 !important;
    border: 2px solid #FFFFFF !important;
    border-top: none !important;
    border-radius: 0px !important;
}}

/* ============================================================
   DIVIDERS Y SCROLLBAR
   ============================================================ */
hr {{
    border: 2px solid #FFFFFF !important;
    opacity: 1 !important;
    border-radius: 0px !important;
    margin: 1.5rem 0 !important;
}}

::-webkit-scrollbar {{
    width: 12px;
    height: 12px;
}}

::-webkit-scrollbar-track {{
    background: #000000;
}}

::-webkit-scrollbar-thumb {{
    background: #FFFFFF;
    border: 2px solid #000000;
    border-radius: 0px !important;
}}

::-webkit-scrollbar-thumb:hover {{
    background: #F37021;
}}

/* ============================================================
   ALERTAS Y NOTIFICACIONES - SIN SOMBRAS
   ============================================================ */
.stAlert {{
    background-color: #121212 !important;
    border: 2px solid #F37021 !important;
    border-radius: 0px !important;
    font-family: 'VT323', monospace !important;
    box-shadow: none !important;
}}

/* ============================================================
   TABS - RESPONSIVO
   ============================================================ */
[data-testid="stTabs"] {{
    width: 100% !important;
}}

[data-testid="stTabs"] button {{
    font-family: 'Press Start 2P', cursive !important;
    font-size: clamp(0.5rem, 1vw, 0.7rem) !important;
    color: #FFFFFF !important;
    background-color: #121212 !important;
    border: 2px solid #FFFFFF !important;
    border-radius: 0px !important;
    padding: 10px 16px !important;
    flex: 1 !important;
}}

[data-testid="stTabs"] button[aria-selected="true"] {{
    background-color: #F37021 !important;
    color: #FFFFFF !important;
    border: 2px solid #F37021 !important;
}}

/* ============================================================
   SPINNER Y LOADING
   ============================================================ */
[data-testid="stSpinner"] {{
    color: #F37021 !important;
}}

/* ============================================================
   LAYOUT SIDE-TO-SIDE: GRÁFICOS + MÉTRICAS AVANZADAS
   ============================================================ */

/* Contenedor principal de dos columnas para gráficos y métricas */
.side-to-side-container {{
    display: flex !important;
    gap: 24px !important;
    align-items: flex-start !important;
    width: 100% !important;
}}

/* Columna izquierda: Gráficos (71% del ancho) */
.charts-column {{
    flex: 2.5 !important;
    min-width: 0 !important;
    max-width: 71% !important;
}}

/* Columna derecha: Métricas avanzadas (29% del ancho) */
.metrics-column {{
    flex: 1 !important;
    min-width: 220px !important;
    max-width: 29% !important;
}}

/* Flex-Column para métricas avanzadas */
.metrics-flex-container {{
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
    width: 100% !important;
}}

/* Cada métrica: Flex con space-between */
.metric-flex-row {{
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    background-color: #121212 !important;
    border: 2px solid #FFFFFF !important;
    border-radius: 0px !important;
    padding: 12px 14px !important;
    min-height: 44px !important;
    width: 100% !important;
    box-sizing: border-box !important;
}}

/* Label a la izquierda */
.metric-flex-label {{
    font-family: 'Press Start 2P', cursive !important;
    color: #FFFFFF !important;
    font-size: 0.55rem !important;
    text-transform: uppercase !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    max-width: 55% !important;
}}

/* Valor a la derecha - FUENTE FIJA 1.1rem */
.metric-flex-value {{
    font-family: 'VT323', monospace !important;
    color: #F37021 !important;
    font-size: 1.1rem !important;
    text-align: right !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    max-width: 45% !important;
}}

/* Ajuste de imagen de gráfico para ocupar todo el ancho disponible */
.charts-column img {{
    width: 100% !important;
    max-width: 100% !important;
    height: auto !important;
    border: 3px solid #FFFFFF !important;
    display: block !important;
}}

/* ============================================================
   MEDIA QUERIES - Laptops 14" y móviles
   ============================================================ */
@media (max-width: 1200px) {{
    .block-container {{
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }}
    
    [data-testid="stHorizontalBlock"] > div {{
        flex: 1 1 calc(33.333% - 16px) !important;
    }}
    
    .side-to-side-container {{
        flex-direction: column !important;
    }}
    
    .metrics-column {{
        max-width: 100% !important;
        width: 100% !important;
    }}
}}

@media (max-width: 768px) {{
    [data-testid="stHorizontalBlock"] > div {{
        flex: 1 1 calc(50% - 16px) !important;
    }}
}}

@media (max-width: 480px) {{
    [data-testid="stHorizontalBlock"] > div {{
        flex: 1 1 100% !important;
    }}
    
    .advanced-metric-value {{
        font-size: 0.85rem !important;
    }}
}}
</style>
"""

# =============================================================================
# FUNCIONES DE PROCESAMIENTO DE DATOS
# =============================================================================

def parse_uploaded_file(uploaded_file) -> pd.DataFrame | None:
    """Parse uploaded OGP file from memory buffer."""
    try:
        content = uploaded_file.read().decode("utf-8")
        
        # Parse OGP data from string
        all_repetitions: list[dict[str, float]] = []
        current_repetition: dict[str, float] = {}
        dimension_specs: dict[str, dict[str, float]] = {}
        
        for line in content.split("\n"):
            line = line.strip()
            
            if line.startswith('":BEGIN"'):
                current_repetition = {}
            elif line.startswith('":END"'):
                if current_repetition:
                    all_repetitions.append(current_repetition)
                    current_repetition = {}
            elif line.startswith('"') and not line.startswith('":') and not line.startswith('"PATTERN') and not line.startswith('"DISPLAY') and not line.startswith('"UNIT'):
                parts = line.split("\t")
                if len(parts) >= 5:
                    raw_dim_name = parts[0].strip('"')
                    dim_name = raw_dim_name.replace("_OUT1", "")
                    try:
                        measurement = float(parts[1])
                        nominal = float(parts[2])
                        upper_tol = float(parts[3])
                        lower_tol = float(parts[4])
                        
                        if dim_name in current_repetition:
                            all_repetitions.append(current_repetition)
                            current_repetition = {}
                        
                        current_repetition[dim_name] = measurement
                        
                        if dim_name not in dimension_specs:
                            dimension_specs[dim_name] = {
                                "nominal": nominal,
                                "upper_tol": upper_tol,
                                "lower_tol": lower_tol,
                            }
                    except ValueError:
                        continue
        
        if current_repetition:
            all_repetitions.append(current_repetition)
        
        df = pd.DataFrame(all_repetitions)
        
        # Compute statistics
        stats = []
        for dim in df.columns:
            spec = dimension_specs.get(dim, {"nominal": "", "upper_tol": "", "lower_tol": ""})
            stats.append({
                "Dimension": dim,
                "Average": df[dim].mean(),
                "Max diff": df[dim].max() - df[dim].min(),
                "Nominal": spec["nominal"],
                "Upper Tol": spec["upper_tol"],
                "Lower Tol": spec["lower_tol"],
            })
        stats_df = pd.DataFrame(stats)
        
        # Build interleaved output
        combined_df = df.copy()
        combined_df[""] = ""
        combined_df[" "] = ""
        for col in ("Dimension", "Average", "Max diff", "Nominal", "Upper Tol", "Lower Tol"):
            combined_df[col] = pd.Series(dtype="object", index=combined_df.index)
        
        for idx, row in stats_df.iterrows():
            combined_df.loc[idx, "Dimension"] = row["Dimension"]
            combined_df.loc[idx, "Average"] = row["Average"]
            combined_df.loc[idx, "Max diff"] = row["Max diff"]
            combined_df.loc[idx, "Nominal"] = row["Nominal"]
            combined_df.loc[idx, "Upper Tol"] = row["Upper Tol"]
            combined_df.loc[idx, "Lower Tol"] = row["Lower Tol"]
        
        return combined_df
    except Exception as e:
        st.error(f"Error parsing file: {e}")
        return None


def compute_all_metrics(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Compute Type 1 Gage Study metrics for all dimensions."""
    _SKIP_COLS = {"", " ", "Dimension", "Average", "Max diff", "Nominal", "Upper Tol", "Lower Tol"}
    summary: list[dict[str, Any]] = []
    
    for col in df.columns:
        if col.strip() not in _SKIP_COLS:
            measurements = df[col].dropna().astype(float)
            if measurements.empty:
                continue
            try:
                spec_row = df[df["Dimension"] == col].iloc[0]
                summary.append(calculate_type1_metrics(col, measurements, spec_row))
            except (KeyError, IndexError, ValueError, TypeError):
                continue
    
    return summary


# =============================================================================
# VISUALIZACIÓN RETRO/PLOTLY
# =============================================================================

def create_retro_run_chart(dim: str, measurements: pd.Series, metrics: dict) -> str:
    """Create a retro-styled Run Chart + Histogram using matplotlib."""
    
    reference_val = float(metrics["Reference"])
    mean_val = float(metrics["Mean"])
    std_val = float(metrics["StdDev"])
    ref_upper = float(metrics["Ref + 0.10*Tol"])
    ref_lower = float(metrics["Ref - 0.10*Tol"])
    status = metrics["Status"]
    
    if pd.isna(std_val) or std_val == 0:
        std_val = 0.0
    
    data_min = float(measurements.min())
    data_max = float(measurements.max())
    data_span = data_max - data_min
    if data_span == 0:
        data_span = abs(mean_val) * 1e-4 if mean_val != 0 else 1e-6
    
    center_line = reference_val
    max_dist = max(
        abs(data_max - center_line),
        abs(data_min - center_line),
        abs(ref_upper - center_line),
        abs(ref_lower - center_line),
    )
    half_range = max_dist * 1.1
    if std_val > 0:
        half_range = max(half_range, 5 * std_val)
    if half_range == 0:
        half_range = data_span * 2
    
    # Color scheme for retro look
    CLR_DATA = WHITE
    CLR_REF = WHITE
    CLR_LIMIT = TANGO
    CLR_MEAN = TANGO
    CLR_GRID = f"rgba(255, 255, 255, 0.2)"
    CLR_LABEL = WHITE
    CLR_TITLE = WHITE
    CLR_BG = BLACK
    
    fig, axes = plt.subplots(2, 1, figsize=(11, 9), gridspec_kw={"height_ratios": [1.2, 0.8]})
    fig.patch.set_facecolor(CLR_BG)
    fig.patch.set_alpha(0.0)
    
    # Top panel: Run Chart
    ax1 = axes[0]
    x_vals = list(range(1, len(measurements) + 1))
    
    # Reference lines
    ax1.axhline(y=ref_upper, color=CLR_LIMIT, ls="--", lw=2, zorder=1, label="Ref+0.10·Tol")
    ax1.axhline(y=reference_val, color=CLR_REF, ls="-", lw=2.5, alpha=0.9, zorder=2, label="Ref")
    ax1.axhline(y=ref_lower, color=CLR_LIMIT, ls="--", lw=2, zorder=1, label="Ref-0.10·Tol")
    
    if abs(mean_val - reference_val) > 1e-12:
        ax1.axhline(y=mean_val, color=CLR_MEAN, ls=":", lw=2, alpha=0.9, zorder=2, label="Mean")
    
    # Data points as SQUARES (pixel art style)
    ax1.plot(
        x_vals,
        measurements.values,
        "-",
        lw=1.5,
        color=CLR_DATA,
        zorder=3,
    )
    
    # Square markers for pixel art look
    ax1.scatter(
        x_vals,
        measurements.values,
        marker="s",
        s=80,
        c=CLR_DATA,
        edgecolors=CLR_BG,
        linewidths=2,
        zorder=4,
    )
    
    # Highlight out-of-tolerance points
    for i, val in enumerate(measurements.values):
        if val > ref_upper or val < ref_lower:
            ax1.scatter([x_vals[i]], [val], marker="s", s=100, c=TANGO, edgecolors=WHITE, linewidths=1, zorder=5)
    
    ax1.set_facecolor(CLR_BG)
    ax1.set_xlabel("OBSERVATION", fontsize=14, color=CLR_LABEL, fontfamily='VT323')
    ax1.set_ylabel(dim.upper(), fontsize=14, color=CLR_TITLE, fontfamily='VT323', fontweight='bold')
    ax1.set_title(f"RUN CHART — {dim.upper()}", fontsize=12, color=CLR_TITLE, fontfamily='Press Start 2P', pad=15)
    ax1.tick_params(labelsize=12, colors=CLR_LABEL)
    for label in ax1.get_xticklabels() + ax1.get_yticklabels():
        label.set_fontfamily('VT323')
        label.set_fontsize(14)
    
    ax1.grid(True, alpha=0.3, color=WHITE, linestyle='-', linewidth=0.8)
    for sp in ax1.spines.values():
        sp.set_color(WHITE)
        sp.set_linewidth(2)
    ax1.set_ylim(center_line - half_range, center_line + half_range)
    ax1.legend(fontsize=10, loc="upper right", facecolor=CLR_BG, edgecolor=WHITE, labelcolor=CLR_LABEL, framealpha=0.9)
    
    # Bottom panel: Histogram
    ax2 = axes[1]
    n_bins = min(12, max(5, int(np.sqrt(len(measurements)))))
    
    # Create histogram with retro colors
    n, bins, patches = ax2.hist(measurements.values, bins=n_bins, color=WHITE, edgecolor=CLR_BG, lw=2, rwidth=0.85, alpha=0.9)
    
    # Color bars outside tolerance in TANGO
    for i, patch in enumerate(patches):
        bin_center = (bins[i] + bins[i+1]) / 2
        if bin_center > ref_upper or bin_center < ref_lower:
            patch.set_facecolor(TANGO)
    
    ax2.set_facecolor(CLR_BG)
    ax2.set_xlabel("VALUE", fontsize=14, color=CLR_LABEL, fontfamily='VT323')
    ax2.set_ylabel("FREQ", fontsize=14, color=CLR_LABEL, fontfamily='VT323')
    ax2.tick_params(labelsize=12, colors=CLR_LABEL)
    for label in ax2.get_xticklabels() + ax2.get_yticklabels():
        label.set_fontfamily('VT323')
        label.set_fontsize(14)
    
    ax2.grid(True, alpha=0.3, color=WHITE, linestyle='-', linewidth=0.8, axis="y")
    for sp in ax2.spines.values():
        sp.set_color(WHITE)
        sp.set_linewidth(2)
    
    hp = data_span * 0.3 if data_span > 0 else 1e-6
    ax2.set_xlim(data_min - hp, data_max + hp)
    ax2.axvline(x=reference_val, color=CLR_REF, ls="-", lw=2.5, alpha=0.9, label="Ref")
    if abs(mean_val - reference_val) > 1e-12:
        ax2.axvline(x=mean_val, color=CLR_MEAN, ls=":", lw=2, alpha=0.9, label="Mean")
    ax2.legend(fontsize=10, loc="best", facecolor=CLR_BG, edgecolor=WHITE, labelcolor=CLR_LABEL, framealpha=0.9)
    
    plt.tight_layout(pad=1.5)
    
    # Convert to base64 for display
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor=CLR_BG)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# =============================================================================
# UI PRINCIPAL DE STREAMLIT
# =============================================================================

def main():
    """Main Streamlit application."""
    
    # Configuración de página: Layout wide para full-width
    st.set_page_config(
        page_title="Type 1 Gage Study",
        page_icon="📐",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Inyectar CSS retro
    st.markdown(RETRO_CSS, unsafe_allow_html=True)
    
    # Inicializar session state
    if "processed" not in st.session_state:
        st.session_state.processed = False
    if "summary" not in st.session_state:
        st.session_state.summary = None
    if "df" not in st.session_state:
        st.session_state.df = None
    if "selected_dim" not in st.session_state:
        st.session_state.selected_dim = None
    
    # Header retro
    st.markdown(f"""
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="font-family: 'Press Start 2P', cursive; color: {WHITE}; font-size: 1.6rem; text-shadow: 4px 4px 0px rgba(0,0,0,0.3);">
            TYPE 1 GAGE STUDY
        </h1>
        <p style="font-family: 'VT323', monospace; color: {TANGO}; font-size: 1.3rem;">
            ◄ METROLOGY DATA ANALYZER v3.0 ►
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Drag & Drop file uploader
    st.markdown(f"""
    <p style="font-family: 'Press Start 2P', cursive; font-size: 0.8rem; color: {WHITE}; margin-bottom: 15px;">
        ▼ DROP YOUR RAW DATA FILE ▼
    </p>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "",
        type=["txt"],
        help="Upload OGP raw measurement file (.txt)",
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        # Procesar archivo
        with st.spinner("PROCESSING DATA..."):
            df = parse_uploaded_file(uploaded_file)
            
            if df is not None and not df.empty:
                st.session_state.df = df
                st.session_state.summary = compute_all_metrics(df)
                st.session_state.processed = True
                
                # Guardar nombre del archivo
                st.session_state.filename = uploaded_file.name
                
                st.success(f"✓ LOADED: {uploaded_file.name}")
            else:
                st.error("✗ FAILED TO PARSE FILE")
    
    # Mostrar resultados si hay datos procesados
    if st.session_state.processed and st.session_state.summary:
        st.markdown("---")
        
        # KPI Cards
        summary = st.session_state.summary
        num_dims = len(summary)
        accepted = sum(1 for s in summary if s["Status"] == "ACCEPT")
        rejected = num_dims - accepted
        pass_rate = round(accepted * 100 / num_dims, 1) if num_dims else 0
        
        best = max(summary, key=lambda s: s["Cgk"])
        worst = min(summary, key=lambda s: s["Cgk"])
        
        st.markdown(f"""
        <p style="font-family: 'Press Start 2P', cursive; font-size: 0.8rem; color: {WHITE}; margin: 20px 0;">
            ▼ EXECUTIVE DASHBOARD ▼
        </p>
        """, unsafe_allow_html=True)
        
        # KPIs en columnas
        kpi_cols = st.columns(5)
        
        with kpi_cols[0]:
            st.metric("PASS RATE", f"{pass_rate:.0f}%", f"{accepted}/{num_dims}")
        with kpi_cols[1]:
            st.metric("ACCEPTED", str(accepted))
        with kpi_cols[2]:
            st.metric("REJECTED", str(rejected))
        with kpi_cols[3]:
            st.metric("BEST CgK", f"{best['Cgk']:.2f}", best['Gage Item'][:12])
        with kpi_cols[4]:
            st.metric("WORST CgK", f"{worst['Cgk']:.2f}", worst['Gage Item'][:12])
        
        st.markdown("---")
        
        # Tabs para diferentes vistas
        tab1, tab2 = st.tabs(["📊 DIMENSIONS", "📋 DATA TABLE"])
        
        with tab1:
            # Selector de dimensión - Columnas controladas
            dim_names = [s["Gage Item"] for s in summary]
            
            # Layout en columnas: selector compacto a la izquierda
            sel_c1, sel_c2, sel_c3 = st.columns([1, 1, 2])
            
            with sel_c1:
                # Label retro encima del selector
                st.markdown(f"""
                <p style="font-family: 'VT323', monospace; font-size: 0.9rem; color: {WHITE}; margin: 0 0 5px 0;">
                    ► SELECT DIMENSION:
                </p>
                """, unsafe_allow_html=True)
                
                selected_dim = st.selectbox(
                    "", 
                    dim_names, 
                    label_visibility="collapsed",
                    key="dim_selector"
                )
            
            # Encontrar métricas de la dimensión seleccionada
            selected_metrics = next((s for s in summary if s["Gage Item"] == selected_dim), None)
            
            if selected_metrics and st.session_state.df is not None:
                measurements = st.session_state.df[selected_dim].dropna().astype(float)
                
                # Métricas de la dimensión en columnas
                st.markdown(f"""
                <p style="font-family: 'Press Start 2P', cursive; font-size: 0.7rem; color: {TANGO}; margin: 20px 0;">
                    ► {selected_dim.upper()} METRICS
                </p>
                """, unsafe_allow_html=True)
                
                metric_cols = st.columns(6)
                
                with metric_cols[0]:
                    status_color = TANGO if selected_metrics["Status"] == "REJECT" else WHITE
                    st.markdown(f"""
                    <div style="background-color: rgba(0,0,0,0.3); border: 3px solid {WHITE}; padding: 10px; text-align: center;">
                        <p style="font-family: 'Press Start 2P'; font-size: 0.5rem; color: {WHITE}; margin: 0;">STATUS</p>
                        <p style="font-family: 'Press Start 2P'; font-size: 0.9rem; color: {status_color}; margin: 5px 0;">{selected_metrics["Status"]}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with metric_cols[1]:
                    cg_color = TANGO if selected_metrics["Cg"] < 1.33 else WHITE
                    st.markdown(f"""
                    <div style="background-color: rgba(0,0,0,0.3); border: 3px solid {WHITE}; padding: 10px; text-align: center;">
                        <p style="font-family: 'Press Start 2P'; font-size: 0.5rem; color: {WHITE}; margin: 0;">Cg</p>
                        <p style="font-family: 'Press Start 2P'; font-size: 0.9rem; color: {cg_color}; margin: 5px 0;">{selected_metrics["Cg"]:.3f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with metric_cols[2]:
                    cgk_color = TANGO if selected_metrics["Cgk"] < 1.33 else WHITE
                    st.markdown(f"""
                    <div style="background-color: rgba(0,0,0,0.3); border: 3px solid {WHITE}; padding: 10px; text-align: center;">
                        <p style="font-family: 'Press Start 2P'; font-size: 0.5rem; color: {WHITE}; margin: 0;">Cgk</p>
                        <p style="font-family: 'Press Start 2P'; font-size: 0.9rem; color: {cgk_color}; margin: 5px 0;">{selected_metrics["Cgk"]:.3f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with metric_cols[3]:
                    st.markdown(f"""
                    <div style="background-color: rgba(0,0,0,0.3); border: 3px solid {WHITE}; padding: 10px; text-align: center;">
                        <p style="font-family: 'Press Start 2P'; font-size: 0.5rem; color: {WHITE}; margin: 0;">MEAN</p>
                        <p style="font-family: 'VT323'; font-size: 1.2rem; color: {WHITE}; margin: 5px 0;">{selected_metrics["Mean"]:.6f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with metric_cols[4]:
                    st.markdown(f"""
                    <div style="background-color: rgba(0,0,0,0.3); border: 3px solid {WHITE}; padding: 10px; text-align: center;">
                        <p style="font-family: 'Press Start 2P'; font-size: 0.5rem; color: {WHITE}; margin: 0;">STDDEV</p>
                        <p style="font-family: 'VT323'; font-size: 1.2rem; color: {WHITE}; margin: 5px 0;">{selected_metrics["StdDev"]:.6f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with metric_cols[5]:
                    bias_color = TANGO if abs(selected_metrics["Bias"]) > (selected_metrics["Tolerance (Tol)"] * 0.1) else WHITE
                    st.markdown(f"""
                    <div style="background-color: rgba(0,0,0,0.3); border: 3px solid {WHITE}; padding: 10px; text-align: center;">
                        <p style="font-family: 'Press Start 2P'; font-size: 0.5rem; color: {WHITE}; margin: 0;">BIAS</p>
                        <p style="font-family: 'VT323'; font-size: 1.2rem; color: {bias_color}; margin: 5px 0;">{selected_metrics["Bias"]:.6f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Layout Side-to-Side: Gráficos [2] | Métricas Avanzadas [1]
                st.markdown(f"""
                <p style="font-family: 'Press Start 2P', cursive; font-size: 0.7rem; color: {WHITE}; margin: 25px 0 15px 0;">
                    ► RUN CHART & ADVANCED METRICS
                </p>
                """, unsafe_allow_html=True)
                
                # Crear columnas proporcionales [2.5, 1] (71% / 29%)
                col_main, col_stats = st.columns([2.5, 1])
                
                with col_main:
                    # Gráfico principal - ancho completo de columna
                    chart_b64 = create_retro_run_chart(selected_dim, measurements, selected_metrics)
                    st.markdown(
                        f'<img src="data:image/png;base64,{chart_b64}" style="width:100%; border: 3px solid {WHITE};">',
                        unsafe_allow_html=True
                    )
                
                with col_stats:
                    # Advanced Metrics - Todos los textos en Sans-Serif
                    SANS_FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
                    advanced_html = f"""<div style="font-family: {SANS_FONT}; color: {WHITE};">
<p style="font-family: {SANS_FONT}; font-size: 1rem; color: {TANGO}; margin: 0 0 12px 0; border-bottom: 1px solid #333; padding-bottom: 6px; font-weight: 600;">
Advanced Metrics
</p>
<div style="margin-bottom: 14px;">
<p style="font-family: {SANS_FONT}; font-size: 0.65rem; color: #666; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 1px; font-weight: 500;">Reference Information</p>
<div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #222;">
<span style="font-family: {SANS_FONT}; color: #999; font-size: 0.85rem;">Reference value</span>
<span style="font-family: {SANS_FONT}; color: {WHITE}; font-size: 0.9rem; text-align: right; font-weight: 500;">{selected_metrics['Reference']:.6f}</span>
</div>
<div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #222;">
<span style="font-family: {SANS_FONT}; color: #999; font-size: 0.85rem;">Tolerance</span>
<span style="font-family: {SANS_FONT}; color: {WHITE}; font-size: 0.9rem; text-align: right; font-weight: 500;">{selected_metrics['Tolerance (Tol)']:.6f}</span>
</div>
</div>
<div style="margin-bottom: 14px;">
<p style="font-family: {SANS_FONT}; font-size: 0.65rem; color: #666; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 1px; font-weight: 500;">Test Statistics</p>
<div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #222;">
<span style="font-family: {SANS_FONT}; color: #999; font-size: 0.85rem;">T-statistic</span>
<span style="font-family: {SANS_FONT}; color: {TANGO}; font-size: 0.9rem; text-align: right; font-weight: 500;">{selected_metrics['T']:.4f}</span>
</div>
<div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #222;">
<span style="font-family: {SANS_FONT}; color: #999; font-size: 0.85rem;">P-value</span>
<span style="font-family: {SANS_FONT}; color: {TANGO}; font-size: 0.9rem; text-align: right; font-weight: 500;">{selected_metrics['PValue']:.6f}</span>
</div>
<div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #222;">
<span style="font-family: {SANS_FONT}; color: #999; font-size: 0.85rem;">Max difference</span>
<span style="font-family: {SANS_FONT}; color: {WHITE}; font-size: 0.9rem; text-align: right; font-weight: 500;">{selected_metrics['Max diff']:.6f}</span>
</div>
</div>
<div style="margin-bottom: 14px;">
<p style="font-family: {SANS_FONT}; font-size: 0.65rem; color: #666; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 1px; font-weight: 500;">Variability</p>
<div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #222;">
<span style="font-family: {SANS_FONT}; color: #999; font-size: 0.85rem;">Study variation (6σ)</span>
<span style="font-family: {SANS_FONT}; color: {WHITE}; font-size: 0.9rem; text-align: right; font-weight: 500;">{selected_metrics['6 x StdDev (SV)']:.6f}</span>
</div>
<div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #222;">
<span style="font-family: {SANS_FONT}; color: #999; font-size: 0.85rem;">%Var (Repeatability)</span>
<span style="font-family: {SANS_FONT}; color: {TANGO}; font-size: 0.9rem; text-align: right; font-weight: 500;">{selected_metrics['%Var(Repeatability)']:.1f}%</span>
</div>
<div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #222;">
<span style="font-family: {SANS_FONT}; color: #999; font-size: 0.85rem;">%Var (Repeat. & Bias)</span>
<span style="font-family: {SANS_FONT}; color: {TANGO}; font-size: 0.9rem; text-align: right; font-weight: 500;">{selected_metrics['%Var(Repeatability and Bias)']:.1f}%</span>
</div>
</div>
<div>
<p style="font-family: {SANS_FONT}; font-size: 0.65rem; color: #666; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 1px; font-weight: 500;">Sample Information</p>
<div style="display: flex; justify-content: space-between; padding: 4px 0;">
<span style="font-family: {SANS_FONT}; color: #999; font-size: 0.85rem;">Observations</span>
<span style="font-family: {SANS_FONT}; color: {WHITE}; font-size: 0.9rem; text-align: right; font-weight: 500;">{selected_metrics['Observations']}</span>
</div>
</div>
</div>"""
                    st.markdown(advanced_html, unsafe_allow_html=True)
        
        with tab2:
            # Tabla resumen
            st.markdown(f"""
            <p style="font-family: 'Press Start 2P', cursive; font-size: 0.7rem; color: {WHITE}; margin: 15px 0;">
                ► ALL DIMENSIONS SUMMARY
            </p>
            """, unsafe_allow_html=True)
            
            summary_df = pd.DataFrame(summary)[[
                "Gage Item", "Status", "Cg", "Cgk", 
                "%Var(Repeatability)", "Bias", "Observations"
            ]].copy()
            
            # Formatear para display
            for col in ["Cg", "Cgk"]:
                summary_df[col] = summary_df[col].map(lambda x: f"{x:.3f}")
            summary_df["%Var(Repeatability)"] = summary_df["%Var(Repeatability)"].map(
                lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A"
            )
            summary_df["Bias"] = summary_df["Bias"].map(lambda x: f"{x:.6f}")
            
            # Aplicar estilo
            def color_status(val):
                if val == "ACCEPT":
                    return f'color: {WHITE}; font-weight: bold;'
                return f'color: {TANGO}; font-weight: bold;'
            
            styled_df = summary_df.style.map(color_status, subset=["Status"])
            st.dataframe(styled_df, use_container_width=True, height=400)
            
            # Botón de descarga de CSV
            csv = summary_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇ DOWNLOAD CSV",
                data=csv,
                file_name="gage_study_summary.csv",
                mime="text/csv",
            )
    
    # Footer retro
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; padding: 20px 0; opacity: 0.7;">
        <p style="font-family: 'VT323', monospace; color: {WHITE}; font-size: 1rem;">
            [ TYPE 1 GAGE STUDY TOOL ] | [ PIXEL ART EDITION v3.0 ] | [ {BLACK} {WHITE} {TANGO} ]
        </p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
