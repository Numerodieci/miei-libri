#!/usr/bin/env python3
"""Genera icone e splash screen a partire dal logo esistente.

Produce:
  icons/icon-192.png, icons/icon-512.png, icons/icon-1024.png   (PNG reali)
  icons/icon-maskable-192.png, icons/icon-maskable-512.png      (safe zone Android)
  icons/apple-touch-icon-180.png                                (iOS)
  splash/splash-WxH.png                                         (iOS)
e aggiorna il blocco splash dentro index.html.

Uso:
    python tools/build-icons.py

Richiede Pillow (pip install pillow).
"""

import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow non installato: esegui prima 'python -m pip install pillow'")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "icons"
SPLASH = ROOT / "splash"
MASTER = ICONS / "logo-master.png"       # sorgente 1024x1024, mai sovrascritta
BACKGROUND = (248, 250, 252)             # #F8FAFC, come il manifest
CARD = (253, 253, 251)                   # colore del riquadro del logo

# Schermi iOS in verticale (larghezza, altezza) in pixel reali.
SPLASH_SIZES = [
    (750, 1334), (828, 1792), (1125, 2436), (1170, 2532), (1179, 2556),
    (1242, 2688), (1284, 2778), (1290, 2796),
    (1536, 2048), (1640, 2360), (1668, 2388), (2048, 2732),
]

# dimensioni CSS corrispondenti per le media query di iOS
CSS_SIZES = {
    (750, 1334): (375, 667, 2), (828, 1792): (414, 896, 2),
    (1125, 2436): (375, 812, 3), (1170, 2532): (390, 844, 3),
    (1179, 2556): (393, 852, 3), (1242, 2688): (414, 896, 3),
    (1284, 2778): (428, 926, 3), (1290, 2796): (430, 932, 3),
    (1536, 2048): (768, 1024, 2), (1640, 2360): (820, 1180, 2),
    (1668, 2388): (834, 1194, 2), (2048, 2732): (1024, 1366, 2),
}


def square(img, size):
    return img.resize((size, size), Image.LANCZOS)


def save(img, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)
    return path.stat().st_size


def main():
    if not MASTER.exists():
        print("Logo di partenza mancante: %s" % MASTER)
        return 1

    master = Image.open(MASTER).convert("RGB")
    if master.size != (1024, 1024):
        master = master.resize((1024, 1024), Image.LANCZOS)
    print("Logo di partenza: %dx%d" % master.size)

    written = []

    # Icone normali: riquadro pieno, come da disegno originale.
    for size in (192, 512, 1024):
        path = ICONS / ("icon-%d.png" % size)
        written.append((path, save(square(master, size), path)))

    # Icone maskable: l'arte resta dentro la safe zone (80% del lato).
    for size in (192, 512):
        canvas = Image.new("RGB", (size, size), CARD)
        inner = int(size * 0.84)
        art = square(master, inner)
        offset = (size - inner) // 2
        canvas.paste(art, (offset, offset))
        path = ICONS / ("icon-maskable-%d.png" % size)
        written.append((path, save(canvas, path)))

    # Icona iOS: iOS applica da solo gli angoli arrotondati.
    path = ICONS / "apple-touch-icon-180.png"
    written.append((path, save(square(master, 180), path)))

    # Splash screen iOS.
    for width, height in SPLASH_SIZES:
        canvas = Image.new("RGB", (width, height), BACKGROUND)
        logo_size = int(min(width, height) * 0.34)
        logo = square(master, logo_size)
        canvas.paste(logo, ((width - logo_size) // 2, (height - logo_size) // 2))
        path = SPLASH / ("splash-%dx%d.png" % (width, height))
        written.append((path, save(canvas, path)))

    for path, size in written:
        print("  %-42s %6.1f KB" % (path.relative_to(ROOT).as_posix(), size / 1024))
    total = sum(size for _, size in written)
    print("Totale: %d file, %.1f KB" % (len(written), total / 1024))

    # Aggiorna il blocco splash in index.html.
    index = ROOT / "index.html"
    text = index.read_text(encoding="utf-8")
    tags = []
    for width, height in SPLASH_SIZES:
        css_w, css_h, ratio = CSS_SIZES[(width, height)]
        tags.append(
            '<link rel="apple-touch-startup-image" '
            'href="splash/splash-%dx%d.png" '
            'media="(device-width: %dpx) and (device-height: %dpx) and '
            '(-webkit-device-pixel-ratio: %d) and (orientation: portrait)">'
            % (width, height, css_w, css_h, ratio))
    block = "<!-- splash:start -->\n" + "\n".join(tags) + "\n<!-- splash:end -->"
    if "<!-- splash:start -->" in text and "<!-- splash:end -->" in text:
        text = re.sub(r"<!-- splash:start -->.*?<!-- splash:end -->", block,
                      text, flags=re.S)
        index.write_text(text, encoding="utf-8")
        print("index.html: blocco splash aggiornato (%d tag)" % len(tags))
    else:
        print("index.html: marcatori splash assenti, blocco non inserito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
