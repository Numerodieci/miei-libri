const CACHE_NAME = 'miei-libri-v13';
const ASSETS = [
  './',
  'index.html',
  'viewer.html',
  'quiz.html',
  'privacy.html',
  'home.css',
  'fonts.css',
  'qrcode.js',
  'quiz-data.js',
  'manifest.webmanifest',
  'search-index.json',
  'favicon.ico',
  'icons/apple-touch-icon-180.png',
  'icons/icon-1024.png',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'icons/icon-maskable-192.png',
  'icons/icon-maskable-512.png',
  'fonts/baloo-2-400-800-latin-ext.woff2',
  'fonts/baloo-2-400-800-latin.woff2',
  'fonts/bebas-neue-400-latin-ext.woff2',
  'fonts/bebas-neue-400-latin.woff2',
  'fonts/cinzel-400-700-latin-ext.woff2',
  'fonts/cinzel-400-700-latin.woff2',
  'fonts/comfortaa-400-700-latin-ext.woff2',
  'fonts/comfortaa-400-700-latin.woff2',
  'fonts/cormorant-garamond-400-700-latin-ext.woff2',
  'fonts/cormorant-garamond-400-700-latin.woff2',
  'fonts/exo-2-400-700-latin-ext.woff2',
  'fonts/exo-2-400-700-latin.woff2',
  'fonts/fredoka-400-latin-ext.woff2',
  'fonts/fredoka-400-latin.woff2',
  'fonts/fredoka-500-latin-ext.woff2',
  'fonts/fredoka-500-latin.woff2',
  'fonts/fredoka-600-latin-ext.woff2',
  'fonts/fredoka-600-latin.woff2',
  'fonts/fredoka-700-latin-ext.woff2',
  'fonts/fredoka-700-latin.woff2',
  'fonts/karla-400-700-latin-ext.woff2',
  'fonts/karla-400-700-latin.woff2',
  'fonts/lato-400-latin-ext.woff2',
  'fonts/lato-400-latin.woff2',
  'fonts/lato-700-latin-ext.woff2',
  'fonts/lato-700-latin.woff2',
  'fonts/lato-900-latin-ext.woff2',
  'fonts/lato-900-latin.woff2',
  'fonts/lora-400-700-latin-ext.woff2',
  'fonts/lora-400-700-latin.woff2',
  'fonts/nunito-400-800-latin-ext.woff2',
  'fonts/nunito-400-800-latin.woff2',
  'fonts/nunito-sans-400-800-latin-ext.woff2',
  'fonts/nunito-sans-400-800-latin.woff2',
  'fonts/orbitron-400-900-latin.woff2',
  'fonts/patrick-hand-400-latin-ext.woff2',
  'fonts/patrick-hand-400-latin.woff2',
  'fonts/playfair-display-400-900-latin-ext.woff2',
  'fonts/playfair-display-400-900-latin.woff2',
  'fonts/quicksand-400-700-latin-ext.woff2',
  'fonts/quicksand-400-700-latin.woff2',
  'fonts/rubik-400-700-latin-ext.woff2',
  'fonts/rubik-400-700-latin.woff2',
  'fonts/source-sans-3-400-700-latin-ext.woff2',
  'fonts/source-sans-3-400-700-latin.woff2',
  'arte-e-immagine.html',
  'educazione-civica.html',
  'educazione-fisica.html',
  'geografia.html',
  'inglese.html',
  'italiano.html',
  'matematica.html',
  'musica.html',
  'religione.html',
  'scienze.html',
  'storia.html',
  'tecnologia-informatica.html',
];

// Salva in cache solo risposte valide: un 404 o un 500 non devono diventare
// contenuto offline. Le risposte parziali (206) non sono memorizzabili.
const putInCache = (request, response) => {
  if (!response || !response.ok || response.status === 206) return;
  const copy = response.clone();
  caches.open(CACHE_NAME)
    .then((cache) => cache.put(request, copy))
    .catch(() => {});
};

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
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  // Non intercettare richieste verso altri domini (es. Google Fonts).
  if (url.origin !== self.location.origin) return;

  // Pagine, dati e manifest: network-first così gli aggiornamenti arrivano
  // subito; in assenza di rete si ricade sulla cache.
  const isContent =
    req.mode === 'navigate' ||
    /\.(html|json|webmanifest)$/.test(url.pathname) ||
    /quiz-data\.js$/.test(url.pathname) ||
    url.pathname.endsWith('/');

  if (isContent) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          putInCache(req, res);
          return res;
        })
        .catch(() =>
          // ignoreSearch: le pagine sono salvate senza parametri, ma il viewer
          // viene aperto come viewer.html?libro=... e deve funzionare offline.
          caches.match(req, { ignoreSearch: true })
            .then((cached) => cached || caches.match('index.html'))
        )
    );
    return;
  }

  // Asset statici (icone, css, qrcode.js, favicon): cache-first.
  event.respondWith(
    caches.match(req).then(
      (cached) =>
        cached ||
        fetch(req)
          .then((res) => {
            putInCache(req, res);
            return res;
          })
          .catch(() => cached)
    )
  );
});
