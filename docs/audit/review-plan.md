# Small review units (not published PRs)

The local history separates the delivery into review units. These notes are not
GitHub Issues/PRs. GitHub GraphQL and REST calls returned `Forbidden` from this
environment. Git HTTPS read access works independently. `api.github.com` has
been added to the environment configuration **draft**; that does not apply the
network change or create/publish a pull request. The user can review/save that
network requirement in environment settings before publication is retried.

| Proposed PR | Head | Base | Scope |
| --- | --- | --- | --- |
| 00 — executable audit baseline | `fix/audit-00-baseline` (`1745db2`) | `main` | Baseline and raw evidence only |
| 01 — scoped result/evidence contract | `fix/audit-01-result-contract` (`67e5abe`) | PR 00 branch | Shared status, conservative Clause 10 checklist, duplicate exporter removal |
| 02 — no hidden PE/cable assumptions | `fix/audit-02-pe-data` (`a582a60`) | PR 01 branch | Real engine helpers, missing cable/PE data, integrated regression matrix |
| 03 — evidence/settings and run identity | `fix/audit-and-product-hardening` | PR 02 branch | Exact applicability, provenance, Ir/I2/IP, immutable run metadata and freshness |

Use [work-items](work-items.md) for each unit's **Observed / Expected /
Implementation / Tests / Evidence / Remaining risks**. Once API access works,
create draft PRs, copy the corresponding unit into its description, attach the
actual validation evidence and leave the engineering gate open. Do not mark a
reviewer as accepted, fabricate Issue IDs/CI badges, merge, or publish a release.

Status checks currently cannot be green: the baseline PDF limitation and global
lint/type debt are explicitly recorded. Engineer sign-off and the independent
reference pack remain prerequisites for P0 acceptance.
