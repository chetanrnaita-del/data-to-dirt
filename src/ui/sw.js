const CACHE_NAME = 'data-to-dirt-v54';
const ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/logo.png',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  '/css/retro_base.css?v=1.2.5',
  '/css/stardew.css?v=1.2.5',
  '/css/animations.css?v=1.2.5',
  '/js/app.js?v=1.2.5',
  '/js/audio.js?v=1.2.5',
  '/js/particles.js?v=1.2.5',
  '/js/tree.js?v=1.2.5',
  '/js/views/login.js?v=1.2.5',
  '/js/views/student.js?v=1.2.5',
  '/js/views/teacher.js?v=1.2.5',
  '/js/views/admin.js?v=1.2.5',
  '/js/views/analytics.js?v=1.2.5'
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
  const url = new URL(event.request.url);
  // Strictly bypass service worker for OAuth and API routes to prevent duplicate requests / invalid_grant errors
  if (url.pathname.startsWith('/auth/') || url.pathname.startsWith('/api/')) {
    return;
  }

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
