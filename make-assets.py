#!/usr/bin/env python3
"""
Generate FinderPilot brand assets.

Outputs into assets/:
  logo.png              combined mark, 1024x1024
  logo-banner.png       GitHub README banner, 1200x300
  showcase.png          Finder-style showcase for the README

Everything is drawn from the two shipped app icons so the brand stays in sync
with what actually ships.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"

# The iconsets are the source of truth for the app icons; the PNGs the README
# embeds are exported from them here so they never drift.
PI_ICONSET = ROOT / "icons" / "pi.iconset" / "icon_512x512.png"
MD_ICONSET = ROOT / "icons" / "md.iconset" / "icon_512x512.png"
PI_ICON = ASSETS / "icon-pi.png"
MD_ICON = ASSETS / "icon-md.png"

# Pulled from the app icons themselves so the two never drift apart.
DARK_TOP = (74, 78, 88)
DARK_BOTTOM = (26, 29, 35)
PI_ORANGE = (243, 155, 62)
MD_BLUE = (96, 165, 214)
FINDER_BLUE = (10, 132, 255)


def vertical_gradient(size, top, bottom):
    """A vertical linear gradient as an RGB image."""
    w, h = size
    grad = Image.new("RGB", (1, h))
    px = grad.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        px[0, y] = (
            round(top[0] + (bottom[0] - top[0]) * t),
            round(top[1] + (bottom[1] - top[1]) * t),
            round(top[2] + (bottom[2] - top[2]) * t),
        )
    return grad.resize((w, h), Image.BICUBIC)


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=255)
    return mask


def drop_shadow(rgba, blur=24, offset=(0, 12), opacity=110):
    """Return a new RGBA image with a soft shadow behind `rgba`."""
    pad = blur * 3
    w, h = rgba.size
    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))

    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow.putalpha(rgba.getchannel("A"))
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, opacity))
    shadow.putalpha(Image.composite(
        Image.new("L", (w, h), opacity),
        Image.new("L", (w, h), 0),
        rgba.getchannel("A"),
    ))
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))

    canvas.alpha_composite(shadow, (pad + offset[0], pad + offset[1]))
    canvas.alpha_composite(rgba, (pad, pad))
    return canvas


def fit_inside(img, box):
    """Scale img down to fit a box, preserving aspect."""
    scale = min(box[0] / img.width, box[1] / img.height)
    return img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)


def make_logo():
    """Combined mark: the pi glyph and the markdown glyph, side by side."""
    size = 1024
    plate = vertical_gradient((size, size), DARK_TOP, DARK_BOTTOM).convert("RGBA")
    plate.putalpha(rounded_mask((size, size), 224))

    # Soft finder-blue glow behind the glyphs for a bit of depth.
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((150, 250, 874, 830), fill=FINDER_BLUE + (46,))
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    plate.alpha_composite(glow)

    # Take only the glyph out of each app icon: the artwork sits on a dark
    # rounded plate, and nesting two plates inside a third reads muddy.
    # Brightness does the separating, not colour: the markdown glyph is pure
    # white (zero chroma) on a dark navy plate, so a chroma test would delete it.
    # The mask is computed once at low resolution and upscaled — per-pixel work
    # at full size is 260k iterations for no extra accuracy.
    def glyph_mask(path, probe=256, largest_only=False):
        small = Image.open(path).convert("RGBA").resize((probe, probe), Image.LANCZOS)
        keep = Image.new("L", (probe, probe), 0)
        sp, kp = small.load(), keep.load()
        for y in range(probe):
            for x in range(probe):
                r, g, b, a = sp[x, y]
                bright = max(r, g, b)
                kp[x, y] = a if (a > 0 and bright >= 175) else 0

        out = keep
        if largest_only:
            label = [0] * (probe * probe)
            best_id, best_size = 0, 0
            current = 0
            for y in range(probe):
                for x in range(probe):
                    idx = y * probe + x
                    if kp[x, y] == 0 or label[idx]:
                        continue
                    current += 1
                    stack = [(x, y)]
                    label[idx] = current
                    size = 0
                    while stack:
                        cx, cy = stack.pop()
                        size += 1
                        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                            if 0 <= nx < probe and 0 <= ny < probe:
                                nidx = ny * probe + nx
                                if kp[nx, ny] and not label[nidx]:
                                    label[nidx] = current
                                    stack.append((nx, ny))
                    if size > best_size:
                        best_size, best_id = size, current

            out = Image.new("L", (probe, probe), 0)
            op = out.load()
            for y in range(probe):
                for x in range(probe):
                    if label[y * probe + x] == best_id:
                        op[x, y] = kp[x, y]

        return out.resize((512, 512), Image.BICUBIC)

    def glyph_only(path, out_size, largest_only=False):
        base = Image.open(path).convert("RGBA").resize((out_size, out_size), Image.LANCZOS)
        base.putalpha(glyph_mask(path, largest_only=largest_only).resize((out_size, out_size), Image.BICUBIC))
        return base

    glyph = int(size * 0.46)
    left = glyph_only(PI_ICON, glyph, largest_only=True)
    right = glyph_only(MD_ICON, glyph)

    gap = int(size * 0.035)
    total = left.width + gap + right.width
    y = (size - left.height) // 2
    x = (size - total) // 2
    plate.alpha_composite(left, (x, y))
    plate.alpha_composite(right, (x + left.width + gap, y))

    plate = plate.resize((512, 512), Image.LANCZOS)
    plate.save(ASSETS / "logo.png")
    print("logo.png")


def make_banner():
    """Wide banner for the README header."""
    w, h = 1200, 300
    bg = vertical_gradient((w, h), (28, 32, 40), (16, 18, 23)).convert("RGBA")

    # Accent bar in the pi orange, fading into the markdown blue.
    bar = Image.new("RGBA", (w, 6))
    bd = ImageDraw.Draw(bar)
    for x in range(w):
        t = x / (w - 1)
        bd.line(
            [(x, 0), (x, 6)],
            fill=(
                round(PI_ORANGE[0] + (MD_BLUE[0] - PI_ORANGE[0]) * t),
                round(PI_ORANGE[1] + (MD_BLUE[1] - PI_ORANGE[1]) * t),
                round(PI_ORANGE[2] + (MD_BLUE[2] - PI_ORANGE[2]) * t),
                255,
            ),
        )
    bg.alpha_composite(bar, (0, 0))

    mark = fit_inside(Image.open(ASSETS / "logo.png").convert("RGBA"), (200, 200))
    mk_x, mk_y = 70, (h - mark.height) // 2
    bg.alpha_composite(mark, (mk_x, mk_y))

    # Wordmark. ASCII only in the asset itself; fonts vary too much across
    # machines to trust anything fancier.
    from PIL import ImageFont

    def load(size):
        for path in (
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNS.ttf",
            "/Library/Fonts/Arial.ttf",
        ):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
        return ImageFont.load_default()

    draw = ImageDraw.Draw(bg)
    text_x = mk_x + mark.width + 46
    draw.text((text_x, 96), "FinderPilot", font=load(64), fill=(242, 244, 247, 255))
    draw.text(
        (text_x + 3, 172),
        "Two Finder tools for pi and Markdown",
        font=load(26),
        fill=(150, 158, 170, 255),
    )

    bg.convert("RGB").save(ASSETS / "logo-banner.png")
    print("logo-banner.png")


def make_showcase():
    """A Finder-window style showcase. Drawn, not screenshotted, so it carries
    no local usernames or paths."""
    from PIL import ImageFont

    w, h = 1000, 348
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    def load(size, bold=False):
        paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNS.ttf",
            "/Library/Fonts/Arial.ttf",
        ]
        if bold:
            paths = ["/System/Library/Fonts/HelveticaNeue.ttc"] + paths
        for path in paths:
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
        return ImageFont.load_default()

    # Window body with rounded corners.
    body = vertical_gradient((w, h), (250, 250, 252), (238, 238, 242)).convert("RGBA")
    body.putalpha(rounded_mask((w, h), 12))
    img.alpha_composite(body, (0, 0))

    d = ImageDraw.Draw(img)

    # Toolbar.
    d.rectangle((0, 0, w, 78), fill=(247, 247, 250, 255))
    d.line((0, 78, w, 78), fill=(216, 216, 222, 255), width=1)

    # Traffic lights.
    for i, colour in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = 30 + i * 26
        d.ellipse((cx - 9, 30 - 9, cx + 9, 30 + 9), fill=colour + (255,))

    d.text((110, 20), "Notes", font=load(21, bold=True), fill=(60, 62, 70, 255))

    # File icons: document sheets.
    doc_w, doc_h = 128, 152
    positions = [(84, 116), (272, 116), (460, 116), (648, 116), (836, 116)]
    labels = ["Field Notes.md", "Daily Log.md", "Reading List.md", "Open in Pi", "New Markdown"]

    for (x, y), label in zip(positions, labels):
        is_app = label in ("Open in Pi", "New Markdown")
        if is_app:
            art = Image.open(ASSETS / ("icon-pi.png" if label == "Open in Pi" else "icon-md.png"))
            art = fit_inside(art.convert("RGBA"), (doc_w, doc_h))
            img.alpha_composite(art, (x + (doc_w - art.width) // 2, y + (doc_h - art.height) // 2))
        else:
            sheet = Image.new("RGBA", (doc_w, doc_h), (0, 0, 0, 0))
            sd = ImageDraw.Draw(sheet)
            sd.rounded_rectangle(
                (6, 4, doc_w - 6, doc_h - 10), 8, fill=(255, 255, 255, 255), outline=(198, 200, 208, 255)
            )
            # Ruled lines inside the sheet.
            for i in range(7):
                ly = 26 + i * 15
                sd.line((20, ly, doc_w - 20 - (i % 3) * 12, ly), fill=(214, 216, 224, 255), width=2)
            # Folded corner.
            sd.polygon(
                [(doc_w - 26, 4), (doc_w - 6, 4), (doc_w - 6, 24)], fill=(226, 228, 234, 255)
            )
            img.alpha_composite(sheet, (x, y))

        # Label under the icon.
        bbox = d.textbbox((0, 0), label, font=load(14))
        d.text(
            (x + doc_w / 2 - (bbox[2] - bbox[0]) / 2, y + doc_h + 12),
            label,
            font=load(14),
            fill=(48, 50, 58, 255),
        )

    # Toolbar badges: the two apps live up here, icon stacked over its label so
    # the two never collide horizontally.
    for i, (src, label) in enumerate([(PI_ICON, "Open in Pi"), (MD_ICON, "New Markdown")]):
        art = fit_inside(Image.open(src).convert("RGBA"), (34, 34))
        cx = 780 + i * 108
        img.alpha_composite(art, (cx - art.width // 2, 8))
        bbox = d.textbbox((0, 0), label, font=load(11))
        d.text(
            (cx - (bbox[2] - bbox[0]) / 2, 46),
            label,
            font=load(11),
            fill=(96, 100, 110, 255),
        )

    img.convert("RGB").save(ASSETS / "showcase.png")
    print("showcase.png")


def export_icons():
    """Pull the app icons out of the iconsets so the README images match what
    actually ships."""
    for src, dst in ((PI_ICONSET, PI_ICON), (MD_ICONSET, MD_ICON)):
        if not src.exists():
            raise SystemExit(f"missing icon source: {src}")
        Image.open(src).convert("RGBA").save(dst)
        print(dst.name)


if __name__ == "__main__":
    ASSETS.mkdir(exist_ok=True)
    export_icons()
    make_logo()
    make_banner()
    make_showcase()