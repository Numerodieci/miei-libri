#!/usr/bin/env python3
"""Scarica i font Google usati dalle pagine e li rende disponibili offline.

Legge i collegamenti a fonts.googleapis.com presenti nei file HTML, scarica i
relativi file .woff2 (solo subset latino e latino-esteso), li salva in fonts/ e
genera fonts.css con regole @font-face locali. Infine sostituisce nelle pagine
il collegamento a Google Fonts con il foglio di stile locale.

Uso:
    python tools/localize-fonts.py

Lo script e' idempotente: se i file esistono gia' non li riscarica.
"""

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / "fonts"
CSS_PATH = ROOT / "fonts.css"

GOOGLE_CSS = "https://fonts.googleapis.com/css2"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
KEEP_SUBSETS = ("latin", "latin-ext")

LINK_PATTERN = re.compile(
    r'(?P<indent>[ \t]*)<link\s+href="https://fonts\.googleapis\.com/css2\?'
    r'(?P<query>[^"]*)"\s+rel="stylesheet">'
)
FACE_PATTERN = re.compile(
    r"/\*\s*(?P<subset>[\w-]+)\s*\*/\s*@font-face\s*\{(?P<body>[^}]*)\}",
    re.S,
)


def fetch(url, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def parse_families(pages):
    """Restituisce {famiglia: set(pesi)} leggendo i link delle pagine."""
    families = {}
    order = []
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for match in LINK_PATTERN.finditer(text):
            for spec in re.findall(r"(?:^|&)family=([^&]+)", match.group("query")):
                spec = spec.replace("+", " ").strip()
                name, _, weights = spec.partition(":")
                name = name.strip()
                if not name:
                    continue
                if name not in families:
                    families[name] = set()
                    order.append(name)
                if weights:
                    values = weights.split("@", 1)[-1]
                    for value in values.split(";"):
                        value = value.strip()
                        if value.isdigit():
                            families[name].add(int(value))
    return [(name, sorted(families[name])) for name in order]


def build_css_url(name, weights):
    family = name.replace(" ", "+")
    if len(weights) > 1:
        return "%s?family=%s:wght@%d..%d&display=swap" % (
            GOOGLE_CSS, family, min(weights), max(weights))
    return "%s?family=%s&display=swap" % (GOOGLE_CSS, family)


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def face_records(css_text):
    records = []
    for match in FACE_PATTERN.finditer(css_text):
        subset = match.group("subset")
        if subset not in KEEP_SUBSETS:
            continue
        body = match.group("body")
        src = re.search(r"url\((https://[^)]+\.woff2)\)", body)
        if not src:
            continue
        records.append({
            "subset": subset,
            "url": src.group(1),
            "font_weight": (re.search(r"font-weight:\s*([^;]+);", body) or [None, "400"])[1].strip(),
            "font_style": (re.search(r"font-style:\s*([^;]+);", body) or [None, "normal"])[1].strip(),
            "font_stretch": (re.search(r"font-stretch:\s*([^;]+);", body) or [None, None])[1],
            "unicode_range": (re.search(r"unicode-range:\s*([^;]+);", body) or [None, None])[1],
        })
    return records


def main():
    pages = sorted(ROOT.glob("*.html"))
    if not pages:
        print("Nessuna pagina HTML trovata.")
        return 1

    families = parse_families(pages)
    if not families:
        print("Nessun collegamento a Google Fonts: niente da fare.")
        return 0

    print("Famiglie richieste: %d" % len(families))
    FONTS_DIR.mkdir(exist_ok=True)

    blocks = []
    downloaded = 0
    for name, weights in families:
        css_text = None
        used_url = build_css_url(name, weights)
        try:
            css_text = fetch(used_url).decode("utf-8")
        except urllib.error.HTTPError:
            # Famiglia non variabile: richiedi i singoli pesi in un'unica URL.
            explicit = "family=%s:wght@%s" % (
                name.replace(" ", "+"), ";".join(str(w) for w in weights))
            used_url = "%s?%s&display=swap" % (GOOGLE_CSS, explicit)
            try:
                css_text = fetch(used_url).decode("utf-8")
            except urllib.error.HTTPError as exc:
                print("  [ERRORE] %s: %s" % (name, exc))
                return 1

        records = face_records(css_text)
        if not records:
            print("  [ERRORE] %s: nessun @font-face latino trovato" % name)
            return 1

        for record in records:
            weight_slug = record["font_weight"].replace(" ", "-")
            filename = "%s-%s-%s.woff2" % (slug(name), weight_slug, record["subset"])
            target = FONTS_DIR / filename
            if not target.exists():
                try:
                    target.write_bytes(fetch(record["url"]))
                    downloaded += 1
                except urllib.error.URLError as exc:
                    print("  [ERRORE] download %s: %s" % (filename, exc))
                    return 1
            lines = [
                "@font-face {",
                "  font-family: '%s';" % name,
                "  font-style: %s;" % record["font_style"],
                "  font-weight: %s;" % record["font_weight"],
            ]
            if record["font_stretch"]:
                lines.append("  font-stretch: %s;" % record["font_stretch"])
            lines.append("  font-display: swap;")
            lines.append("  src: url('fonts/%s') format('woff2');" % filename)
            if record["unicode_range"]:
                lines.append("  unicode-range: %s;" % record["unicode_range"])
            lines.append("}")
            blocks.append("\n".join(lines))

    CSS_PATH.write_text(
        "/* Caratteri tipografici ospitati localmente per l'uso offline.\n"
        "   Generato da tools/localize-fonts.py - non modificare a mano. */\n\n"
        + "\n\n".join(blocks) + "\n",
        encoding="utf-8")

    total = sum(f.stat().st_size for f in FONTS_DIR.glob("*.woff2"))
    print("File woff2: %d (nuovi: %d), totale %.1f KB"
          % (len(list(FONTS_DIR.glob('*.woff2'))), downloaded, total / 1024))
    print("fonts.css: %d regole @font-face" % len(blocks))

    changed = 0
    for page in pages:
        text = page.read_text(encoding="utf-8")
        new_text, count = LINK_PATTERN.subn(
            lambda m: '%s<link rel="stylesheet" href="fonts.css">' % m.group("indent"),
            text)
        if count:
            page.write_text(new_text, encoding="utf-8")
            changed += count
    print("Collegamenti aggiornati in %d punti" % changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
