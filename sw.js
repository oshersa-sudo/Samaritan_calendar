// Minimal service worker — required for "install app" on mobile, plus light offline caching.
const CACHE = 'shomron-luach-v21';
const SHELL = ['./', 'index.html', 'Sam_font.ttf', 'manifest.json', 'icon-192.png', 'icon-512.png'];

self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).catch(() => {}));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks =>
    Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
// Network-first so updates always show; fall back to cache when offline.
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).then(r => {
      const copy = r.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy)).catch(() => {});
      return r;
    }).catch(() => caches.match(e.request))
  );
});

// ===================== Web-Push: compose the notification ON-DEVICE =====================
// The Worker sends an empty "wake" push; here we read the saved prefs + the calendar .dat
// and show the right notification (Shabbat times / holiday / rosh chodesh / community).
self.addEventListener('push', e => { e.waitUntil(handlePush()); });

async function handlePush() {
  let prefs = {}; try { prefs = await idbGet('prefs') || {}; } catch (e) {}
  const il = israelParts(new Date());
  const shown = [];
  try {
    if (prefs.shabbat && il.weekday === 5) {          // Friday → Shabbat entry/exit (Holon)
      const t = await shabbatTimes(il);
      if (t) shown.push({ title: 'שבת שלום — זמני שבת (חולון)', body: `כניסת שבת ${t.entry} · יציאת שבת (מוצ״ש) ${t.exit}`, tag: 'shabbat' });
    }
    if (prefs.events) {                                // today/tomorrow: holiday / eve / rosh chodesh / community
      const ev = await upcomingEvent(il);
      if (ev) shown.push({ title: ev.when === 'today' ? 'אירוע היום בלוח' : 'אירוע מחר בלוח', body: ev.names.join(' · '), tag: 'event-' + ev.date, date: ev.date });
    }
  } catch (e) {}
  for (const n of shown)
    await self.registration.showNotification(n.title, { body: n.body, tag: n.tag, icon: 'icon-192.png', badge: 'icon-192.png', dir: 'rtl', lang: 'he', data: { date: n.date || '' } });
  if (!shown.length)   // a push must render something; keep it quiet if nothing applied
    await self.registration.showNotification('חשבון קשט — הלוח השומרוני', { body: 'הלוח מעודכן.', tag: 'idle', icon: 'icon-192.png', silent: true });
}

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const date = e.notification.data && e.notification.data.date;
  e.waitUntil((async () => {
    const wins = await clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const c of wins) { if ('focus' in c) { await c.focus(); if (date) c.postMessage({ goto: date }); return; } }
    if (clients.openWindow) return clients.openWindow(date ? ('./#goto=' + date) : './');
  })());
});

// ---- calendar helpers (mirror the site's decode) ----
const DAT_KEY = 'shomron-luach-5786';
function decodeDat(b64) {
  const raw = atob(b64); let out = '';
  for (let i = 0; i < raw.length; i++) out += String.fromCharCode(raw.charCodeAt(i) ^ DAT_KEY.charCodeAt(i % DAT_KEY.length));
  return decodeURIComponent(escape(out));
}
const _yc = {};
async function fetchYC(gy) {
  if (_yc[gy] !== undefined) return _yc[gy];
  try { const r = await fetch('cal/' + gy + '.dat', { cache: 'no-cache' }); _yc[gy] = r.ok ? JSON.parse(decodeDat(await r.text())) : null; }
  catch (e) { _yc[gy] = null; }
  return _yc[gy];
}
async function findDay(iso) {
  const y = +iso.slice(0, 4);
  for (const gy of [y, y - 1]) { const yc = await fetchYC(gy); if (!yc) continue;
    for (const mo of yc.months) for (const rec of mo.days) if (rec.greg === iso) return rec; }
  return null;
}
async function shabbatTimes(il) {
  const fri = isoOf(il.y, il.m, il.d);
  const sd = new Date(Date.UTC(il.y, il.m - 1, il.d + 1));
  const sat = isoOf(sd.getUTCFullYear(), sd.getUTCMonth() + 1, sd.getUTCDate());
  const f = await findDay(fri), s = await findDay(sat);
  if (!f || !f.sunset) return null;
  return { entry: f.sunset, exit: (s && s.sunset) || f.sunset };
}
const NOTABLE = new Set(['sam', 'moed', 'rosh', 'community']);
async function upcomingEvent(il) {
  const today = isoOf(il.y, il.m, il.d);
  const td = new Date(Date.UTC(il.y, il.m - 1, il.d + 1));
  const tomorrow = isoOf(td.getUTCFullYear(), td.getUTCMonth() + 1, td.getUTCDate());
  for (const [iso, when] of [[today, 'today'], [tomorrow, 'tomorrow']]) {
    const rec = await findDay(iso); if (!rec) continue;
    const names = (rec.festivals || []).filter(f => NOTABLE.has(f.kind)).map(f => f.name);
    if (names.length) return { date: iso, when, names: [...new Set(names)] };
  }
  return null;
}
function israelParts(d) {
  const f = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Jerusalem', year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'short', hour12: false });
  const p = {}; for (const x of f.formatToParts(d)) p[x.type] = x.value;
  const wd = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  return { y: +p.year, m: +p.month, d: +p.day, weekday: wd[p.weekday] };
}
function isoOf(y, m, d) { return y + '-' + String(m).padStart(2, '0') + '-' + String(d).padStart(2, '0'); }

// ---- tiny IndexedDB (shared with the page) for the push prefs ----
function idbOpen() {
  return new Promise((res, rej) => {
    const r = indexedDB.open('sam-push', 1);
    r.onupgradeneeded = () => r.result.createObjectStore('kv');
    r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
  });
}
async function idbGet(k) {
  const db = await idbOpen();
  return new Promise((res, rej) => {
    const t = db.transaction('kv', 'readonly').objectStore('kv').get(k);
    t.onsuccess = () => res(t.result); t.onerror = () => rej(t.error);
  });
}
