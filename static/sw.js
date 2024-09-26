self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open('tier-scooter-scanner-v1').then(function(cache) {
            return cache.addAll([
                '/',
                '/static/css/style.css',
                '/static/js/main.js',
                '/static/js/qr-scanner.min.js',
                '/static/audio/beep.mp3',
                '/static/manifest.json',
                '/templates/index.html',
                '/templates/scan.html'
            ]);
        })
    );
});

self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request).then(function(response) {
            return response || fetch(event.request);
        })
    );
});
