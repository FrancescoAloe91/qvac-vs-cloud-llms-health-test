"""Ranking charts: radar, bar charts, dimension breakdown."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from lib.i18n import t
from lib.metrics import URGENCY_META, _L
from lib.tiers import MODEL_CONFIG

MODEL_CONFIG_NAME = {key: cfg["name"] for key, cfg in MODEL_CONFIG.items()}

MODEL_COLORS = {
    "chatgpt": "#10a37f",
    "claude": "#d97706",
    "gemini": "#8ab4f8",
    "qvac": "#00d09c",
}

FILL_COLORS = {
    "chatgpt": "rgba(16,163,127,0.18)",
    "claude": "rgba(217,119,6,0.18)",
    "gemini": "rgba(138,180,248,0.18)",
    "qvac": "rgba(0,208,156,0.22)",
}

CHART_BG = "#0e1117"
PLOT_BG = "#161b26"
GRID = "#2a3142"


def _base_layout(title: str, height: int = 500) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=16, color="#fafafa")),
        template="plotly_dark",
        paper_bgcolor=CHART_BG,
        plot_bgcolor=PLOT_BG,
        height=height,
        font=dict(color="#e2e8f0"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=40, r=40, t=80, b=40),
    )


def fig_radar(ranking_df, use_gold: bool, lang: str = "en", sem_available: bool = False) -> go.Figure:
    L = _L(lang)
    if use_gold:
        col_keys = [L["rel_short"], L["acc_cons_short"]]
        if sem_available:
            col_keys.append(L["sem_short"])
        col_keys += [
            L["acc_clin_short"],
            L["ddx_short"],
            L["privacy"],
            L["score_cons_short"],
            L["score_clin_short"],
        ]
        categories = col_keys[:]
    else:
        col_keys = [L["rel_short"], L["acc_cons_short"]]
        if sem_available:
            col_keys.append(L["sem_short"])
        col_keys += [L["privacy"], L["score_final"]]
        categories = col_keys[:]

    fig = go.Figure()
    for _, row in ranking_df.iterrows():
        key = row["key"]
        color = MODEL_COLORS.get(key, "#94a3b8")
        values = [row[c] if row[c] is not None else 0 for c in col_keys]
        values_closed = values + [values[0]]
        cats_closed = categories + [categories[0]]

        fig.add_trace(
            go.Scatterpolar(
                r=values_closed,
                theta=cats_closed,
                name=row[L["model"]],
                line=dict(color=color, width=2.5),
                fill="toself",
                fillcolor=FILL_COLORS.get(key, "rgba(148,163,184,0.15)"),
                marker=dict(size=7, color=color),
            )
        )

    fig.update_layout(
        **_base_layout(t("chart.radar_title", lang), height=440),
        polar=dict(
            bgcolor=PLOT_BG,
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor=GRID,
                linecolor=GRID,
                tickfont=dict(size=10),
            ),
            angularaxis=dict(gridcolor=GRID, linecolor=GRID),
        ),
    )
    return fig


def fig_ranking_bars(ranking_df, use_gold: bool, lang: str = "en", height: int = 320) -> go.Figure:
    L = _L(lang)
    models = ranking_df[L["model"]].tolist()
    colors = [MODEL_COLORS.get(k, "#94a3b8") for k in ranking_df["key"]]

    fig = make_subplots(
        rows=1,
        cols=2 if use_gold else 1,
        subplot_titles=(
            [t("chart.bars_final", lang), t("chart.bars_vs", lang)]
            if use_gold
            else [t("chart.bars_consensus", lang)]
        ),
        horizontal_spacing=0.12,
    )

    fig.add_trace(
        go.Bar(
            y=models,
            x=ranking_df[L["score_final"]],
            orientation="h",
            marker=dict(color=colors, line=dict(color="#1e293b", width=1)),
            text=[
                f"#{r} · {v}%"
                for r, v in zip(ranking_df[L["rank"]], ranking_df[L["score_final"]])
            ],
            textposition="outside",
            name=L["score_final"],
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    if use_gold:
        fig.add_trace(
            go.Bar(
                y=models,
                x=ranking_df[L["score_cons_short"]],
                orientation="h",
                name=L["score_cons_short"],
                marker_color="#3b82f6",
                opacity=0.85,
            ),
            row=1,
            col=2,
        )
        fig.add_trace(
            go.Bar(
                y=models,
                x=ranking_df[L["score_clin_short"]],
                orientation="h",
                name=L["score_clin_short"],
                marker_color="#f5c518",
                opacity=0.85,
            ),
            row=1,
            col=2,
        )

    layout = _base_layout(t("chart.bars_title", lang), height=height)
    layout["barmode"] = "group"
    score_lbl = t("chart.score_pct", lang)
    layout["xaxis"] = dict(range=[0, 105], title=score_lbl)
    if use_gold:
        layout["xaxis2"] = dict(range=[0, 105], title=score_lbl)
    fig.update_layout(**layout)
    fig.update_yaxes(autorange="reversed")
    return fig


def fig_dimensions_grouped(ranking_df, use_gold: bool, lang: str = "en", sem_available: bool = False) -> go.Figure:
    L = _L(lang)
    models = ranking_df[L["model"]].tolist()
    fig = go.Figure()

    dims = [
        (L["rel_short"], "#6366f1"),
        (L["acc_cons_short"], "#3b82f6"),
    ]
    if sem_available:
        dims.append((L["sem_short"], "#a855f7"))
    if use_gold:
        dims += [
            (L["acc_clin_short"], "#f5c518"),
            (L["ddx_short"], "#f97316"),
        ]
    dims.append((L["privacy"], "#00d09c"))

    for dim_name, color in dims:
        fig.add_bar(name=dim_name, x=models, y=ranking_df[dim_name].fillna(0), marker_color=color)

    fig.update_layout(
        **_base_layout(t("chart.dims_title", lang), height=360),
        barmode="group",
        yaxis=dict(range=[0, 105], title=t("chart.score_pct", lang)),
        xaxis=dict(title=""),
    )
    return fig


def fig_privacy_gauges(ranking_df, lang: str = "en", height: int = 230) -> go.Figure:
    """Gauge per modello: 0% (dati inviati al cloud) → 100% (elaborazione locale)."""
    L = _L(lang)
    n = len(ranking_df)
    fig = make_subplots(
        rows=1,
        cols=max(n, 1),
        specs=[[{"type": "indicator"}] * max(n, 1)],
    )
    for i, (_, row) in enumerate(ranking_df.iterrows(), start=1):
        key = row["key"]
        color = MODEL_COLORS.get(key, "#94a3b8")
        value = row[L["privacy"]]
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=value,
                number=dict(suffix="%", font=dict(size=26, color=color)),
                title=dict(text=row[L["model"]], font=dict(size=13, color="#e2e8f0")),
                gauge=dict(
                    axis=dict(range=[0, 100], tickcolor=GRID, tickfont=dict(size=9)),
                    bar=dict(color=color, thickness=0.32),
                    bgcolor=PLOT_BG,
                    borderwidth=0,
                    steps=[
                        {"range": [0, 40], "color": "rgba(239,68,68,0.18)"},
                        {"range": [40, 75], "color": "rgba(245,197,24,0.14)"},
                        {"range": [75, 100], "color": "rgba(0,208,156,0.14)"},
                    ],
                ),
                domain={"row": 0, "column": i - 1},
            ),
            row=1,
            col=i,
        )
    layout = _base_layout(t("chart.privacy_title", lang), height=height)
    layout["margin"] = dict(l=20, r=20, t=70, b=10)
    fig.update_layout(**layout)
    return fig


def fig_concordance_heatmap(matrix_keyed: dict, model_keys: list, lang: str = "en") -> go.Figure:
    """Heatmap di concordanza diagnostica pairwise tra tutti i modelli attivi."""
    names = [MODEL_CONFIG_NAME.get(k, k) for k in model_keys]
    z = []
    for a in model_keys:
        row = []
        for b in model_keys:
            if a == b:
                row.append(100.0)
            else:
                row.append(matrix_keyed.get((a, b), 0.0))
        z.append(row)

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=names,
            y=names,
            colorscale=[
                [0.0, "#1e293b"],
                [0.4, "#3b82f6"],
                [0.75, "#00d09c"],
                [1.0, "#f5c518"],
            ],
            zmin=0,
            zmax=100,
            text=[[f"{v:.0f}%" for v in row] for row in z],
            texttemplate="%{text}",
            textfont=dict(size=13),
            hovertemplate="%{y} ↔ %{x}: %{z:.1f}%<extra></extra>",
            colorbar=dict(title=t("chart.score_pct", lang), ticksuffix="%"),
        )
    )
    layout = _base_layout(t("chart.heatmap_title", lang), height=380)
    layout["xaxis"] = dict(side="top")
    layout["margin"] = dict(l=40, r=40, t=90, b=20)
    fig.update_layout(**layout)
    return fig


def fig_keyword_bar(keyword_counts: dict, total_models: int, lang: str = "en") -> go.Figure:
    """Barre delle keyword cliniche di consenso, ordinate per frequenza tra modelli."""
    if not keyword_counts:
        return go.Figure()
    items = sorted(keyword_counts.items(), key=lambda kv: kv[1], reverse=True)[:14]
    items.reverse()
    words = [w for w, _ in items]
    counts = [c for _, c in items]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=words,
            orientation="h",
            marker=dict(
                color=counts,
                colorscale=[[0, "#3b82f6"], [1, "#00d09c"]],
                line=dict(color="#1e293b", width=1),
            ),
            text=[f"{c}/{total_models}" for c in counts],
            textposition="outside",
        )
    )
    fig.update_layout(
        **_base_layout(t("chart.keywords_title", lang), height=380),
        xaxis=dict(title=t("chart.keywords_axis", lang), range=[0, total_models + 0.5]),
        yaxis=dict(title=""),
    )
    return fig


def fig_urgency_compare(urgency: dict, lang: str = "en") -> go.Figure:
    """Confronto del livello di urgenza/triage dichiarato da ciascun modello."""
    keys, scores, colors, labels = [], [], [], []
    for key, u in urgency.items():
        meta = URGENCY_META.get(u.get("label"), URGENCY_META[None])
        keys.append(MODEL_CONFIG_NAME.get(key, key))
        scores.append(u.get("score") or 0)
        colors.append(meta["color"])
        labels.append(t(meta["label_key"], lang))

    fig = go.Figure(
        go.Bar(
            x=keys,
            y=scores,
            marker=dict(color=colors, line=dict(color="#1e293b", width=1)),
            text=labels,
            textposition="outside",
        )
    )
    fig.update_layout(
        **_base_layout(t("chart.urgency_title", lang), height=320),
        yaxis=dict(range=[0, 115], title=t("chart.score_pct", lang)),
        xaxis=dict(title=""),
    )
    return fig


def fig_leaderboard(leaderboard_df, lang: str = "en") -> go.Figure:
    """Classifica cumulativa vittorie/score medio tra i round eseguiti in sessione."""
    L = _L(lang)
    if leaderboard_df is None or leaderboard_df.empty:
        return go.Figure()
    colors = [MODEL_COLORS.get(k, "#94a3b8") for k in leaderboard_df["key"]]
    wins_col = t("leaderboard.wins", lang)
    avg_col = t("leaderboard.avg_score", lang)

    fig = make_subplots(rows=1, cols=2, subplot_titles=(wins_col, avg_col), horizontal_spacing=0.12)
    fig.add_trace(
        go.Bar(
            x=leaderboard_df[L["model"]],
            y=leaderboard_df[wins_col],
            marker_color=colors,
            showlegend=False,
            text=leaderboard_df[wins_col],
            textposition="outside",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=leaderboard_df[L["model"]],
            y=leaderboard_df[avg_col],
            marker_color=colors,
            showlegend=False,
            text=[f"{v}%" for v in leaderboard_df[avg_col]],
            textposition="outside",
        ),
        row=1,
        col=2,
    )
    layout = _base_layout(t("chart.leaderboard_title", lang), height=340)
    fig.update_layout(**layout)
    fig.update_yaxes(range=[0, max(leaderboard_df[wins_col].max() + 1, 3)], row=1, col=1)
    fig.update_yaxes(range=[0, 110], row=1, col=2)
    return fig
