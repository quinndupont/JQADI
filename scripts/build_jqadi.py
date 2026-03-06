#!/usr/bin/env python3
"""
Build Job Quality Index (JQI) and Job Quality-Adjusted Displacement Index (JQADI)
per job_quality_adjusted_ai_displacement.md
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW = DATA_DIR / "raw"
OUT = DATA_DIR / "processed"
OUT.mkdir(parents=True, exist_ok=True)


def normalize(x: pd.Series) -> pd.Series:
    """Min-max normalize to [0, 1]. Higher = better."""
    mn, mx = x.min(), x.max()
    if mx == mn:
        return pd.Series(0.5, index=x.index)
    return (x - mn) / (mx - mn)


def inv_normalize(x: pd.Series) -> pd.Series:
    """Inverse normalize: higher raw = lower score. 1 - norm."""
    return 1 - normalize(x)


def load_eloundou() -> pd.DataFrame:
    """Eloundou et al. AI exposure (β scores) by O*NET-SOC."""
    df = pd.read_csv(RAW / "eloundou_occ_exposure.csv")
    df["soc"] = df["O*NET-SOC Code"].astype(str).str.replace(r"\.\d+$", "", regex=True)
    return df[["soc", "Title", "dv_rating_beta", "human_rating_beta"]].drop_duplicates("soc")


def load_anthropic_exposure() -> pd.DataFrame | None:
    """Anthropic Economic Index observed exposure from job_exposure.csv."""
    for path in [RAW / "job_exposure.csv", RAW / "labor_market_impacts" / "job_exposure.csv"]:
        if path.exists():
            df = pd.read_csv(path)
            if "occ_code" in df.columns and "observed_exposure" in df.columns:
                out = df[["occ_code", "observed_exposure"]].copy()
                out["soc"] = out["occ_code"].astype(str).str.replace(r"\.\d+$", "", regex=True).str.strip()
                return out.groupby("soc")["observed_exposure"].mean().reset_index().rename(columns={"observed_exposure": "observed_coverage"})
    return None


def load_oews() -> pd.DataFrame:
    """BLS OEWS: wages and employment by SOC."""
    df = pd.read_csv(RAW / "oes_national_2021.csv")
    df = df[df["O_GROUP"] == "detailed"].copy()
    df["soc"] = df["OCC_CODE"].astype(str).str.strip()
    for col in ["TOT_EMP", "H_MEDIAN", "H_MEAN"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "").replace("#", "").replace("*", ""), errors="coerce")
    return df


def _norm_title(s: str) -> str:
    """Normalize occupation title for matching."""
    if pd.isna(s):
        return ""
    return str(s).lower().replace(",", "").replace("-", " ").strip()


def load_onet_work_context() -> pd.DataFrame:
    """O*NET Work Context: physical demands, hazards, autonomy (expanded per plan)."""
    wc = pd.read_excel(RAW / "onet_Work_Context.xlsx")
    wc = wc[wc["Scale ID"] == "CX"].copy()
    wc["soc"] = wc["O*NET-SOC Code"].astype(str).str.replace(r"\.\d+$", "", regex=True)
    piv = wc.pivot_table(index="soc", columns="Element ID", values="Data Value", aggfunc="mean").reset_index()

    # Body posture toll (higher = worse): standing, climbing, walking, kneeling, balance, bending, repetitive
    body_toll = [
        "4.C.2.d.1.b",  # Spend Time Standing
        "4.C.2.d.1.c",  # Climbing Ladders, Scaffolds, Poles
        "4.C.2.d.1.d",  # Walking or Running
        "4.C.2.d.1.e",  # Kneeling, Crouching, Stooping, Crawling
        "4.C.2.d.1.f",  # Keeping or Regaining Balance
        "4.C.2.d.1.h",  # Bending or Twisting Your Body
        "4.C.2.d.1.i",  # Making Repetitive Motions
    ]
    # Environmental hazards
    hazard_cols = [
        "4.C.2.b.1.a",  # Noise
        "4.C.2.b.1.b",  # Temperature
        "4.C.2.b.1.d",  # Contaminants
        "4.C.2.b.1.e",  # Cramped work space
        "4.C.2.b.1.f",  # Whole Body Vibration
        "4.C.2.c.1.a",  # Radiation
        "4.C.2.c.1.b",  # Disease or Infections
        "4.C.2.c.1.c",  # High Places
        "4.C.2.c.1.d",  # Hazardous Conditions
        "4.C.2.c.1.e",  # Hazardous Equipment
        "4.C.2.c.1.f",  # Burns, Cuts, Bites, Stings
    ]
    # Protective equipment (more = worse conditions)
    protect_cols = ["4.C.2.e.1.d", "4.C.2.e.1.e"]
    body_cols = [c for c in body_toll if c in piv.columns]
    hazard_cols = [c for c in hazard_cols if c in piv.columns]
    protect_cols = [c for c in protect_cols if c in piv.columns]

    toll_parts = []
    if body_cols:
        toll_parts.append(piv[body_cols].mean(axis=1))
    if hazard_cols:
        toll_parts.append(piv[hazard_cols].mean(axis=1))
    if protect_cols:
        toll_parts.append(piv[protect_cols].mean(axis=1))
    # Inverse of sitting: more sitting = less physical toll (positive for sustainability)
    if "4.C.2.d.1.a" in piv.columns:
        piv["sitting"] = piv["4.C.2.d.1.a"]

    if toll_parts:
        piv["physical_toll"] = pd.concat(toll_parts, axis=1).mean(axis=1)
        if "4.C.2.d.1.a" in piv.columns:
            piv["physical_toll"] = piv["physical_toll"] - 0.2 * piv["sitting"].fillna(0)
        piv["physical_sustainability"] = inv_normalize(piv["physical_toll"])
    else:
        piv["physical_sustainability"] = 0.5

    # Autonomy (expanded): Freedom to Make Decisions, Determine Tasks, Frequency of Decision Making,
    # inverse of Repetition, inverse of Pace by Equipment
    autonomy_parts = []
    if "4.C.3.a.4" in piv.columns:
        autonomy_parts.append(normalize(piv["4.C.3.a.4"]))
    if "4.C.3.b.8" in piv.columns:
        autonomy_parts.append(normalize(piv["4.C.3.b.8"]))
    if "4.C.3.a.2.b" in piv.columns:
        autonomy_parts.append(normalize(piv["4.C.3.a.2.b"]))
    if "4.C.3.b.7" in piv.columns:
        autonomy_parts.append(inv_normalize(piv["4.C.3.b.7"]))
    if "4.C.3.d.3" in piv.columns:
        autonomy_parts.append(inv_normalize(piv["4.C.3.d.3"]))
    if autonomy_parts:
        piv["autonomy"] = pd.concat(autonomy_parts, axis=1).mean(axis=1)
    else:
        piv["autonomy"] = 0.5
    return piv


def load_onet_work_activities() -> pd.DataFrame:
    """O*NET Work Activities: cognitive vs physical task composition for task-residual analysis."""
    wa = pd.read_excel(RAW / "onet_Work_Activities.xlsx")
    wa["soc"] = wa["O*NET-SOC Code"].astype(str).str.replace(r"\.\d+$", "", regex=True)
    piv = wa.pivot_table(index="soc", columns="Element ID", values="Data Value", aggfunc="mean")

    cognitive_ids = [c for c in piv.columns if c.startswith("4.A.1.") or c.startswith("4.A.2.")]
    physical_ids = ["4.A.3.a.1", "4.A.3.a.2"]  # General Physical, Handling/Moving Objects
    physical_ids = [c for c in physical_ids if c in piv.columns]
    cognitive_ids = [c for c in cognitive_ids if c in piv.columns]

    out = pd.DataFrame(index=piv.index).reset_index()
    if cognitive_ids:
        out["cognitive_share"] = piv[cognitive_ids].mean(axis=1)
    else:
        out["cognitive_share"] = 0.5
    if physical_ids:
        out["physical_share"] = piv[physical_ids].mean(axis=1)
    else:
        out["physical_share"] = 0.5
    total = out["cognitive_share"] + out["physical_share"]
    out["task_ratio"] = np.where(total > 0, out["physical_share"] / total, 0.5)
    return out


def load_onet_abilities_physical() -> pd.DataFrame:
    """O*NET Abilities: Dynamic Strength (lifting, climbing)."""
    if not (RAW / "onet_Abilities.xlsx").exists():
        return pd.DataFrame(columns=["soc", "dynamic_strength"])
    ab = pd.read_excel(RAW / "onet_Abilities.xlsx")
    ab = ab[ab["Element ID"] == "1.A.3.a.3"].copy()
    if ab.empty:
        return pd.DataFrame(columns=["soc", "dynamic_strength"])
    ab["soc"] = ab["O*NET-SOC Code"].astype(str).str.replace(r"\.\d+$", "", regex=True)
    return ab[["soc", "Data Value"]].rename(columns={"Data Value": "dynamic_strength"})


def load_onet_job_zones() -> pd.DataFrame:
    """O*NET Job Zones: training/education level."""
    jz = pd.read_excel(RAW / "onet_Job_Zones.xlsx")
    jz["soc"] = jz["O*NET-SOC Code"].astype(str).str.replace(r"\.\d+$", "", regex=True)
    return jz[["soc", "Job Zone"]].drop_duplicates()


def load_bls_projections() -> pd.DataFrame:
    """BLS employment projections: pct_emp_change by occupation. Crosswalk to SOC via title match."""
    if not (RAW / "bls_projections.csv").exists():
        return pd.DataFrame(columns=["soc", "pct_emp_change"])
    proj = pd.read_csv(RAW / "bls_projections.csv")
    proj["occupation_norm"] = proj["occupation"].astype(str).apply(_norm_title)
    proj = proj[~proj["occupation"].str.contains("Total|occupations$", case=False, regex=True, na=False)]
    proj["pct_emp_change"] = pd.to_numeric(proj["pct_emp_change_2020_2030"], errors="coerce")
    return proj[["occupation", "occupation_norm", "pct_emp_change"]].dropna(subset=["pct_emp_change"])


def load_bls_age_ratio() -> pd.DataFrame | None:
    """Occupational lifespan: ratio of workers 55+ to 25-34. Low ratio = burns through workers.
    Source: CPS Table 11b (cpsaat11b.xlsx)."""
    for path in [RAW / "cpsaat11b.xlsx", RAW / "cps_ea19_age_occupation.xlsx"]:
        if not path.exists():
            continue
        try:
            df = pd.read_excel(path, header=None)
            df.columns = range(len(df.columns))
            # Find header row with age bands (25 to 34, 55 to 64, etc.)
            header_idx = None
            col_25_34, col_55_64, col_65_plus, col_occ = None, None, None, None
            for i in range(min(10, len(df))):
                row = df.iloc[i]
                for col in range(len(row)):
                    val = str(row[col] if pd.notna(row[col]) else "").lower()
                    if "25 to 34" in val or "25-34" in val:
                        col_25_34 = col
                    if "55 to 64" in val or "55-64" in val:
                        col_55_64 = col
                    if "65 years" in val or "65 and" in val or "65 and over" in val:
                        col_65_plus = col
                    if "occupation" in val and col_occ is None:
                        col_occ = col
                if col_25_34 is not None and col_55_64 is not None:
                    header_idx = i
                    break
            if header_idx is None or col_25_34 is None or col_55_64 is None:
                continue
            # Occupation in column 1 for BLS Table 11b (often col 0 is empty)
            if col_occ is None:
                col_occ = 1
            data = df.iloc[header_idx + 1 :].copy()
            data = data[data.iloc[:, col_occ].notna() & (data.iloc[:, col_occ].astype(str).str.strip() != "")]
            data = data[~data.iloc[:, col_occ].astype(str).str.contains("Total|occupations", case=False, na=False)]
            def _tonum(s):
                return pd.to_numeric(s.astype(str).str.replace(",", "").replace("–", "").replace("-", ""), errors="coerce")

            age_25_34 = _tonum(data.iloc[:, col_25_34])
            age_55_64 = _tonum(data.iloc[:, col_55_64])
            age_65_plus = _tonum(data.iloc[:, col_65_plus]) if col_65_plus is not None else pd.Series(0.0, index=data.index)
            age_55_plus = age_55_64.fillna(0) + age_65_plus.fillna(0)
            out = pd.DataFrame({
                "occupation": data.iloc[:, col_occ].values,
                "age_25_34": age_25_34.values,
                "age_55_plus": age_55_plus.values,
            })
            out["age_25_34"] = out["age_25_34"].replace(0, np.nan)
            out["age_ratio"] = out["age_55_plus"] / out["age_25_34"]
            out["occupation_norm"] = out["occupation"].astype(str).apply(_norm_title)
            return out[["occupation", "occupation_norm", "age_ratio"]].dropna(subset=["age_ratio"])
        except Exception:
            pass
    return None


def load_onet_bls_matched() -> pd.DataFrame:
    """O*NET-BLS matched: employment, wages for O*NET occupations."""
    df = pd.read_csv(RAW / "onet_bls_matched.csv")
    df = df[df["TOT_EMP"].notna()].copy()
    df["soc"] = df["OCC_CODE"].astype(str).str.replace(r"-\d+$", "", regex=True)
    return df


def _build_title_to_soc() -> pd.DataFrame:
    """Build occupation title (normalized) to SOC mapping from onet_bls_matched."""
    bls = pd.read_csv(RAW / "onet_bls_matched.csv")
    bls["soc"] = bls["OCC_CODE"].astype(str).str.replace(r"\.\d+$", "", regex=True).str.strip()
    bls["title_norm"] = bls["OCC_TITLE"].fillna(bls["occupation"]).astype(str).apply(_norm_title)
    return bls[["soc", "title_norm"]].drop_duplicates("soc", keep="first")


def build_jqi() -> pd.DataFrame:
    """Construct Job Quality Index from available data (expanded per plan)."""
    oews = load_oews()
    oews_soc = oews.groupby("soc").agg(
        wage_median=("H_MEDIAN", "first"),
        employment=("TOT_EMP", "first"),
    ).reset_index()

    wc = load_onet_work_context()
    wa = load_onet_work_activities()
    ab_phys = load_onet_abilities_physical()
    wc = wc.merge(wa[["soc", "physical_share", "cognitive_share", "task_ratio"]], on="soc", how="left")
    if not ab_phys.empty:
        wc = wc.merge(ab_phys, on="soc", how="left")
    toll_parts = [normalize(wc["physical_toll"])]
    if "physical_share" in wc.columns:
        toll_parts.append(normalize(wc["physical_share"].fillna(wc["physical_share"].median())))
    if "dynamic_strength" in wc.columns:
        toll_parts.append(normalize(wc["dynamic_strength"].fillna(wc["dynamic_strength"].median())))
    wc["physical_toll"] = pd.concat(toll_parts, axis=1).mean(axis=1)
    wc["physical_sustainability"] = inv_normalize(wc["physical_toll"])

    jz = load_onet_job_zones()
    jz["career_investment"] = normalize(jz["Job Zone"].astype(float))

    occ = pd.read_excel(RAW / "onet_Occupation_Data.xlsx")
    occ["soc"] = occ["O*NET-SOC Code"].astype(str).str.replace(r"\.\d+$", "", regex=True)
    jqi = occ[["soc", "Title"]].drop_duplicates("soc")
    jqi = jqi.merge(oews_soc, on="soc", how="left")
    jqi = jqi.merge(wc[["soc", "physical_sustainability", "autonomy", "cognitive_share", "physical_share", "task_ratio"]], on="soc", how="left")
    jqi = jqi.merge(jz[["soc", "career_investment"]], on="soc", how="left")

    title_soc = _build_title_to_soc()
    proj = load_bls_projections()
    if not proj.empty and "occupation_norm" in proj.columns:
        proj_map = proj.set_index("occupation_norm")["pct_emp_change"].to_dict()
        soc_to_bls_title = title_soc.set_index("soc")["title_norm"].to_dict()
        jqi["bls_title_norm"] = jqi["soc"].map(soc_to_bls_title)
        jqi["onet_title_norm"] = jqi["Title"].astype(str).apply(_norm_title)
        pct_vals = []
        for _, row in jqi.iterrows():
            match = proj_map.get(row["bls_title_norm"]) or proj_map.get(row["onet_title_norm"])
            if pd.isna(match):
                bls_n = str(row["bls_title_norm"]) if pd.notna(row["bls_title_norm"]) else ""
                for pn, pv in proj_map.items():
                    if bls_n and (bls_n in str(pn) or str(pn) in bls_n):
                        match = pv
                        break
            pct_vals.append(match)
        jqi["pct_emp_change"] = pct_vals
        jqi["pct_emp_change"] = pd.to_numeric(jqi["pct_emp_change"], errors="coerce")
        jqi["employment_outlook"] = normalize(jqi["pct_emp_change"].fillna(0))
        jqi = jqi.drop(columns=["bls_title_norm", "onet_title_norm"], errors="ignore")
    else:
        jqi["employment_outlook"] = 0.5
        jqi["pct_emp_change"] = np.nan

    age_df = load_bls_age_ratio()
    if age_df is not None and not age_df.empty:
        age_map = age_df.set_index("occupation_norm")["age_ratio"].to_dict()
        title_soc_bls = title_soc.set_index("soc")["title_norm"].to_dict()
        jqi["age_ratio"] = jqi["soc"].map(lambda s: age_map.get(title_soc_bls.get(s, "")))
        jqi["age_ratio"] = jqi["age_ratio"].fillna(jqi["Title"].astype(str).apply(_norm_title).map(age_map))
        jqi["age_sustainability"] = normalize(jqi["age_ratio"].fillna(jqi["age_ratio"].median()))
    else:
        jqi["age_ratio"] = np.nan
        jqi["age_sustainability"] = 0.5

    jqi["compensation"] = normalize(jqi["wage_median"].fillna(jqi["wage_median"].median()))
    for col in ["physical_sustainability", "autonomy", "career_investment"]:
        jqi[col] = jqi[col].fillna(0.5)

    jqi["JQI"] = (
        0.20 * jqi["compensation"]
        + 0.25 * jqi["physical_sustainability"]
        + 0.25 * jqi["autonomy"]
        + 0.20 * jqi["career_investment"]
        + 0.05 * jqi["employment_outlook"]
        + 0.05 * jqi["age_sustainability"]
    )
    wage_med = jqi["wage_median"].median()
    jz_vals = jqi.merge(jz[["soc", "Job Zone"]], on="soc", how="left")["Job Zone"].astype(float)
    jqi["trapped"] = (jqi["wage_median"].fillna(wage_med) < wage_med) & (jz_vals.fillna(3) <= 2)
    return jqi


def build_jqadi(jqi: pd.DataFrame, ai_exposure: pd.DataFrame) -> pd.DataFrame:
    """Compute JQADI. Rebalanced: w2>w1 so Low AI + Low Quality jobs rank higher."""
    ai_col = "observed_coverage" if "observed_coverage" in ai_exposure.columns else "dv_rating_beta"
    df = jqi.merge(ai_exposure, on="soc", how="inner")
    if ai_col == "observed_coverage":
        df["ai_exposure"] = df["observed_coverage"].fillna(0)
    else:
        df["ai_exposure"] = df["dv_rating_beta"].fillna(df["human_rating_beta"]).fillna(0)
    df["low_quality"] = 1 - df["JQI"]

    w1, w2, w3 = 0.25, 0.6, 0.15
    df["JQADI"] = w1 * df["ai_exposure"] + w2 * df["low_quality"] + w3 * df["ai_exposure"] * df["low_quality"]
    df["trapped_index"] = np.where(df["ai_exposure"] < 0.3, df["low_quality"], np.nan)
    df["task_residual_risk"] = np.where(
        (df["ai_exposure"] > 0.2) & (df["ai_exposure"] < 0.7),
        df["ai_exposure"] * df.get("cognitive_share", 0.5) * df.get("physical_share", 0.5),
        np.nan,
    )
    return df


def main():
    print("Building JQI...")
    jqi = build_jqi()
    jqi.to_csv(OUT / "jqi.csv", index=False)
    print(f"  JQI: {len(jqi)} occupations")

    ai_soc = load_anthropic_exposure()
    if ai_soc is None:
        print("Loading AI exposure (Eloundou fallback)...")
        ai = load_eloundou()
        ai_soc = ai.groupby("soc").agg(
            dv_rating_beta=("dv_rating_beta", "mean"),
            human_rating_beta=("human_rating_beta", "mean"),
        ).reset_index()
    else:
        print("Loading AI exposure (Anthropic observed coverage)...")

    print("Computing JQADI...")
    jqadi = build_jqadi(jqi, ai_soc)
    oews = load_oews()
    oews_emp = oews.groupby("soc").agg(employment=("TOT_EMP", "first")).reset_index()
    jqadi = jqadi.merge(oews_emp, on="soc", how="left", suffixes=("", "_dup"))
    jqadi = jqadi[[c for c in jqadi.columns if not c.endswith("_dup")]]
    if "employment" not in jqadi.columns or jqadi["employment"].isna().all():
        bls = load_onet_bls_matched()
        bls["soc"] = bls["OCC_CODE"].astype(str).str.replace(r"-\d+$", "", regex=True)
        emp_map = bls.groupby("soc")["TOT_EMP"].first().to_dict()
        jqadi["employment"] = jqadi["employment"].fillna(jqadi["soc"].map(emp_map))
    jqadi["employment"] = pd.to_numeric(jqadi["employment"], errors="coerce").fillna(0)
    jqadi["population_risk"] = jqadi["JQADI"] * jqadi["employment"]
    jqadi = jqadi.drop_duplicates("soc", keep="first")
    jqadi.to_csv(OUT / "jqadi.csv", index=False)

    trapped = jqadi[jqadi["trapped_index"].notna()].nlargest(30, "trapped_index")
    trapped[["Title", "ai_exposure", "JQI", "trapped_index", "employment"]].to_csv(OUT / "trapped_workers.csv", index=False)
    print(f"  Trapped workers (low-AI, low-quality): {OUT / 'trapped_workers.csv'}")

    jqi_med = jqadi["JQI"].median()
    wage_med = jqadi["wage_median"].median()
    good_safe = jqadi[(jqadi["ai_exposure"] < 0.3) & (jqadi["JQI"] > jqi_med)].sort_values("JQI", ascending=False)
    cols = ["Title", "JQI", "ai_exposure", "wage_median", "age_ratio", "physical_sustainability", "autonomy", "employment"]
    good_safe[[c for c in cols if c in good_safe.columns]].to_csv(OUT / "good_safe_jobs.csv", index=False)
    print(f"  Good safe jobs (low AI, high quality): {OUT / 'good_safe_jobs.csv'} ({len(good_safe)} occupations)")

    task_res = jqadi[jqadi["task_residual_risk"].notna()].nlargest(50, "task_residual_risk")
    tr_cols = ["Title", "ai_exposure", "cognitive_share", "physical_share", "task_residual_risk", "JQI", "employment"]
    task_res[[c for c in tr_cols if c in task_res.columns]].to_csv(OUT / "task_residual_risk.csv", index=False)
    print(f"  Task residual risk (AI strips cognitive, leaves physical): {OUT / 'task_residual_risk.csv'}")

    age_thresh = jqadi["age_ratio"].quantile(0.5) if jqadi["age_ratio"].notna().any() else 0
    career_viable = good_safe[
        (good_safe["age_ratio"].fillna(0) >= age_thresh) & (good_safe["wage_median"].fillna(0) >= wage_med)
    ]
    career_viable[[c for c in cols if c in career_viable.columns]].to_csv(OUT / "career_viable_safe.csv", index=False)
    print(f"  Career-viable safe jobs: {OUT / 'career_viable_safe.csv'} ({len(career_viable)} occupations)")

    print(f"\nOutput: {OUT}")
    print(f"  Total population risk (employment-weighted): {jqadi['population_risk'].sum():,.0f}")


if __name__ == "__main__":
    main()
