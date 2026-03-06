# JQADI Outputs

Results from the Job Quality-Adjusted Displacement Index pipeline. All figures are sized by employment where applicable.

## Visualizations

### AI Exposure × Job Quality (quadrant map)

![JQADI scatter](jqadi_scatter.png)

Four quadrants: High/Low AI × High/Low Quality. Bubble size = employment. Color = JQADI (combined risk). The lower-left quadrant—low AI, low quality—contains the "trapped" workers (meat machines).

### Good Safe vs. Trapped (low-AI jobs)

![Good safe vs trapped](good_safe_vs_trapped.png)

Employment in low-AI-exposure jobs split by quality: good safe jobs (high JQI) vs. trapped workers (low JQI).

### Task Residual Risk

![Task residual scatter](task_residual_scatter.png)

Cognitive task share vs. AI exposure. Color = physical share remaining. High values indicate jobs where AI strips cognitive work, leaving physical drudgery.

### Employment-Weighted Cumulative Risk

![JQADI cumulative](jqadi_cumulative.png)

Cumulative employment (millions) as occupations are sorted by JQADI ascending.

---

## CSV Files

| File | Description |
|------|--------------|
| `quadrant_analysis.csv` | Counts and employment by quadrant (High/Low AI × High/Low Quality) |
| `top_jqadi_occupations.csv` | Top 15 occupations by combined JQADI risk |
| `trapped_workers.csv` | Low AI, low quality—landscapers, construction laborers, meat cutters, dishwashers |
| `good_safe_jobs.csv` | Low AI exposure + JQI above median |
| `task_residual_risk.csv` | Jobs where AI automates cognitive work, leaving physical tasks |
| `career_viable_safe.csv` | Good safe jobs with wage above median and sustainable age ratio (55+ / 25–34) |
