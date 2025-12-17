from google import genai
from google.genai import types
import pandas as pd

def prepare_ai_context(df: pd.DataFrame, file_info: list) -> str:
    """
    Готовит контекст с ПОЧАСОВОЙ детализацией для точного анализа пиков и аномалий.
    """
    if df.empty:
        return "Данные отсутствуют."

    # 1. Информация о файлах
    files_str = ", ".join([f['name'] for f in file_info[:10]])
    if len(file_info) > 10: files_str += "..."

    # 2. Общая статистика (Сумма, Пик, Среднее)
    # Это помогает ИИ быстро понять масштаб цифр
    stats = df.groupby(['MeterID', 'Type'])['Value'].agg(['sum', 'max', 'mean']).reset_index()
    stats['sum'] = stats['sum'].round(0)
    stats['max'] = stats['max'].round(2)
    stats['mean'] = stats['mean'].round(2)
    
    # 3. ПОЧАСОВАЯ АГРЕГАЦИЯ (Core Data)
    # Группируем по часу, суммируя 30-минутные интервалы (получаем кВт*ч за час)
    # Используем copy(), чтобы не влиять на основной df
    df_work = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_work['DateTime']):
        df_work['DateTime'] = pd.to_datetime(df_work['DateTime'])

    hourly = df_work.set_index('DateTime').groupby(['MeterID', 'Type'])['Value'].resample('1h').sum().reset_index()
    
    # Оптимизация формата для экономии токенов
    # Убираем секунды, округляем значения
    hourly['DateTime'] = hourly['DateTime'].dt.strftime('%Y-%m-%d %H:%M')
    hourly['Value'] = hourly['Value'].round(2)
    
    # Преобразуем в CSV (самый экономный формат для ИИ)
    csv_data = hourly.to_csv(index=False)
    
    system_prompt = f"""
    ТЫ - ЭКСПЕРТ-ЭНЕРГЕТИК. Твоя цель - найти аномалии, пики и неэффективность.
    
    ДАННЫЕ:
    Файлы: {files_str}
    
    СВОДКА (Общие показатели):
    {stats.to_markdown(index=False)}
    
    ДЕТАЛЬНЫЕ ДАННЫЕ (ПОЧАСОВЫЕ ЗНАЧЕНИЯ):
    {csv_data}
    
    ИНСТРУКЦИЯ:
    1. Ищи конкретные часы пиковой нагрузки. Укажи дату и время.
    2. Проверь наличие аномального потребления ночью (когда производство должно стоять).
    3. Сравнивай показатели между счетчиками, если их несколько.
    4. Отвечай на украинском языке. Будь краток и используй списки.
    """
    return system_prompt

def ai_generate_reply(api_key: str, model_name: str, history: list):
    """
    Генерация ответа через библиотеку google-genai (v2.0 support).
    """
    if not api_key: return "Помилка: Немає API ключа."
    
    try:
        client = genai.Client(api_key=api_key)
        
        gemini_contents = []
        
        for msg in history:
            role = "model" if msg["role"] == "assistant" else "user"
            # В истории Streamlit мы храним 'model' как 'assistant'
            if msg["role"] == "model": role = "model" 
            
            part = types.Part.from_text(text=str(msg["content"]))
            content = types.Content(role=role, parts=[part])
            gemini_contents.append(content)
            
        generate_content_config = types.GenerateContentConfig(
            temperature=0.3, # Понижаем температуру для более точного анализа цифр
            top_p=0.95,
            max_output_tokens=4096,
        )

        response = client.models.generate_content(
            model=model_name,
            contents=gemini_contents,
            config=generate_content_config
        )
        
        return response.text
        
    except Exception as e:
        return f"AI Error: {str(e)}"