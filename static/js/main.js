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

console.debug("Variables initialized.");

// Initialize QR Scanner with new API
const qrScanner = new QrScanner(
    video,
    result => {
        console.debug("QR code scanned:", result);
        processScannedData(result.data); // Use result.data instead of result
    },
    {
        returnDetailedScanResult: true, // Use new API
        maxScansPerSecond: 1, // Limit scans to 1 per second
        preferredCamera: 'environment', // Use the back camera
        highlightScanRegion: true,
        highlightCodeOutline: true,
        calculateScanRegion: (video) => {
            // Adjust the scan region to cover more area (zoom out effect)
            const smallestDimension = Math.min(video.videoWidth, video.videoHeight);
            const scanRegionSize = smallestDimension * 0.9; // Adjust as needed
            return {
                x: (video.videoWidth - scanRegionSize) / 2,
                y: (video.videoHeight - scanRegionSize) / 2,
                width: scanRegionSize,
                height: scanRegionSize,
            };
        }
    }
);

console.debug("Starting QR Scanner.");
qrScanner.start().then(() => {
    console.debug("QR Scanner started successfully.");
}).catch(error => {
    console.debug("Error starting QR Scanner:", error);
});

// Variables for scan throttling
let lastScanTime = 0;
const SCAN_DELAY = 1000; // 1 second delay between scans

// Process scanned data
function processScannedData(scooterId) {
    console.debug("Processing scanned data:", scooterId);

    const currentTime = Date.now();
    if (currentTime - lastScanTime < SCAN_DELAY) {
        console.debug("Scan ignored due to scan delay.");
        return;
    }
    lastScanTime = currentTime;

    // Validate scooter ID
    const validPrefixes = ['https://tier.app/', 'https://qr.tier-services.io/'];
    if (!validPrefixes.some(prefix => scooterId.startsWith(prefix))) {
        console.debug("Invalid scooter ID prefix:", scooterId);
        // Display error message
        scannedScooterIdDiv.textContent = "Invalid QR code";
        scannedScooterIdDiv.style.display = 'block';
        setTimeout(() => {
            scannedScooterIdDiv.style.display = 'none';
        }, 5000);
        return;
    }

    // Remove URL prefix from scooterId for display
    let displayId = scooterId;
    validPrefixes.forEach(prefix => {
        if (scooterId.startsWith(prefix)) {
            displayId = scooterId.slice(prefix.length);
        }
    });

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
            // Play beep sound
            beepSound.play();

            // Flash green overlay
            overlay.style.backgroundColor = 'green';
            overlay.style.opacity = '0.7';
            setTimeout(() => {
                overlay.style.opacity = '0';
            }, 300);

            // Display scanned scooter ID
            scannedScooterIdDiv.textContent = displayId;
            scannedScooterIdDiv.style.display = 'block';
            setTimeout(() => {
                scannedScooterIdDiv.style.display = 'none';
            }, 5000);

            let listItem = document.createElement('li');
            listItem.dataset.scanId = data.scan_id; // Store the scan ID

            let timestamp = new Date();
            let formattedTime = timestamp.getHours().toString().padStart(2, '0') + ':' +
                                timestamp.getMinutes().toString().padStart(2, '0') + ' | ' +
                                timestamp.getDate().toString().padStart(2, '0') + '.' +
                                (timestamp.getMonth() + 1).toString().padStart(2, '0') + '.' +
                                timestamp.getFullYear();

            listItem.innerHTML = `<span class="scooter-id" data-full-id="${scooterId}" data-short-id="${displayId}">${displayId}</span> - ${formattedTime} <button class="delete-scan-btn" data-scan-id="${data.scan_id}">Delete</button>`;
            scooterList.insertBefore(listItem, scooterList.firstChild);
            totalScootersSpan.textContent = data.total;
            console.debug(`Scooter ID ${scooterId} added to list. Total scooters: ${data.total}`);
        } else if (data.status === 'duplicate') {
            console.debug("Duplicate scooter ID detected:", scooterId);
            // Do not flash red or play beep
            scannedScooterIdDiv.textContent = "Duplicate ID: " + displayId;
            scannedScooterIdDiv.style.display = 'block';
            setTimeout(() => {
                scannedScooterIdDiv.style.display = 'none';
            }, 5000);
        } else if (data.status === 'invalid') {
            console.debug("Invalid scooter ID:", scooterId);
            scannedScooterIdDiv.textContent = "Invalid QR code";
            scannedScooterIdDiv.style.display = 'block';
            setTimeout(() => {
                scannedScooterIdDiv.style.display = 'none';
            }, 5000);
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

function toggleListVisibility() {
    if (isListVisible) {
        listContainer.style.display = 'none';
        console.debug("List container hidden.");
    } else {
        listContainer.style.display = 'block';
        console.debug("List container shown.");
    }
    isListVisible = !isListVisible;
}

// Finish list
document.getElementById('finish-list-btn').addEventListener('click', () => {
    console.debug("Finish List button clicked.");
    if (confirm('Are you sure you want to finish the list?')) {
        qrScanner.stop();
        console.debug("QR Scanner stopped.");
        alert(`List "${listName}" saved at ${new Date().toLocaleString()} with ${totalScootersSpan.textContent} scooters.`);
        window.location.href = '/';
    } else {
        console.debug("Finish list canceled.");
    }
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
});

// Adjust camera size based on screen height
function adjustCameraSize() {
    const availableHeight = window.innerHeight;
    const buttonContainerHeight = document.getElementById('button-container').offsetHeight;
    const desiredCameraHeight = availableHeight - buttonContainerHeight;
    document.getElementById('camera-container').style.height = desiredCameraHeight + 'px';
    console.debug("Camera size adjusted.");
}

// Initial adjustment
adjustCameraSize();

// Handle window resize
window.addEventListener('resize', adjustCameraSize);

// Event delegation for delete buttons in the list
scooterList.addEventListener('click', function(event) {
    if (event.target.classList.contains('delete-scan-btn')) {
        const scanId = event.target.dataset.scanId;
        const scooterIdElement = event.target.parentElement.querySelector('.scooter-id');
        const scooterId = scooterIdElement.dataset.shortId;
        if (confirm(`Are you sure you want to delete ID ${scooterId}?`)) {
            fetch(`/delete_scan/${scanId}`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    console.debug(`Scan ${scanId} deleted successfully.`);
                    // Remove the list item
                    event.target.parentElement.remove();
                    // Update total scooters count
                    totalScootersSpan.textContent = parseInt(totalScootersSpan.textContent) - 1;
                } else {
                    console.debug(`Error deleting scan ${scanId}.`);
                    alert('Error deleting scooter ID.');
                }
            });
        }
    }
});

// Add focus mode
video.addEventListener('click', () => {
    console.debug('Video clicked. Attempting to refocus camera.');
    const track = video.srcObject.getVideoTracks()[0];
    const capabilities = track.getCapabilities();
    if (capabilities.focusMode && capabilities.focusDistance) {
        console.debug('Camera supports focusMode and focusDistance. Setting focusMode to "manual".');
        const focusDistance = (capabilities.focusDistance.max + capabilities.focusDistance.min) / 2;
        track.applyConstraints({
            advanced: [{ focusMode: 'manual', focusDistance: focusDistance }]
        }).then(() => {
            console.debug('Focus adjusted successfully.');
        }).catch(err => {
            console.debug('Error adjusting focus:', err);
        });
    } else {
        console.debug('Camera does not support focusMode or focusDistance.');
    }
});
