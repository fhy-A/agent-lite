"""Export the selected Code Ribbon A mark to PNG and multi-size ICO."""

from pathlib import Path
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
ASSET_PNG = ROOT / "assets" / "code-icon.png"
ROOT_ICO = ROOT / "code-icon.ico"
SCALE = 8
CANVAS = 64 * SCALE


def points(values):
    return [(round(x * SCALE), round(y * SCALE)) for x, y in values]


def render(size=256):
    image = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Main A silhouette.
    draw.polygon(points([
        (8, 54), (27.8, 12.8), (29.6, 10.8), (32, 10.1),
        (34.3, 10.8), (35.8, 12.8), (56, 54), (43, 54),
        (31.8, 29.5), (21, 54),
    ]), fill="#2563EB")

    # Folded right ribbon.
    draw.polygon(points([
        (31.8, 29.5), (43, 54), (56, 54), (35.8, 12.8),
        (34.3, 10.8), (32, 10.1), (29.6, 10.8), (25.5, 14.1),
    ]), fill="#60A5FA")

    # Crossbar adds a stable horizontal anchor at tray size.
    draw.polygon(points([(24.6, 42), (39.4, 42), (43.7, 51), (20.3, 51)]), fill="#1D4ED8")

    return image.resize((size, size), Image.Resampling.LANCZOS)


def main():
    ASSET_PNG.parent.mkdir(parents=True, exist_ok=True)
    render(256).save(ASSET_PNG, "PNG", optimize=True)
    base = render(256)
    base.save(
        ROOT_ICO,
        format="ICO",
        sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (40, 40),
               (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"PNG: {ASSET_PNG}")
    print(f"ICO: {ROOT_ICO}")


if __name__ == "__main__":
    main()
