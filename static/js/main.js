// Main JavaScript for Discord Translation Bot Dashboard

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Close alerts automatically
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Update bot status regularly
    updateBotStatus();
    setInterval(updateBotStatus, 5000);
});

// Function to update bot status
function updateBotStatus() {
    const statusContainer = document.getElementById('bot-status-container');
    if (!statusContainer) return;
    
    fetch('/bot_status')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Update status badge
            const statusBadge = document.getElementById('bot-status');
            if (statusBadge) {
                statusBadge.className = data.running ? 'badge bg-success' : 'badge bg-danger';
                statusBadge.textContent = data.running ? 'Online' : 'Offline';
            }
            
            // Update connected servers
            const connectedServers = document.getElementById('connected-servers');
            if (connectedServers) {
                connectedServers.textContent = data.connected_servers || 0;
            }
            
            // Update controls based on bot status
            updateBotControls(data.running);
        })
        .catch(error => {
            console.error('Error fetching bot status:', error);
            // Handle errors gracefully by assuming bot is offline
            const statusBadge = document.getElementById('bot-status');
            if (statusBadge) {
                statusBadge.className = 'badge bg-warning';
                statusBadge.textContent = 'Unknown';
            }
        });
}

// Update controls based on bot status
function updateBotControls(isRunning) {
    const startBotForm = document.querySelector('form[action*="start_bot"]');
    const stopBotForm = document.querySelector('form[action*="stop_bot"]');
    const setupLink = document.querySelector('a[href*="bot_setup"]');
    
    if (startBotForm && stopBotForm) {
        if (isRunning) {
            startBotForm.style.display = 'none';
            stopBotForm.style.display = 'block';
            if (setupLink) setupLink.style.display = 'none';
        } else {
            startBotForm.style.display = 'block';
            stopBotForm.style.display = 'none';
            if (setupLink) setupLink.style.display = 'inline-block';
        }
    }
}