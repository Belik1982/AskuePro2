import imaplib
import email
from email.header import decode_header
import streamlit as st
import os

def decode_mime_words(s):
    """
    Декодирует тему письма и имена файлов (учитывает кириллицу и спецсимволы).
    """
    if not s: return ""
    try:
        decoded_list = decode_header(s)
        result = []
        for content, encoding in decoded_list:
            if isinstance(content, bytes):
                if encoding:
                    try:
                        result.append(content.decode(encoding))
                    except LookupError:
                        try: result.append(content.decode('cp1251'))
                        except: result.append(content.decode('utf-8', errors='ignore'))
                    except UnicodeDecodeError:
                         result.append(content.decode('cp1251', errors='ignore'))
                else:
                    # Если кодировка не указана
                    result.append(content.decode('utf-8', errors='ignore'))
            elif isinstance(content, str):
                result.append(content)
        return "".join(result)
    except Exception:
        return str(s)

def fetch_attachments_from_mail(limit=15):
    """
    Подключается к почте и ищет вложения .txt.
    Фильтр: Игнорируем отправителя, ищем "30917" в любой части темы.
    """
    try:
        cfg = st.secrets["email"]
        IMAP_SERVER = cfg["imap_server"]
        EMAIL_USER = cfg["email_user"]
        EMAIL_PASS = cfg["email_password"]
        EMAIL_PORT = int(cfg.get("email_port", 993))
        # allowed_sender больше не используется для фильтрации поиска
    except Exception:
        return [], "Ошибка: Не заполнен файл .streamlit/secrets.toml"

    found_files = []
    
    try:
        # 1. Подключение
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, EMAIL_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        
        status, _ = mail.select("INBOX")
        if status != "OK":
            return [], "Не удалось открыть папку входящие."

        # 2. Поиск писем (Широкий фильтр)
        # Ищем письма, где в теме ЕСТЬ подстрока "30917". Отправитель любой.
        search_criteria = '(SUBJECT "30917")'

        status, messages = mail.search(None, search_criteria)
        
        if status != "OK":
            return [], "Ошибка при выполнении поиска."

        email_ids = messages[0].split()
        
        if not email_ids:
            return [], "Писем с темой, содержащей '30917', не найдено."

        # Берем последние письма (с конца списка)
        latest_email_ids = email_ids[-limit:] 
        
        for e_id in reversed(latest_email_ids):
            # Скачиваем структуру письма
            res, msg_data = mail.fetch(e_id, "(RFC822)")
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    try:
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Дополнительная проверка темы после декодирования (для надежности)
                        subject = decode_mime_words(msg.get("Subject"))
                        
                        # Если вдруг сервер ошибся, проверяем Python-ом
                        if "30917" not in subject:
                            continue

                        # 3. Перебор вложений
                        for part in msg.walk():
                            if part.get_content_maintype() == 'multipart':
                                continue
                            if part.get('Content-Disposition') is None:
                                continue

                            filename = part.get_filename()
                            if filename:
                                filename = decode_mime_words(filename)
                                
                                # Берем только .txt
                                if filename.lower().endswith('.txt'):
                                    content = part.get_payload(decode=True)
                                    if content:
                                        found_files.append((filename, content))
                                        
                    except Exception as e:
                        print(f"Error parsing email {e_id}: {e}")
                        continue

        mail.close()
        mail.logout()
        
        if not found_files:
            return [], "Письма с '30917' найдены, но вложений .txt в них нет."
            
        return found_files, None

    except imaplib.IMAP4.error as e:
        return [], f"Ошибка входа: {e}"
    except Exception as e:
        return [], f"Ошибка соединения: {str(e)}"