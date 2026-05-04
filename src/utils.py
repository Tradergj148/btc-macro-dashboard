"""Shared utilities: paths, IO, z-score, normalization."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    with open(CONFIG_DIR / "indicators.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_parquet(df: pd.DataFrame, name: str) -> Path:
    path = DATA_DIR / f"{name}.parquet"
    df.to_parquet(path, index=True)
    return path


def load_parquet(name: str) -> pd.DataFrame:
    path = DATA_DIR / f"{name}.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def zscore(series: pd.Series, window: int = 252) -> pd.Series:
    s = series.astype(float)
    mu = s.rolling(window, min_periods=30).mean()
    sd = s.rolling(window, min_periods=30).std(ddof=0)
    z = (s - mu) / sd.replace(0, np.nan)
    return z


def squash(z):
    if isinstance(z, pd.Series):
        arr = np.tanh(z.to_numpy() / 2.0)
        return pd.Series(arr, index=z.index, name=z.name)
    if isinstance(z, pd.DataFrame):
        arr = np.tanh(z.to_numpy() / 2.0)
        return pd.DataFrame(arr, index=z.index, columns=z.columns)
    return float(np.tanh(float(z) / 2.0))


def pct_change_n(series: pd.Series, n: int) -> pd.Series:
    return series.pct_change(n)


def diff_n(series: pd.Series, n: int) -> pd.Series:
    return series.diff(n)
