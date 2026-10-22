const CACHE_NAME = 'data-to-dirt-v22';
const ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/logo.png',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  '/css/retro_base.css',
  '/css/stardew.css',
  '/css/animations.css',
  '/js/app.js',
  '/js/audio.js',
  '/js/particles.js',
  '/js/tree.js',
  '/js/views/login.js',
  '/js/views/student.js',
  '/js/views/teacher.js',
  '/js/views/admin.js'
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
