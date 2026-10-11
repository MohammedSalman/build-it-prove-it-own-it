"""Where did the lab time go? Producing, checking and integrating, lab by lab.

Labs 1 to 13 each end with "One measurement": every student, on their own, writes down the
minutes they spent PRODUCING (writing code, tests, text or prompts; waiting for an agent to
produce), CHECKING (running, reading, reviewing, comparing, measuring) and INTEGRATING
(merging, resolving conflicts, wiring parts together; 0 when there was none). This script
summarises such numbers. The file format is the course's one contract for the class dataset,
plan/class-dataset.md; Lecture 14's analyse_minutes.py reads the same files.

    python economics/effort.py                            # the SYNTHETIC example data
    python economics/effort.py my-effort.csv              # your own numbers
    python economics/effort.py class.csv --svg effort.svg # also draw a chart

The CSV has a header row with exactly these six columns, in this order:
    source,student,lab,producing_min,checking_min,integrating_min
source is "class" for real collected numbers or "synthetic" for invented example data (a file
that mixes the two is refused); student is a pseudonym, never a name or student number; lab
is 1 to 13; the minutes are whole numbers from 0 to 300 (integrating_min may be blank, which
counts as 0). Lines that start with # are comments.

A row is excluded, and counted in the "Excluded" line, if it cannot be read (a blank or
non-whole number, an unknown source, a lab outside 1 to 13), if any value is outside 0-300, if
its total is 0, or if its total is over 360 minutes.

Privacy: the script prints aggregates only. It never prints one student's row, and it hides
any lab with fewer than 5 valid rows. The overall line covers the labs that are shown; when no
lab has 5 valid rows (a file with only your own numbers), it covers all the valid rows instead.

This script reports POOLED shares: each kind's minutes summed over all the valid rows, divided
by all their minutes. Every minute counts once, so a student who recorded more minutes weighs
more. (Lecture 14's analyse_minutes.py reports the MEDIAN OF INDIVIDUAL shares instead: each
student's own share, then the middle student. The two can differ.) The bars use the MEAN
minutes per row, because effort adds up: the mean times the number of rows is the total, so
each part's share of a bar is its pooled share. (For latency we use percentiles instead,
because there we care about what individual people experience.)

These are self-reported estimates written down after the lab. People misjudge their own
time, and METR found developers' own estimates of AI speed-up far off the measured value.
Treat the output as a rough picture of where attention went, not as a measurement of
productivity, and never as a grade.
Only the Python standard library is used.
"""

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
DEFAULT = HERE / "effort-synthetic.csv"
COLUMNS = ["source", "student", "lab", "producing_min", "checking_min", "integrating_min"]
KINDS = ["producing", "checking", "integrating"]
MAX_VALUE = 300          # minutes, for any one of the three numbers
MAX_TOTAL = 360          # minutes, for a whole row: a 2-hour lab plus its homework
MIN_GROUP = 5            # hide any lab with fewer valid rows than this


def whole(text: str | None, blank_is_zero: bool = False) -> int:
    text = (text or "").strip()
    if not text and blank_is_zero:
        return 0
    return int(text)     # raises ValueError for a blank, "12.5", "nan" or "twenty"


def load(path: Path) -> tuple[list[dict], Counter, str]:
    """Read a file in the class-dataset format. Returns (valid rows, excluded counts, source)."""
    lines = [ln for ln in path.read_text(encoding="utf-8-sig").splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    reader = csv.reader(lines)
    header = [h.strip() for h in next(reader, [])]
    if header != COLUMNS:
        sys.exit(f"{path}: the header must be exactly\n  {','.join(COLUMNS)}\n"
                 f"(plan/class-dataset.md), but it is\n  {','.join(header) or '(empty file)'}")
    rows, excluded, sources = [], Counter(), set()
    for cells in reader:
        if len(cells) != len(COLUMNS):
            excluded[f"not {len(COLUMNS)} fields"] += 1
            continue
        raw = dict(zip(COLUMNS, cells))
        source = raw["source"].strip().lower()
        try:
            if source not in ("class", "synthetic") or not raw["student"].strip():
                raise ValueError
            lab = whole(raw["lab"])
            if not 1 <= lab <= 13:
                raise ValueError
            minutes = {"producing": whole(raw["producing_min"]),
                       "checking": whole(raw["checking_min"]),
                       "integrating": whole(raw["integrating_min"], blank_is_zero=True)}
        except ValueError:
            excluded["cannot be read"] += 1
            continue
        total = sum(minutes.values())
        if any(not 0 <= v <= MAX_VALUE for v in minutes.values()):
            excluded[f"a value outside 0-{MAX_VALUE}"] += 1
        elif total == 0:
            excluded["total of 0 minutes"] += 1
        elif total > MAX_TOTAL:
            excluded[f"total over {MAX_TOTAL} minutes"] += 1
        else:
            sources.add(source)
            rows.append({"student": raw["student"].strip(), "lab": lab, **minutes,
                         "total": total})
    if len(sources) > 1:
        sys.exit(f"{path} mixes class and synthetic rows. The two never go in one chart: "
                 "split the file by its source column.")
    return rows, excluded, (sources.pop() if sources else "")


def pooled(rows: list[dict]) -> dict:
    """Each kind's minutes summed over the rows, divided by all their minutes."""
    total = sum(r["total"] for r in rows)                  # never 0: 0-minute rows are excluded
    return {k: sum(r[k] for r in rows) / total for k in KINDS}


def summarise(rows: list[dict]) -> list[dict]:
    out = []
    for lab in sorted({r["lab"] for r in rows}):
        rs = [r for r in rows if r["lab"] == lab]
        entry = {"lab": lab, "n": len(rs), "shown": len(rs) >= MIN_GROUP}
        if entry["shown"]:
            entry["mean"] = {k: sum(r[k] for r in rs) / len(rs) for k in KINDS}
            entry["share"] = pooled(rs)
        out.append(entry)
    return out


# Styles scoped to this chart. Inside a course chapter the colour variables come from
# course.css (and follow its light and dark themes); opened on its own, the file uses the
# fallback colours after the commas.
STYLE = """<style>
.effort-chart { background: var(--card, #ffffff); }
.effort-chart text { font-family: Kalam, "Comic Sans MS", cursive; fill: var(--ink, #17233a); font-size: 17px; }
.effort-chart .t-sm { font-size: 14px; }
.effort-chart .t-lg { font-size: 22px; font-weight: 700; }
.effort-chart .t-mono { font-family: "JetBrains Mono", monospace; font-size: 12.5px; }
.effort-chart .t-2 { fill: var(--ink-2, #4a5970); }
.effort-chart .t-red { fill: var(--red, #b02a21); }
.effort-chart .s { fill: none; stroke: var(--ink, #17233a); stroke-width: 2; }
.effort-chart .s-thin { stroke-width: 1.4; }
.effort-chart .f-pen { fill: var(--pen-soft, #e3eafc); }
.effort-chart .f-mark { fill: var(--marker, #ffe36e); }
.effort-chart .f-green { fill: var(--green-soft, #e1f3e9); }
</style>"""


def draw_svg(labs: list[dict], synthetic: bool, path: Path) -> None:
    """A stacked-bar chart of the labs shown: opens on its own in a browser, or paste it
    into a chapter."""
    top = max(sum(l["mean"].values()) for l in labs)
    scale_max = max(60, -(-top // 20) * 20)
    x0, y0, h, bw, gap = 90, 330, 250, 44, 22
    px = h / scale_max
    width = x0 + len(labs) * (bw + gap) + 190
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" class="sk min effort-chart" '
             f'viewBox="0 0 {width} 400" role="img" aria-label="Stacked bars of mean producing, '
             f'checking and integrating minutes per row, per lab'
             f'{", synthetic example data" if synthetic else ""}.">', STYLE]
    parts.append(f'<path d="M{x0 - 10},{y0} H{x0 + len(labs) * (bw + gap)}" class="s s-thin"/>')
    for v in range(0, int(scale_max) + 1, 20):
        y = y0 - v * px
        parts.append(f'<path d="M{x0 - 16},{y:.1f} H{x0 - 10}" class="s s-thin"/>')
        parts.append(f'<text x="{x0 - 20}" y="{y + 5:.1f}" text-anchor="end" '
                     f'class="t-mono t-sm t-2">{v}</text>')
    for i, l in enumerate(labs):
        x, base = x0 + i * (bw + gap), y0
        for kind, fill in (("producing", "f-pen"), ("checking", "f-mark"),
                           ("integrating", "f-green")):
            hk = l["mean"][kind] * px
            if hk > 0:
                parts.append(f'<rect x="{x}" y="{base - hk:.1f}" width="{bw}" '
                             f'height="{hk:.1f}" class="s s-thin {fill}"/>')
            base -= hk
        parts.append(f'<text x="{x + bw / 2}" y="{y0 + 22}" text-anchor="middle" '
                     f'class="t-mono t-sm">{l["lab"]}</text>')
    xl = x0 + len(labs) * (bw + gap) + 10
    for j, (label, fill) in enumerate((("integrating", "f-green"), ("checking", "f-mark"),
                                       ("producing", "f-pen"))):
        parts.append(f'<rect x="{xl}" y="{60 + 30 * j}" width="26" height="16" '
                     f'class="s s-thin {fill}"/>'
                     f'<text x="{xl + 34}" y="{74 + 30 * j}" class="t-sm">{label}</text>')
    parts.append(f'<text x="{x0 + len(labs) * (bw + gap) / 2}" y="{y0 + 50}" '
                 f'text-anchor="middle" class="t-sm">lab</text>')
    parts.append('<text x="20" y="24" class="t-sm t-2">mean minutes per row '
                 '(each part\'s share of a bar is its pooled share)</text>')
    if synthetic:
        parts.append(f'<text x="{x0}" y="{y0 - h - 16}" class="t-lg t-red">'
                     f'SYNTHETIC EXAMPLE DATA, not real</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", nargs="?", default=str(DEFAULT))
    parser.add_argument("--svg", help="also write a stacked-bar chart to this SVG file")
    args = parser.parse_args()
    rows, excluded, source = load(Path(args.csv))
    excluded_line = (f"Excluded: {sum(excluded.values())} row(s)"
                     + (" (" + "; ".join(f"{why}: {n}" for why, n in sorted(excluded.items()))
                        + ")" if excluded else "") + ".")
    if not rows:
        print(excluded_line)
        sys.exit("No valid rows found.")
    synthetic = source == "synthetic"
    banner = "SYNTHETIC EXAMPLE DATA: invented for teaching. These are not findings."
    if synthetic:
        print(banner + "\n")

    labs = summarise(rows)
    shown = [l for l in labs if l["shown"]]
    students = len({r["student"] for r in rows})
    print(f"Source: {source}. {len(rows)} valid rows from {students} student(s) "
          f"in {len(labs)} lab(s).")
    print(excluded_line)
    print("\nPOOLED shares: each kind's minutes summed over the lab's valid rows, divided by "
          "all their minutes.\nBars: mean minutes per row, one letter for about 4 minutes "
          "(P producing, C checking, I integrating).\n")
    print(f"{'lab':>3}  {'rows':>4}   {'mean minutes per row':^22}   "
          f"{'pooled share of minutes':^25}")
    print(f"{'':>3}  {'':>4}   {'prod':>6} {'check':>7} {'integ':>7}   "
          f"{'prod':>7} {'check':>8} {'integ':>8}")
    for l in labs:
        if not l["shown"]:
            print(f"{l['lab']:>3}  {l['n']:>4}   fewer than {MIN_GROUP} valid rows: hidden")
            continue
        m, s = l["mean"], l["share"]
        bar = "".join(letter * round(m[k] / 4) for letter, k in zip("PCI", KINDS))
        print(f"{l['lab']:>3}  {l['n']:>4}   {m['producing']:>6.0f} {m['checking']:>7.0f} "
              f"{m['integrating']:>7.0f}   {s['producing']:>7.0%} {s['checking']:>8.0%} "
              f"{s['integrating']:>8.0%}   {bar}")

    scope = [r for r in rows if any(l["lab"] == r["lab"] for l in shown)]
    what = "the labs shown"
    if not shown:
        scope, what = rows, "all valid rows (no lab has 5 valid rows, so none is shown)"
    if scope:
        s = pooled(scope)
        more = sum(1 for r in scope if r["checking"] > r["producing"])
        print(f"\nOverall, {what}: {sum(r['total'] for r in scope):,} minutes in {len(scope)} "
              f"rows. POOLED shares: producing {s['producing']:.0%}, checking "
              f"{s['checking']:.0%}, integrating {s['integrating']:.0%}.\n"
              f"Checking took longer than producing in {more} of {len(scope)} rows.")
    else:
        print("\nNo valid rows: no overall line.")
    print("\nRead with care: self-reported estimates; the same students appear in every lab; "
          "labs differ in what they asked for, so a change from lab to lab is not a trend in "
          "anyone's skill.")
    if args.svg:
        if shown:
            draw_svg(shown, synthetic, Path(args.svg))
            print(f"Chart written to {args.svg}")
        else:
            print(f"No chart: no lab has {MIN_GROUP} valid rows.")
    if synthetic:
        print("\n" + banner)


if __name__ == "__main__":
    main()
