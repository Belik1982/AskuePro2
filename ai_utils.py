import pandas as pd
import google.generativeai as genai

def prepare_ai_system_prompt(df: pd.DataFrame, file_info: list, lang: str = "ru"):
    schema = "- DateTime\n- MeterID\n- Type\n- Value (avg 1h)"
    files_str = ", ".join([f["name"] for f in file_info[:30]])
    
    try:
        ai_df = df.copy()
        ai_df.set_index("DateTime", inplace=True)
        # Ресемплинг до 1 часа для ИИ
        resampled = ai_df.groupby(["MeterID", "Type"])["Value"].resample("1H").mean().reset_index()
        resampled["Value"] = resampled["Value"].round(2)
        sample_csv = resampled.to_csv(index=False)
        data_note = "Note: Data is resampled to 1-hour average."
    except:
        sample_csv = df.head(500).to_csv(index=False)
        data_note = "Note: Raw 30-min data (truncated)."

    system_prompt = (
        "You are an expert energy analyst.\n"
        f"DATA SCHEMA:\n{schema}\n"
        f"FILES: {files_str}\n"
        f"{data_note}\n\n"
        "Analyze consumption/generation. Look for anomalies, peak hours, and trends.\n"
        "CSV DATA:\n" + sample_csv
    )
    return system_prompt, sample_csv

def ai_generate_reply(api_key: str, model_name: str, messages: list):
    try:
        genai.configure(api_key=api_key)
        # Формирование истории для Gemini
        gemini_history = []
        for msg in messages:
            role = "user" if msg.get("role") == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg.get("content", "")]})
            
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(gemini_history)
        return response.text
    except Exception as e:
        return f"AI Error: {str(e)}"