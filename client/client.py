import requests
import time
import logging
from hardware_detector import HardwareDetector
from driver_installer import DriverInstaller
import json
import sys


class DriverClient:
    def __init__(self, server_url="http://localhost:8000"):
        self.server_url = server_url
        self.computer_name = None
        self.hardware_info = None

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('driver_client.log', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def detect_hardware(self):
        self.logger.info("[SCAN] Определяем оборудование...")
        detector = HardwareDetector()
        self.hardware_info = detector.get_all_hardware()
        self.computer_name = detector.get_computer_name()

        self.logger.info(f"[PC] Компьютер: {self.computer_name}")
        self.logger.info(f"[CPU] Процессор: {self.hardware_info['cpu']}")
        self.logger.info(f"[GPU] Видеокарта: {self.hardware_info['gpu']}")
        self.logger.info(f"[MB] Мат. плата: {self.hardware_info['motherboard']}")

        return self.hardware_info

    def register_computer(self):
        self.logger.info("[REG] Регистрируем компьютер на сервере...")

        registration_data = {
            "name": self.computer_name,
            "ip": self.hardware_info["ip_address"],
            "cpu": self.hardware_info["cpu"],
            "gpu": self.hardware_info["gpu"],
            "motherboard": self.hardware_info["motherboard"],
            "network_adapters": self.hardware_info["network_adapters"]
        }

        try:
            response = requests.post(
                f"{self.server_url}/computers/register",
                json=registration_data,
                timeout=10
            )

            if response.status_code == 200:
                self.logger.info("[OK] Компьютер успешно зарегистрирован")
                return True
            else:
                self.logger.error(f"[ERROR] Ошибка регистрации: {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"[ERROR] Ошибка подключения к серверу: {e}")
            return False

    def check_updates(self):
        self.logger.info("[UPDATE] Проверяем доступные обновления...")

        try:
            response = requests.get(
                f"{self.server_url}/computers/{self.computer_name}/check-updates",
                timeout=10
            )

            if response.status_code == 200:
                updates = response.json()
                available_updates = updates.get("available_updates", [])

                if available_updates:
                    self.logger.info(f"[DRIVER] Найдено {len(available_updates)} обновлений")
                    for update in available_updates:
                        self.logger.info(f"  - {update['hardware']}: {update['available_driver']} v{update['version']}")
                else:
                    self.logger.info("[OK] Все драйверы актуальны")

                return available_updates
            else:
                self.logger.error(f"[ERROR] Ошибка проверки обновлений: {response.text}")
                return []

        except Exception as e:
            self.logger.error(f"[ERROR] Ошибка подключения: {e}")
            return []

    def install_driver(self, hardware_id, driver_info):
        self.logger.info(f"[DOWNLOAD] Устанавливаем драйвер: {driver_info['available_driver']}")

        installer = DriverInstaller(self.server_url)
        success = installer.install_driver(hardware_id, driver_info, self.computer_name)

        return success

    def run_auto_update(self):
        self.logger.info("[START] Запуск клиента управления драйверами")

        if not self.detect_hardware():
            self.logger.error("[ERROR] Не удалось определить оборудование")
            return

        if not self.register_computer():
            self.logger.error("[ERROR] Не удалось зарегистрировать компьютер")
            return

        updates = self.check_updates()

        for update in updates:
            success = self.install_driver(
                update["hardware_id"],
                update
            )

            if success:
                self.logger.info(f"[OK] Драйвер {update['available_driver']} успешно установлен")
            else:
                self.logger.error(f"[ERROR] Ошибка установки {update['available_driver']}")


if __name__ == "__main__":
    server_url = "http://DESKTOP-6CA6O4K:8000"

    client = DriverClient(server_url)
    client.run_auto_update()