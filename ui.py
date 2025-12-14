import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

# Кольори для графіків (HEX)
DEFAULT_HEX = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#00FFFF", "#FF00FF", "#800000", "#808000", "#008080", "#000080"]

def render_kpi_custom(value_str, label, theme_mode, is_consumption=True):
    theme_cls = "dark-theme" if theme_mode == "Dark" else ""
    color_cls = "kpi-green" if is_consumption else "kpi-red"
    arrow = "↑" if is_consumption else "↓"
    return f'<div class="{theme_cls}" style="line-height: 1.2;"><div class="kpi-custom-val" style="font-size: 24px; font-weight: 600;">{value_str}</div><div class="kpi-custom-label {color_cls}" style="font-size: 0.8rem; font-weight: 500;">{arrow} {label}</div></div>'

def generate_detailed_stats_html(stats_list, time_range):
    if not stats_list: return ""
    rows = ""
    for idx, s in enumerate(stats_list):
        bg = "background-color: rgba(128,128,128,0.1);" if idx % 2 != 0 else ""
        rows += f'<tr style="{bg}"><td><b>{s["name"]}</b></td><td>{s["sum"]:,.0f}</td><td>{s["avg"]:.2f}</td><td>{s["min"]:.1f} / {s["max"]:.1f}</td></tr>'
    t_str = f"{time_range[0].strftime('%d.%m %H:%M')} - {time_range[1].strftime('%d.%m %H:%M')}"
    return f"""
    <div style="margin-top: 15px; border: 1px solid #777; border-radius: 4px; overflow: hidden; font-size: 0.8rem;">
        <div style="background: #333; color: #fff; padding: 5px 10px; font-weight: bold;">{t_str} | Статистика виділення</div>
        <table style="width: 100%; border-collapse: collapse;">
            <thead><tr style="border-bottom: 2px solid #555;"><th>Канал</th><th>Сума</th><th>Сер</th><th>Мін/Макс</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """

def render_start_screen():
    st.markdown("# Вітаємо в АСКОЕ Pro ⚡")
    st.markdown("#### Професійна система аналізу даних комерційного обліку електроенергії (формат 30917).")
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 📘 Інструкція: з чого почати?")
        st.markdown("**1. Підготовка даних:**")
        st.caption("Завантажте файли макетів **30917**.")
        st.markdown("**2. Завантаження:**")
        st.caption("Перетягніть файли в зону **'Завантаження'** або завантажте з пошти.")
        st.markdown("**3. Аналіз:**")
        st.caption("Система побудує графіки та звіти.")
    with c2:
        st.markdown("### 🚀 Можливості програми")
        st.markdown("📊 **Аналітика:** Детальні профілі, добові графіки, теплові карти.")
        st.markdown("📐 **Розумна статистика:** Виділіть ділянку на графіку — отримайте суму та середнє.")
        st.markdown("---")
        st.markdown("### 🤖 ШІ-Асистент")
        st.caption("Допомога в інтерпретації даних.")
        st.markdown("Кнопка 💬 внизу праворуч.")

def render_footer():
    theme_cls = "dark-theme" if st.session_state.get("theme_mode", "Light") == "Dark" else ""
    st.markdown(f'<div class="app-footer {theme_cls}" style="text-align: center; color: #888; font-size: 0.7rem; margin-top: 3rem; border-top: 1px solid #ccc; padding-top: 10px;">&copy; Розроблено <b>Byelotserkovsky A.</b> за допомогою ШІ для використання службою ЕМЕС АТ "ЕФЕКТ"</div>', unsafe_allow_html=True)

def render_chat_html_js():
    pass 

def render_file_grid(file_info):
    if not file_info: return
    st.caption(f"**Завантажено файлів: {len(file_info)}**")
    
    css = """
    <style>
        .file-grid-wrapper { display: grid; grid-template-columns: repeat(4, 1fr); gap: 2px; margin-bottom: 10px; }
        .file-card { background-color: rgba(128, 128, 128, 0.1); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 3px; padding: 2px 1px; text-align: center; overflow: hidden; cursor: help; }
        .file-icon { font-size: 0.85rem; line-height: 1; margin-bottom: 0px; }
        .file-name { font-size: 0.65rem; font-weight: normal; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.1; padding: 0 1px; color: inherit; }
    </style>
    """
    cards = "".join([f'<div class="file-card" title="{f["name"]} ({f.get("size", "")})"><div class="file-icon">📄</div><div class="file-name">{f["name"]}</div></div>' for f in file_info])
    st.markdown(css + f'<div class="file-grid-wrapper">{cards}</div>', unsafe_allow_html=True)

def render_sidebar(df_context=None, file_info=None):
    st.markdown("""
    <style>
        @media print {
            section[data-testid="stSidebar"] { display: none !important; }
            header, footer, .stButton, .stDeployButton { display: none !important; }
            .block-container { padding-top: 0 !important; margin: 0 !important; }
            .js-plotly-plot { display: block !important; width: 100% !important; }
        }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        with st.expander("⚙️ Налаштування", expanded=True):
            th_mode = st.radio("Тема", ["Світла", "Темна"], horizontal=True)
            st.session_state["theme_mode"] = "Dark" if th_mode == "Темна" else "Light"
            st.session_state["bw_mode"] = st.checkbox("Ч/Б (Друк)", value=st.session_state.get("bw_mode", False))

            pal_opts = ["Default", "Vivid", "Pastel", "Tableau", "Custom"]
            st.session_state["palette_name"] = st.selectbox("Кольорова схема", pal_opts)
            
            # Динамічні пікери кольорів
            if st.session_state["palette_name"] == "Custom" and df_context is not None and not df_context.empty:
                st.markdown("**Налаштування кольорів серій:**")
                active_series = sorted(df_context.groupby(["MeterID", "Type"]).groups.keys())
                custom_colors = []
                for i, (meter, typ) in enumerate(active_series):
                    pk_key = f"clr_{meter}_{typ}_{i}"
                    def_val = DEFAULT_HEX[i % len(DEFAULT_HEX)]
                    c = st.color_picker(f"{meter} {typ}", value=def_val, key=pk_key)
                    custom_colors.append(c)
                st.session_state["custom_colors"] = custom_colors

            nav = st.session_state.get("nav_tab", "tab_graph")
            
            # Налаштування для кожної вкладки
            if nav == "tab_graph":
                st.session_state["chart_type"] = st.selectbox("Тип графіку", ["Line", "Step", "Spline", "Area", "Bar", "Scatter"])
                res_opts = {"30T": "30 хв", "1h": "1 год", "2h": "2 год", "4h": "4 год"}
                rv = st.selectbox("Деталізація", list(res_opts.keys()), format_func=lambda x: res_opts[x])
                st.session_state["resample_val"] = rv
                st.session_state["show_anom"] = st.checkbox("Аномалії")
                st.session_state["show_pts"] = st.checkbox("Маркери точок")
                st.session_state["line_w"] = st.slider("Товщина лінії", 1, 5, 2)
            
            if nav == "tab_daily":
                st.session_state["show_vals"] = st.checkbox("Показувати значення (цифри)", value=False)
            
            if nav == "tab_matrix":
                heat_opts = ["Default", "Vivid", "Neon", "Pastel", "Tableau"]
                st.session_state["heatmap_palette_name"] = st.selectbox("Палітра матриці", heat_opts)
                st.session_state["show_vals"] = st.checkbox("Показувати значення", value=False)
            
            if nav == "tab_pq":
                st.session_state["show_pq_labels"] = st.checkbox("Підписи точок (Час)", value=False)

            st.session_state["chart_h"] = st.slider("Висота графіку", 300, 1000, 500, 50)
            
            st.markdown("---")
            components.html("""<button onclick="window.parent.print()" style="width: 100%; background: #ff4b4b; color: white; border: none; padding: 5px; border-radius: 4px; font-weight: bold;">🖨️ Друк сторінки</button>""", height=40)