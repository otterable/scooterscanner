console.debug("Main.js loaded.");

let video = document.getElementById('video');
let overlay = document.getElementById('overlay');
let scannedScooterIdDiv = document.getElementById('scanned-scooter-id');
let scooterList = document.getElementById('scooter-list');
let totalScootersSpan = document.getElementById('total-scooters');
let beepSound = document.getElementById('beep-sound');
let listContainer = document.getElementById('list-container');
let isListVisible = false;
let isPaused = false;
let scannedScooters = new Set(); // To track scanned scooters

console.debug("Variables initialized.");

// Initialize QR Scanner with new API
const qrScanner = new QrScanner(
    video,
    result => {
        console.debug("QR code scanned:", result);
        processScannedData(result.data); // Use result.data instead of result
    },
    { returnDetailedScanResult: true } // Use new API
);

console.debug("Starting QR Scanner.");
qrScanner.start().catch(error => {
    console.debug("Error starting QR Scanner:", error);
});

// Process scanned data
function processScannedData(scooterId) {
    console.debug("Processing scanned data:", scooterId);

    // Check for duplicates
    if (scannedScooters.has(scooterId)) {
        console.debug("Duplicate scooter ID detected:", scooterId);
        // Flash red overlay
        overlay.style.backgroundColor = 'red';
        overlay.style.opacity = '0.7';
        setTimeout(() => {
            overlay.style.opacity = '0';
        }, 300);
        // Do not play beep or add to list
        return;
    } else {
        scannedScooters.add(scooterId);
    }

    // Play beep sound
    beepSound.play();

    // Flash green overlay
    overlay.style.backgroundColor = 'green';
    overlay.style.opacity = '0.7';
    setTimeout(() => {
        overlay.style.opacity = '0';
    }, 300);

    // Display scanned scooter ID
    scannedScooterIdDiv.textContent = scooterId;
    scannedScooterIdDiv.style.display = 'block';
    setTimeout(() => {
        scannedScooterIdDiv.style.display = 'none';
    }, 5000);

    // Add to list
    fetch('/save_scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, scooter_id: scooterId })
    })
    .then(response => response.json())
    .then(data => {
        console.debug("Response from save_scan:", data);
        if (data.status === 'success') {
            let listItem = document.createElement('li');
            let timestamp = new Date();
            let formattedTime = timestamp.getHours().toString().padStart(2, '0') + ':' +
                                timestamp.getMinutes().toString().padStart(2, '0') + ' | ' +
                                timestamp.getDate() + '.' + (timestamp.getMonth() + 1) + '.' + timestamp.getFullYear();
            listItem.textContent = `${scooterId} - ${formattedTime}`;
            scooterList.insertBefore(listItem, scooterList.firstChild);
            totalScootersSpan.textContent = data.total;
        } else {
            console.debug("Error: Unable to save scan data.");
        }
    })
    .catch(error => {
        console.debug("Fetch error:", error);
    });
}

// Toggle list visibility
document.getElementById('toggle-list-btn').addEventListener('click', () => {
    console.debug("Toggle List button clicked.");
    toggleListVisibility();
});

// Finish list
document.getElementById('finish-list-btn').addEventListener('click', () => {
    console.debug("Finish List button clicked.");
    qrScanner.stop();
    console.debug("QR Scanner stopped.");
    window.location.href = '/';
});

// Export list
document.getElementById('export-btn').addEventListener('click', () => {
    console.debug("Export button clicked.");
    window.location.href = `/export/${sessionId}`;
});

// Pause/Resume scanning
document.getElementById('pause-btn').addEventListener('click', () => {
    if (isPaused) {
        // Resume scanning
        qrScanner.start();
        document.getElementById('pause-btn').textContent = 'Pause';
        console.debug("Scanning resumed.");
    } else {
        // Pause scanning
        qrScanner.stop();
        document.getElementById('pause-btn').textContent = 'Resume';
        console.debug("Scanning paused.");
    }
    isPaused = !isPaused;
    toggleListVisibility();
});

function toggleListVisibility() {
    if (isListVisible) {
        listContainer.style.display = 'none';
        adjustCameraSize();
        console.debug("List container hidden.");
    } else {
        listContainer.style.display = 'block';
        adjustCameraSize();
        console.debug("List container shown.");
    }
    isListVisible = !isListVisible;
}

// Adjust camera size based on screen height
function adjustCameraSize() {
    const availableHeight = window.innerHeight;
    const buttonContainerHeight = document.getElementById('button-container').offsetHeight;
    const desiredCameraHeight = availableHeight - buttonContainerHeight;
    document.getElementById('camera-container').style.height = desiredCameraHeight + 'px';
}

// Initial adjustment
adjustCameraSize();

// Handle window resize
window.addEventListener('resize', adjustCameraSize);

// Install PWA
let deferredPrompt;
const savePwaBtn = document.getElementById('save-pwa-btn');
if (savePwaBtn) {
    window.addEventListener('beforeinstallprompt', (e) => {
        console.debug("beforeinstallprompt event fired.");
        e.preventDefault();
        deferredPrompt = e;
        savePwaBtn.style.display = 'block';
    });

    savePwaBtn.addEventListener('click', () => {
        console.debug("Save as PWA button clicked.");
        if (deferredPrompt) {
            deferredPrompt.prompt();
            deferredPrompt.userChoice.then((choiceResult) => {
                if (choiceResult.outcome === 'accepted') {
                    console.debug('User accepted the install prompt');
                } else {
                    console.debug('User dismissed the install prompt');
                }
                deferredPrompt = null;
            });
        }
    });
}
