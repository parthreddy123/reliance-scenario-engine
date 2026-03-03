"""Dark executive theme for Reliance Scenario Engine."""

# -- Background & Surface --
BG_PRIMARY = "#0E1117"
BG_CARD = "#1A1F2E"
BG_ELEVATED = "#151A28"
BORDER_SUBTLE = "rgba(255,255,255,0.06)"

# -- Text --
TEXT_PRIMARY = "#F9FAFB"
TEXT_SECONDARY = "#9CA3AF"
TEXT_MUTED = "#6B7280"
TEXT_DIM = "#4B5563"

# -- Accent Palette --
TEAL = "#00D4AA"
CYAN = "#00D4FF"
BLUE = "#3B82F6"
EMERALD = "#10B981"
CORAL = "#EF4444"
AMBER = "#F59E0B"
GOLD = "#F0B429"
PURPLE = "#8B5CF6"

# -- Scenario Colors --
SCENARIO_COLORS = {
    "quick_ceasefire": EMERALD,
    "prolonged_standoff": AMBER,
    "regional_conflagration": CORAL,
    "regime_collapse": PURPLE,
    "negotiated_settlement": CYAN,
}

# -- Plotly base layout --
PLOTLY_LAYOUT = dict(
    paper_bgcolor=BG_ELEVATED,
    plot_bgcolor=BG_ELEVATED,
    font=dict(family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif", color=TEXT_SECONDARY, size=12),
    title=dict(font=dict(color=TEXT_PRIMARY, size=15), x=0, xanchor="left", pad=dict(l=10)),
    legend=dict(
        bgcolor="rgba(0,0,0,0)", bordercolor=BORDER_SUBTLE,
        font=dict(color=TEXT_SECONDARY, size=11),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    ),
    margin=dict(l=55, r=25, t=55, b=45),
    xaxis=dict(
        gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.08)",
        zerolinecolor="rgba(255,255,255,0.08)",
        tickfont=dict(color=TEXT_MUTED, size=10),
    ),
    yaxis=dict(
        gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.08)",
        zerolinecolor="rgba(255,255,255,0.08)",
        tickfont=dict(color=TEXT_MUTED, size=10),
    ),
    hoverlabel=dict(bgcolor="#1F2937", bordercolor="rgba(255,255,255,0.1)",
                    font=dict(color=TEXT_PRIMARY, size=12)),
    hovermode="x unified",
)


def apply_theme(fig, height=400):
    """Apply dark theme to a Plotly figure."""
    fig.update_layout(**PLOTLY_LAYOUT, height=height)
    return fig


PLOTLY_CONFIG = {
    "displayModeBar": "hover",
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "displaylogo": False,
    "responsive": True,
}


GLOBAL_CSS = """
<style>
.block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; max-width: 100% !important; }
[data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A0E1A 0%, #111827 100%);
    border-right: 1px solid rgba(0, 212, 170, 0.15);
}
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1A1F2E 0%, #151A28 100%);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px; padding: 1rem 1.2rem;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}
[data-testid="stMetric"]:hover {
    border-color: rgba(0, 212, 170, 0.2);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}
[data-testid="stMetric"] label { color: #9CA3AF !important; font-size: 0.72rem !important;
    text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.5rem !important; font-weight: 700; color: #F9FAFB !important; }
[data-testid="stMetric"] [data-testid="stMetricDelta"] { font-size: 0.8rem !important; font-weight: 600; }
h1 { font-weight: 800 !important; letter-spacing: -0.02em; color: #F9FAFB !important; }
h2 { color: #E5E7EB !important; font-weight: 700 !important; font-size: 1.3rem !important;
     border-bottom: 2px solid rgba(0, 212, 170, 0.3); padding-bottom: 0.4rem; margin-top: 1.5rem !important; }
h3 { color: #D1D5DB !important; font-weight: 600 !important; font-size: 1.1rem !important; }
hr { border-color: rgba(255, 255, 255, 0.06) !important; }

/* Scenario card styling */
.scenario-card {
    background: linear-gradient(135deg, #1A1F2E 0%, #151A28 100%);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 1.2rem;
    margin-bottom: 1rem;
}
.scenario-card:hover {
    border-color: rgba(255, 255, 255, 0.12);
}
.kpi-box {
    background: linear-gradient(135deg, #1A1F2E 0%, #151A28 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    text-align: center;
}
.kpi-title {
    color: #9CA3AF;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 600;
    margin-bottom: 0.3rem;
}
.kpi-value {
    color: #F9FAFB;
    font-size: 1.6rem;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
}
.kpi-range {
    color: #6B7280;
    font-size: 0.72rem;
    margin-top: 0.2rem;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0E1117; }
::-webkit-scrollbar-thumb { background: #374151; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #4B5563; }
</style>
"""
