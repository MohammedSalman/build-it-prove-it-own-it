"""Make the SYNTHETIC example dataset in effort-synthetic.csv.

Every number this script writes is invented. It exists so that the analysis script
(effort.py) has something to run on before a class has collected its own numbers, and so that
instructors can see the file format (plan/class-dataset.md). Do not quote anything computed
from it as a finding about students, agents or software work.

What we typed in (so you can see that any "pattern" in the output was put there by us):
  * 24 made-up students, labs 1 to 10 (the labs done by Week 11), one row per student per lab;
  * producing, checking and integrating minutes drawn at random around a per-lab typical
    value (the typical values below are guesses, not measurements); integrating is 0 in the
    labs where we typed 0, and largest in Lab 10;
  * about 1 row in 12 missing, as happens when someone skips a hand-in;
  * two invalid rows (a typo with an extra 0, and a total longer than a lab and its homework
    could take), because real hand-in data has those too and the analysis should exclude them.

    python economics/make_synthetic.py        # rewrites effort-synthetic.csv
"""

import csv
import random
from pathlib import Path

OUT = Path(__file__).with_name("effort-synthetic.csv")

# (lab, typical producing, checking, integrating minutes): invented for the example.
TYPICAL = [
    (1, 40, 50, 5), (2, 45, 35, 0), (3, 40, 45, 0), (4, 45, 45, 5), (5, 30, 60, 0),
    (6, 45, 55, 5), (7, 20, 75, 0), (8, 30, 60, 0), (9, 25, 65, 0), (10, 40, 50, 35),
]


def main() -> None:
    rnd = random.Random(1111)
    rows = []
    for s in range(1, 25):
        student = f"S{s:02d}"
        speed = rnd.uniform(0.75, 1.25)      # some people are just faster at everything
        for lab, produce, check, integrate in TYPICAL:
            if rnd.random() < 1 / 12:
                continue                        # missing hand-in
            p = max(5, round(produce * speed * rnd.lognormvariate(0, 0.35) / 5) * 5)
            c = max(5, round(check * speed * rnd.lognormvariate(0, 0.35) / 5) * 5)
            i = round(integrate * speed * rnd.lognormvariate(0, 0.5) / 5) * 5 if integrate else 0
            rows.append(["synthetic", student, lab, p, c, i])
    rows[17][3] = 450                           # a typo with an extra 0: outside 0-300
    rows[40][3:6] = [200, 170, 0]               # 370 minutes: more than a lab and its homework
    with OUT.open("w", newline="") as f:
        f.write("# SYNTHETIC EXAMPLE DATA. Invented by make_synthetic.py, not collected from anyone.\n")
        f.write("# Format: plan/class-dataset.md. Replace it with your class's real numbers "
                "(same columns, source = class).\n")
        w = csv.writer(f)
        w.writerow(["source", "student", "lab", "producing_min", "checking_min", "integrating_min"])
        w.writerows(rows)
    print(f"Wrote {len(rows)} synthetic rows to {OUT.name}")


if __name__ == "__main__":
    main()
