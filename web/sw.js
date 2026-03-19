// Service Worker for bwForCluster NEMO 2 Easybuild Module Browser
// Enables offline functionality and caching

const CACHE_NAME = 'hpc-modules-v2';
const CACHE_URLS = [
    './',
    './index.html',
    './module-browser.js',
    './sample-data.json',
    './metadata.json',
];

// Installation
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(CACHE_URLS))
            .then(() => self.skipWaiting())
    );
});

// Activation
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch events
self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Cache hit - return cached version
                if (response) {
                    return response;
                }

                // No cache hit - fetch from network
                return fetch(event.request).then(response => {
                    // Check if we have a valid response
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }

                    // Clone the response for cache
                    const responseToCache = response.clone();

                    caches.open(CACHE_NAME)
                        .then(cache => {
                            cache.put(event.request, responseToCache);
                        });

                    return response;
                });
            })
            .catch(() => {
                // Offline fallback for JSON data
                if (event.request.url.includes('.json')) {
                    return caches.match('./sample-data.json');
                }
            })
    );
});