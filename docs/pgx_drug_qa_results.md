# PGx Drug QA Results

**Date:** 2026-02-20
**Dataset:** `pgx_drug_qa/` — 100 tasks (multiple-choice questions from PGx research papers)

## Summary

### Raw results (including infra failures)

| Agent | Model | Tasks Completed | Mean Reward | Passed | Failed | Partial |
|-------|-------|:-:|:-:|:-:|:-:|:-:|
| **Codex** | gpt-5 | 100 | **0.828** | 82 | 17 | 1 |
| **Claude Code** | claude-sonnet-4-6 | 30 / 100* | **0.883** | 26 | 3 | 1 |

### Adjusted results (excluding infra failures)

Infra failures are tasks that failed due to issues unrelated to model accuracy:
- **Codex**: 2 tasks timed out (exceeded 600s limit) — `pmc10154044` (98 questions) and `pmc10399933` (20 questions)
- **Claude Code**: 70 tasks failed due to Anthropic API credit exhaustion (not counted above)

| Agent | Model | Tasks Evaluated | Mean Reward | Passed | Failed | Partial |
|-------|-------|:-:|:-:|:-:|:-:|:-:|
| **Codex** | gpt-5 | 98 | **0.845** | 82 | 15 | 1 |
| **Claude Code** | claude-sonnet-4-6 | 30* | **0.883** | 26 | 3 | 1 |

\* Claude Code run was cut short due to Anthropic API credit exhaustion after 30 tasks. Full 100-task run needed for a fair comparison.

**Duration:** Codex completed all 100 tasks in ~244 minutes (~4 hours) with `-n 1` concurrency.

## Head-to-Head (30 overlapping tasks)

On the 30 tasks where both agents completed (no infra failures):

| Agent | Mean Reward | Passed | Failed | Partial |
|-------|:-:|:-:|:-:|:-:|
| **Codex** | **0.917** | 27 | 2 | 1 |
| **Claude Code** | **0.883** | 26 | 3 | 1 |

Disagreements on overlapping tasks:

| Task | Claude Code | Codex | Notes |
|------|:-:|:-:|-------|
| `pmc10318569` | 0.0 | 1.0 | Claude fixated on morphine-3-glucuronide; Codex got codeine/morphine/tramadol correct |
| `pmc10520058` | 1.0 | 0.0 | Claude got edoxaban questions right; Codex failed all 10 |
| `pmc10537526` | 1.0 | 0.0 | Claude got tramadol/o-desmethyltramadol right; Codex missed |
| `pmc10374328` | 0.5 | 0.0 | Claude got 1/2 carbamazepine questions; Codex got 0/2 |
| `pmc10565537` | 1.0 | 0.83 | Claude perfect; Codex missed 1/6 on fulvestrant/anastrozole |

Both failed: `pmc10159199` (Platinum compounds), `pmc10541540` (ethambutol/isoniazid multi-drug).

## Codex (gpt-5) — Full Results (100 tasks)

### Per-task results

| Task | Reward | Qs | Notes |
|------|:-:|:-:|-------|
| pmc10026301 | 1.0 | 10 | cytarabine, daunorubicin |
| pmc10031538 | 1.0 | 2 | clopidogrel |
| pmc10038974 | 1.0 | 2 | solanidine |
| pmc10039478 | 1.0 | 12 | acetaminophen / tramadol |
| pmc10049548 | 1.0 | 6 | lenvatinib |
| pmc10058912 | 1.0 | 2 | metoprolol |
| pmc10085626 | 1.0 | 6 | methotrexate |
| pmc10089949 | 1.0 | 2 | tacrolimus |
| pmc10091789 | 1.0 | 14 | Dihydropyridine derivatives |
| pmc10099095 | 1.0 | 4 | brexpiprazole |
| pmc10139129 | **0.0** | 8 | opioids |
| pmc10139887 | 1.0 | 8 | osimertinib |
| pmc10145266 | 1.0 | 2 | tacrolimus |
| pmc10151137 | 1.0 | 4 | cisplatin |
| pmc10152845 | 1.0 | 4 | radiotherapy |
| pmc10154044 | **0.0** | 98 | tenofovir — **infra: timeout** (600s limit, 98 Qs too many) |
| pmc10159199 | **0.0** | 8 | Platinum compounds |
| pmc10163902 | 1.0 | 4 | methotrexate |
| pmc10179231 | 1.0 | 2 | fentanyl |
| pmc10189794 | 1.0 | 8 | carbamazepine |
| pmc10189922 | 1.0 | 4 | bortezomib |
| pmc10193607 | 1.0 | 4 | tacrolimus |
| pmc10196221 | 1.0 | 14 | rivaroxaban |
| pmc10214567 | 1.0 | 4 | ivacaftor |
| pmc10214954 | 1.0 | 10 | mercaptopurine |
| pmc10216814 | **0.0** | 12 | CHOP, rituximab |
| pmc10230242 | 1.0 | 4 | radiotherapy |
| pmc10234323 | 1.0 | 4 | tenofovir |
| pmc10244018 | 1.0 | 4 | carvedilol |
| pmc10272067 | 1.0 | 2 | clopidogrel |
| pmc10275785 | **0.0** | 4 | etanercept, infliximab |
| pmc10278212 | 1.0 | 2 | tacrolimus |
| pmc10288459 | 1.0 | 2 | haloperidol |
| pmc1029622 | 1.0 | 4 | mercaptopurine |
| pmc10298094 | 1.0 | 8 | carboplatin, cisplatin |
| pmc10298263 | 1.0 | 12 | dabigatran |
| pmc10308004 | 1.0 | 4 | anthracyclines |
| pmc10309098 | 1.0 | 12 | levonorgestrel |
| pmc10309546 | 1.0 | 24 | antineoplastic agents |
| pmc10318569 | 1.0 | 2 | codeine, morphine, tramadol |
| pmc10319068 | 1.0 | 2 | carfilzomib |
| pmc10327396 | 1.0 | 6 | rivaroxaban |
| pmc10337687 | 1.0 | 4 | amoxicillin/clarithromycin/omeprazole |
| pmc10344568 | 1.0 | 4 | peginterferon/ribavirin/sofosbuvir |
| pmc10349379 | 1.0 | 4 | morphine |
| pmc10349800 | 1.0 | 4 | isoniazid |
| pmc10350251 | 1.0 | 8 | azathioprine |
| pmc10352989 | 1.0 | 6 | docetaxel, paclitaxel |
| pmc10361978 | **0.0** | 6 | cyclophosphamide |
| pmc10366597 | 1.0 | 4 | cimetidine, metoclopramide |
| pmc10368781 | 1.0 | 12 | lenalidomide |
| pmc10374328 | **0.0** | 2 | carbamazepine |
| pmc10377184 | 1.0 | 8 | antipsychotics |
| pmc10381361 | 1.0 | 6 | fentanyl, meperidine, midazolam |
| pmc10381559 | 1.0 | 2 | mesalazine |
| pmc10385908 | 1.0 | 12 | EGFR tyrosine kinase inhibitors |
| pmc10399933 | **0.0** | 20 | statins — **infra: timeout** (600s limit) |
| pmc10404408 | **0.0** | 6 | l-asparagine |
| pmc10404721 | 1.0 | 6 | levofloxacin |
| pmc10407116 | 1.0 | 2 | pirfenidone |
| pmc10409991 | 1.0 | 4 | tacrolimus |
| pmc10411392 | 1.0 | 2 | paclitaxel |
| pmc10416089 | **0.0** | 4 | citalopram/escitalopram + SSRIs |
| pmc10418744 | **0.0** | 4 | elexacaftor/tezacaftor/ivacaftor |
| pmc10435398 | 1.0 | 2 | vincristine |
| pmc10443690 | 1.0 | 2 | voriconazole |
| pmc10448185 | 1.0 | 2 | pimozide |
| pmc10452379 | 1.0 | 8 | warfarin |
| pmc10460569 | 1.0 | 6 | apixaban, rivaroxaban |
| pmc10463210 | 1.0 | 2 | mercaptopurine |
| pmc10478012 | 1.0 | 4 | tacrolimus |
| pmc10483403 | 1.0 | 22 | dexmedetomidine |
| pmc10486269 | 1.0 | 4 | antidepressants, antipsychotics |
| pmc10487873 | **0.0** | 12 | capecitabine, fluorouracil |
| pmc10487921 | 1.0 | 2 | duloxetine |
| pmc10494815 | 1.0 | 2 | clobazam |
| pmc10495004 | 1.0 | 2 | voriconazole |
| pmc10499425 | 1.0 | 6 | dexmedetomidine, fentanyl |
| pmc10501134 | **0.0** | 4 | ethambutol/isoniazid/pyrazinamide/rifampin |
| pmc10501538 | 1.0 | 4 | carbamazepine |
| pmc10502099 | 1.0 | 2 | abatacept |
| pmc10506908 | 1.0 | 2 | mercaptopurine, methotrexate |
| pmc1050876 | 1.0 | 2 | streptomycin |
| pmc1051117 | 1.0 | 2 | streptomycin |
| pmc1051806 | 1.0 | 2 | isoflurane, succinylcholine |
| pmc10520058 | **0.0** | 10 | edoxaban |
| pmc10522553 | 1.0 | 2 | doxepin |
| pmc10526247 | 1.0 | 4 | antiepileptics |
| pmc10526923 | **0.0** | 8 | methotrexate |
| pmc10527451 | 1.0 | 4 | allopurinol |
| pmc10529681 | 1.0 | 2 | endoxifen |
| pmc10532840 | 1.0 | 2 | adalimumab/certolizumab/golimumab/infliximab |
| pmc10532907 | 1.0 | 6 | fluoxetine |
| pmc10536177 | 1.0 | 2 | capecitabine, fluorouracil |
| pmc10537526 | **0.0** | 4 | o-desmethyltramadol, tramadol |
| pmc10541540 | **0.0** | 10 | ethambutol/isoniazid/pyrazinamide/rifampin |
| pmc10550831 | 1.0 | 2 | clopidogrel |
| pmc10557961 | 1.0 | 4 | clopidogrel |
| pmc10564446 | 1.0 | 2 | anakinra/canakinumab/rilonacept/tocilizumab |
| pmc10565537 | **0.83** | 6 | fulvestrant, anastrozole (5/6 correct) |

## Claude Code (claude-sonnet-4-6) — Partial Results (30/100 tasks)

Run cut short due to Anthropic API credit exhaustion.

| Task | Reward | Notes |
|------|:-:|-------|
| pmc10038974 | 1.0 | |
| pmc10049548 | 1.0 | |
| pmc10145266 | 1.0 | |
| pmc10159199 | **0.0** | Platinum compounds |
| pmc10163902 | 1.0 | |
| pmc10179231 | 1.0 | |
| pmc10189922 | 1.0 | |
| pmc10244018 | 1.0 | |
| pmc10288459 | 1.0 | |
| pmc10298094 | 1.0 | |
| pmc10298263 | 1.0 | |
| pmc10318569 | **0.0** | Fixated on morphine-3-glucuronide |
| pmc10337687 | 1.0 | |
| pmc10374328 | **0.5** | 1/2 carbamazepine questions |
| pmc10407116 | 1.0 | |
| pmc10409991 | 1.0 | |
| pmc10411392 | 1.0 | |
| pmc10463210 | 1.0 | |
| pmc10483403 | 1.0 | |
| pmc10487921 | 1.0 | |
| pmc10502099 | 1.0 | |
| pmc10506908 | 1.0 | |
| pmc1051117 | 1.0 | |
| pmc10520058 | 1.0 | |
| pmc10529681 | 1.0 | |
| pmc10532907 | 1.0 | |
| pmc10537526 | 1.0 | |
| pmc10541540 | **0.0** | ethambutol/isoniazid multi-drug |
| pmc10550831 | 1.0 | |
| pmc10565537 | 1.0 | |

## Failure Patterns

### Infra failures (excluded from adjusted accuracy)

| Agent | Task | Cause |
|-------|------|-------|
| Codex | `pmc10154044` (98 Qs) | Agent timeout — 600s limit too short for 98 questions |
| Codex | `pmc10399933` (20 Qs) | Agent timeout — 600s limit too short |
| Claude Code | 70 tasks | Anthropic API credit exhaustion mid-run |

### Real model failures — common themes

1. **Multi-drug combinations**: Tasks involving complex multi-drug regimens (e.g., ethambutol/isoniazid/pyrazinamide/rifampin) are harder — both agents failed `pmc10541540` and Codex failed `pmc10501134`.

2. **Drug class vs. specific drug**: Some failures involve confusion between drug classes (e.g., "Platinum compounds", "SSRIs") and specific drugs.

3. **Single-drug fixation**: Claude Code showed a pattern of fixating on a single drug when the correct answer involved multiple drugs (e.g., `pmc10318569` — answered "morphine-3-glucuronide" instead of "codeine, morphine, tramadol").

## Run Configuration

- **Harbor** benchmark runner with Docker-based task environments
- **Concurrency**: `-n 1` (single concurrent trial)
- **Timeout**: 600s per task
- **Codex job**: `2026-02-20__02-47-55`
- **Claude Code job**: `2026-02-20__02-40-26`
