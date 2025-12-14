import streamlit as st
import pandas as pd
import os
import math
import base64
from datetime import datetime
import numpy as np

# Локальні модулі
import ui
import parser
import graph_utils
import export_utils
import selection_utils
import ai_utils
import mail_utils

# 1. Config
st.set_page_config(page_title="АСКОЕ Pro", layout="wide", page_icon="⚡", initial_sidebar_state="expanded")

# 2. State Initialization
if "data_df" not in st.session_state: st.session_state["data_df"] = pd.DataFrame()
if "file_info" not in st.session_state: st.session_state["file_info"] = []
if "messages" not in st.session_state: st.session_state["messages"] = []
if "nav_tab" not in st.session_state: st.session_state["nav_tab"] = "tab_graph"
if "is_chat_open" not in st.session_state: st.session_state["is_chat_open"] = False
if "palette_name" not in st.session_state: st.session_state["palette_name"] = "Default"
if "custom_colors" not in st.session_state: st.session_state["custom_colors"] = ["#FF0000"] * 8
if "pdf_bytes" not in st.session_state: st.session_state["pdf_bytes"] = None

# Стан майстра звітів
if "report_blocks" not in st.session_state: 
    st.session_state["report_blocks"] = [{"type": "stats", "id": 0, "title": "Зведена статистика"}]
if "report_counter" not in st.session_state: st.session_state["report_counter"] = 1

defaults = {
    "chart_h": 500, "chart_type": "Line", "line_w": 2, 
    "show_pts": False, "show_anom": False, "legend_pos_val": "top", "bw_mode": False,
    "resample_val": "30T", "theme_mode": "Light", "show_vals": False
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# --- ФУНКЦІЇ ---
def merge_new_data(new_df, new_files):
    """Об'єднує нові дані з існуючими"""
    if new_df.empty: return

    if st.session_state["data_df"].empty:
        st.session_state["data_df"] = new_df
        st.session_state["file_info"] = new_files
    else:
        # Запобігаємо конфліктам типів
        old_df = st.session_state["data_df"]
        
        # Конкатенація
        combined = pd.concat([old_df, new_df], ignore_index=True)
        
        # Видалення дублікатів (залишаємо останні завантажені)
        combined = combined.drop_duplicates(subset=["DateTime", "MeterID", "Type"], keep="last")
        combined = combined.sort_values("DateTime")
        
        st.session_state["data_df"] = combined
        
        # Оновлення списку файлів
        existing_names = {f['name'] for f in st.session_state["file_info"]}
        for f in new_files:
            if f['name'] not in existing_names:
                st.session_state["file_info"].append(f)

def add_report_block(b_type, title, default_meters=None, default_types=None):
    st.session_state["report_counter"] += 1
    if b_type == 'graph_matrix':
        sel_m = [default_meters[0]] if default_meters else []
        sel_t = [default_types[0]] if default_types else []
    else:
        sel_m = default_meters if default_meters else []
        sel_t = default_types if default_types else []

    new_block = {
        "type": b_type, "id": st.session_state["report_counter"],
        "title": title, "meters": sel_m, "types": sel_t
    }
    st.session_state["report_blocks"].append(new_block)

def delete_report_block(idx):
    if 0 <= idx < len(st.session_state["report_blocks"]):
        st.session_state["report_blocks"].pop(idx)

# 3. Header
if os.path.exists("logo.png"): st.image("logo.png", width=250)
else: st.title(f"⚡ АСКОЕ Pro")

df = st.session_state["data_df"]

# --- APP LOGIC: ЗАВАНТАЖЕННЯ (СТАРТОВИЙ ЕКРАН) ---
if df.empty:
    ui.render_sidebar()
    ui.render_start_screen()
    st.markdown("### Джерело даних")
    src_tab1, src_tab2 = st.tabs(["📂 Завантаження файлів", "📧 Завантаження з пошти"])
    
    with src_tab1:
        up = st.file_uploader("Оберіть .txt (Формат 30917)", type=["txt"], accept_multiple_files=True, label_visibility="collapsed")
        if up:
            files = [(f.name, f.read()) for f in up]
            with st.spinner("Обробка файлів..."):
                d, i, errs = parser.parse_askue_files(files, datetime.now().year)
            if errs:
                st.error("Помилки читання файлів:")
                for e in errs: st.write(f"- {e}")
            if not d.empty:
                st.session_state["data_df"] = d
                st.session_state["file_info"] = i
                st.rerun()

    with src_tab2:
        st.info("Автоматичний пошук вкладень (тема 30917).")
        if st.button("🔄 Перевірити пошту", type="primary"):
            with st.spinner("Підключення до серверу..."):
                mail_files, error_msg = mail_utils.fetch_attachments_from_mail(limit=15)
                if error_msg: st.error(error_msg)
                elif not mail_files: st.warning("Вкладень не знайдено.")
                else:
                    st.success(f"Знайдено файлів: {len(mail_files)}")
                    d, i, errs = parser.parse_askue_files(mail_files, datetime.now().year)
                    if not d.empty:
                        st.session_state["data_df"] = d
                        st.session_state["file_info"] = i
                        st.rerun()
    ui.render_footer()

else:
    # --- БОКОВА ПАНЕЛЬ: ДЖЕРЕЛО ---
    ui.render_sidebar(df_context=df, file_info=st.session_state.get("file_info", []))
    
    with st.sidebar:
        with st.expander("📂 Джерело даних", expanded=False):
            sb_tab1, sb_tab2 = st.tabs(["Інфо", "Додати"])
            with sb_tab1:
                st.number_input("Рік", 2000, 2100, 2025, key="year_input")
                ui.render_file_grid(st.session_state.get("file_info", []))
                if st.button("🗑️ Очистити все"):
                    st.session_state["data_df"] = pd.DataFrame()
                    st.session_state["file_info"] = []
                    st.rerun()
            
            with sb_tab2:
                st.caption("Додати до поточних даних:")
                
                # --- ВИПРАВЛЕННЯ: Використовуємо форму для уникнення циклічних перезавантажень ---
                with st.form("add_files_form", clear_on_submit=True):
                    add_up = st.file_uploader("Оберіть файли .txt", type=["txt"], accept_multiple_files=True, label_visibility="collapsed")
                    submitted = st.form_submit_button("📥 Завантажити")
                    
                    if submitted and add_up:
                        files = [(f.name, f.read()) for f in add_up]
                        d, i, _ = parser.parse_askue_files(files, datetime.now().year)
                        if not d.empty:
                            merge_new_data(d, i)
                            st.success(f"Додано файлів: {len(files)}")
                            st.rerun()
                
                st.divider()
                
                if st.button("📧 Додати з пошти", key="add_mail"):
                    with st.spinner("Завантаження..."):
                        mail_files, err = mail_utils.fetch_attachments_from_mail(limit=10)
                        if mail_files:
                            d, i, _ = parser.parse_askue_files(mail_files, datetime.now().year)
                            if not d.empty:
                                merge_new_data(d, i)
                                st.toast(f"Додано з пошти: {len(mail_files)}")
                                st.rerun()
                        elif err: st.error(err)
                        else: st.toast("Нових файлів не знайдено.")

    # --- НАВІГАЦІЯ ---
    tabs_map = {
        "tab_graph": "Графіки 30хв", "tab_daily": "Добові",
        "tab_matrix": "Матриця", "tab_pq": "P vs Q", 
        "tab_table": "Таблиця", "tab_report": "📄 Майстер Звітів"
    }
    nav = st.radio("Nav", list(tabs_map.keys()), format_func=lambda x: tabs_map[x], horizontal=True, label_visibility="collapsed")
    st.session_state["nav_tab"] = nav 

    # --- ФІЛЬТРИ ---
    show_filters = (nav != "tab_report")
    if show_filters:
        with st.expander("🔎 Фільтри даних", expanded=True):
            c1, c2, c3 = st.columns([1.5, 3, 1])
            all_m = sorted(df["MeterID"].unique())
            all_t = sorted(df["Type"].unique())
            d_min, d_max = df["Date"].min(), df["Date"].max()
            
            def select_all_meters(all_m):
                for m in all_m: st.session_state[f"chk_m_{m}"] = True
            def clear_all_meters(all_m):
                for m in all_m: st.session_state[f"chk_m_{m}"] = False
            
            with c1:
                with st.container(border=True):
                    h1, h2, h3 = st.columns([4, 1, 1])
                    h1.markdown('<span style="font-size:0.8rem;font-weight:700;color:#0068c9">ЛІЧИЛЬНИКИ</span>', unsafe_allow_html=True)
                    if nav == "tab_matrix":
                        sel_m = [st.radio("Meter", all_m, label_visibility="collapsed")]
                    else:
                        h2.button("☑️", on_click=select_all_meters, args=(all_m,), key="btn_m_all", help="Всі")
                        h3.button("⬜", on_click=clear_all_meters, args=(all_m,), key="btn_m_clr", help="Скинути")
                        sel_m = []
                        m_cols = st.columns(3)
                        for idx, m in enumerate(all_m):
                            k = f"chk_m_{m}"
                            if k not in st.session_state: st.session_state[k] = True
                            if m_cols[idx % 3].checkbox(str(m), key=k): sel_m.append(m)
            with c2:
                with st.container(border=True):
                    sel_t = []
                    cons_list = [t for t in all_t if "потребление" in t.lower() or "споживання" in t.lower()]
                    gen_list = [t for t in all_t if "генерация" in t.lower() or "генерація" in t.lower()]
                    
                    if nav == "tab_matrix":
                        st.markdown('<span style="font-size:0.8rem;font-weight:700;color:#0068c9">ПАРАМЕТР</span>', unsafe_allow_html=True)
                        sel_t = [st.radio("Channel", all_t, label_visibility="collapsed")]
                    elif nav == "tab_pq":
                        st.markdown('<span style="font-size:0.8rem;font-weight:700;color:#0068c9">РЕЖИМ</span>', unsafe_allow_html=True)
                        pq_mode = st.radio("Mode", ["Споживання", "Генерація"], horizontal=True)
                        sel_t = cons_list if pq_mode == "Споживання" else gen_list
                    else:
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            st.caption("Споживання")
                            for item in cons_list:
                                if st.checkbox(item, value=True, key=f"chk_{item}"): sel_t.append(item)
                        with cc2:
                            st.caption("Генерація")
                            for item in gen_list:
                                if st.checkbox(item, value=False, key=f"chk_{item}"): sel_t.append(item)
            with c3:
                with st.container(border=True):
                    st.markdown('<span style="font-size:0.8rem;font-weight:700;color:#0068c9">ПЕРІОД</span>', unsafe_allow_html=True)
                    sel_d = st.date_input("D", [d_min, d_max], label_visibility="collapsed")

        mask = (df["MeterID"].isin(sel_m)) & (df["Type"].isin(sel_t))
        if len(sel_d) == 2: mask &= (df["Date"] >= sel_d[0]) & (df["Date"] <= sel_d[1])
        df_v = df[mask].copy()
    else:
        df_v = df.copy()

    # Розрахунок аномалій
    if not df_v.empty and "is_anomaly" not in df_v.columns:
        grouped = df_v.groupby(["MeterID", "Type"])["Value"]
        df_v["mean"] = grouped.transform("mean")
        df_v["std"] = grouped.transform("std")
        df_v["z_score"] = (df_v["Value"] - df_v["mean"]) / df_v["std"].replace(0, 1)
        df_v["is_anomaly"] = df_v["z_score"].abs() > 3.0

    # === МАЙСТЕР ЗВІТІВ ===
    if nav == "tab_report":
        st.header("📄 Майстер звітів")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            rep_title = c1.text_input("Заголовок звіту", "Звіт з енергоспоживання")
            d_min, d_max = df["Date"].min(), df["Date"].max()
            rep_dates = c2.date_input("Період звіту", [d_min, d_max])
        
        st.subheader("Структура звіту")
        all_meters = sorted(df["MeterID"].unique())
        all_types = sorted(df["Type"].unique())
        
        for i, block in enumerate(st.session_state["report_blocks"]):
            with st.expander(f"{i+1}. {block.get('title', 'Блок')} ({block['type']})", expanded=True):
                c_del, c_conf = st.columns([1, 15])
                c_del.button("❌", key=f"del_{block['id']}", on_click=delete_report_block, args=(i,))
                with c_conf:
                    if block['type'] == 'graph_matrix':
                        mm_col, tt_col = st.columns(2)
                        curr_m = block.get('meters', [all_meters[0]])[0] if block.get('meters') else all_meters[0]
                        idx_m = all_meters.index(curr_m) if curr_m in all_meters else 0
                        sel_m_single = mm_col.radio(f"Лічильник", all_meters, index=idx_m, key=f"mat_m_{block['id']}")
                        
                        curr_t = block.get('types', [all_types[0]])[0] if block.get('types') else all_types[0]
                        idx_t = all_types.index(curr_t) if curr_t in all_types else 0
                        sel_t_single = tt_col.radio(f"Параметр", all_types, index=idx_t, key=f"mat_t_{block['id']}")
                        
                        block["meters"] = [sel_m_single]
                        block["types"] = [sel_t_single]
                        block["title"] = f"Матрица: {sel_m_single} ({sel_t_single.split('(')[0]})"
                    else:
                        block["title"] = st.text_input("Заголовок блоку", block.get("title", ""), key=f"tit_{block['id']}")
                        rc1, rc2 = st.columns(2)
                        with rc1:
                            st.markdown(f"**Лічильники**")
                            current_meters = set(block.get("meters", []))
                            new_meters = []
                            m_cols = st.columns(3)
                            for idx, m in enumerate(all_meters):
                                is_checked = m in current_meters
                                if m_cols[idx % 3].checkbox(str(m), value=is_checked, key=f"b{block['id']}_m_{m}"):
                                    new_meters.append(m)
                            block["meters"] = sorted(new_meters)
                        with rc2:
                            st.markdown(f"**Каналы**")
                            cons_list_R = [tp for tp in all_types if "потребление" in tp.lower() or "споживання" in tp.lower()]
                            gen_list_R = [tp for tp in all_types if "генерация" in tp.lower() or "генерація" in tp.lower()]
                            current_types = set(block.get("types", []))
                            new_types = []
                            tc1, tc2 = st.columns(2)
                            with tc1:
                                st.caption("Споживання")
                                for item in cons_list_R:
                                    is_checked = item in current_types
                                    if st.checkbox(item, value=is_checked, key=f"b{block['id']}_t_{item}"): new_types.append(item)
                            with tc2:
                                st.caption("Генерація")
                                for item in gen_list_R:
                                    is_checked = item in current_types
                                    if st.checkbox(item, value=is_checked, key=f"b{block['id']}_t_{item}"): new_types.append(item)
                            block["types"] = new_types

        st.markdown("---")
        c_add1, c_add2, c_add3, c_add4, c_gen = st.columns(5)
        
        safe_all_meters = all_meters if all_meters else []
        safe_cons_types = [t for t in all_types if "потребление" in t.lower()]
        safe_def_types = safe_cons_types if safe_cons_types else all_types
        safe_mat_m = [safe_all_meters[0]] if safe_all_meters else []
        safe_mat_t = [safe_def_types[0]] if safe_def_types else []
        
        c_add1.button("➕ Статистика", on_click=add_report_block, args=("stats", "Зведена таблиця", safe_all_meters, safe_def_types))
        c_add2.button("➕ Графік 30хв", on_click=add_report_block, args=("graph_30m", "Графік навантаження", safe_all_meters, safe_def_types))
        c_add3.button("➕ Графік Доба", on_click=add_report_block, args=("graph_daily", "Добовий графік", safe_all_meters, safe_def_types))
        c_add4.button("➕ Матриця", on_click=add_report_block, args=("graph_matrix", "Теплова карта", safe_mat_m, safe_mat_t))
        
        if c_gen.button("🚀 Сформувати PDF", type="primary"):
            with st.spinner("Генерація звіту..."):
                report_config = { "title": rep_title, "dates": rep_dates, "blocks": st.session_state["report_blocks"] }
                try:
                    pdf_bytes = export_utils.export_custom_pdf(df, st.session_state["file_info"], report_config)
                    st.session_state["pdf_bytes"] = pdf_bytes
                    st.success("Готово!")
                except Exception as e:
                    st.error(f"Помилка: {e}")

        if st.session_state.get("pdf_bytes"):
            st.download_button("💾 СКАЧАТИ ЗВІТ", st.session_state["pdf_bytes"], "report.pdf", "application/pdf", use_container_width=True)

    # --- ОСНОВНИЙ ДАШБОРД ---
    elif nav != "tab_report":
        if df_v.empty: st.warning("Немає даних для відображення.")
        else:
            cons_act = df_v[df_v["Suffix"] == 2]["Value"].sum(); cons_react = df_v[df_v["Suffix"] == 4]["Value"].sum()
            peak_val = df_v[df_v["Suffix"] == 2]["Value"].max(); 
            if pd.isna(peak_val): peak_val = 0
            cos_phi = cons_act / math.sqrt(cons_act**2 + cons_react**2) if cons_act > 0 else 0
            gen_act = df_v[df_v["Suffix"] == 1]["Value"].sum(); gen_react = df_v[df_v["Suffix"] == 3]["Value"].sum()
            tm = st.session_state["theme_mode"]

            with st.container(border=True):
                k1, k2, k3, k4, k5, k6 = st.columns(6)
                with k1:
                    st.caption(f"Актив (кВт·год)")
                    st.markdown(ui.render_kpi_custom(f"{cons_act:,.0f}".replace(",", " "), "СПОЖИВАННЯ", tm, True), unsafe_allow_html=True)
                with k2:
                    st.caption(f"Реактив (кВАр·год)")
                    st.markdown(ui.render_kpi_custom(f"{cons_react:,.0f}".replace(",", " "), "СПОЖИВАННЯ", tm, True), unsafe_allow_html=True)
                with k3:
                    st.caption(f"Актив (кВт·год)")
                    st.markdown(ui.render_kpi_custom(f"{gen_act:,.0f}".replace(",", " "), "ГЕНЕРАЦІЯ", tm, False), unsafe_allow_html=True)
                with k4:
                    st.caption(f"Реактив (кВАр·год)")
                    st.markdown(ui.render_kpi_custom(f"{gen_react:,.0f}".replace(",", " "), "ГЕНЕРАЦІЯ", tm, False), unsafe_allow_html=True)
                k5.metric("Cos φ", f"{cos_phi:.3f}")
                k6.metric(f"Пік (кВт)", f"{peak_val:,.0f}".replace(",", " "))
            
            h = st.session_state["chart_h"]; w = st.session_state["line_w"]
            l_pos = st.session_state.get("legend_pos_val", "top")
            bw = st.session_state.get("bw_mode", False)
            pl_template = "plotly_dark" if st.session_state.get("theme_mode") == "Dark" else "plotly_white"
            ap = df_v["Suffix"].isin([1, 2]).any(); rp = df_v["Suffix"].isin([3, 4]).any()
            units = " (кВт)" if ap and not rp else " (кВАр)" if rp and not ap else " (кВт / кВАр)"
            common_labels = {"x": "Дата і час", "y": "Значення" + units, "bw": bw}
            current_palette = st.session_state.get("palette_name", "Default")
            cust_colors = st.session_state.get("custom_colors") if current_palette == "Custom" else None
            
            if nav == "tab_graph":
                st.caption("ℹ️ **Графік профілю потужності (30 хв).**")
                res_val = st.session_state.get("resample_val", "30T")
                res = res_val.replace("H", "h") if "H" in res_val else res_val
                anom = st.session_state["show_anom"]
                if res == "30T": plot_df = df_v.copy()
                else:
                    grouped = df_v.set_index("DateTime").groupby(["MeterID", "Type"])["Value"]
                    plot_df = grouped.resample(res).agg(['min', 'max', 'mean']).reset_index()
                    plot_df = plot_df.rename(columns={'mean': 'Value', 'min': 'min_val', 'max': 'max_val'})
                    if "is_anomaly" in df_v.columns:
                        try:
                            anoms = df_v.set_index("DateTime").groupby(["MeterID", "Type"])["is_anomaly"].resample(res).max().reset_index()
                            anoms["is_anomaly"] = anoms["is_anomaly"].fillna(0).astype(bool)
                            plot_df = pd.merge(plot_df, anoms, on=["DateTime", "MeterID", "Type"], how="left")
                        except: pass
                fig = graph_utils.plot_30min_graph(plot_df, h, w, st.session_state["show_pts"], anom, st.session_state["chart_type"], l_pos, bw, common_labels, pl_template, palette_name=current_palette, custom_colors=cust_colors)
                ev = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="box")
                sel_range = None
                if ev and ev.get("selection") and ev["selection"].get("box"):
                    xs = ev["selection"]["box"][0].get("x", [])
                    if len(xs) >= 2: sel_range = [pd.to_datetime(xs[0]), pd.to_datetime(xs[1])]
                if sel_range:
                    stats, tr = selection_utils.compute_detailed_selection_stats(df_v, sel_range)
                    if stats: st.markdown(ui.generate_detailed_stats_html(stats, tr), unsafe_allow_html=True)

            elif nav == "tab_daily": 
                st.caption("ℹ️ **Добове споживання.**")
                show_v = st.session_state.get("show_vals", False)
                fig = graph_utils.plot_daily_bar(df_v, h, l_pos, common_labels, pl_template, palette_name=current_palette, custom_colors=cust_colors, show_vals=show_v)
                st.plotly_chart(fig, use_container_width=True)

            elif nav == "tab_matrix": 
                st.caption("ℹ️ **Теплова карта.**")
                matrix_palette = st.session_state.get("heatmap_palette_name", "Default")
                fig = graph_utils.plot_heatmap(df_v, h, st.session_state.get("show_vals", False), common_labels, pl_template, palette_name=matrix_palette)
                st.plotly_chart(fig, use_container_width=True)

            elif nav == "tab_pq": 
                st.caption("ℹ️ **P vs Q.**")
                pq_lbl = {"p": "P (Активна)", "q": "Q (Реактивна)", "bw": bw}
                show_lbls = st.session_state.get("show_pq_labels", False)
                fig = graph_utils.plot_pq_scatter(df_v, h, True, l_pos, bw, pq_lbl, pl_template, palette_name=current_palette, custom_colors=cust_colors, show_labels=show_lbls)
                st.plotly_chart(fig, use_container_width=True)
            
            elif nav == "tab_table":
                st.caption("ℹ️ **Таблиця даних.**")
                c_mode, _ = st.columns([1, 3])
                table_mode = c_mode.radio("Формат даних:", ["Список (Raw)", "Зведена (Pivot)"], horizontal=True)
                
                col_map = {"DateTime": "Дата та Час", "MeterID": "Лічильник", "Type": "Параметр", "Value": "Значення"}
                
                if table_mode == "Список (Raw)":
                    cols_to_show = ["DateTime", "MeterID", "Type", "Value"]
                    display_df = df_v[cols_to_show].copy().rename(columns=col_map)
                    include_idx = False
                else:
                    pivot = df_v.pivot_table(index="DateTime", columns=["MeterID", "Type"], values="Value")
                    pivot.columns = [f"{m} - {t.split('(')[0]}" for m, t in pivot.columns]
                    pivot.index.name = col_map["DateTime"]
                    display_df = pivot
                    include_idx = True
                
                st.dataframe(display_df, use_container_width=True, height=600)
                st.download_button("📥 Завантажити Excel", export_utils.export_excel_bytes(display_df, include_index=include_idx), "data.xlsx")

    ui.render_footer()
    ui.render_chat_html_js()
    fab_container = st.container()
    with fab_container:
        st.markdown('<div id="chat-fab-container"></div>', unsafe_allow_html=True)
        if st.button("💬", key="fab_chat_toggle"):
            st.session_state.is_chat_open = not st.session_state.is_chat_open
            st.rerun()

    if st.session_state.is_chat_open:
        chat_content_container = st.container()
        with chat_content_container:
            st.markdown('<div id="streamlit-chat-content"></div>', unsafe_allow_html=True)
            with st.expander("Налаштування ШІ"):
                api_key = st.secrets.get("GOOGLE_API_KEY")
                if not api_key: st.error("Введіть API ключ")
                st.session_state["model_name"] = st.selectbox("Model", ["gemini-1.5-flash", "gemini-1.5-pro"])
            messages_container = st.container(height=300)
            for msg in st.session_state.get("messages", []):
                messages_container.chat_message(msg["role"]).write(msg["content"])
            if prompt := st.chat_input("Ваше питання..."):
                if not api_key: st.error("Введіть API ключ")
                else:
                    st.session_state["messages"].append({"role": "user", "content": prompt})
                    with st.spinner("Аналізую..."):
                        from ai_utils import ai_generate_reply
                        history = st.session_state.get("messages", [])
                        response = ai_generate_reply(api_key, st.session_state["model_name"], history)
                        st.session_state["messages"].append({"role": "assistant", "content": response})
                        st.rerun()