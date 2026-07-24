const CACHE = 'teenmind-v2';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './icon.svg',
];

// Install — cache core assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(ASSETS))
      .catch((err) => console.error('Cache install failed:', err))
  );
  self.skipWaiting();
});

// Activate — delete old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
        .catch((err) => console.error('Cache activation failed:', err))
    )
  );
  self.clients.claim();
});

// Fetch — cache-first for same-origin assets, network-only for everything else
self.addEventListener('fetch', (event) => {
  // Let WebSocket, external fonts, and API calls pass through untouched
  const url = new URL(event.request.url);
  if (url.origin !== location.origin) return;
  if (event.request.method !== 'GET') return;

  // Network-first for page navigations so updates are picked up immediately;
  // fall back to cache when offline. Cache-first for other static assets.
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE).then((cache) => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then(
      (cached) => cached || fetch(event.request)
    )
  );
});
