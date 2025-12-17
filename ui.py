import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

DEFAULT_HEX = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#00FFFF", "#FF00FF", "#800000", "#808000", "#008080", "#000080"]

# --- ТЕКСТИ ІНТЕРФЕЙСУ (UA) ---
TRANS = {
    # Основні
    "settings": "Налаштування", 
    "source": "Джерело даних", 
    "files_loaded_lbl": "Завантажено файлів:", 
    "clear_data": "🗑️ Очистити все",
    "no_data": "Немає даних для відображення",
    
    # Вкладки
    "tab_graph": "Графіки 30хв", 
    "tab_daily": "Добові", 
    "tab_matrix": "Матриця",
    "tab_pq": "P vs Q", 
    "tab_dist": "Розподіл", 
    "tab_table": "Таблиця", 
    "tab_report": "📄 Майстер Звітів",
    
    # Фільтри
    "flt_meters": "ЛІЧИЛЬНИКИ", 
    "flt_period": "ПЕРІОД", 
    "mode_cons": "СПОЖИВАННЯ", 
    "mode_gen": "ГЕНЕРАЦІЯ",
    "select_all": "Всі", 
    "deselect_all": "Скинути",
    
    # KPI
    "kpi_cons_label": "СПОЖИВАННЯ", 
    "kpi_gen_label": "ГЕНЕРАЦІЯ",
    "kpi_act_name": "Актив", 
    "kpi_react_name": "Реактив", 
    "kpi_cos": "Cos φ", 
    "kpi_peak": "Пік",
    "kpi_act_suffix": "кВт·год", 
    "kpi_react_suffix": "кВАр·год", 
    "kpi_peak_suffix": "кВт",
    
    # Осі
    "ax_date": "Дата і час", 
    "ax_value": "Значення", 
    "ax_p": "P (Активна)", 
    "ax_q": "Q (Реактивна)",
    
    # --- ДЕТАЛЬНІ ОПИСИ ГРАФІКІВ ---
    "desc_30m": """
    ### ℹ️ Графік профілю потужності (30 хв)
    **Що показує:** Детальну динаміку навантаження з кроком 30 хвилин.  
    **Як читати:** Гострі піки вказують на запуск потужного обладнання. Провали до 0 — на відключення або аварії. Використовуйте для пошуку конкретного часу подій.
    """,
    
    "desc_daily": """
    ### ℹ️ Добове споживання
    **Що показує:** Сумарне споживання енергії за кожну добу.  
    **Як читати:** Порівнюйте висоту стовпців для виявлення тенденцій (зростання/спад) та різниці між робочими і вихідними днями.
    """,
    
    "desc_matrix": """
    ### ℹ️ Теплова карта (Матриця)
    **Що показує:** Інтенсивність споживання кольором у розрізі: **Години** (вертикаль) × **Дні** (горизонталь).  
    **Як читати:** 
    *   🟥/🟨 Яскраві плями — години пікового навантаження.
    *   🟩 Темні зони — мінімальне споживання.
    *   Вертикальні смуги — характерний режим дня.
    """,
    
    "desc_pq": """
    ### ℹ️ P vs Q (Активна проти Реактивної)
    **Що показує:** Залежність реактивної потужності від активної (косинус фі).  
    **Як читати:**
    *   Точки мають групуватися вздовж лінії (ідеальний Cos φ).
    *   Великий розкид вгору свідчить про **перекомпенсацію** або **недокомпенсацію** реактивної потужності.
    """,
    
    "desc_dist": """
    ### ℹ️ Статистичний розподіл (Скрипковий графік)
    Цей графік показує не просто середнє, а **яким саме** було навантаження найчастіше.
    
    **Як читати фігуру:**
    *   **Ширина ("Живіт"):** Показує, де зосереджено найбільше даних. Якщо фігура широка внизу — обладнання частіше простоює або працює на мінімумі. Якщо широка посередині — працює в номіналі.
    *   **Висота:** Показує повний діапазон від мінімуму до максимуму.
    *   **Два горби:** Якщо фігура схожа на пісочний годинник, це означає два режими роботи (наприклад, "ВКЛ" і "ВИКЛ"), а проміжних станів майже немає.
    
    **Статистика:**
    *   **median (50%):** Реальний центр навантаження.
    *   **kde:** Показник "густини". Чим вище число, тим стабільніше навантаження в цій точці.
    """,
    
    "desc_table": "### ℹ️ Таблиця даних\nВихідний масив для детального перегляду значень, фільтрації та експорту в Excel.",
    
    # Майстер звітів
    "rep_add_stats": "➕ Статистика", 
    "rep_add_30m": "➕ Графік 30хв",
    "rep_add_daily": "➕ Графік Доба", 
    "rep_add_matrix": "➕ Матриця",
    "rep_gen": "🚀 Сформувати PDF", 
    "rep_download": "💾 СКАЧАТИ ЗВІТ",
    
    # Інше
    "chat_head": "Чат з асистентом", "chat_open_btn": "💬", 
    "ai_sets": "Налаштування ШІ", "ai_key_err": "Введіть API ключ", 
    "ai_ready": "Готовий", "ai_load_btn": "Завантажити контекст", 
    "ai_analyzing": "Аналізую...", "ai_q_placeholder": "Ваше питання...",
    "palette": "Кольорова схема", "custom_cols_lbl": "Налаштування кольорів серій:",
    "print_btn": "🖨️ Друк сторінки",
    
    "welcome_header": "Вітаємо в АСКОЕ Pro ⚡",
    "welcome_sub": "Система професійного аналізу даних (формат 30917).",
    "instr_header": "📘 Інструкція: з чого почати?",
    "instr_step1": "**1. Підготовка даних:**",
    "instr_text1": "Завантажте файли макетів **30917**.",
    "instr_step2": "**2. Завантаження:**",
    "instr_text2": "Перетягніть файли в зону **'Завантаження'** або завантажте з пошти.",
    "instr_step3": "**3. Аналіз:**",
    "instr_text3": "Система побудує графіки.",
    "feat_header": "🚀 Можливості програми",
    "feat_graph": "📊 **Аналітика:** Детальні профілі, добові графіки, матриці, скрипкові діаграми.",
    "feat_stats": "📐 **Розумна статистика:** Виділіть ділянку — отримайте суму.",
    "ai_header": "🤖 ШІ-Асистент",
    "ai_desc": "Допомога в інтерпретації.",
    "ai_how": "Кнопка 💬 внизу праворуч."
}

def t(key):
    return TRANS.get(key, key)

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

def render_ai_onboarding():
    st.info("""
    **🤖 ШІ-Аналітик готовий!**
    
    Я проаналізував завантажені дані. Запитайте мене про:
    - Пікові навантаження та їх час.
    - Аномалії в нічний час.
    - Порівняння споживання (будні vs вихідні).
    """)

def render_start_screen():
    st.markdown(f"# {t('welcome_header')}")
    st.markdown(f"#### {t('welcome_sub')}")
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"### {t('instr_header')}")
        st.markdown(t('instr_step1')); st.caption(t('instr_text1'))
        st.markdown(t('instr_step2')); st.caption(t('instr_text2'))
        st.markdown(t('instr_step3')); st.caption(t('instr_text3'))
    with c2:
        st.markdown(f"### {t('feat_header')}")
        st.markdown(t('feat_graph')); st.markdown(t('feat_stats'))
        st.markdown("---")
        st.markdown(f"### {t('ai_header')}")
        st.caption(t('ai_desc')); st.markdown(t('ai_how'))

def render_footer():
    theme_cls = "dark-theme" if st.session_state.get("theme_mode", "Light") == "Dark" else ""
    st.markdown(f'<div class="app-footer {theme_cls}" style="text-align: center; color: #888; font-size: 0.7rem; margin-top: 3rem; border-top: 1px solid #ccc; padding-top: 10px;">&copy; Розроблено <b>Byelotserkovsky A.</b> за допомогою ШІ для використання службою ЕМЕС АТ "ЕФЕКТ"</div>', unsafe_allow_html=True)

def render_chat_html_js():
    pass 

def render_file_grid(file_info, date_range=None):
    if not file_info: return
    
    count_text = f"**Завантажено файлів: {len(file_info)}**"
    if date_range and date_range[0] is not pd.NaT and date_range[1] is not pd.NaT:
        s_str = date_range[0].strftime("%d.%m.%y")
        e_str = date_range[1].strftime("%d.%m.%y")
        count_text += f" (Період: {s_str} - {e_str})"

    st.caption(count_text)
    
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
        with st.expander(f"⚙️ {t('settings')}", expanded=True):
            th_mode = st.radio(t("theme"), ["Світла", "Темна"], horizontal=True)
            st.session_state["theme_mode"] = "Dark" if th_mode == "Темна" else "Light"
            st.session_state["bw_mode"] = st.checkbox("Ч/Б (Друк)", value=st.session_state.get("bw_mode", False))

            pal_opts = ["Default", "Vivid", "Pastel", "Tableau", "Custom"]
            st.session_state["palette_name"] = st.selectbox(t("palette"), pal_opts)
            
            if st.session_state["palette_name"] == "Custom" and df_context is not None and not df_context.empty:
                st.markdown(f"**{t('custom_cols_lbl')}**")
                active_series = sorted(df_context.groupby(["MeterID", "Type"]).groups.keys())
                custom_colors = []
                for i, (meter, typ) in enumerate(active_series):
                    pk_key = f"clr_{meter}_{typ}_{i}"
                    def_val = DEFAULT_HEX[i % len(DEFAULT_HEX)]
                    c = st.color_picker(f"{meter} {typ}", value=def_val, key=pk_key)
                    custom_colors.append(c)
                st.session_state["custom_colors"] = custom_colors

            nav = st.session_state.get("nav_tab", "tab_graph")
            
            if nav == "tab_graph":
                st.session_state["chart_type"] = st.selectbox("Тип", ["Line", "Step", "Spline", "Area", "Bar", "Scatter"])
                res_opts = {"30T": "30 хв", "1h": "1 год", "2h": "2 год", "4h": "4 год"}
                rv = st.selectbox("Детализация", list(res_opts.keys()), format_func=lambda x: res_opts[x])
                st.session_state["resample_val"] = rv
                st.session_state["show_anom"] = st.checkbox("Аномалии")
                st.session_state["show_pts"] = st.checkbox("Точки")
                st.session_state["line_w"] = st.slider("Толщина", 1, 5, 2)
            
            if nav == "tab_daily":
                st.session_state["show_vals"] = st.checkbox("Значения (Цифры)", value=False)
            
            if nav == "tab_matrix":
                heat_opts = ["Default", "Vivid", "Neon", "Pastel", "Tableau"]
                st.session_state["heatmap_palette_name"] = st.selectbox("Palette Matrix", heat_opts)
                st.session_state["show_vals"] = st.checkbox("Значения", value=False)
            
            if nav == "tab_pq":
                st.session_state["show_pq_labels"] = st.checkbox("Метки точек (Labels)", value=False)

            st.session_state["chart_h"] = st.slider("Высота", 300, 1000, 500, 50)
            
            st.markdown("---")
            components.html(f"""<button onclick="window.parent.print()" style="width: 100%; background: #ff4b4b; color: white; border: none; padding: 5px; border-radius: 4px; font-weight: bold;">{t('print_btn')}</button>""", height=40)