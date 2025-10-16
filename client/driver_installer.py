import requests
import os
import tempfile
import subprocess
import logging


class DriverInstaller:
    def __init__(self, server_url):
        self.server_url = server_url
        self.temp_dir = tempfile.gettempdir()
        self.logger = logging.getLogger(__name__)

    def download_driver(self, hardware_id):
        try:
            response = requests.get(f"{self.server_url}/drivers/{hardware_id}")
            if response.status_code != 200:
                self.logger.error(f"❌ Драйвер {hardware_id} не найден")
                return None

            driver_info = response.json()
            file_url = f"{self.server_url}/static/{hardware_id}.exe"

            file_response = requests.get(file_url, stream=True)
            if file_response.status_code == 200:
                file_path = os.path.join(self.temp_dir, f"{hardware_id}.exe")
                with open(file_path, 'wb') as f:
                    for chunk in file_response.iter_content(chunk_size=8192):
                        f.write(chunk)

                self.logger.info(f"✅ Драйвер скачан: {file_path}")
                return file_path
            else:
                self.logger.error(f"❌ Не удалось скачать файл драйвера")
                return None

        except Exception as e:
            self.logger.error(f"❌ Ошибка скачивания: {e}")
            return None

    def install_driver(self, file_path):
        try:
            self.logger.info(f"🔄 Устанавливаем драйвер: {file_path}")

            if platform.system() == "Windows":
                process = subprocess.Popen(
                    [file_path, '/S', '/quiet'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                stdout, stderr = process.communicate(timeout=300)

                if process.returncode == 0:
                    self.logger.info("✅ Драйвер успешно установлен")
                    return True
                else:
                    self.logger.error(f"❌ Ошибка установки: {stderr}")
                    return False
            else:
                self.logger.error("❌ Автоматическая установка только для Windows")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("❌ Таймаут установки драйвера")
            return False
        except Exception as e:
            self.logger.error(f"❌ Ошибка установки: {e}")
            return False

    def send_installation_report(self, computer_name, hardware_id, status, message=""):
        try:
            report_data = {
                "computer_name": computer_name,
                "hardware_id": hardware_id,
                "status": status,
                "message": message
            }

            response = requests.post(
                f"{self.server_url}/installation/report",
                json=report_data
            )

            if response.status_code == 200:
                self.logger.info("✅ Отчет отправлен на сервер")
                return True
            else:
                self.logger.error(f"❌ Ошибка отправки отчета: {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки отчета: {e}")
            return False

    def install_driver(self, hardware_id, driver_info, computer_name):
        try:
            driver_path = self.download_driver(hardware_id)
            if not driver_path:
                self.send_installation_report(
                    computer_name, hardware_id,
                    "failed", "Не удалось скачать драйвер"
                )
                return False

            success = self.install_driver_file(driver_path)

            if success:
                self.send_installation_report(
                    computer_name, hardware_id,
                    "success", f"Драйвер {driver_info['available_driver']} установлен"
                )
            else:
                self.send_installation_report(
                    computer_name, hardware_id,
                    "failed", "Ошибка установки драйвера"
                )

            try:
                if os.path.exists(driver_path):
                    os.remove(driver_path)
            except:
                pass

            return success

        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка установки: {e}")
            self.send_installation_report(
                computer_name, hardware_id,
                "failed", f"Критическая ошибка: {str(e)}"
            )
            return False