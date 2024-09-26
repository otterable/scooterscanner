console.debug("Main.js loaded.");

let video = document.getElementById('video');
let overlay = document.getElementById('overlay');
let scannedScooterIdDiv = document.getElementById('scanned-scooter-id');
let scooterList = document.getElementById('scooter-list');
let totalScootersSpan = document.getElementById('total-scooters');
let beepSound = document.getElementById('beep-sound');
let listContainer = document.getElementById('list-container');
let isListVisible = false;

console.debug("Variables initialized.");

// Initialize QR Scanner
const qrScanner = new QrScanner(video, result => {
    console.debug("QR code scanned:", result);
    processScannedData(result);
});

console.debug("Starting QR Scanner.");
qrScanner.start().catch(error => {
    console.debug("Error starting QR Scanner:", error);
});

// Process scanned data
function processScannedData(scooterId) {
    console.debug("Processing scanned data:", scooterId);
    // Play beep sound
    beepSound.play();

    // Flash green overlay
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
    if (isListVisible) {
        listContainer.style.display = 'none';
        video.style.height = '90vh';
        console.debug("List container hidden.");
    } else {
        listContainer.style.display = 'block';
        video.style.height = '50vh';
        console.debug("List container shown.");
    }
    isListVisible = !isListVisible;
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
