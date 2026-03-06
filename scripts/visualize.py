#!/usr/bin/env python3
"""Generate JQADI visualizations per job_quality_adjusted_ai_displacement.md"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT = DATA_DIR / "processed"
FIGS = Path(__file__).resolve().parent.parent / "output"
FIGS.mkdir(parents=True, exist_ok=True)

sns.set_style("whitegrid")
plt.rcParams["figure.dpi"] = 120


def _annotate_quadrant(ax, df, quadrant, n=2):
    """Add representative occupation names to a quadrant."""
    q = df[df["quadrant"] == quadrant].nlargest(n, "employment")
    for i, (_, row) in enumerate(q.iterrows()):
        offset = (10, 10) if i == 0 else (-10, -10)
        ax.annotate(
            row["Title"][:22] + (".." if len(str(row["Title"])) > 22 else ""),
            (row["ai_exposure"], row["JQI"]),
            fontsize=7,
            alpha=0.85,
            xytext=offset,
            textcoords="offset points",
        )


def main():
    df = pd.read_csv(OUT / "jqadi.csv")
    df["employment"] = pd.to_numeric(df["employment"], errors="coerce").fillna(0)
    df = df[df["employment"] > 0]

    df["quadrant"] = "Low AI, High Quality"
    df.loc[df["ai_exposure"] >= 0.5, "quadrant"] = "High AI, High Quality"
    df.loc[(df["ai_exposure"] < 0.5) & (df["JQI"] < 0.5), "quadrant"] = "Low AI, Low Quality"
    df.loc[(df["ai_exposure"] >= 0.5) & (df["JQI"] < 0.5), "quadrant"] = "High AI, Low Quality"

    # 1. 2D scatter: AI Exposure × Job Quality (sized by employment, annotated)
    fig, ax = plt.subplots(figsize=(12, 9))
    size = (df["employment"] / 1000).clip(upper=500)
    scatter = ax.scatter(
        df["ai_exposure"],
        df["JQI"],
        s=size,
        alpha=0.6,
        c=df["JQADI"],
        cmap="YlOrRd",
    )
    ax.axhline(0.5, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(0.5, color="gray", linestyle="--", alpha=0.5)
    ax.set_xlabel("AI Exposure")
    ax.set_ylabel("Job Quality Index")
    ax.set_title("JQADI: AI Exposure × Job Quality (bubble size = employment)")
    for quad, x, y in [
        ("Low AI, High Quality", 0.15, 0.85),
        ("High AI, High Quality", 0.75, 0.85),
        ("Low AI, Low Quality", 0.15, 0.15),
        ("High AI, Low Quality", 0.75, 0.15),
    ]:
        ax.text(x, y, quad, fontsize=10, alpha=0.7, transform=ax.transAxes)
    _annotate_quadrant(ax, df, "Low AI, High Quality")
    _annotate_quadrant(ax, df, "Low AI, Low Quality")
    _annotate_quadrant(ax, df, "High AI, Low Quality")
    _annotate_quadrant(ax, df, "High AI, High Quality")
    plt.colorbar(scatter, ax=ax, label="JQADI")
    plt.tight_layout()
    plt.savefig(FIGS / "jqadi_scatter.png", bbox_inches="tight")
    plt.close()
    print(f"  Saved {FIGS / 'jqadi_scatter.png'}")

    # 2. Quadrant analysis
    quad = df.groupby("quadrant").agg(
        occupations=("soc", "count"),
        employment=("employment", "sum"),
        mean_jqadi=("JQADI", "mean"),
    )
    quad["employment"] = quad["employment"].round(0)
    quad["mean_jqadi"] = quad["mean_jqadi"].round(3)
    quad.to_csv(FIGS / "quadrant_analysis.csv")
    print(f"  Saved {FIGS / 'quadrant_analysis.csv'}")

    # 3. Top 15 highest JQADI (highest combined risk)
    top = df.nlargest(15, "JQADI")[["Title", "ai_exposure", "JQI", "JQADI", "employment"]]
    top.to_csv(FIGS / "top_jqadi_occupations.csv", index=False)
    print(f"  Saved {FIGS / 'top_jqadi_occupations.csv'}")

    # 3b. Trapped workers, good safe jobs, task residual - copy from build output
    for fname in ["trapped_workers.csv", "good_safe_jobs.csv", "task_residual_risk.csv", "career_viable_safe.csv"]:
        src = OUT / fname
        if src.exists():
            pd.read_csv(src).to_csv(FIGS / fname, index=False)
            print(f"  Saved {FIGS / fname}")

    # 4. Bar chart: good safe jobs vs trapped jobs (employment)
    jqi_med = df["JQI"].median()
    good_safe_emp = df[(df["ai_exposure"] < 0.3) & (df["JQI"] > jqi_med)]["employment"].sum()
    trapped_emp = df[(df["ai_exposure"] < 0.3) & (df["JQI"] <= jqi_med)]["employment"].sum()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["Good safe jobs\n(low AI, high quality)", "Trapped workers\n(low AI, low quality)"], [good_safe_emp / 1e6, trapped_emp / 1e6])
    ax.set_ylabel("Employment (millions)")
    ax.set_title("Low-AI-Exposure Jobs: Good vs Trapped")
    plt.tight_layout()
    plt.savefig(FIGS / "good_safe_vs_trapped.png", bbox_inches="tight")
    plt.close()
    print(f"  Saved {FIGS / 'good_safe_vs_trapped.png'}")

    # 5. Task-residual scatter: cognitive_share vs ai_exposure, colored by physical_share
    if "cognitive_share" in df.columns and "physical_share" in df.columns:
        tr_df = df[(df["ai_exposure"] > 0.2) & (df["ai_exposure"] < 0.7) & (df["employment"] > 1000)]
        if not tr_df.empty:
            fig, ax = plt.subplots(figsize=(10, 7))
            size = (tr_df["employment"] / 1000).clip(upper=300)
            scatter = ax.scatter(
                tr_df["ai_exposure"],
                tr_df["cognitive_share"],
                s=size,
                alpha=0.6,
                c=tr_df["physical_share"],
                cmap="viridis",
            )
            ax.set_xlabel("AI Exposure")
            ax.set_ylabel("Cognitive task share")
            ax.set_title("Task residual risk: AI automates cognitive work (color = physical share remaining)")
            plt.colorbar(scatter, ax=ax, label="Physical share")
            plt.tight_layout()
            plt.savefig(FIGS / "task_residual_scatter.png", bbox_inches="tight")
            plt.close()
            print(f"  Saved {FIGS / 'task_residual_scatter.png'}")

    # 6. Employment-weighted risk distribution
    fig, ax = plt.subplots(figsize=(8, 5))
    df_sorted = df.sort_values("JQADI")
    df_sorted["cum_employment"] = df_sorted["employment"].cumsum()
    ax.fill_between(range(len(df_sorted)), 0, df_sorted["cum_employment"] / 1e6, alpha=0.7)
    ax.set_xlabel("Occupations (sorted by JQADI)")
    ax.set_ylabel("Cumulative employment (millions)")
    ax.set_title("Employment-weighted JQADI distribution")
    plt.tight_layout()
    plt.savefig(FIGS / "jqadi_cumulative.png", bbox_inches="tight")
    plt.close()
    print(f"  Saved {FIGS / 'jqadi_cumulative.png'}")

    print(f"\nOutput: {FIGS}")


if __name__ == "__main__":
    main()
