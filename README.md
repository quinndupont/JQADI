# Job Quality-Adjusted Displacement Index (JQADI)

AI displacement risk focuses on *which* jobs get automated. The harder question is *who* gets left doing the jobs no one wants—the "meat machines" of the coming economy: cooks, roofers, dishwashers, construction laborers. Safe from AI, unsustainable for humans. Low pay, high physical toll, no career trajectory. This repository implements a **Job Quality-Adjusted Displacement Index** that reframes labor market vulnerability to capture both AI exposure and the quality of the jobs that remain.

---

## The Original Index

Anthropic's "Labor market impacts of AI" (Massenkoff & McCrory, 2026) and Eloundou et al.'s GPTs-are-GPTs (2023) measure *observed exposure*—which occupations face AI displacement risk based on task-level LLM capability and real-world Claude usage. The bottom 30% of workers by their measure have zero observed coverage: cooks, lifeguards, bartenders, dishwashers, dressing room attendants.

The implicit assumption: low exposure means "safe." But the most AI-exposed workers are older, more educated, and earn 47% more than the least exposed. AI displacement risk is inversely correlated with job quality. The "safe" jobs are, in many cases, the worst jobs.

---

## The JQADI Framework

For each occupation *o*:

```
JQADI_o = f(AI_Exposure_o, Job_Quality_o)
```

We identify **two danger zones**:

1. **High AI exposure** → Traditional displacement risk (the original papers' focus)
2. **Low AI exposure, low quality** → "Trapped" workers: grinding, unsustainable jobs with no upward mobility

And the **most concerning** category:

3. **Moderate AI exposure, low quality** → Partial automation strips cognitive work, leaving physical drudgery—wage compression, deskilling, task intensification without displacement (the **task residual** effect)

---

## Job Quality Index (JQI)

A composite index [0, 1] from six sub-dimensions:

| Dimension | Weight | Data |
|-----------|--------|------|
| Compensation | 20% | Median hourly wage (OEWS) |
| Physical sustainability | 25% | O\*NET body posture, hazards, environmental exposure, protective equipment; Work Activities physical; Abilities dynamic strength |
| Autonomy | 25% | O\*NET Freedom to Make Decisions, Determine Tasks, Decision Frequency, inverse Repetition, inverse Pace by Equipment |
| Career | 20% | O\*NET Job Zone |
| Employment outlook | 5% | BLS projections pct change (when matched) |
| Age sustainability | 5% | CPS Table 11b ratio 55+ / 25–34 (when available) |

**Age ratio** (55+ / 25–34): A low ratio indicates the occupation "burns through" workers before they age—you don't see 60-year-old roofers. CPS Table 11b provides this directly.

---

## JQADI Formula

```
JQADI = 0.25×AI_Exposure + 0.6×(1−JQI) + 0.15×AI_Exposure×(1−JQI)
```

Weights elevate low-quality jobs so trapped workers rank higher. **Trapped index**: For AI < 0.3, rank by 1−JQI.

---

## Key Outputs

| File | Description |
|------|--------------|
| `good_safe_jobs.csv` | Low AI exposure + high JQI—Podiatrists, Nurse Anesthetists, Dentists, Physical Therapists, etc. |
| `trapped_workers.csv` | Low AI, low quality—landscapers, construction laborers, meat cutters, dishwashers |
| `task_residual_risk.csv` | Jobs where AI automates cognitive work, leaving physical drudgery |
| `career_viable_safe.csv` | Good safe jobs with wage above median and sustainable age profile |

See [output/](output/) for visualizations and full results.

---

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python scripts/download_data.py
python scripts/build_jqadi.py
python scripts/visualize.py
```

**Data requirements**: O\*NET 30.2, Anthropic job_exposure (or Eloundou β fallback), GPTs repo OEWS/projections, CPS Table 11b (manual download if BLS blocks). See `scripts/download_data.py` for URLs.

---

## Limitations

- **GSS-QWL, SOII, NCS, JOLTS** not integrated (require registration, crosswalks, or different granularity)
- **Observed exposure** is single-platform (Claude); Eloundou β used as fallback
- **Robotics** not modeled; physical labor faces separate automation threat (e.g., Acemoglu & Restrepo)
- **Weighting** is a judgment call; sensitivity analysis recommended

---

## References

- Massenkoff, M. & McCrory, P. (2026). Labor market impacts of AI: A new measure and early evidence. Anthropic.
- Eloundou, T., Manning, S., Mishkin, P., & Rock, D. (2023). GPTs are GPTs: An early look at the labor market impact potential of large language models.
- Handa, K., et al. (2025). Which economic tasks are performed with AI? Evidence from millions of Claude conversations.
- Acemoglu, D. & Restrepo, P. (2020). Robots and Jobs: Evidence from US Labor Markets. JPE.
