"""Generate Agent Lite icon from SVG logo."""
from PIL import Image, ImageDraw

SZ = 256
img = Image.new("RGBA", (SZ, SZ), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Scale SVG 24x24 → approx 256x256
s = SZ / 28
ox, oy = 2 * s, 1 * s

# Outer arrow (accent blue)
outer = [
    (ox + 12 * s, oy + 2 * s),
    (ox + 2 * s, oy + 22 * s),
    (ox + 7 * s, oy + 22 * s),
    (ox + 12 * s, oy + 12 * s),
    (ox + 17 * s, oy + 22 * s),
    (ox + 22 * s, oy + 22 * s),
]
draw.polygon([(int(x), int(y)) for (x, y) in outer], fill="#2f78ff")

# Inner triangle (light blue)
inner = [
    (ox + 12 * s, oy + 12 * s),
    (ox + 7 * s, oy + 22 * s),
    (ox + 17 * s, oy + 22 * s),
]
draw.polygon([(int(x), int(y)) for (x, y) in inner], fill="#eaf2ff")

img.save("agent-lite-icon.ico", format="ICO", sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)])
print("Icon saved: agent-lite-icon.ico")
