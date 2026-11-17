const CACHE_NAME = 'miei-libri-v4';
const ASSETS = [
  './',
  './index.html',
  './viewer.html',
  './home.css',
  './manifest.webmanifest',
  './search-index.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './arte-e-immagine.html',
  './educazione-civica.html',
  './educazione-fisica.html',
  './geografia.html',
  './inglese.html',
  './italiano.html',
  './matematica.html',
  './musica.html',
  './religione.html',
  './scienze.html',
  './storia.html',
  './tecnologia-informatica.html'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => {
      return cached || fetch(event.request).then((response) => {
        if (event.request.method === 'GET' && response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => cached);
    })
  );
});
