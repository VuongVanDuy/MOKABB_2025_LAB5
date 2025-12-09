import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import zipfile
from pathlib import Path

def send_gmail_with_attachment(sender_email, sender_password, recipient_email, subject, message, attachment_path=None):
    
    try:
        # Создаем сообщение
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Добавляем текст письма
        msg.attach(MIMEText(message, 'plain'))
        
        # Прикрепляем файл, если указан путь
        if attachment_path:
            if not os.path.exists(attachment_path):
                print(f"Ошибка: файл {attachment_path} не найден")
                return False
            
            # Открываем файл в бинарном режиме
            with open(attachment_path, 'rb') as attachment:
                # Создаем объект MIMEBase
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            # Кодируем файл в base64
            encoders.encode_base64(part)
            
            # Получаем имя файла из пути
            filename = os.path.basename(attachment_path)
            
            # Добавляем заголовки для вложения
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}',
            )
            
            # Прикрепляем файл к сообщению
            msg.attach(part)
            print(f"Файл {filename} прикреплен к письму")
        
        # Подключаемся к серверу Gmail
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Включаем шифрование
        
        # Логинимся
        server.login(sender_email, sender_password)
        
        # Отправляем письмо
        server.send_message(msg)
        
        # Закрываем соединение
        server.quit()
        
        print("Письмо успешно отправлено!")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("Ошибка аутентификации. Проверьте email и пароль приложения.")
        return False
    except smtplib.SMTPException as e:
        print(f"Ошибка SMTP: {e}")
        return False
    except FileNotFoundError as e:
        print(f"Файл не найден: {e}")
        return False
    except Exception as e:
        print(f"Ошибка при отправке письма: {e}")
        return False

def create_zip_zipfile(source_folder, output_zip):
    source_path = Path(source_folder)
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_folder):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(source_path.parent)
                zipf.write(file_path, arcname)
    
    print(f"Архив создан: {output_zip}")
    return True

if __name__ == "__main__":

    sender_email = "mokaiv118@gmail.com"
    sender_password = "xxxx xxxx xxxx"  # пароль приложения
    recipient_email = "mokaiv118@gmail.com"
    subject = "5 секунд"
    message = "Привет! Это письмо содержит файл с 5ю секундами."
    create_zip_zipfile("data_collection", "data_collection.zip")
    
    print("Пример 1: Отправка письма с одним вложением")
    file_path = "data_collection.zip"  
    
    send_gmail_with_attachment(
        sender_email=sender_email,
        sender_password=sender_password,
        recipient_email=recipient_email,
        subject=subject,
        message=message,
        attachment_path=file_path
    )
