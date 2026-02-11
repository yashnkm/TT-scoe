// Global application JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Form validation
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Confirm delete actions
    var deleteLinks = document.querySelectorAll('a[href*="/delete/"]');
    deleteLinks.forEach(function(link) {
        link.addEventListener('click', function(event) {
            if (!confirm('Are you sure you want to delete this item?')) {
                event.preventDefault();
            }
        });
    });
});

// Utility functions
function showLoading(elementId) {
    var element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
        element.disabled = true;
    }
}

function hideLoading(elementId, originalText) {
    var element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = originalText;
        element.disabled = false;
    }
}

function showAlert(message, type = 'info') {
    // Create toast container if it doesn't exist
    var toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; max-width: 350px; pointer-events: none;';
        document.body.appendChild(toastContainer);
    }
    
    // Map type to icons
    var icons = {
        'success': 'fa-check-circle',
        'danger': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    };
    
    var icon = icons[type] || icons['info'];
    
    // Create toast notification
    var toast = document.createElement('div');
    toast.className = `toast-notification alert alert-${type} alert-dismissible fade show shadow-sm`;
    toast.style.cssText = 'margin-bottom: 10px; font-size: 0.875rem; padding: 10px 14px; border-radius: 6px; pointer-events: auto; display: flex; align-items: center;';
    toast.innerHTML = `
        <i class="fas ${icon} me-2" style="font-size: 1rem;"></i>
        <span style="flex: 1; line-height: 1.4;">${message}</span>
        <button type="button" class="btn-close btn-close-sm" data-bs-dismiss="alert" style="margin-left: 8px; opacity: 0.7;"></button>
    `;
    
    toastContainer.appendChild(toast);
    
    // Limit to max 3 toasts at once - remove oldest if exceeded
    var allToasts = toastContainer.querySelectorAll('.toast-notification');
    if (allToasts.length > 3) {
        var oldestToast = allToasts[0];
        var bsAlert = new bootstrap.Alert(oldestToast);
        bsAlert.close();
        setTimeout(function() {
            if (oldestToast.parentNode) {
                oldestToast.remove();
            }
        }, 300);
    }
    
    // Auto-hide after 3 seconds (shorter for less intrusion)
    setTimeout(function() {
        var bsAlert = new bootstrap.Alert(toast);
        bsAlert.close();
        
        // Remove from DOM after animation
        setTimeout(function() {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 300);
    }, 3000);
}

// API helper functions
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Timetable utilities
function formatTimeSlot(timeSlot) {
    return timeSlot.replace('-', ' - ');
}

function getSessionTypeColor(type) {
    return type === 'theory' ? 'info' : 'warning';
}

function getSessionTypeIcon(type) {
    return type === 'theory' ? 'fa-book' : 'fa-flask';
}

// Export utilities
function exportToCSV(data, filename) {
    const csv = arrayToCSV(data);
    downloadFile(csv, filename, 'text/csv');
}

function arrayToCSV(data) {
    if (!data.length) return '';
    
    const headers = Object.keys(data[0]);
    const csvContent = [
        headers.join(','),
        ...data.map(row => headers.map(header => {
            const value = row[header];
            // Escape commas and quotes
            if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                return `"${value.replace(/"/g, '""')}"`;
            }
            return value;
        }).join(','))
    ].join('\n');
    
    return csvContent;
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Theme utilities
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-bs-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// Load saved theme
(function() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-bs-theme', savedTheme);
    }
})();
