// battery_main.js
console.debug("Battery Main.js loaded.");

let video = document.getElementById('video');
let overlay = document.getElementById('overlay');
let scannedBatteryIdDiv = document.getElementById('scanned-battery-id');
let batteryList = document.getElementById('battery-list');
let totalBatteriesSpan = document.getElementById('total-batteries');
let zoomSlider = document.getElementById('zoom-slider');

console.debug("Battery scanning variables initialized.");

// Initialize QR Scanner
const qrScanner = new QrScanner(
    video,
    result => {
        console.debug("QR code scanned:", result);
        processBatteryData(result.data);
    },
    {
        returnDetailedScanResult: true,
        maxScansPerSecond: 1,
        preferredCamera: 'environment',
        highlightScanRegion: true,
        highlightCodeOutline: true,
        calculateScanRegion: (video) => {
            // Use full video dimensions to reduce zoomed-in effect
            return {
                x: 0,
                y: 0,
                width: video.videoWidth,
                height: video.videoHeight,
            };
        }
    }
);

console.debug("Starting QR Scanner for battery scanning.");
qrScanner.start().then(() => {
    console.debug("QR Scanner started successfully for battery scanning.");
    // After starting, set initial zoom level
    setupZoomSlider();
}).catch(error => {
    console.debug("Error starting QR Scanner:", error);
});

// Variables for scan throttling
let lastScanTime = 0;
const SCAN_DELAY = 1000; // 1 second delay between scans

// Process Scanned Battery Data
function processBatteryData(batteryId) {
    console.debug("Processing battery scan:", batteryId);

    const currentTime = Date.now();
    if (currentTime - lastScanTime < SCAN_DELAY) {
        console.debug("Scan ignored due to scan delay.");
        return;
    }
    lastScanTime = currentTime;

    // Send battery data to server
    fetch('/save_battery_scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, battery_id: batteryId })
    })
    .then(response => response.json())
    .then(data => {
        console.debug("Response from save_battery_scan:", data);
        if (data.status === 'success') {
            // Flash green overlay
            overlay.style.backgroundColor = 'green';
            overlay.style.opacity = '0.7';
            setTimeout(() => {
                overlay.style.opacity = '0';
            }, 300);

            // Display scanned battery ID
            scannedBatteryIdDiv.textContent = batteryId;
            scannedBatteryIdDiv.style.display = 'block';
            setTimeout(() => {
                scannedBatteryIdDiv.style.display = 'none';
            }, 5000);

            // Add to battery list
            let listItem = document.createElement('li');
            listItem.textContent = batteryId;
            batteryList.insertBefore(listItem, batteryList.firstChild);
            totalBatteriesSpan.textContent = data.total;
            console.debug(`Battery ID ${batteryId} added to list. Total batteries: ${data.total}`);
        } else if (data.status === 'duplicate') {
            console.debug("Duplicate battery ID detected:", batteryId);
            scannedBatteryIdDiv.textContent = "Duplicate ID: " + batteryId;
            scannedBatteryIdDiv.style.display = 'block';
            setTimeout(() => {
                scannedBatteryIdDiv.style.display = 'none';
            }, 5000);
        } else {
            console.debug("Error: Unable to save battery scan data.");
        }
    })
    .catch(error => {
        console.debug("Fetch error:", error);
    });
}

// Finish list
document.getElementById('finish-list-btn').addEventListener('click', () => {
    console.debug("Finish List button clicked.");
    if (confirm('Are you sure you want to finish the battery list?')) {
        qrScanner.stop();
        console.debug("QR Scanner stopped.");
        alert(`Battery List "${listName}" saved at ${new Date().toLocaleString()} with ${totalBatteriesSpan.textContent} batteries.`);
        window.location.href = '/';
    } else {
        console.debug("Finish battery list canceled.");
    }
});

// Manual Entry
document.getElementById('manual-entry-btn').addEventListener('click', () => {
    console.debug("Manual Entry button clicked.");
    const batteryId = prompt("Enter Battery ID:");
    if (batteryId) {
        processBatteryData(batteryId.trim());
    }
});

// Adjust camera size based on screen height
function adjustCameraSize() {
    const availableHeight = window.innerHeight;
    const buttonContainerHeight = document.getElementById('button-container').offsetHeight;
    const zoomContainerHeight = document.getElementById('zoom-container').offsetHeight || 0;
    const desiredCameraHeight = availableHeight - buttonContainerHeight - zoomContainerHeight;
    document.getElementById('camera-container').style.height = desiredCameraHeight + 'px';
    console.debug("Camera size adjusted.");
}

// Initial adjustment
adjustCameraSize();

// Handle window resize
window.addEventListener('resize', adjustCameraSize);

// Tap-to-focus functionality
video.addEventListener('click', async (event) => {
    console.debug('Video clicked for focus');
    const rect = video.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const track = video.srcObject.getVideoTracks()[0];
    const capabilities = track.getCapabilities();
    if (capabilities.focusMode && capabilities.focusMode.includes('single-shot')) {
        await track.applyConstraints({
            advanced: [{
                focusMode: 'single-shot',
                pointsOfInterest: [{ x: x / rect.width, y: y / rect.height }]
            }]
        });
        console.debug('Focus triggered at point:', x, y);
    } else {
        console.debug('Focus is not supported by this device.');
    }
});

// Zoom control
zoomSlider.addEventListener('input', () => {
    const zoomLevel = parseFloat(zoomSlider.value);
    setZoom(zoomLevel);
});

// Function to set zoom level
async function setZoom(zoomLevel) {
    const track = video.srcObject.getVideoTracks()[0];
    const capabilities = track.getCapabilities();
    if (capabilities.zoom) {
        const settings = track.getSettings();
        const min = capabilities.zoom.min || 1;
        const max = capabilities.zoom.max || 1;
        const newZoomLevel = Math.max(min, Math.min(zoomLevel, max));
        await track.applyConstraints({
            advanced: [{ zoom: newZoomLevel }]
        });
        console.debug(`Zoom level set to ${newZoomLevel}`);
    } else {
        console.debug('Zoom is not supported by this device.');
        document.getElementById('zoom-container').style.display = 'none'; // Hide zoom slider if not supported
    }
}

// Adjust zoom slider range based on camera capabilities
async function setupZoomSlider() {
    const track = video.srcObject.getVideoTracks()[0];
    const capabilities = track.getCapabilities();
    if (capabilities.zoom) {
        zoomSlider.min = capabilities.zoom.min;
        zoomSlider.max = capabilities.zoom.max;
        zoomSlider.step = capabilities.zoom.step || 0.1;
        zoomSlider.value = capabilities.zoom.min;
        console.debug('Zoom capabilities:', capabilities.zoom);
    } else {
        console.debug('Zoom is not supported by this device.');
        document.getElementById('zoom-container').style.display = 'none'; // Hide zoom slider if not supported
    }
}

// Wait until video stream is ready
video.addEventListener('loadedmetadata', () => {
    setupZoomSlider();
    adjustCameraSize();
});
