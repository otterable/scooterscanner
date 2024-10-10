const CACHE_NAME = 'tier-scooter-scanner-v6'; // Updated cache version
const STATIC_ASSETS = [
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/js/qr-scanner.umd.min.js',
    '/static/audio/beep.mp3',
    '/static/manifest.json',
    '/static/icons/logo2_192x192.png',
    '/static/icons/logo2_512x512.png'
];

// Install event
self.addEventListener('install', function(event) {
    console.debug('Service Worker installing. Cache version:', CACHE_NAME);
    event.waitUntil(
        caches.open(CACHE_NAME).then(function(cache) {
            console.debug('Caching static assets.');
            return cache.addAll(STATIC_ASSETS);
        })
    );
});

// Activate event
self.addEventListener('activate', function(event) {
    console.debug('Service Worker activating.');
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.filter(function(cacheName) {
                    // Delete old caches
                    return cacheName !== CACHE_NAME;
                }).map(function(cacheName) {
                    console.debug('Deleting old cache:', cacheName);
                    return caches.delete(cacheName);
                })
            );
        })
    );
});

// Fetch event
self.addEventListener('fetch', function(event) {
    const requestUrl = new URL(event.request.url);
    console.debug('Fetch event for:', requestUrl.href);

    // For all requests, use network-first strategy
    event.respondWith(
        fetch(event.request)
            .then(function(networkResponse) {
                console.debug('Network response received for:', requestUrl.href);
                // Optionally, update the cache with the new response for static assets
                if (STATIC_ASSETS.includes(requestUrl.pathname)) {
                    caches.open(CACHE_NAME).then(function(cache) {
                        cache.put(event.request, networkResponse.clone());
                    });
                }
                return networkResponse;
            })
            .catch(function(error) {
                console.debug('Network request failed, serving from cache if available:', requestUrl.href);
                return caches.match(event.request).then(function(cachedResponse) {
                    if (cachedResponse) {
                        return cachedResponse;
                    } else {
                        console.debug('No cached response available.');
                        return new Response('Network error occurred and no cached data available.', {
                            status: 504,
                            statusText: 'Gateway Timeout'
                        });
                    }
                });
            })
    );
});
