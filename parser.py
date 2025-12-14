import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

@st.cache_data(show_spinner=False)
def parse_askue_files(file_objs_bytes, selected_year):
    """
    Парсит файлы макета 30917.
    
    Структура строки данных:
    (CODE):TOTAL_SUM:VAL1:VAL2:...:VAL48
    
    Алгоритм:
    1. Индекс 0: Код счетчика
    2. Индекс 1: Сумма за сутки (используем для проверки целостности)
    3. Индекс 2..49: Получасовые значения
    
    Возвращает: DataFrame, список файлов, список ошибок/предупреждений.
    """
    all_rows = []
    file_info_list = []
    error_files = []

    for name, b in file_objs_bytes:
        try:
            size_kb = len(b) / 1024
            
            try:
                text = b.decode("utf-8")
            except UnicodeDecodeError:
                text = b.decode("cp1251", errors="ignore")
                
            file_info_list.append({"name": name, "size": f"{size_kb:.1f} KB"})
        except Exception as e:
            error_files.append(f"{name}: Ошибка чтения файла ({str(e)})")
            continue

        lines = text.splitlines()
        file_date = None
        
        # --- 1. ПАРСИНГ ЗАГОЛОВКА ---
        # Пример: ((//30917:1101:000057:++  -> 1 ноября
        if lines:
            header = lines[0]
            if "30917" in header:
                parts = header.split(":")
                if len(parts) >= 2:
                    date_part = parts[1].strip()
                    try:
                        # ВАРИАНТ А: 6 цифр (YYMMDD), например 250101
                        if len(date_part) == 6 and date_part.isdigit():
                            day = int(date_part[4:6])
                            month = int(date_part[2:4])
                            year = 2000 + int(date_part[0:2])
                            file_date = datetime(year, month, day).date()
                            
                        # ВАРИАНТ Б: 4 цифры (MMDD), например 1101
                        # Год берем из интерфейса
                        elif len(date_part) == 4 and date_part.isdigit():
                            month = int(date_part[:2])
                            day = int(date_part[2:])
                            file_date = datetime(selected_year, month, day).date()
                    except:
                        pass
        
        if not file_date:
            error_files.append(f"{name}: Дата не найдена в заголовке")
            continue

        # --- 2. ПАРСИНГ СТРОК С ДАННЫМИ ---
        for line_idx, line in enumerate(lines):
            if line.startswith("(") and "):" in line:
                try:
                    parts = line.split(":")
                    
                    # parts[0] -> (Code)
                    code_raw = parts[0].replace("(", "").replace(")", "")
                    if len(code_raw) < 5: continue
                    
                    mid = code_raw[:5] # ID счетчика
                    try:
                        suf = int(code_raw[-1]) # Суффикс канала
                    except:
                        continue
                    
                    if suf not in [1, 2, 3, 4]: continue

                    t_lbl = {
                        1: "Активная генерация(1) (кВт)",
                        2: "Активное потребление(2) (кВт)",
                        3: "Реактивная генерация(3) (кВАр)",
                        4: "Реактивное потребление(4) (кВАр)"
                    }.get(suf, "Unknown")

                    # --- ПРОВЕРОЧНАЯ СУММА (parts[1]) ---
                    expected_sum = 0.0
                    if len(parts) > 1:
                        try:
                            expected_sum = float(parts[1].replace(",", "."))
                        except:
                            pass
                    
                    calculated_sum = 0.0
                    row_data_buffer = []

                    # Цикл по 48 получасовкам
                    # ВАЖНО: Данные начинаются с индекса 2 (0=Код, 1=Сумма)
                    for i in range(48):
                        data_index = i + 2 
                        
                        if data_index < len(parts):
                            raw_val = parts[data_index].replace(",", ".").strip()
                            if not raw_val: 
                                val = 0.0
                            else:
                                val = float(raw_val)
                        else:
                            val = 0.0
                        
                        calculated_sum += val
                        
                        ts = datetime.combine(file_date, datetime.min.time()) + timedelta(minutes=i*30)
                        
                        row_data_buffer.append({
                            "DateTime": ts, 
                            "Date": file_date, 
                            "Time": ts.time(),
                            "MeterID": mid, 
                            "Type": t_lbl,
                            "Suffix": suf, 
                            "Value": val
                        })

                    # --- ВАЛИДАЦИЯ ---
                    # Если разница между суммой в файле и суммой распаршенных значений > 1.0,
                    # выдаем предупреждение, но данные сохраняем.
                    if abs(calculated_sum - expected_sum) > 1.0 and expected_sum > 0:
                        error_files.append(f"Warn: {name} ({mid}-{suf}) SumMismatch: File={expected_sum:.1f}, Calc={calculated_sum:.1f}")

                    all_rows.extend(row_data_buffer)

                except Exception as e:
                    # Можно включить для детальной отладки
                    # error_files.append(f"Error parsing line in {name}: {e}")
                    pass
    
    df = pd.DataFrame(all_rows)
    
    if not df.empty:
        df = df.drop_duplicates(subset=["DateTime", "MeterID", "Type"], keep="last")
        df = df.sort_values("DateTime")

    return df, file_info_list, error_files