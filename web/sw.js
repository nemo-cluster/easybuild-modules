// Service Worker für HPC Module Browser
// Ermöglicht Offline-Funktionalität und Caching

const CACHE_NAME = 'hpc-modules-v1';
const CACHE_URLS = [
    './',
    './index.html',
    './module-browser.js',
    './sample-data.json'
];

// Installation
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(CACHE_URLS))
            .then(() => self.skipWaiting())
    );
});

// Aktivierung
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

// Fetch-Ereignisse
self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Cache-Hit - gib gecachte Version zurück
                if (response) {
                    return response;
                }

                // Kein Cache-Hit - hole von Netzwerk
                return fetch(event.request).then(response => {
                    // Prüfe ob wir eine gültige Antwort haben
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }

                    // Clone die Antwort für Cache
                    const responseToCache = response.clone();

                    caches.open(CACHE_NAME)
                        .then(cache => {
                            cache.put(event.request, responseToCache);
                        });

                    return response;
                });
            })
            .catch(() => {
                // Offline-Fallback für JSON-Daten
                if (event.request.url.includes('.json')) {
                    return caches.match('./sample-data.json');
                }
            })
    );
});