"""Contrast ratio between two colours, as WCAG 2.2 defines it.

Usage:
    python scripts/contrast.py "#625b8a" "#1f1a3d"
    python scripts/contrast.py "rgb(98, 91, 138)" "rgb(31, 26, 61)"

Copy the two colours from your browser's developer tools (the computed `color` of the text
and the `background-color` behind it). Normal text needs at least 4.5:1; large text (at least
18 pt, or 14 pt bold) and the edges of controls, focus indicators and icons need at least 3:1.

The formula (WCAG 2.2, "contrast ratio" and "relative luminance"):
    each channel c in 0..1:  c/12.92 if c <= 0.04045, else ((c + 0.055)/1.055) ** 2.4
    L = 0.2126 R + 0.7152 G + 0.0722 B
    ratio = (L_lighter + 0.05) / (L_darker + 0.05)        from 1:1 up to 21:1
Only the Python standard library is used.
"""

import re
import sys


def parse(colour: str) -> tuple[int, int, int]:
    colour = colour.strip()
    if colour.startswith("#"):
        h = colour[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    numbers = re.findall(r"[\d.]+", colour)
    if colour.startswith("rgb") and len(numbers) >= 3:
        return tuple(round(float(n)) for n in numbers[:3])
    sys.exit(f"Can't read the colour {colour!r}. Use #rrggbb or rgb(r, g, b).")


def luminance(rgb: tuple[int, int, int]) -> float:
    def channel(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a: str, b: str) -> float:
    la, lb = sorted((luminance(parse(a)), luminance(parse(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    r = ratio(sys.argv[1], sys.argv[2])
    verdict = "passes 4.5:1 (normal text)" if r >= 4.5 else (
        "passes 3:1 only (large text, control edges, focus indicators)" if r >= 3 else "fails 3:1")
    print(f"{r:.2f}:1  {verdict}")
