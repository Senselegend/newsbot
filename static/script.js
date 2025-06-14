// SmartLab News Bot JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);   
    }
);

    // Channel test functionality
    const testChannelBtn = document.getElementById('test-channel-btn');
    if (testChannelBtn) {
        testChannelBtn.addEventListener('click', function() {
            testTelegramChannel();
        });
    }

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Auto-save settings
    const settingsForm = document.getElementById('settings-form');
    if (settingsForm) {
        const inputs = settingsForm.querySelectorAll('input, select, textarea');
        inputs.forEach(function(input) {
            input.addEventListener('change', function() {
                showSaveIndicator();
            });
        });
    }

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            if (!confirm('Вы уверены, что хотите удалить этот элемент?')) {
                e.preventDefault();
            }
        });
    });

    // Auto-refresh functionality
    if (window.location.pathname === '/') {
        setInterval(refreshDashboard, 60000); // Refresh every minute
    }
    // OpenRouter API test
const testOpenRouterBtn = document.getElementById('test-openrouter-btn');
if (testOpenRouterBtn) {
    testOpenRouterBtn.addEventListener('click', function() {
        const resultDiv = document.getElementById('api-test-result');
        resultDiv.style.display = 'block';
        resultDiv.className = 'alert alert-info mt-2';
        resultDiv.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Проверка OpenRouter API...';
        fetch('/test_openrouter_api')
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    resultDiv.className = 'alert alert-success mt-2';
                    resultDiv.innerHTML = '<i class="fas fa-check me-1"></i>' + data.message;
                } else {
                    resultDiv.className = 'alert alert-danger mt-2';
                    resultDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>' + (data.error || 'Ошибка проверки');
                }
            })
            .catch(e => {
                resultDiv.className = 'alert alert-danger mt-2';
                resultDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Ошибка соединения';
            });
    });
}
const testGeminiBtn = document.getElementById('test-gemini-btn');
if (testGeminiBtn) {
    testGeminiBtn.addEventListener('click', function() {
        const resultDiv = document.getElementById('api-test-result');
        resultDiv.style.display = 'block';
        resultDiv.className = 'alert alert-info mt-2';
        resultDiv.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Проверка Gemini API...';
        fetch('/test_gemini_api')
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    resultDiv.className = 'alert alert-success mt-2';
                    resultDiv.innerHTML = '<i class="fas fa-check me-1"></i>' + data.message;
                } else {
                    resultDiv.className = 'alert alert-danger mt-2';
                    resultDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>' + (data.error || 'Ошибка проверки');
                }
            })
            .catch(e => {
                resultDiv.className = 'alert alert-danger mt-2';
                resultDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Ошибка соединения';
            });
    });
}

// Telegram test message
const testTelegramBtn = document.getElementById('test-telegram-btn');
if (testTelegramBtn) {
    testTelegramBtn.addEventListener('click', function() {
        const resultDiv = document.getElementById('api-test-result');
        resultDiv.style.display = 'block';
        resultDiv.className = 'alert alert-info mt-2';
        resultDiv.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Отправка тестового сообщения...';
        fetch('/test_telegram_message', {method: 'POST'})
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    resultDiv.className = 'alert alert-success mt-2';
                    resultDiv.innerHTML = '<i class="fas fa-check me-1"></i>Тестовое сообщение отправлено!';
                } else {
                    resultDiv.className = 'alert alert-danger mt-2';
                    resultDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>' + (data.error || 'Ошибка отправки');
                }
            })
            .catch(e => {
                resultDiv.className = 'alert alert-danger mt-2';
                resultDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Ошибка соединения';
            });
    });
}
});

function testTelegramChannel() {
    const channelId = document.getElementById('channel_id').value.trim();
    const testBtn = document.getElementById('test-channel-btn');
    const resultDiv = document.getElementById('test-result');
    
    if (!channelId) {
        showTestResult('error', 'Введите ID канала');
        return;
    }
    
    // Show loading state
    testBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Тестирование...';
    testBtn.disabled = true;
    
    const formData = new FormData();
    formData.append('channel_id', channelId);
    
    fetch('/test_channel', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showTestResult('success', `Канал найден: ${data.chat_title || channelId}`);
        } else {
            showTestResult('error', data.error);
        }
    })
    .catch(error => {
        showTestResult('error', 'Ошибка соединения: ' + error.message);
    })
    .finally(() => {
        // Restore button state
        testBtn.innerHTML = '<i class="fas fa-test me-1"></i>Проверить канал';
        testBtn.disabled = false;
    });
}

function showTestResult(type, message) {
    const resultDiv = document.getElementById('test-result');
    if (resultDiv) {
        resultDiv.className = `alert alert-${type === 'success' ? 'success' : 'danger'} mt-2`;
        resultDiv.innerHTML = `<i class="fas fa-${type === 'success' ? 'check' : 'exclamation-triangle'} me-1"></i>${message}`;
        resultDiv.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            resultDiv.style.display = 'none';
        }, 5000);
    }
}

function showSaveIndicator() {
    // Show that settings have changed
    const saveBtn = document.querySelector('.btn-save-settings');
    if (saveBtn && !saveBtn.classList.contains('btn-warning')) {
        saveBtn.classList.remove('btn-primary');
        saveBtn.classList.add('btn-warning');
        saveBtn.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Есть несохраненные изменения';
    }
}

function refreshDashboard() {
    // Refresh dashboard statistics
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            updateDashboardStats(data);
        })
        .catch(error => {
            console.log('Error refreshing dashboard:', error);
        });
}

function updateDashboardStats(data) {
    // Update statistics cards
    const elements = {
        'today-posts': data.today_posts,
        'total-articles': data.total_articles,
        'posted-articles': data.posted_articles,
        'pending-articles': data.pending_articles
    };
    
    Object.keys(elements).forEach(id => {
        const element = document.getElementById(id);
        if (element && elements[id] !== undefined) {
            element.textContent = elements[id];
            element.classList.add('fade-in-up');
        }
    });
}

function confirmAction(message) {
    return confirm(message || 'Вы уверены?');
}

function showLoading(element) {
    if (element) {
        element.classList.add('loading');
        const spinner = document.createElement('span');
        spinner.className = 'spinner-border spinner-border-sm me-1';
        element.insertBefore(spinner, element.firstChild);
    }
}

function hideLoading(element) {
    if (element) {
        element.classList.remove('loading');
        const spinner = element.querySelector('.spinner-border');
        if (spinner) {
            spinner.remove();
        }
    }
}

// Article management functions
function regenerateSummary(articleId) {
    if (!confirm('Регенерировать резюме статьи? Текущее резюме будет заменено.')) {
        return;
    }
    
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/regenerate_summary/${articleId}`;
    document.body.appendChild(form);
    form.submit();
}

function postArticle(articleId, channelId) {
    if (!confirm('Опубликовать статью в канале?')) {
        return;
    }
    
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/post_article/${articleId}`;
    
    if (channelId) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'channel_id';
        input.value = channelId;
        form.appendChild(input);
    }
    
    document.body.appendChild(form);
    form.submit();
}

// Utility functions
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showToast('Скопировано в буфер обмена', 'success');
    }).catch(function(err) {
        console.error('Could not copy text: ', err);
        showToast('Ошибка копирования', 'error');
    });
}

function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 300px;';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 3000);
}

// Form helpers
function validateForm(form) {
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

function resetForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
        form.classList.remove('was-validated');
        
        // Remove validation classes
        const inputs = form.querySelectorAll('.is-invalid, .is-valid');
        inputs.forEach(input => {
            input.classList.remove('is-invalid', 'is-valid');
        });
    }
}

// Export functions for use in templates
window.testTelegramChannel = testTelegramChannel;
window.regenerateSummary = regenerateSummary;
window.postArticle = postArticle;
window.confirmAction = confirmAction;
window.copyToClipboard = copyToClipboard;
