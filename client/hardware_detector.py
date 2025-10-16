import platform
import socket
import subprocess
import re


class HardwareDetector:
    def __init__(self):
        self.system_info = {}

    def get_computer_name(self):
        return socket.gethostname()

    def get_cpu_info(self):
        try:
            if platform.system() == "Windows":
                result = subprocess.check_output(
                    "wmic cpu get name",
                    shell=True,
                    text=True
                )
                cpu_name = result.strip().split('\n')[1]
                return cpu_name
            else:
                return platform.processor()
        except:
            return "Неизвестный процессор"

    def get_gpu_info(self):
        try:
            if platform.system() == "Windows":
                result = subprocess.check_output(
                    "wmic path win32_videocontroller get name",
                    shell=True,
                    text=True
                )
                gpu_lines = result.strip().split('\n')[1:]
                gpus = [line.strip() for line in gpu_lines if line.strip()]
                return gpus[0] if gpus else "Неизвестная видеокарта"
            else:
                return "Видеокарта (требуется ручная настройка для Linux)"
        except:
            return "Неизвестная видеокарта"

    def get_motherboard_info(self):
        try:
            if platform.system() == "Windows":
                result = subprocess.check_output(
                    "wmic baseboard get product, manufacturer",
                    shell=True,
                    text=True
                )
                lines = result.strip().split('\n')[1:]
                if lines:
                    mb_info = lines[0].strip()
                    return mb_info
            return "Неизвестная материнская плата"
        except:
            return "Неизвестная материнская плата"

    def get_network_adapters(self):
        try:
            if platform.system() == "Windows":
                result = subprocess.check_output(
                    "wmic nic where netenabled=true get name",
                    shell=True,
                    text=True
                )
                adapters = result.strip().split('\n')[1:]
                return [adapter.strip() for adapter in adapters if adapter.strip()]
            return ["Сетевой адаптер"]
        except:
            return ["Сетевой адаптер"]

    def get_ip_address(self):
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            return ip_address
        except:
            return "127.0.0.1"

    def get_all_hardware(self):
        return {
            "cpu": self.get_cpu_info(),
            "gpu": self.get_gpu_info(),
            "motherboard": self.get_motherboard_info(),
            "network_adapters": self.get_network_adapters(),
            "ip_address": self.get_ip_address(),
            "os": f"{platform.system()} {platform.release()}"
        }