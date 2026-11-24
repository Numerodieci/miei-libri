#!/usr/bin/env python3
"""Verifica automatica degli asset della PWA "I Miei Libri".

Controlla, senza dipendenze esterne:
  * validita' e completezza di manifest.webmanifest
  * esistenza e dimensioni reali delle icone dichiarate
  * esistenza di ogni file elencato nel precache di sw.js
  * assenza di riferimenti a font esterni (Google Fonts)
  * esistenza dei file .woff2 referenziati in fonts.css
  * presenza di lang, title e viewport in ogni pagina HTML
  * esistenza di tutti i collegamenti locali (href/src) delle pagine
  * presenza e collegamento della privacy policy

Uso:
    python tools/check-pwa.py

Esce con codice 0 se tutti i controlli passano, 1 altrimenti.
"""

import json
import re
import struct
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ERRORS = []
WARNINGS = []
CHECKS = 0


def ok(message):
    global CHECKS
    CHECKS += 1
    print("  [OK]   " + message)


def fail(message):
    global CHECKS
    CHECKS += 1
    ERRORS.append(message)
    print("  [FAIL] " + message)


def warn(message):
    global CHECKS
    CHECKS += 1
    WARNINGS.append(message)
    print("  [WARN] " + message)


# --------------------------------------------------------------------------
# utilita'
# --------------------------------------------------------------------------

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_size(path):
    """Restituisce (larghezza, altezza) leggendo l'header IHDR, o None."""
    try:
        with open(path, "rb") as handle:
            header = handle.read(24)
    except OSError:
        return None
    if len(header) < 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def local_target(reference):
    """Normalizza un riferimento locale; None se non e' un file del progetto."""
    reference = reference.strip()
    if not reference:
        return None
    lowered = reference.lower()
    for prefix in ("http://", "https://", "//", "data:", "mailto:", "tel:",
                   "about:", "javascript:", "#"):
        if lowered.startswith(prefix):
            return None
    reference = reference.split("#", 1)[0].split("?", 1)[0]
    if not reference:
        return None
    return urllib.parse.unquote(reference)


def resolve(reference, base_dir=ROOT):
    if reference.startswith("/"):
        return base_dir / reference.lstrip("/")
    return (base_dir / reference).resolve()


HTML_ATTR = re.compile(r'(?:href|src)\s*=\s*"([^"]*)"', re.IGNORECASE)

# Gli attributi dentro <script>/<style> sono codice, non collegamenti reali:
# vanno rimossi prima di controllare i percorsi locali.
SCRIPT_BLOCK = re.compile(r"(<script\b[^>]*>).*?(</script>)", re.S | re.I)
STYLE_BLOCK = re.compile(r"(<style\b[^>]*>).*?(</style>)", re.S | re.I)


def strip_code_blocks(text):
    text = SCRIPT_BLOCK.sub(r"\1\2", text)
    return STYLE_BLOCK.sub(r"\1\2", text)


# --------------------------------------------------------------------------
# 1. manifest
# --------------------------------------------------------------------------

def check_manifest():
    print("\n== manifest.webmanifest ==")
    path = ROOT / "manifest.webmanifest"
    if not path.exists():
        fail("manifest.webmanifest mancante")
        return {}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        fail("manifest.webmanifest non e' JSON valido: %s" % exc)
        return {}

    required = ["name", "short_name", "start_url", "display", "lang",
                "background_color", "theme_color", "icons"]
    missing = [key for key in required if key not in manifest]
    if missing:
        fail("manifest: chiavi mancanti -> " + ", ".join(missing))
    else:
        ok("manifest: chiavi obbligatorie presenti")

    if manifest.get("id"):
        ok("manifest: campo id presente (%s)" % manifest["id"])
    else:
        warn("manifest: campo id assente (consigliato per identificare l'app)")

    if manifest.get("display") != "standalone":
        warn("manifest: display e' %r, atteso 'standalone'"
             % manifest.get("display"))
    else:
        ok("manifest: display standalone")

    icons = manifest.get("icons") or []
    if not icons:
        fail("manifest: nessuna icona dichiarata")
    sizes = set()
    maskable = False
    for icon in icons:
        src = icon.get("src", "")
        declared = icon.get("sizes", "")
        purpose = (icon.get("purpose") or "").lower()
        if "maskable" in purpose:
            maskable = True
        target = resolve(local_target(src) or "", ROOT)
        if not target.exists():
            fail("manifest: icona mancante -> %s" % src)
            continue
        measured = png_size(target)
        if measured is None:
            fail("manifest: %s non e' un PNG valido" % src)
            continue
        if declared and "%sx%s" % measured != declared:
            fail("manifest: %s dichiarata %s ma reale %sx%s"
                 % (src, declared, measured[0], measured[1]))
            continue
        sizes.add(measured[0])
        ok("manifest: icona %s %dx%d (%s)"
           % (src, measured[0], measured[1], purpose or "any"))

    if 192 not in sizes:
        fail("manifest: manca un'icona 192x192")
    if 512 not in sizes:
        fail("manifest: manca un'icona 512x512")
    if not maskable:
        fail("manifest: nessuna icona con purpose 'maskable'")
    return manifest


# --------------------------------------------------------------------------
# 2. service worker
# --------------------------------------------------------------------------

def check_service_worker():
    print("\n== sw.js ==")
    path = ROOT / "sw.js"
    if not path.exists():
        fail("sw.js mancante")
        return
    source = path.read_text(encoding="utf-8")

    cache_match = re.search(r"CACHE_NAME\s*=\s*['\"]([^'\"]+)['\"]", source)
    if cache_match:
        ok("sw.js: CACHE_NAME = %s" % cache_match.group(1))
    else:
        fail("sw.js: CACHE_NAME non trovato")

    assets_block = re.search(r"const\s+ASSETS\s*=\s*\[(.*?)\];", source, re.S)
    if not assets_block:
        fail("sw.js: elenco ASSETS non trovato")
        return
    assets = re.findall(r"['\"]([^'\"]+)['\"]", assets_block.group(1))
    if not assets:
        fail("sw.js: elenco ASSETS vuoto")
        return

    missing = []
    for asset in assets:
        target = resolve(local_target(asset) or "", ROOT)
        if target.is_dir():
            target = target / "index.html"
        if not target.exists():
            missing.append(asset)
    if missing:
        for asset in missing:
            fail("sw.js: file in precache inesistente -> %s" % asset)
    else:
        ok("sw.js: tutti i %d file del precache esistono" % len(assets))

    normalized = {a[2:] if a.startswith("./") else a for a in assets}
    if "privacy.html" in normalized:
        ok("sw.js: privacy.html inclusa nel precache")
    else:
        fail("sw.js: privacy.html non e' nel precache")

    if "fonts.css" in source:
        ok("sw.js: fonts.css citato nel precache")
    else:
        warn("sw.js: fonts.css non citato (font locali non ancora attivati)")


# --------------------------------------------------------------------------
# 3. font
# --------------------------------------------------------------------------

def check_fonts():
    print("\n== font ==")
    external = []
    for path in list(ROOT.glob("*.html")) + list(ROOT.glob("*.css")) + list(ROOT.glob("*.js")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for domain in ("fonts.googleapis.com", "fonts.gstatic.com"):
            if domain in text:
                external.append("%s -> %s" % (path.name, domain))
    if external:
        for item in external:
            fail("riferimento a font esterni: " + item)
    else:
        ok("nessun riferimento a Google Fonts")

    fonts_css = ROOT / "fonts.css"
    if not fonts_css.exists():
        warn("fonts.css assente: i caratteri arrivano ancora dal web")
        return

    css = fonts_css.read_text(encoding="utf-8")
    urls = re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", css)
    local = [u for u in urls if local_target(u)]
    if not local:
        fail("fonts.css non referenzia alcun file locale")
        return
    missing = 0
    for reference in local:
        target = resolve(local_target(reference), fonts_css.parent)
        if not target.exists():
            missing += 1
            fail("fonts.css: file mancante -> %s" % reference)
    if not missing:
        ok("fonts.css: %d file woff2 presenti" % len(local))


# --------------------------------------------------------------------------
# 4. pagine HTML
# --------------------------------------------------------------------------

def check_pages():
    print("\n== pagine HTML ==")
    pages = sorted(ROOT.glob("*.html"))
    if not pages:
        fail("nessuna pagina HTML trovata")
        return

    for page in pages:
        text = page.read_text(encoding="utf-8", errors="ignore")
        name = page.name

        if not re.search(r"<html[^>]+lang=\"it\"", text, re.I):
            fail("%s: attributo lang=\"it\" mancante" % name)
        if not re.search(r"<title>[^<]+</title>", text, re.I):
            fail("%s: <title> mancante o vuoto" % name)
        if not re.search(r'name="viewport"', text, re.I):
            fail("%s: meta viewport mancante" % name)

        for reference in HTML_ATTR.findall(strip_code_blocks(text)):
            local = local_target(reference)
            if not local:
                continue
            target = resolve(local, page.parent)
            if target.exists():
                continue
            if target.suffix == "" and (target / "index.html").exists():
                continue
            fail("%s: collegamento locale inesistente -> %s" % (name, reference))
    ok("controllati %d file HTML" % len(pages))

    index = ROOT / "index.html"
    if index.exists():
        text = index.read_text(encoding="utf-8")
        if 'rel="manifest"' in text:
            ok("index.html: manifest collegato")
        else:
            fail("index.html: link al manifest mancante")
        if 'name="apple-mobile-web-app-capable"' in text:
            ok("index.html: meta per l'installazione su iOS presenti")
        else:
            fail("index.html: meta apple-mobile-web-app-capable mancante")
        if 'href="privacy.html"' in text:
            ok("index.html: link alla privacy policy presente")
        else:
            fail("index.html: link alla privacy policy mancante")


# --------------------------------------------------------------------------
# 5. privacy
# --------------------------------------------------------------------------

def check_privacy():
    print("\n== privacy policy ==")
    path = ROOT / "privacy.html"
    if not path.exists():
        fail("privacy.html mancante")
        return
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "Informativa aggiornata" not in text:
        warn("privacy.html: data di aggiornamento non trovata")
    else:
        ok("privacy.html presente con data di aggiornamento")
    if "cookie" not in text.lower():
        warn("privacy.html: nessuna menzione dei cookie")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    print("Verifica PWA - I Miei Libri")
    print("Cartella: %s" % ROOT)
    check_manifest()
    check_service_worker()
    check_fonts()
    check_pages()
    check_privacy()

    print("\n----------------------------------------")
    print("Controlli eseguiti: %d" % CHECKS)
    print("Errori: %d   Avvisi: %d" % (len(ERRORS), len(WARNINGS)))
    if ERRORS:
        print("\nESITO: FALLITO")
        for item in ERRORS:
            print("  * " + item)
        return 1
    print("\nESITO: PASSATO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
