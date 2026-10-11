# Licences

## This repository's own code

No licence has been chosen yet (known risk KR-8). Until the course team adds a `LICENSE`
file, treat the code as usable for this course only.

## What we depend on

The table below lists every package this app installs, including the dependencies of our
dependencies, with the licence each one **declares** in its package metadata. All of them are
permissive licences (MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, PSF-2.0): they allow use,
change and redistribution, and they ask you to keep their copyright and licence notices when
you redistribute the code. Nobody on the team is a lawyer; for anything beyond this course,
read each licence and ask someone who is.

- **Needed to run the app:** fastapi, uvicorn, and what they pull in.
- **Needed only to run the tests:** pytest (with iniconfig, packaging, pluggy, pygments) and
  httpx2 (FastAPI's test client uses it, with its own dependencies).
- **Declared is not proven.** The table reads metadata, not the licence files. If a package
  ever shows "not declared: read the licence file", or a licence you do not recognise, read
  its licence file before you ship.
- **Regenerate** after any change to `requirements.txt`:
  `python scripts/licences.py --out docs/licences.md`. It keeps everything above the marker
  line below and replaces the table.

<!-- licences.py writes below this line -->

Generated 2026-09-28 by `python scripts/licences.py` with Python 3.11.9, from `requirements.txt` and what is installed.

| Package | Version | Declared licence | Declared in | Needed by |
|---|---|---|---|---|
| annotated-doc | 0.0.5 | MIT | License-Expression | fastapi |
| annotated-types | 0.8.0 | MIT | License-Expression | pydantic |
| anyio | 4.15.1 | MIT | License-Expression | httpx2, starlette |
| click | 8.5.0 | BSD-3-Clause | License-Expression | uvicorn |
| fastapi | 0.141.1 | MIT | License-Expression | requirements.txt |
| h11 | 0.16.0 | MIT | License | httpcore2, uvicorn |
| httpcore2 | 2.13.1 | BSD-3-Clause | License-Expression | httpx2 |
| httpx2 | 2.13.1 | BSD-3-Clause | License-Expression | requirements.txt |
| idna | 3.20 | BSD-3-Clause | License-Expression | anyio, httpx2 |
| iniconfig | 2.3.0 | MIT | License-Expression | pytest |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | License-Expression | pytest |
| pluggy | 1.6.0 | MIT | License | pytest |
| pydantic | 2.13.5 | MIT | License-Expression | fastapi |
| pydantic-core | 2.46.5 | MIT | License-Expression | pydantic |
| pygments | 2.21.0 | BSD-2-Clause | License-Expression | pytest |
| pytest | 9.1.1 | MIT | License-Expression | requirements.txt |
| starlette | 1.7.0 | BSD-3-Clause | License-Expression | fastapi |
| truststore | 0.10.4 | MIT | License-Expression | httpcore2, httpx2 |
| typing-extensions | 4.16.0 | PSF-2.0 | License-Expression | anyio, fastapi, httpx2, pydantic, pydantic-core, starlette, typing-inspection |
| typing-inspection | 0.4.4 | MIT | License-Expression | fastapi, pydantic |
| uvicorn | 0.54.0 | BSD-3-Clause | License-Expression | requirements.txt |

21 packages. Licence not declared, check by hand: none. Required but not installed here, check by hand: none.
