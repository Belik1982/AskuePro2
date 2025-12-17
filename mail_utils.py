import imaplib
import email
from email.header import decode_header
import email.utils 
import streamlit as st
from datetime import datetime

def decode_mime_words(s):
    if not s: return ""
    try:
        decoded_list = decode_header(s)
        result = []
        for content, encoding in decoded_list:
            if isinstance(content, bytes):
                if encoding:
                    try: result.append(content.decode(encoding))
                    except: result.append(content.decode('utf-8', errors='ignore'))
                else:
                    result.append(content.decode('utf-8', errors='ignore'))
            elif isinstance(content, str):
                result.append(content)
        return "".join(result)
    except Exception:
        return str(s)

def fetch_attachments_from_mail(limit=15):
    """
    Повертає список: [(filename, content_bytes, email_date), ...]
    """
    try:
        cfg = st.secrets["email"]
        IMAP_SERVER = cfg["imap_server"]
        EMAIL_USER = cfg["email_user"]
        EMAIL_PASS = cfg["email_password"]
        EMAIL_PORT = int(cfg.get("email_port", 993))
    except Exception:
        return [], "Помилка: Не заповнено файл .streamlit/secrets.toml"

    found_files = []
    
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, EMAIL_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        
        status, _ = mail.select("INBOX")
        if status != "OK": return [], "Не вдалося відкрити INBOX."

        # Шукаємо "30917" у темі листа
        search_criteria = '(SUBJECT "30917")'
        status, messages = mail.search(None, search_criteria)
        
        if status != "OK" or not messages[0]:
            return [], "Листів з темою '30917' не знайдено."

        email_ids = messages[0].split()
        latest_email_ids = email_ids[-limit:] 
        
        for e_id in reversed(latest_email_ids):
            res, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    try:
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Отримуємо дату листа
                        email_date_str = msg.get("Date")
                        if email_date_str:
                            email_dt = email.utils.parsedate_to_datetime(email_date_str)
                            if email_dt.tzinfo is not None:
                                email_dt = email_dt.replace(tzinfo=None)
                        else:
                            email_dt = datetime.now()

                        subject = decode_mime_words(msg.get("Subject"))
                        if "30917" not in subject: continue

                        for part in msg.walk():
                            if part.get_content_maintype() == 'multipart': continue
                            if part.get('Content-Disposition') is None: continue

                            filename = part.get_filename()
                            if filename:
                                filename = decode_mime_words(filename)
                                if filename.lower().endswith('.txt'):
                                    content = part.get_payload(decode=True)
                                    if content:
                                        found_files.append((filename, content, email_dt))
                                        
                    except Exception as e:
                        print(f"Error parsing email {e_id}: {e}")
                        continue

        mail.close()
        mail.logout()
        
        if not found_files:
            return [], "Листи знайдено, але вкладень .txt немає."
            
        return found_files, None

    except Exception as e:
        return [], f"Помилка пошти: {str(e)}"