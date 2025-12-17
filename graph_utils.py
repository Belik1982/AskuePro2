import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import math

PALETTES = {
    "Default": ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3", "#FF6692", "#B6E880"],
    "Vivid": ["#FF0D0D", "#0051FF", "#00D604", "#FFC400", "#FF00E6", "#00E0E0", "#FF8800"],
    "Neon": ["#00FEFE", "#FE00FE", "#FEFE00", "#00FF00", "#FF0000", "#39FF14"],
    "Pastel": ["#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF", "#E2F0CB", "#FFDAC1"],
    "Tableau": ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7"],
}

PALETTE_TO_HEATMAP = {
    "Default": "RdYlGn_r", "Vivid": "Jet", "Neon": "HSV", "Pastel": "Tealrose", "Tableau": "Blues", "Custom": "Viridis"
}

LINE_STYLES_BW = [
    dict(dash="solid", marker="circle"), dict(dash="longdash", marker="square"),  
    dict(dash="dot", marker="diamond"), dict(dash="dashdot", marker="cross")
]
BAR_PATTERNS_BW = ["/", "\\", "x", "-", "|", "+"]

def get_color(i, palette_name, bw_mode, custom_colors=None):
    if bw_mode: return "black"
    if palette_name == "Custom" and custom_colors:
        return custom_colors[i % len(custom_colors)]
    colors = PALETTES.get(palette_name, PALETTES["Default"])
    return colors[i % len(colors)]

def get_style_settings(index, bw_mode, palette_name, custom_colors=None):
    if bw_mode:
        style = LINE_STYLES_BW[index % len(LINE_STYLES_BW)]
        return "black", style["dash"], style["marker"]
    else:
        color = get_color(index, palette_name, False, custom_colors)
        return color, "solid", "circle"

def configure_legend(fig, pos):
    if not pos: fig.update_layout(showlegend=False); return
    fig.update_layout(showlegend=True)
    if pos == "top": fig.update_layout(legend=dict(orientation="h", y=1.1, x=0))
    elif pos == "bottom": fig.update_layout(legend=dict(orientation="h", y=-0.2, x=0))
    elif pos == "right": fig.update_layout(legend=dict(orientation="v", y=1, x=1.02))

def get_axis_style(bw_mode):
    c = "#333" if bw_mode else "#888"
    gc = "#bbb" if bw_mode else "#ddd"
    return dict(showline=True, linewidth=2, linecolor=c, mirror=True, showgrid=True, gridcolor=gc)

def plot_30min_graph(df, height, line_width, show_pts, show_anomalies, chart_type, legend_pos, bw_mode, labels, template, palette_name="Default", custom_colors=None):
    fig = go.Figure()
    has_range = 'min_val' in df.columns and 'max_val' in df.columns
    series_keys = sorted(df.groupby(["MeterID", "Type"]).groups.keys())
    
    for i, (meter, typ) in enumerate(series_keys):
        sub = df[(df["MeterID"] == meter) & (df["Type"] == typ)]
        if sub.empty: continue
        
        color, dash_style, marker_sym = get_style_settings(i, bw_mode, palette_name, custom_colors)
        name = f"{meter} {typ}"
        mode = "lines"
        text_labels = None
        if show_pts and chart_type != "Bar": 
            mode = "lines+markers+text"
            text_labels = [t.strftime("%H:%M") for t in sub["DateTime"]]
        if chart_type == "Scatter": mode = "markers"
        
        ht = "<b>%{y:,.2f}</b><br>%{x|%d.%m %H:%M}<extra>" + name + "</extra>"
        common = dict(x=sub["DateTime"], y=sub["Value"], name=name, hovertemplate=ht)
        line_shape = 'linear'
        if chart_type == "Step": line_shape = 'hv'
        elif chart_type == "Spline": line_shape = 'spline'

        if chart_type == "Bar":
            ms = dict(color=color)
            if bw_mode:
                pat = BAR_PATTERNS_BW[i % len(BAR_PATTERNS_BW)]
                ms = dict(color="white", line=dict(color="black", width=1), pattern=dict(shape=pat, fgcolor="black"))
            fig.add_trace(go.Bar(**common, marker=ms))
        elif chart_type == "Area":
            fig.add_trace(go.Scatter(**common, mode=mode, fill='tozeroy', line=dict(width=line_width, color=color, dash=dash_style, shape=line_shape), marker=dict(symbol=marker_sym, size=6), text=text_labels))
        else:
            fig.add_trace(go.Scatter(**common, mode=mode, line=dict(width=line_width, color=color, dash=dash_style, shape=line_shape), marker=dict(symbol=marker_sym, size=6), text=text_labels))
        
        if has_range and not bw_mode and chart_type in ["Line", "Spline", "Step", "Area"]:
             fig.add_trace(go.Scatter(x=pd.concat([sub["DateTime"], sub["DateTime"][::-1]]), y=pd.concat([sub["max_val"], sub["min_val"][::-1]]), fill='toself', fillcolor=color, opacity=0.2, line=dict(width=0), hoverinfo="skip", showlegend=False))

        if show_anomalies and "is_anomaly" in sub.columns:
            anom = sub[sub["is_anomaly"]==True]
            if not anom.empty:
                ac = "black" if bw_mode else "red"
                fig.add_trace(go.Scatter(x=anom["DateTime"], y=anom["Value"], mode="markers", marker=dict(color=ac, size=10, symbol="x"), name=f"{name} (Alert)", showlegend=False))

    axis = get_axis_style(bw_mode)
    x_ax = axis.copy()
    x_ax.update(dict(
        title=labels.get("x", ""),
        tickformatstops=[dict(dtickrange=[None, 86400000], value="%H:%M\n%d.%m"), dict(dtickrange=[86400000, None], value="%d.%m")],
        rangeslider=dict(visible=True, thickness=0.08),
        showgrid=True, gridcolor="rgba(128,128,128,0.2)", nticks=30,
    ))

    fig.update_layout(
        height=height, template=template, hovermode="x unified", dragmode="select",
        margin=dict(t=30, b=20, l=40, r=40),
        xaxis=x_ax, yaxis=dict(**axis, title=labels.get("y", ""))
    )
    configure_legend(fig, legend_pos)
    return fig

def plot_daily_bar(df, height, l_pos, labels, template, palette_name="Default", custom_colors=None, show_vals=False):
    daily = df.groupby(["Date", "Type", "MeterID"])["Value"].sum().reset_index()
    fig = go.Figure()
    bw_mode = labels.get("bw", False)
    groups = sorted(daily.groupby(["MeterID", "Type"]).groups.keys())
    
    for i, key in enumerate(groups):
        meter, typ = key
        sub = daily[(daily["MeterID"]==meter) & (daily["Type"]==typ)]
        if bw_mode:
            pat = BAR_PATTERNS_BW[i % len(BAR_PATTERNS_BW)]
            ms = dict(color="white", line=dict(color="black", width=1.5), pattern=dict(shape=pat, fgcolor="black"))
        else:
            color = get_color(i, palette_name, False, custom_colors)
            ms = dict(color=color)
        
        text_template = "%{y:,.0f}" if show_vals else None
        text_pos = "auto" if show_vals else None

        ht = "<b>%{y:,.2f}</b><br>%{x|%d.%m.%Y}<extra>" + f"{meter} {typ}" + "</extra>"
        fig.add_trace(go.Bar(x=sub["Date"], y=sub["Value"], name=f"{meter} {typ}", marker=ms, hovertemplate=ht, texttemplate=text_template, textposition=text_pos))

    axis_x = get_axis_style(bw_mode).copy()
    axis_x.update(dict(title=labels.get("x", ""), tickformat="%d.%m", tickmode="linear", dtick=86400000.0, showgrid=True, gridcolor="rgba(128,128,128,0.2)", gridwidth=1))

    fig.update_layout(height=height, template=template, barmode="group", margin=dict(t=30, b=20, l=40, r=40), xaxis=axis_x, yaxis=dict(**get_axis_style(bw_mode), title=labels.get("y", "")))
    configure_legend(fig, l_pos)
    return fig

def plot_heatmap(df, height, show_text, labels, template, palette_name="Default"):
    if df.empty: return go.Figure()
    m, t = df.iloc[0]["MeterID"], df.iloc[0]["Type"]
    sub = df[(df["MeterID"] == m) & (df["Type"] == t)].copy()
    sub["TimeStr"] = sub["Time"].apply(lambda x: x.strftime("%H:%M"))
    piv = sub.pivot_table(index="TimeStr", columns="Date", values="Value", aggfunc="sum")
    piv.index = pd.to_datetime(piv.index, format="%H:%M").time
    piv = piv.sort_index(); piv.index = [tm.strftime("%H:%M") for tm in piv.index]
    new_cols = [d.strftime("%d.%m") for d in piv.columns]
    piv.columns = new_cols
    scale = PALETTE_TO_HEATMAP.get(palette_name, "RdYlGn_r")
    txt = ".1f" if show_text else False
    fig = px.imshow(piv, aspect="auto", color_continuous_scale=scale, text_auto=txt)
    fig.update_layout(height=height, title=f"{m} {t}", template=template, margin=dict(t=40, b=20, l=40, r=40))
    return fig

def plot_pq_scatter(df, height, show_cos, l_pos, bw_mode, labels, template, palette_name="Default", custom_colors=None, show_labels=False):
    df_c = df[df["Suffix"].isin([2, 4])]
    if df_c.empty: return go.Figure()
    piv = df_c.pivot_table(index=["DateTime", "MeterID"], columns="Suffix", values="Value").reset_index()
    if 2 not in piv.columns or 4 not in piv.columns: return go.Figure()
    piv["TimeStr"] = piv["DateTime"].dt.strftime("%d.%m %H:%M")
    fig = go.Figure()
    meters = sorted(piv["MeterID"].unique())
    for i, m in enumerate(meters):
        d = piv[piv["MeterID"] == m]
        if bw_mode: c = "black"; sym = get_style_settings(i, True, palette_name)[2]
        else: c = get_color(i, palette_name, False, custom_colors); sym = "circle"
        mode = "markers"; text_arr = None
        if show_labels: mode = "markers+text"; text_arr = d["DateTime"].dt.strftime("%H:%M")
        fig.add_trace(go.Scatter(x=d[2], y=d[4], mode=mode, name=str(m), marker=dict(symbol=sym, size=8, opacity=0.7, color=c), customdata=d["TimeStr"], text=text_arr, textposition="top center", hovertemplate="<b>%{customdata}</b><br>P: %{x:,.1f}<br>Q: %{y:,.1f}<extra></extra>"))
    axis = get_axis_style(bw_mode)
    fig.update_layout(xaxis=dict(**axis, title=labels.get("p", "P")), yaxis=dict(**axis, title=labels.get("q", "Q")), height=height, template=template, margin=dict(t=30, b=20, l=40, r=40))
    if show_cos:
        mx = piv[2].max() if not piv.empty else 100
        slope = math.tan(math.acos(0.96))
        fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx*slope], mode="lines", line=dict(color="black" if bw_mode else "green", dash="dash"), name="Cos φ 0.96"))
    configure_legend(fig, l_pos)
    return fig

# --- НОВА ФУНКЦІЯ (СКРИПКОВИЙ ГРАФІК) ---
def plot_violin_distribution(df, height, group_by, template, palette_name="Default", custom_colors=None, labels=None):
    if df.empty: return go.Figure()
    df = df.copy()
    
    if group_by == 'Hour':
        df['X_Axis'] = df['DateTime'].dt.hour
        x_label = "Година доби"
        category_orders = {'X_Axis': list(range(24))}
    else: 
        days_map = {0: '01. Пн', 1: '02. Вт', 2: '03. Ср', 3: '04. Чт', 4: '05. Пт', 5: '06. Сб', 6: '07. Нд'}
        df['X_Axis'] = df['DateTime'].dt.dayofweek.map(days_map)
        x_label = "День тижня"
        category_orders = {'X_Axis': sorted(list(days_map.values()))}

    if palette_name == "Custom" and custom_colors:
        scale = custom_colors
    else:
        scale = PALETTES.get(palette_name, PALETTES["Default"])

    y_title = labels.get("y", "Значення") if labels else "Значення"

    fig = px.violin(
        df, x='X_Axis', y='Value', color='Type', box=True, points=False,
        hover_data=['DateTime'], color_discrete_sequence=scale, category_orders=category_orders
    )
    
    # --- ВИПРАВЛЕННЯ: Додано spanmode='hard' для обрізки "хвостів" ---
    fig.update_traces(spanmode='hard')

    fig.update_layout(
        height=height, template=template, 
        xaxis_title=x_label, yaxis_title=y_title, 
        violinmode='group', 
        margin=dict(t=30, b=20, l=40, r=40), 
        legend=dict(orientation="h", y=1.1, x=0)
    )
    return fig