const CACHE_NAME = 'tier-scooter-scanner-v4'; // Updated cache version
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/js/qr-scanner.umd.min.js',
    '/static/audio/beep.mp3',
    '/static/manifest.json',
    '/static/icons/logo2_192x192.png',
    '/static/icons/logo2_512x512.png'
];

self.addEventListener('install', function(event) {
    console.debug('Service Worker installing.');
    event.waitUntil(
        caches.open(CACHE_NAME).then(function(cache) {
            console.debug('Caching static assets.');
            return cache.addAll(STATIC_ASSETS);
        })
    );
});

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

self.addEventListener('fetch', function(event) {
    const requestUrl = new URL(event.request.url);
    console.debug('Fetch event for:', requestUrl.href);

    // Define dynamic routes (add more if necessary)
    const dynamicRoutes = ['/lists', '/list/', '/scan', '/save_scan'];

    // Check if the request is for dynamic content
    if (dynamicRoutes.some(route => requestUrl.pathname.startsWith(route))) {
        // Network-first strategy for dynamic content
        event.respondWith(
            fetch(event.request)
                .then(function(networkResponse) {
                    console.debug('Network response received for dynamic content:', requestUrl.href);
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
    } else {
        // Cache-first strategy for static assets
        event.respondWith(
            caches.match(event.request).then(function(cachedResponse) {
                if (cachedResponse) {
                    console.debug('Serving from cache:', requestUrl.href);
                    return cachedResponse;
                }
                console.debug('Fetching from network:', requestUrl.href);
                return fetch(event.request).then(function(networkResponse) {
                    // Optionally cache new static assets
                    // caches.open(CACHE_NAME).then(function(cache) {
                    //     cache.put(event.request, networkResponse.clone());
                    // });
                    return networkResponse;
                });
            })
        );
    }
});
