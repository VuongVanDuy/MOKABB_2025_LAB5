import os
import zipfile
import smtplib
from email.message import EmailMessage
from pathlib import Path


class MailZipClient:
    """
    Классы используются для:
    - Сожмите папку в ZIP-файл.
    - Отправка письма по SMTP (в теме — команда, в теле — текст)
    - Читайте электронные письма через IMAP, получайте тему/текст/вложения.

    Пример темы содержит команду: "RUN_BACKUP"
    В теле письмах — полезная информация.
    """

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        default_from: str | None = None,
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.default_from = default_from or username

    def zip_folder(self, folder_path: str, zip_path: str) -> str:
        """
        Сжать весь путь к папке в файл zip_path.
        Возвращает путь к zip-файлу.
        """
        folder_path = os.path.abspath(folder_path)
        zip_path = os.path.abspath(zip_path)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, start=folder_path)
                    zipf.write(abs_path, arcname=rel_path)

        return zip_path

    def send_email_with_attachment(
        self,
        to_addrs: list[str],
        subject: str,
        body: str,
        attachment_paths: list[str] | None = None,
        from_addr: str | None = None,
    ):
        """
        Отправка электронной почты через SMTP.
        В теме письма — команда.
        В теле — полезная информация.
        Вложения — пути_вложений.
        """
        msg = EmailMessage()
        msg["From"] = from_addr or self.default_from
        msg["To"] = ", ".join(to_addrs)
        msg["Subject"] = subject
        msg.set_content(body)

        attachment_paths = attachment_paths or []
        for path in attachment_paths:
            file_path = Path(path)
            if not file_path.is_file():
                print(f"Файл вложения не найден: {file_path}")
                continue

            with open(file_path, "rb") as f:
                file_data = f.read()

            # đơn giản: luôn dùng octet-stream
            msg.add_attachment(
                file_data,
                maintype="application",
                subtype="octet-stream",
                filename=file_path.name,
            )

        with smtplib.SMTP_SSL(self.smtp_server, 25) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.username, self.password)
            server.send_message(msg)
            print("Письмо отправлено.")
