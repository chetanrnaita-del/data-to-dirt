const CACHE_NAME = 'data-to-dirt-v75';
const ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/logo.png',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  '/css/retro_base.css?v=1.5.0',
  '/css/stardew.css?v=1.5.0',
  '/css/animations.css?v=1.5.0',
  '/js/app.js?v=1.5.0',
  '/js/audio.js?v=1.5.0',
  '/js/particles.js?v=1.5.0',
  '/js/tree.js?v=1.5.0',
  '/js/views/login.js?v=1.5.0',
  '/js/views/student.js?v=1.5.0',
  '/js/views/teacher.js?v=1.5.0',
  '/js/views/admin.js?v=1.5.0',
  '/js/views/analytics.js?v=1.5.0'
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
            console.log('[SW] Purging old cache:', cacheName);
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
    req = event.request;
  }

  // Network-first strategy for scripts, stylesheets, and navigation HTML to guarantee freshest client build
  if (req.mode === 'navigate' || url.pathname.endsWith('.js') || url.pathname.endsWith('.css') || url.pathname.endsWith('.html') || url.pathname === '/') {
    event.respondWith(
      fetch(req).then(networkResponse => {
        if (networkResponse && networkResponse.status === 200) {
          const respClone = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, respClone));
        }
        return networkResponse;
      }).catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then(response => response || fetch(req))
  );
});
