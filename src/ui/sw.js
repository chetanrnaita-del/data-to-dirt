const CACHE_NAME = 'data-to-dirt-v31';
const ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/logo.png',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  '/css/retro_base.css?v=1.0.9',
  '/css/stardew.css?v=1.0.9',
  '/css/animations.css?v=1.0.9',
  '/js/app.js?v=1.0.9',
  '/js/audio.js?v=1.0.9',
  '/js/particles.js?v=1.0.9',
  '/js/tree.js?v=1.0.9',
  '/js/views/login.js?v=1.0.9',
  '/js/views/student.js?v=1.0.9',
  '/js/views/teacher.js?v=1.0.9',
  '/js/views/admin.js?v=1.0.9',
  '/js/views/analytics.js?v=1.0.9'
];

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
});

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

self.addEventListener('fetch', event => {
  // Add bypass-tunnel-reminder header to all outgoing requests
  let req = event.request;
  try {
    const headers = new Headers(req.headers);
    headers.set('bypass-tunnel-reminder', 'true');
    headers.set('Bypass-Tunnel-Reminder', 'true');
    req = new Request(req, { headers, mode: req.mode === 'navigate' ? undefined : req.mode });
  } catch (e) {
    // Fall back to original request if constructing new request fails
    req = event.request;
  }

  event.respondWith(
    fetch(req).catch(() => caches.match(event.request))
  );
});
