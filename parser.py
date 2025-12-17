import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

@st.cache_data(show_spinner=False)
def parse_askue_files(files_data):
    """
    Парсить файли. 
    files_data - список кортежів: (name, bytes, context_date)
    """
    all_rows = []
    file_info_list = []
    error_files = []

    for item in files_data:
        # Розпаковка: якщо передано 2 елементи, дату ставимо поточну
        if len(item) == 3:
            name, b, context_date = item
        else:
            name, b = item
            context_date = datetime.now()

        try:
            size_kb = len(b) / 1024
            try: text = b.decode("utf-8")
            except UnicodeDecodeError: text = b.decode("cp1251", errors="ignore")
            file_info_list.append({"name": name, "size": f"{size_kb:.1f} KB"})
        except Exception as e:
            error_files.append(f"{name}: Помилка читання ({str(e)})")
            continue

        lines = text.splitlines()
        file_date = None
        
        # 1. Пошук дати в заголовку
        if lines:
            header = lines[0]
            if "30917" in header:
                parts = header.split(":")
                if len(parts) >= 2:
                    date_part = parts[1].strip()
                    try:
                        # ВАРІАНТ А: 6 цифр (YYMMDD) - Рік є
                        if len(date_part) == 6 and date_part.isdigit():
                            day = int(date_part[4:6])
                            month = int(date_part[2:4])
                            year = 2000 + int(date_part[0:2])
                            file_date = datetime(year, month, day).date()
                            
                        # ВАРІАНТ Б: 4 цифри (MMDD) - Рік з контексту
                        elif len(date_part) == 4 and date_part.isdigit():
                            month = int(date_part[:2])
                            day = int(date_part[2:])
                            
                            # Базовий рік - рік отримання файлу
                            year = context_date.year
                            
                            # Корекція на стику років
                            # Якщо файл за Грудень (12), а зараз Січень (1) -> це минулий рік
                            if month == 12 and context_date.month == 1:
                                year -= 1
                            # Якщо файл за Січень (1), а зараз Грудень (12) -> це майбутній рік (рідко)
                            elif month == 1 and context_date.month == 12:
                                year += 1
                                
                            file_date = datetime(year, month, day).date()
                    except:
                        pass
        
        if not file_date:
            error_files.append(f"{name}: Дата не знайдена в заголовку")
            continue

        # 2. Парсинг рядків
        for line in lines:
            if line.startswith("(") and "):" in line:
                try:
                    parts = line.split(":")
                    code_raw = parts[0].replace("(", "").replace(")", "")
                    if len(code_raw) < 5: continue
                    
                    mid = code_raw[:5]
                    try: suf = int(code_raw[-1])
                    except: continue
                    if suf not in [1, 2, 3, 4]: continue

                    t_lbl = {
                        1: "Активная генерация(1) (кВт)",
                        2: "Активное потребление(2) (кВт)",
                        3: "Реактивная генерация(3) (кВАр)",
                        4: "Реактивное потребление(4) (кВАр)"
                    }.get(suf, "Unknown")

                    for i in range(48):
                        data_index = i + 2 
                        val = 0.0
                        if data_index < len(parts):
                            raw_val = parts[data_index].replace(",", ".").strip()
                            if raw_val: val = float(raw_val)
                        
                        ts = datetime.combine(file_date, datetime.min.time()) + timedelta(minutes=i*30)
                        
                        all_rows.append({
                            "DateTime": ts, "Date": file_date, "Time": ts.time(),
                            "MeterID": mid, "Type": t_lbl, "Suffix": suf, "Value": val
                        })

                except Exception: pass
    
    df = pd.DataFrame(all_rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["DateTime", "MeterID", "Type"], keep="last")
        df = df.sort_values("DateTime")

    return df, file_info_list, error_files