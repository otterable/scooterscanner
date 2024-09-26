self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open('tier-scooter-scanner-v1').then(function(cache) {
            return cache.addAll([
                '/',
                '/scan',
                '/lists',
                '/static/css/style.css',
                '/static/js/main.js',
                '/static/js/qr-scanner.umd.min.js',
                '/static/audio/beep.mp3',
                '/static/manifest.json',
                '/static/icons/logo2_192x192.png',
                '/static/icons/logo2_512x512.png'
            ]);
        })
    );
});

self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request).then(function(response) {
            // Return cached response or fetch from network
            return response || fetch(event.request);
        })
    );
});
