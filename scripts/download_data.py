#!/usr/bin/env python3
"""Download datasets for JQADI construction."""

import urllib.request
import urllib.parse
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "JQADI-Research/1.0 (labor market analysis)"}


def download(url: str, path: Path) -> bool:
    """Download file with retry."""
    if path.exists():
        print(f"  Skip (exists): {path.name}")
        return True
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=60) as r:
            path.write_bytes(r.read())
        print(f"  Downloaded: {path.name}")
        return True
    except Exception as e:
        print(f"  Failed {path.name}: {e}")
        return False


def main():
    print("Downloading JQADI datasets...\n")

    # 1. O*NET 30.2 (Work Context, Work Activities, Abilities, Job Zones, Occupation Data)
    onet_base = "https://www.onetcenter.org/dl_files/database/db_30_2_excel"
    onet_files = [
        "Work Context.xlsx",
        "Work Activities.xlsx",
        "Abilities.xlsx",
        "Job Zones.xlsx",
        "Occupation Data.xlsx",
    ]
    print("1. O*NET 30.2")
    for f in onet_files:
        url = f"{onet_base}/{urllib.parse.quote(f)}"
        download(url, RAW_DIR / f"onet_{f.replace(' ', '_')}")

    # 2. Anthropic Economic Index - job_exposure.csv (observed AI exposure by occupation)
    print("\n2. Anthropic Economic Index (job exposure)")
    (RAW_DIR / "labor_market_impacts").mkdir(parents=True, exist_ok=True)
    download(
        "https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/labor_market_impacts/job_exposure.csv",
        RAW_DIR / "labor_market_impacts" / "job_exposure.csv",
    )

    # 3. Eloundou et al. GPTs are GPTs (occ_level, OEWS, projections)
    print("\n3. Eloundou et al. (GPTs are GPTs)")
    gpt_files = [
        ("https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/data/occ_level.csv", "eloundou_occ_exposure.csv"),
        ("https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/data/national_May2021_dl.csv", "oes_national_2021.csv"),
        ("https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/data/occupations_onet_bls_matched.csv", "onet_bls_matched.csv"),
        ("https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/data/occupations_projections_processed.csv", "bls_projections.csv"),
    ]
    for url, fname in gpt_files:
        download(url, RAW_DIR / fname)

    # 4. CPS Table 11b (age × occupation)
    print("\n4. CPS Table 11b (age × occupation)")
    phase3_urls = [
        ("https://www.bls.gov/cps/aa2023/cpsaat11b.xlsx", "cpsaat11b.xlsx"),
        ("https://www.bls.gov/web/empsit/cpseea19.xlsx", "cps_ea19_age_occupation.xlsx"),
    ]
    for url, fname in phase3_urls:
        download(url, RAW_DIR / fname)
    if not (RAW_DIR / "cpsaat11b.xlsx").exists():
        print("  CPS Table 11b: if download failed (403), manually save from bls.gov/cps/cpsaat11b.htm to data/raw/cpsaat11b.xlsx")

    print("\nDone.")


if __name__ == "__main__":
    main()
