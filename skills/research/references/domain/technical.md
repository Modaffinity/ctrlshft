# Technical Domain

Use for software, APIs, standards, scientific computing, models, libraries, and implementation choices.

| Priority | Sources | Notes |
|---|---|---|
| 1 | Official docs, specs, changelogs, repository source | Prefer current primary documentation for behavior. |
| 2 | arXiv, OpenAlex, Crossref, DOI singleton lookups | Use papers for claims about measured performance. |
| 3 | GitHub issues and releases | Useful for current limitations; distinguish maintainer statements from user reports. |

Recency half-life: about 18 months unless the artifact is a stable standard.

`OPENALEX_API_KEY` is optional but preferred when available. Anonymous OpenAlex calls can work, but a free key provides more daily headroom. Prefer DOI or ID singleton lookups when possible.

For rate-limited sources, stop on 429 and record the gap; do not route around identity or access limits.
