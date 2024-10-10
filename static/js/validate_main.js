console.debug("Validate Main.js loaded.");

let video = document.getElementById('video');
let overlay = document.getElementById('overlay');
let scannedScooterIdDiv = document.getElementById('scanned-scooter-id');
let scannedCountSpan = document.getElementById('scanned-count');
let totalCountSpan = document.getElementById('total-count');
let beepSound = document.getElementById('beep-sound');
let listContainer = document.getElementById('list-container');
let isListVisible = false;
let isPaused = false;
let totalValidated = parseInt(scannedCountSpan.textContent);
let validatedCountSpan = document.getElementById('validated-count');
let scootersLeftSpan = document.getElementById('scooters-left');
let showFullURLs = false; // For toggling URLs

console.debug("Variables initialized.");

// Initialize QR Scanner with new API
const qrScanner = new QrScanner(
    video,
    result => {
        console.debug("QR code scanned:", result);
        processValidationData(result.data);
    },
    {
        returnDetailedScanResult: true,
        maxScansPerSecond: 1,
        preferredCamera: 'environment',
        highlightScanRegion: true,
        highlightCodeOutline: true,
        calculateScanRegion: (video) => {
            const smallestDimension = Math.min(video.videoWidth, video.videoHeight);
            const scanRegionSize = smallestDimension * 0.9;
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

function processValidationData(scooterId) {
    console.debug("Processing validation data:", scooterId);

    const currentTime = Date.now();
    if (currentTime - lastScanTime < SCAN_DELAY) {
        console.debug("Scan ignored due to scan delay.");
        return;
    }
    lastScanTime = currentTime;

    // Remove URL prefix from scooterId for display
    const validPrefixes = ['https://tier.app/', 'https://qr.tier-services.io/'];
    let displayId = scooterId;
    validPrefixes.forEach(prefix => {
        if (scooterId.startsWith(prefix)) {
            displayId = scooterId.slice(prefix.length);
            scooterId = displayId; // Update scooterId to short ID
        }
    });

    // Send validation data to server
    fetch('/save_validation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, scooter_id: scooterId })
    })
    .then(response => response.json())
    .then(data => {
        console.debug("Response from save_validation:", data);
        if (data.status === 'success') {
            totalValidated = data.total_validated;
            scannedCountSpan.textContent = totalValidated;
            validatedCountSpan.textContent = totalValidated;
            scootersLeftSpan.textContent = totalScooters - totalValidated;
            // Play beep sound
            beepSound.play();
            // Flash green overlay
            overlay.style.backgroundColor = 'green';
            overlay.style.opacity = '0.7';
            setTimeout(() => {
                overlay.style.opacity = '0';
            }, 300);
            // Display scanned scooter ID
            scannedScooterIdDiv.textContent = `ID ${displayId} checked in`;
            scannedScooterIdDiv.style.display = 'block';
            setTimeout(() => {
                scannedScooterIdDiv.style.display = 'none';
            }, 5000);
            // Update validation status in the table
            updateValidationStatus(displayId);
            console.debug(`Scooter ID ${scooterId} validated. Total validated: ${totalValidated}/${totalScooters}`);
        } else if (data.status === 'duplicate') {
            console.debug("Scooter ID already validated:", scooterId);
            scannedScooterIdDiv.textContent = `ID ${displayId} already validated`;
            scannedScooterIdDiv.style.display = 'block';
            setTimeout(() => {
                scannedScooterIdDiv.style.display = 'none';
            }, 5000);
        } else if (data.status === 'not_in_list') {
            console.debug("Scooter ID not in the original list:", scooterId);
            // Flash red overlay
            overlay.style.backgroundColor = 'red';
            overlay.style.opacity = '0.7';
            setTimeout(() => {
                overlay.style.opacity = '0';
            }, 300);
            scannedScooterIdDiv.textContent = `Scooter is not in the list`;
            scannedScooterIdDiv.style.display = 'block';
            setTimeout(() => {
                scannedScooterIdDiv.style.display = 'none';
            }, 5000);
        } else {
            console.debug("Error: Unable to validate scan data.");
        }
    })
    .catch(error => {
        console.debug("Fetch error:", error);
    });
}

// Update validation status in the table
function updateValidationStatus(scooterId) {
    const row = document.querySelector(`tr[data-scooter-id='${scooterId}']`);
    if (row) {
        const statusCell = row.querySelector('.validation-status');
        statusCell.textContent = 'Validated';
        // Add unvalidate button if not present
        let actionCell = row.querySelector('td:nth-child(3)');
        if (!actionCell.querySelector('.unvalidate-btn')) {
            actionCell.innerHTML = `<button class="unvalidate-btn" data-scooter-id="${scooterId}">Unvalidate</button>`;
            // Add event listener to the new button
            actionCell.querySelector('.unvalidate-btn').addEventListener('click', unvalidateScooter);
        }
    }
}

// Unvalidate scooter
function unvalidateScooter(event) {
    let scooterId = event.target.getAttribute('data-scooter-id');
    console.debug("Unvalidating scooter:", scooterId);
    if (confirm(`Are you sure you want to unvalidate scooter ID ${scooterId}?`)) {
        // Send unvalidate request to server
        fetch('/unvalidate_scooter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, scooter_id: scooterId })
        })
        .then(response => response.json())
        .then(data => {
            console.debug("Response from unvalidate_scooter:", data);
            if (data.status === 'success') {
                totalValidated = data.total_validated;
                scannedCountSpan.textContent = totalValidated;
                validatedCountSpan.textContent = totalValidated;
                scootersLeftSpan.textContent = totalScooters - totalValidated;
                // Update status in table
                const row = document.querySelector(`tr[data-scooter-id='${scooterId}']`);
                if (row) {
                    const statusCell = row.querySelector('.validation-status');
                    statusCell.textContent = 'Not Validated';
                    // Remove unvalidate button
                    let actionCell = row.querySelector('td:nth-child(3)');
                    actionCell.innerHTML = '';
                }
                console.debug(`Scooter ID ${scooterId} unvalidated. Total validated: ${totalValidated}/${totalScooters}`);
            } else {
                console.debug("Error: Unable to unvalidate scooter.");
            }
        })
        .catch(error => {
            console.debug("Fetch error:", error);
        });
    }
}

// Add event listeners to existing unvalidate buttons
document.querySelectorAll('.unvalidate-btn').forEach(button => {
    button.addEventListener('click', unvalidateScooter);
});

// Toggle list visibility
document.getElementById('toggle-list-btn').addEventListener('click', () => {
    console.debug("Toggle List button clicked.");
    toggleListVisibility();
});

function toggleListVisibility() {
    if (isListVisible) {
        listContainer.style.display = 'none';
        document.getElementById('camera-container').style.display = 'block';
        console.debug("List container hidden, camera shown.");
    } else {
        listContainer.style.display = 'block';
        document.getElementById('camera-container').style.display = 'none';
        console.debug("List container shown, camera hidden.");
    }
    isListVisible = !isListVisible;
}

// Finish validation
document.getElementById('finish-validation-btn').addEventListener('click', () => {
    console.debug("Finish Validation button clicked.");
    if (confirm('Are you sure you want to finish the validation?')) {
        qrScanner.stop();
        console.debug("QR Scanner stopped.");
        alert(`Validation for "${listName}" completed at ${new Date().toLocaleString()} with ${totalValidated}/${totalScooters} scooters validated.`);
        window.location.href = '/';
    } else {
        console.debug("Finish validation canceled.");
    }
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

// Manual Entry
document.getElementById('manual-entry-btn').addEventListener('click', () => {
    console.debug("Manual Entry button clicked.");
    const scooterId = prompt("Enter Scooter ID (5-9 characters):");
    if (scooterId) {
        processValidationData(scooterId.trim());
    }
});

// Toggle Full URLs
document.getElementById('toggle-url-btn').addEventListener('click', () => {
    showFullURLs = !showFullURLs;
    document.querySelectorAll('tr[data-scooter-id]').forEach(row => {
        let scooterIdCell = row.querySelector('.scooter-id-cell');
        if (showFullURLs) {
            scooterIdCell.textContent = row.getAttribute('data-full-id');
        } else {
            scooterIdCell.textContent = row.getAttribute('data-scooter-id');
        }
    });
    console.debug("Toggled full URLs:", showFullURLs);
});
