#!/usr/bin/env python3
"""Rigenera l'elenco ASSETS nel service worker leggendo i file su disco.

Evita di dover aggiornare a mano il precache quando si aggiungono font, icone o
pagine: l'elenco viene riscritto in ordine stabile e senza duplicati.

Uso:
    python tools/sync-precache.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SW = ROOT / "sw.js"

# Le splash screen iOS non entrano nel precache: sono decorative e peserebbero
# quasi 1 MB. Vengono richieste dal sistema al momento dell'avvio.
PRECACHE_PATTERNS = [
    "index.html", "viewer.html", "quiz.html", "privacy.html",
    "home.css", "fonts.css", "qrcode.js", "quiz-data.js",
    "manifest.webmanifest", "search-index.json", "favicon.ico",
]
PRECACHE_GLOBS = ["icons/*.png", "fonts/*.woff2", "*.html"]


def collect():
    assets = ["./"]
    seen = {"./"}
    for name in PRECACHE_PATTERNS:
        if (ROOT / name).exists() and name not in seen:
            assets.append(name)
            seen.add(name)
    for pattern in PRECACHE_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT).as_posix()
            if relative in seen:
                continue
            assets.append(relative)
            seen.add(relative)
    return assets


def main():
    if not SW.exists():
        print("sw.js non trovato")
        return 1

    assets = collect()
    source = SW.read_text(encoding="utf-8")

    body = "const ASSETS = [\n" + "".join("  '%s',\n" % a for a in assets) + "];"
    new_source, count = re.subn(
        r"const ASSETS = \[.*?\];", body.replace("\\", "\\\\"), source, flags=re.S)
    if count != 1:
        print("Impossibile trovare l'elenco ASSETS in sw.js")
        return 1

    SW.write_text(new_source, encoding="utf-8")
    print("sw.js: %d file nel precache" % len(assets))
    for asset in assets[:5]:
        print("  " + asset)
    print("  ...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
