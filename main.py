from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3
import os
import uvicorn
from typing import List, Optional
from datetime import datetime
import hashlib
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Driver Deploy",
    description="Сервер для централизованного управления драйверами в локальной сети",
    version="3.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="frontend"), name="static")# Путь к базе данных
DB_PATH = "drivers.db"
DRIVERS_DIR = "drivers"


os.makedirs(DRIVERS_DIR, exist_ok=True)



class ComputerRegister(BaseModel):
    name: str
    ip: str
    cpu: str
    gpu: str
    motherboard: str
    network_adapters: List[str]


class InstallationReport(BaseModel):
    computer_name: str
    hardware_id: str
    status: str
    message: str = ""


class ComputerDelete(BaseModel):
    name: str
    reason: str = "Не указана"


class DriverDelete(BaseModel):
    hardware_id: str
    reason: str = "Не указана"



def generate_hardware_id(model: str, version: str) -> str:
    base_string = f"{model}_{version}"
    clean_string = "".join(c if c.isalnum() else "_" for c in base_string)
    hash_object = hashlib.md5(base_string.encode())
    hash_hex = hash_object.hexdigest()[:8]
    return f"{clean_string.lower()}_{hash_hex}"


def update_db_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(drivers)")
    existing_columns = [column[1] for column in cursor.fetchall()]

    if 'file_size' not in existing_columns:
        print("🔄 Добавляем колонку file_size...")
        cursor.execute("ALTER TABLE drivers ADD COLUMN file_size INTEGER")

    if 'original_filename' not in existing_columns:
        print("🔄 Добавляем колонку original_filename...")
        cursor.execute("ALTER TABLE drivers ADD COLUMN original_filename TEXT")

    if 'upload_date' not in existing_columns:
        print("🔄 Добавляем колонку upload_date...")
        cursor.execute("ALTER TABLE drivers ADD COLUMN upload_date TIMESTAMP")
        cursor.execute("UPDATE drivers SET upload_date = CURRENT_TIMESTAMP WHERE upload_date IS NULL")

    conn.commit()
    conn.close()
    print("✅ Структура базы данных обновлена")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS computers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            ip TEXT NOT NULL,
            cpu TEXT,
            gpu TEXT,
            motherboard TEXT,
            network_adapters TEXT,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hardware_id TEXT UNIQUE NOT NULL,
            model TEXT NOT NULL,
            driver_version TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            original_filename TEXT,
            os_version TEXT DEFAULT 'Windows 10',
            supported_hardware TEXT,
            upload_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS installation_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            computer_name TEXT NOT NULL,
            hardware_id TEXT NOT NULL,
            driver_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")


@app.on_event("startup")
async def startup_event():
    init_db()
    update_db_schema()
    print("✅ Сервер запущен и готов к работе!")
    print("📚 Документация API доступна по адресу: http://localhost:8000/docs")


#Для компьютеров

@app.post("/computers/register", response_model=dict)
async def register_computer(computer: ComputerRegister):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        network_adapters_str = ",".join(computer.network_adapters)

        cursor.execute('''
            INSERT OR REPLACE INTO computers 
            (name, ip, cpu, gpu, motherboard, network_adapters, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            computer.name, computer.ip, computer.cpu, computer.gpu,
            computer.motherboard, network_adapters_str
        ))

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": f"Компьютер {computer.name} зарегистрирован",
            "computer": computer.name
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка регистрации: {str(e)}")


@app.get("/computers", response_model=List[dict])
async def get_computers():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT name, ip, cpu, gpu, last_seen 
        FROM computers 
        ORDER BY last_seen DESC
    ''')

    computers = []
    for row in cursor.fetchall():
        computers.append({
            "name": row[0],
            "ip": row[1],
            "cpu": row[2],
            "gpu": row[3],
            "last_seen": row[4]
        })

    conn.close()
    return computers


@app.get("/computers/{computer_name}/info")
async def get_computer_info(computer_name: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT name, ip, cpu, gpu, motherboard, network_adapters, last_seen, created_at
            FROM computers WHERE name = ?
        ''', (computer_name,))

        computer = cursor.fetchone()

        if not computer:
            raise HTTPException(status_code=404, detail="Компьютер не найден")

        cursor.execute('''
            SELECT COUNT(*) FROM installation_jobs 
            WHERE computer_name = ? AND status IN ('pending', 'in_progress')
        ''', (computer_name,))

        active_jobs = cursor.fetchone()[0]
        conn.close()

        return {
            "name": computer[0],
            "ip": computer[1],
            "cpu": computer[2],
            "gpu": computer[3],
            "motherboard": computer[4],
            "network_adapters": computer[5].split(",") if computer[5] else [],
            "last_seen": computer[6],
            "created_at": computer[7],
            "active_installations": active_jobs,
            "can_be_deleted": active_jobs == 0
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения информации: {str(e)}")


@app.delete("/computers/delete", response_model=dict)
async def delete_computer(delete_data: ComputerDelete):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM computers WHERE name = ?", (delete_data.name,))
        computer = cursor.fetchone()

        if not computer:
            raise HTTPException(status_code=404, detail=f"Компьютер {delete_data.name} не найден")

        cursor.execute("DELETE FROM computers WHERE name = ?", (delete_data.name,))
        cursor.execute("DELETE FROM installation_jobs WHERE computer_name = ?", (delete_data.name,))

        conn.commit()
        conn.close()

        print(f"🗑️ Удален компьютер: {delete_data.name}. Причина: {delete_data.reason}")

        return {
            "status": "success",
            "message": f"Компьютер {delete_data.name} удален из системы",
            "reason": delete_data.reason
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления компьютера: {str(e)}")


#Для драйверов

@app.post("/drivers/register", response_model=dict)
async def register_driver(
        file: UploadFile = File(..., description="Файл драйвера"),
        model: str = Form(..., description="Модель оборудования"),
        driver_version: str = Form(..., description="Версия драйвера"),
        hardware_id: str = Form("",
                                description="Уникальный идентификатор оборудования (опционально - сгенерируется автоматически)"),
        os_version: str = Form("Windows 10", description="Версия ОС"),
        supported_hardware: Optional[str] = Form(None, description="Поддерживаемое оборудование")
):
    try:
        if not model or not driver_version:
            raise HTTPException(status_code=400, detail="Обязательные поля: model, driver_version")

        if not hardware_id:
            hardware_id = generate_hardware_id(model, driver_version)
            print(f"🔧 Автоматически сгенерирован hardware_id: {hardware_id}")

        allowed_extensions = {'.exe', '.msi', '.zip', '.inf', '.cab'}
        file_extension = os.path.splitext(file.filename.lower())[1]
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый формат файла. Разрешены: {', '.join(allowed_extensions)}"
            )

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM drivers WHERE hardware_id = ?", (hardware_id,))
        existing_driver = cursor.fetchone()
        if existing_driver:
            new_hardware_id = generate_hardware_id(model, driver_version + "_dup")
            print(f"⚠️ Hardware_id {hardware_id} уже существует. Генерируем новый: {new_hardware_id}")
            hardware_id = new_hardware_id

        safe_filename = f"{hardware_id}{file_extension}"
        file_path = os.path.join(DRIVERS_DIR, safe_filename)

        file_size = 0
        with open(file_path, "wb") as buffer:
            content = await file.read()
            file_size = len(content)
            buffer.write(content)

        cursor.execute('''
            INSERT INTO drivers 
            (hardware_id, model, driver_version, file_path, file_size, original_filename, 
             os_version, supported_hardware, upload_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            hardware_id,
            model,
            driver_version,
            file_path,
            file_size,
            file.filename,
            os_version,
            supported_hardware
        ))

        driver_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"✅ Зарегистрирован драйвер: {model} v{driver_version} (ID: {hardware_id})")

        return {
            "status": "success",
            "message": f"Драйвер {model} v{driver_version} успешно зарегистрирован",
            "driver_id": driver_id,
            "hardware_id": hardware_id,
            "auto_generated_id": not hardware_id,
            "file_info": {
                "original_name": file.filename,
                "saved_as": safe_filename,
                "size_bytes": file_size,
                "path": file_path
            },
            "driver_info": {
                "model": model,
                "version": driver_version,
                "os_version": os_version,
                "supported_hardware": supported_hardware
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Ошибка регистрации драйвера: {str(e)}")


@app.get("/drivers", response_model=List[dict])
async def get_drivers():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT hardware_id, model, driver_version, os_version, file_size, original_filename, upload_date
        FROM drivers 
        ORDER BY model, driver_version
    ''')

    drivers = []
    for row in cursor.fetchall():
        drivers.append({
            "hardware_id": row[0],
            "model": row[1],
            "version": row[2],
            "os": row[3],
            "file_size": row[4],
            "original_filename": row[5],
            "upload_date": row[6]
        })

    conn.close()
    return drivers


@app.get("/drivers/{hardware_id}")
async def get_driver_info(hardware_id: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT hardware_id, model, driver_version, file_path, file_size, original_filename,
                   os_version, supported_hardware, upload_date
            FROM drivers WHERE hardware_id = ?
        ''', (hardware_id,))

        driver = cursor.fetchone()

        if not driver:
            raise HTTPException(status_code=404, detail="Драйвер не найден")

        file_exists = os.path.exists(driver[3])
        conn.close()

        return {
            "hardware_id": driver[0],
            "model": driver[1],
            "version": driver[2],
            "file_info": {
                "path": driver[3],
                "size_bytes": driver[4],
                "original_name": driver[5],
                "exists": file_exists
            },
            "compatibility": {
                "os_version": driver[6],
                "supported_hardware": driver[7]
            },
            "upload_date": driver[8]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения информации: {str(e)}")


@app.delete("/drivers/delete", response_model=dict)
async def delete_driver(delete_data: DriverDelete):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT model, driver_version, file_path FROM drivers WHERE hardware_id = ?",
                       (delete_data.hardware_id,))
        driver = cursor.fetchone()

        if not driver:
            raise HTTPException(status_code=404, detail=f"Драйвер с hardware_id {delete_data.hardware_id} не найден")

        model, version, file_path = driver

        cursor.execute("DELETE FROM drivers WHERE hardware_id = ?", (delete_data.hardware_id,))
        cursor.execute("DELETE FROM installation_jobs WHERE hardware_id = ?", (delete_data.hardware_id,))

        conn.commit()
        conn.close()

        file_deleted = False
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                file_deleted = True
            except Exception as e:
                print(f"⚠️ Не удалось удалить файл {file_path}: {e}")

        print(f"🗑️ Удален драйвер: {model} v{version}. Причина: {delete_data.reason}")

        return {
            "status": "success",
            "message": f"Драйвер {model} v{version} удален из системы",
            "hardware_id": delete_data.hardware_id,
            "file_deleted": file_deleted,
            "reason": delete_data.reason
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления драйвера: {str(e)}")


#Обновления

@app.get("/computers/{computer_name}/check-updates")
async def check_updates(computer_name: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('SELECT cpu, gpu, motherboard FROM computers WHERE name = ?', (computer_name,))
        computer_data = cursor.fetchone()

        if not computer_data:
            raise HTTPException(status_code=404, detail="Компьютер не найден")

        cpu, gpu, motherboard = computer_data
        available_updates = []

        if gpu:
            search_terms = []
            if "NVIDIA" in gpu.upper():
                search_terms.append("%NVIDIA%")
            if "AMD" in gpu.upper() or "RADEON" in gpu.upper():
                search_terms.append("%AMD%")
                search_terms.append("%RADEON%")
            if "INTEL" in gpu.upper():
                search_terms.append("%INTEL%")

            for term in search_terms:
                cursor.execute(
                    'SELECT hardware_id, model, driver_version FROM drivers WHERE model LIKE ?',
                    (term,)
                )
                gpu_drivers = cursor.fetchall()

                for driver in gpu_drivers:
                    available_updates.append({
                        "hardware": "GPU",
                        "current_model": gpu,
                        "available_driver": driver[1],
                        "version": driver[2],
                        "hardware_id": driver[0],
                        "action": "install"
                    })

        conn.close()

        return {
            "computer": computer_name,
            "available_updates": available_updates,
            "last_checked": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка проверки обновлений: {str(e)}")


@app.post("/installation/report")
async def installation_report(report: InstallationReport):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE installation_jobs 
            SET status = ?, completed_at = CURRENT_TIMESTAMP
            WHERE computer_name = ? AND hardware_id = ?
        ''', (report.status, report.computer_name, report.hardware_id))

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": f"Отчет от {report.computer_name} принят",
            "installation_status": report.status
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки отчета: {str(e)}")

#Статус и устаревшее

@app.delete("/computers/cleanup", response_model=dict)
async def cleanup_old_computers(days_offline: int = 30):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT name, last_seen 
            FROM computers 
            WHERE date(last_seen) < date('now', '-' || ? || ' days')
        ''', (days_offline,))

        old_computers = cursor.fetchall()

        if not old_computers:
            return {
                "status": "success",
                "message": "Нет устаревших компьютеров для удаления",
                "deleted_count": 0
            }

        deleted_count = 0
        for computer_name, last_seen in old_computers:
            cursor.execute("DELETE FROM computers WHERE name = ?", (computer_name,))
            cursor.execute("DELETE FROM installation_jobs WHERE computer_name = ?", (computer_name,))
            deleted_count += 1
            print(f"🗑️ Автоудаление: {computer_name} (последний раз онлайн: {last_seen})")

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": f"Удалено {deleted_count} устаревших компьютеров",
            "deleted_count": deleted_count,
            "criteria": f"Не онлайн более {days_offline} дней"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка очистки устаревших компьютеров: {str(e)}")


@app.get("/status")
async def get_status():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM computers")
    computers_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM drivers")
    drivers_count = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(file_size) FROM drivers")
    total_size = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM installation_jobs WHERE status = 'pending'")
    pending_jobs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM computers WHERE date(last_seen) < date('now', '-30 days')")
    outdated_computers = cursor.fetchone()[0]

    conn.close()

    return {
        "status": "running",
        "computers_registered": computers_count,
        "drivers_available": drivers_count,
        "total_drivers_size_mb": round(total_size / (1024 * 1024), 2),
        "pending_installations": pending_jobs,
        "outdated_computers": outdated_computers,
        "cleanup_available": outdated_computers > 0,
        "server_time": datetime.now().isoformat()
    }
