// Watch build service worker — scope /watch/ only, so it never disturbs the
// full site's worker at the root (which owns Web-Push).
//
// Strategy: stale-while-revalidate. A watch face has to paint instantly and
// often has no link of its own, so we always answer from cache when we have
// it and refresh in the background for the next launch.
const CACHE = 'sam-watch-v1';
const SHELL = ['./', 'index.html', 'manifest.json', '../Sam_font.ttf', '../icon-192.png'];

// Israel's calendar year, not the device's — matches the page's own date logic.
function israelYear() {
  const p = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Jerusalem', year: 'numeric' })
    .formatToParts(new Date()).find(x => x.type === 'year');
  return +p.value;
}
// Only the years the page can actually reach (it probes y-1 … y+1) — three
// ~93 KB files, never the full 103 MB archive.
function dataFiles() {
  const y = israelYear();
  return [y - 1, y, y + 1].map(gy => '../cal/' + gy + '.dat');
}

self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(async c => {
    await c.addAll(SHELL).catch(() => {});
    // Data files are best-effort: a missing year must not fail the install.
    await Promise.all(dataFiles().map(u => c.add(u).catch(() => {})));
  }).catch(() => {}));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== CACHE && k.startsWith('sam-watch-')).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  if (new URL(req.url).origin !== self.location.origin) return;   // let the network handle anything remote

  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const hit = await cache.match(req, { ignoreSearch: true });

    const fresh = fetch(req).then(r => {
      if (r && r.ok) cache.put(req, r.clone()).catch(() => {});
      return r;
    }).catch(() => null);

    if (hit) { e.waitUntil(fresh); return hit; }                  // instant paint, refresh behind it
    return (await fresh) || Response.error();
  })());
});

// Let the page ask for a specific year up front (e.g. before a year rollover).
self.addEventListener('message', e => {
  const gy = e.data && e.data.cacheYear;
  if (gy) e.waitUntil(caches.open(CACHE).then(c => c.add('../cal/' + gy + '.dat')).catch(() => {}));
});
