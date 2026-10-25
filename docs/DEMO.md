# Five-minute demonstration

## 1. Explain the workflow (30 seconds)

“This app follows the five components in the brief. The orchestrator calls PDF extraction, an evaluator, validation, and deterministic ranking, then saves results to SQLite. Only content judgment belongs to the LLM. Python controls every formula and tie-break.”

## 2. Show database-driven criteria (30 seconds)

Open **Evaluation criteria**. Show the five defaults and the 100% total. Explain activation, maximum scores and descriptions. To demonstrate rejection, change a weight without compensating elsewhere and press **Save criteria**: the app rejects the change without corrupting the stored configuration. Restore the original value.

## 3. Complete a run (90 seconds)

Choose **Offline demonstration**, then **Run four-supplier demo**. This is explicitly a reproducible fixture demonstration, not a live AI result. All four three-page PDFs pass through actual extraction, evidence matching, arithmetic and SQL persistence.

Expected default ranking:

| Rank | Supplier | Absolute / 100 | PPI % |
|---:|---|---:|---:|
| 1 | NexaWorks | 83.00 | 92.22 |
| 2 | Apex Systems | 79.00 | 87.78 |
| 3 | Orbit Digital | 66.00 | 73.33 |
| 4 | BrightPath Tech | 58.00 | 64.44 |

Inspect NexaWorks, expand Implementation Plan, and compare the exact page-two evidence with the proposal. Show the raw score, weight, weighted score, peer best, negative gap and relative percentage. Explain that historical experience only breaks equal PPIs after submission dates.

## 4. Show a validation/error case (45 seconds)

Open **Validation lab**. Run **Malformed JSON**: it is rejected. In a real run, the orchestrator retries up to three total attempts; a supplier that still fails is excluded and the cohort is marked partial or failed.

Next run **Out-of-range and missing criteria**. Show score clipping and missing criteria set to zero with warnings. Run **Unsupported evidence** to show invented quotations cannot earn a positive score.

## 5. Prove persistence and export (45 seconds)

Open **Saved runs**, choose the run and click **Load saved run**. Return to **Evaluate & compare** and download complete JSON. Point out the RFP_RUN_ID, criteria snapshot, extracted source pages, fingerprints, warnings and workflow trace. A later configuration change cannot rewrite the criteria in the earlier JSON.

## 6. Live AI demonstration (additional time / API key needed)

Download the bundled proposals. Select **Live Gemini evaluation**, enter your own Gemini key in the password field, confirm a model available to your account, and upload all four PDFs. Enter the metadata from `samples/manifest.json`, consent to sending text to Google, and click **Evaluate uploaded proposals**. Inspect the returned evidence and warnings. Live scores may differ from the authored fixtures; arithmetic remains deterministic for fixed validated inputs.

Do not put API keys in screenshots, a recording, a commit, or this README. Click **Forget API key** when finished. No API key is required to assess the offline path.

## SQL inspection

Run `python -m scripts.run_demo` to create `data/demo.sqlite`, then inspect it with SQLite:

```sql
SELECT criterion_id, name, weight, max_score, is_active FROM evaluation_criteria;
SELECT rfp_run_id, created_at, status FROM rfp_runs;
SELECT supplier_name, absolute_score, ppi, final_rank
FROM supplier_results ORDER BY rfp_run_id, final_rank;
PRAGMA integrity_check;
```

The browser uses a separate database per session so visitors on a public deployment cannot browse each other's runs. Its files are under `data/sessions/` and are deliberately excluded from Git.
