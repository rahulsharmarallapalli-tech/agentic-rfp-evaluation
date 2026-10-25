# Rubric traceability

| Brief area | Marks | Implementation and evidence |
|---|---:|---|
| Agentic workflow and tool use | 20 | `rfp/orchestrator.py`: explicit tool order, fresh criteria snapshot, bounded retries, isolated supplier failures, audit trace |
| PDF extraction and prompting | 15 | `rfp/document.py`, `rfp/evaluator.py`: page-aware PyMuPDF extraction, size limits, encrypted/empty rejection, dynamic criteria, JSON-only evidence prompt, untrusted-content instruction |
| Validation and scoring | 20 | `rfp/validation.py`, `rfp/models.py`: Pydantic normalized schema, missing/invalid defaults, clipping, unknown/duplicate ID handling, actual quote matching; formula unit tests |
| Peer ranking and tie-breaks | 20 | `rfp/ranking.py`: weighted absolute score, best observed benchmark, gaps, relative %, PPI, Decimal arithmetic and exact mandatory sorting sequence |
| SQLite and persistence | 10 | `rfp/db.py`: three required SQL tables, parameterized queries, atomic saves, immutable criteria snapshots, complete run JSON, round-trip and integrity tests |
| Streamlit UI | 10 | `app.py`: editable criteria, multiple PDF upload and metadata, leaderboard, detailed evidence, risks, warnings, run history, export, validation lab |
| Documentation and testing | 5 | README, four three-page proposals, sample export, demonstration script, automated tests and GitHub Actions |

## Deliberate design choices

- The orchestrator is a lightweight Python workflow, as expressly permitted in the brief. It is not a free-running autonomous agent or a LangGraph system.
- Peer benchmarks are computed from the current successful cohort. No external industry benchmark is claimed.
- If a criterion's peer benchmark is zero, all suppliers receive 0 relative percent for that criterion. Its weight remains in the PPI denominator. This avoids awarding full credit for universal lack of evidence.
- The model's maximum is never trusted; the SQLite configuration is authoritative.
- A positive score requires a normalized exact quotation found on a source page. This verifies provenance, not the truth of supplier claims or the adequacy of the reasoning.
- Missing and malformed criterion rows become zero scores with warnings. Invalid top-level JSON triggers retry. Failure after the bound is visible and excluded from benchmarks.
- PPI is computed without display rounding. Date sorts ascending, experience descending, and supplier name case-insensitively ascending. Duplicate names are rejected.
- The bundled scorecards are authored fixtures, clearly labeled in the interface, export and documentation. They demonstrate reproducibility without misrepresenting a live LLM run.

## Remaining submission verification

The live Gemini request path has mocked contract tests. A real provider call requires the student's own API key and quota. A completed offline run is not evidence that live Gemini authentication or quota is working. Public deployment must be checked separately after publishing.
