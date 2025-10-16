const API_BASE = 'http://localhost:8000'; 
// Показать уведомление
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container');
    const alertId = 'alert-' + Date.now();
    
    const alertHTML = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show alert-auto" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    alertContainer.innerHTML += alertHTML;
    
    // Автоудаление через 3 секунды
    setTimeout(() => {
        const alert = document.getElementById(alertId);
        if (alert) alert.remove();
    }, 3000);
}

// Загрузка компьютеров
async function loadComputers() {
    try {
        const response = await fetch(`${API_BASE}/computers`);
        const computers = await response.json();
        
        const container = document.getElementById('computers-list');
        
        if (computers.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    Нет зарегистрированных компьютеров
                </div>
            `;
            return;
        }
        
        let html = `
            <div class="table-responsive">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Имя</th>
                            <th>IP адрес</th>
                            <th>Процессор</th>
                            <th>Видеокарта</th>
                            <th>Последний онлайн</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        computers.forEach(computer => {
            html += `
                <tr>
                    <td><strong>${computer.name}</strong></td>
                    <td><span class="badge bg-secondary">${computer.ip}</span></td>
                    <td>${computer.cpu || 'Не указан'}</td>
                    <td>${computer.gpu || 'Не указана'}</td>
                    <td><small>${new Date(computer.last_seen).toLocaleString()}</small></td>
                </tr>
            `;
        });
        
        html += `</tbody></table></div>`;
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Ошибка:', error);
        showAlert('Ошибка загрузки компьютеров', 'danger');
    }
}

// Загрузка драйверов
async function loadDrivers() {
    try {
        const response = await fetch(`${API_BASE}/drivers`)
        const drivers = await response.json();
        
        const container = document.getElementById('drivers-list');
        
        if (drivers.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    Нет загруженных драйверов
                </div>
            `;
            return;
        }
        
        let html = '';
        drivers.forEach(driver => {
            const sizeMB = driver.file_size ? (driver.file_size / (1024 * 1024)).toFixed(2) : 'Неизвестно';
            
            html += `
                <div class="card driver-card mb-3">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h5 class="card-title">${driver.model}</h5>
                                <p class="card-text mb-1">
                                    <strong>Версия:</strong> ${driver.version} | 
                                    <strong>ОС:</strong> ${driver.os} |
                                    <strong>Размер:</strong> ${sizeMB} MB
                                </p>
                                <p class="card-text">
                                    <small class="text-muted">
                                        ID: ${driver.hardware_id} | 
                                        Загружен: ${new Date(driver.upload_date).toLocaleDateString()}
                                    </small>
                                </p>
                            </div>
                            <button class="btn btn-outline-danger btn-sm" onclick="deleteDriver('${driver.hardware_id}')">
                                Удалить
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Ошибка:', error);
        showAlert('Ошибка загрузки драйверов', 'danger');
    }
}

// Загрузка статуса
async function loadStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`)
        const status = await response.json();
        
        const container = document.getElementById('status-info');
        
        container.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <div class="card bg-light mb-3">
                        <div class="card-body">
                            <h5 class="card-title">📊 Статистика</h5>
                            <p><strong>Компьютеров:</strong> ${status.computers_registered}</p>
                            <p><strong>Драйверов:</strong> ${status.drivers_available}</p>
                            <p><strong>Общий размер:</strong> ${status.total_drivers_size_mb} MB</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card bg-light mb-3">
                        <div class="card-body">
                            <h5 class="card-title">⚡ Активность</h5>
                            <p><strong>Ожидают установки:</strong> ${status.pending_installations}</p>
                            <p><strong>Устаревших компьютеров:</strong> ${status.outdated_computers}</p>
                            <p><strong>Статус сервера:</strong> 
                                <span class="badge bg-success">${status.status}</span>
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
    } catch (error) {
        console.error('Ошибка:', error);
        showAlert('Ошибка загрузки статуса', 'danger');
    }
}

// Загрузка драйвера
async function uploadDriver(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData();
    
    const fileInput = document.getElementById('driver-file');
    const model = document.getElementById('model').value;
    const version = document.getElementById('version').value;
    
    formData.append('file', fileInput.files[0]);
    formData.append('model', model);
    formData.append('driver_version', version);
    
    try {
        const response = await fetch(`${API_BASE}/drivers/register`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            showAlert(`Драйвер ${model} успешно загружен!`, 'success');
            form.reset();
            loadDrivers(); // Обновляем список драйверов
        } else {
            throw new Error('Ошибка загрузки');
        }
        
    } catch (error) {
        console.error('Ошибка:', error);
        showAlert('Ошибка загрузки драйвера', 'danger');
    }
}

// Удаление драйвера
async function deleteDriver(hardwareId) {
    if (!confirm('Вы уверены, что хотите удалить этот драйвер?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/drivers/delete`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                hardware_id: hardwareId,
                reason: "Удалено через веб-интерфейс"
            })
        });
        
        if (response.ok) {
            showAlert('Драйвер успешно удален', 'success');
            loadDrivers(); // Обновляем список
        } else {
            throw new Error('Ошибка удаления');
        }
        
    } catch (error) {
        console.error('Ошибка:', error);
        showAlert('Ошибка удаления драйвера', 'danger');
    }
}

// Загружаем данные при открытии страницы
document.addEventListener('DOMContentLoaded', function() {
    loadComputers();
    loadStatus();
});