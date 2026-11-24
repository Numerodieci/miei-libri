#!/usr/bin/env node
/**
 * Verifica offline del service worker con Chrome pilotato via DevTools Protocol.
 *
 * Controlla, su un profilo Chrome pulito:
 *  1. il service worker si attiva e il precache si popola (>= 75 voci)
 *  2. una URL inesistente visitata online restituisce la pagina 404 del server
 *  3. con il server spento, la stessa URL viene servita dal fallback (home)
 *  4. nessuna voce in cache ha status diverso da 2xx
 *  5. con il server spento funzionano home, una pagina materia e il viewer
 *  6. i font sono presenti in cache e leggibili
 *
 * Uso:  python -m http.server non serve: lo script avvia e ferma lui il server.
 *       node tools/verify-offline.mjs [cartella-progetto]
 *
 * Esce con 0 se tutti i controlli passano, 1 altrimenti.
 */

import { spawn } from 'node:child_process';
import { readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';

const ROOT = path.resolve(process.argv[2] || process.cwd());
const PORT = Number(process.env.PWA_PORT || 4173);
const CDP_PORT = Number(process.env.PWA_CDP_PORT || 9333);
const ORIGIN = `http://127.0.0.1:${PORT}`;
const CHROME = process.env.PWA_CHROME
  || 'C:/Program Files/Google/Chrome/Application/chrome.exe';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
let failures = 0;

function report(ok, label, detail = '') {
  if (!ok) failures += 1;
  console.log(`  [${ok ? 'OK' : 'FAIL'}] ${label}${detail ? ' — ' + detail : ''}`);
}

async function waitFor(label, fn, timeoutMs = 30000, intervalMs = 250) {
  const started = Date.now();
  for (;;) {
    try {
      const value = await fn();
      if (value) return value;
    } catch {
      /* riprova */
    }
    if (Date.now() - started > timeoutMs) {
      throw new Error(`timeout in attesa di: ${label}`);
    }
    await sleep(intervalMs);
  }
}

// ---------------------------------------------------------------- service worker
function cacheNameFromSource() {
  const source = readFileSync(path.join(ROOT, 'sw.js'), 'utf8');
  const match = source.match(/CACHE_NAME\s*=\s*'([^']+)'/);
  if (!match) throw new Error('CACHE_NAME non trovato in sw.js');
  return match[1];
}

// ---------------------------------------------------------------- server statico
async function startServer() {
  const child = spawn('python', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], {
    cwd: ROOT,
    stdio: 'ignore',
    windowsHide: true,
  });
  await waitFor('server statico', async () => {
    const res = await fetch(`${ORIGIN}/index.html`);
    return res.ok;
  });
  return child;
}

async function stopServer(child) {
  if (!child) return;
  child.kill();
  await waitFor('server spento', async () => {
    try {
      await fetch(`${ORIGIN}/index.html`, { signal: AbortSignal.timeout(1000) });
      return false;
    } catch {
      return true;
    }
  }, 15000);
}

// ---------------------------------------------------------------- CDP
class Session {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.id && this.pending.has(message.id)) {
        const { resolve, reject } = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) reject(new Error(JSON.stringify(message.error)));
        else resolve(message.result);
      }
    };
  }

  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`timeout CDP su ${method}`));
        }
      }, 30000);
    });
  }

  async evaluate(expression) {
    const result = await this.send('Runtime.evaluate', {
      expression,
      awaitPromise: true,
      returnByValue: true,
    });
    if (result.exceptionDetails) {
      throw new Error(result.exceptionDetails.text || 'errore JS nella pagina');
    }
    return result.result.value;
  }

  async navigate(url) {
    await this.send('Page.navigate', { url });
    await waitFor(`caricamento ${url}`, async () => {
      const ready = await this.evaluate(
        'document.readyState === "complete" && location.href.indexOf(' +
        JSON.stringify(url.split('?')[0]) + ') === 0');
      return ready;
    }, 20000);
  }
}

async function launchChrome(profile) {
  const child = spawn(CHROME, [
    '--headless=new',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-extensions',
    '--disable-background-networking',
    `--user-data-dir=${profile}`,
    `--remote-debugging-port=${CDP_PORT}`,
    'about:blank',
  ], { stdio: 'ignore', windowsHide: true });

  await waitFor('Chrome DevTools', async () => {
    const res = await fetch(`http://127.0.0.1:${CDP_PORT}/json/version`);
    return res.ok;
  }, 30000);

  const created = await fetch(
    `http://127.0.0.1:${CDP_PORT}/json/new?${encodeURIComponent('about:blank')}`,
    { method: 'PUT' });
  const target = await created.json();

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = () => reject(new Error('connessione WebSocket CDP fallita'));
  });

  const session = new Session(ws);
  await session.send('Page.enable');
  await session.send('Runtime.enable');
  return { child, session };
}

// ---------------------------------------------------------------- test
async function main() {
  console.log('Verifica offline PWA — I Miei Libri');
  console.log('Cartella: ' + ROOT);

  let cacheName;
  try {
    cacheName = cacheNameFromSource();
    console.log('Cache attesa: ' + cacheName);
  } catch (error) {
    console.error('Impossibile leggere CACHE_NAME: ' + error.message);
    return 1;
  }

  const profile = mkdtempSync(path.join(tmpdir(), 'pwa-offline-'));
  let server = null;
  let chrome = null;

  try {
    server = await startServer();
    const launched = await launchChrome(profile);
    chrome = launched.child;
    const session = launched.session;

    // 1. service worker attivo
    await session.navigate(`${ORIGIN}/index.html`);
    const ready = await session.evaluate(
      'Promise.race([navigator.serviceWorker.ready.then(() => true),' +
      ' new Promise((r) => setTimeout(() => r(false), 20000))])');
    report(ready === true, 'service worker attivo');

    // 2. precache popolato
    const count = await waitFor('precache popolato', async () => {
      const value = await session.evaluate(
        `caches.open(${JSON.stringify(cacheName)}).then((c) => c.keys()).then((k) => k.length)`);
      return value >= 75 ? value : 0;
    }, 40000);
    report(count >= 75, 'precache offline popolato', `${count} voci`);

    // 3. online: la URL inesistente risponde 404 del server
    await session.navigate(`${ORIGIN}/pagina-perduta-404.html`);
    const online = await session.evaluate(
      'JSON.stringify({title: document.title, len: document.body.innerHTML.length})');
    const onlineInfo = JSON.parse(online);
    report(onlineInfo.title === 'Error response', 'online: URL inesistente dà 404',
      `${onlineInfo.len} byte`);

    // 3b. un asset inesistente non deve finire in cache (ramo cache-first)
    const assetProbe = JSON.parse(await session.evaluate(`
      (async () => {
        const response = await fetch('/asset-inesistente.png');
        const cache = await caches.open(${JSON.stringify(cacheName)});
        const cached = await cache.match('/asset-inesistente.png');
        return JSON.stringify({ status: response.status, cached: !!cached });
      })()`));
    report(assetProbe.status === 404 && assetProbe.cached === false,
      'asset inesistente non memorizzato',
      `status ${assetProbe.status}, in cache: ${assetProbe.cached}`);

    // 4. offline: la stessa URL deve ricadere sulla home
    await stopServer(server);
    server = null;
    await session.navigate(`${ORIGIN}/pagina-perduta-404.html`);
    const offline = JSON.parse(await session.evaluate(
      'JSON.stringify({title: document.title, len: document.body.innerHTML.length,' +
      ' cards: document.querySelectorAll(".card").length,' +
      ' text: document.body.innerText.slice(0, 200)})'));
    const fallbackOk = offline.title.includes('I Miei Libri')
      && offline.cards === 12
      && !offline.text.includes('Error code');
    report(fallbackOk, 'offline: URL inesistente ricade sulla home',
      `${offline.cards} card, ${offline.len} byte, titolo "${offline.title}"`);

    // 5. nessuna risposta di errore in cache
    const cacheAudit = JSON.parse(await session.evaluate(`
      (async () => {
        const names = await caches.keys();
        let total = 0, bad = 0;
        for (const name of names) {
          const cache = await caches.open(name);
          for (const request of await cache.keys()) {
            const response = await cache.match(request);
            total += 1;
            if (!response || !response.ok) bad += 1;
          }
        }
        return JSON.stringify({ names, total, bad });
      })()`));
    report(cacheAudit.bad === 0,
      'nessuna risposta non-2xx in cache',
      `${cacheAudit.total} voci, ${cacheAudit.bad} non valide`);

    // 6. regressione: pagine reali offline
    await session.navigate(`${ORIGIN}/storia.html`);
    const storia = JSON.parse(await session.evaluate(
      'JSON.stringify({title: document.title, len: document.body.innerHTML.length})'));
    report(storia.title.includes('Storia') && storia.len > 10000,
      'offline: pagina materia', `${storia.len} byte`);

    await session.navigate(`${ORIGIN}/viewer.html?libro=scienze.html`);
    const viewer = JSON.parse(await session.evaluate(
      'JSON.stringify({title: document.title, src: document.getElementById("frame")' +
      ' ? document.getElementById("frame").getAttribute("src") : null})'));
    report(viewer.title.startsWith('scienze') && viewer.src === 'scienze.html',
      'offline: viewer con parametro', `titolo "${viewer.title}"`);

    await session.navigate(`${ORIGIN}/index.html`);
    const home = JSON.parse(await session.evaluate(
      'JSON.stringify({title: document.title, cards: document.querySelectorAll(".card").length})'));
    report(home.title.includes('I Miei Libri') && home.cards === 12,
      'offline: home con 12 materie', `${home.cards} card`);

    // 7. font in cache e leggibili
    const font = JSON.parse(await session.evaluate(`
      (async () => {
        const cache = await caches.open(${JSON.stringify(cacheName)});
        const response = await cache.match('fonts/lato-400-latin.woff2');
        if (!response) return JSON.stringify({ found: false });
        const buffer = await response.arrayBuffer();
        return JSON.stringify({ found: true, ok: response.ok, bytes: buffer.byteLength });
      })()`));
    report(font.found && font.ok && font.bytes > 1000,
      'font locali disponibili offline', font.found ? `${font.bytes} byte` : 'assente');
  } catch (error) {
    report(false, 'esecuzione dei test', error.message);
  } finally {
    await stopServer(server);
    if (chrome) chrome.kill();
    await sleep(500);
    try { rmSync(profile, { recursive: true, force: true }); } catch { /* ignora */ }
  }

  console.log('\n----------------------------------------');
  if (failures) {
    console.log(`ESITO: FALLITO (${failures} controlli)`);
    return 1;
  }
  console.log('ESITO: PASSATO');
  return 0;
}

process.exitCode = await main();
