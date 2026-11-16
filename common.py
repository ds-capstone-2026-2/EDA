"""월별 데이터 읽기·정제 공통 함수."""
import re
import numpy as np
import pandas as pd
import config

STR_COLS = ["OP_UNIQUE_CARRIER", "TAIL_NUM", "ORIGIN", "DEST", "CANCELLATION_CODE"]


def _has_pyarrow():
    try:
        import pyarrow  # noqa: F401
        return True
    except ImportError:
        return False


def month_path(y, m):
    ext = "parquet" if _has_pyarrow() else "csv.gz"
    return config.DATA_DIR / "months" / f"{y}_{m:02d}.{ext}"


def write_month(df, y, m):
    p = month_path(y, m)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix == ".parquet":
        df.to_parquet(p, index=False)
    else:
        df.to_csv(p, index=False, compression={"method": "gzip", "compresslevel": 1})
    return p


def read_month(path):
    path = str(path)
    if path.endswith(".parquet"):
        d = pd.read_parquet(path)
    else:
        d = pd.read_csv(path, parse_dates=["FL_DATE"], low_memory=False,
                        dtype={c: str for c in STR_COLS})
    for c in STR_COLS:
        d[c] = d[c].astype(object).where(d[c].notna(), None)
    return d


def iter_months():
    """(ym, 블록 번호, 월 데이터) 를 시간순으로 돌려준다. ym 예: '2023_09'."""
    files = sorted(list((config.DATA_DIR / "months").glob("*.parquet")) +
                   list((config.DATA_DIR / "months").glob("*.csv.gz")))
    if not files:
        raise SystemExit("월별 정리 파일이 없습니다. 먼저 01_build_months.py 를 실행하세요.")
    for i, p in enumerate(files):
        ym = re.match(r"(\d{4}_\d{2})", p.name).group(1)
        yield ym, i // config.BLOCK_MONTHS, read_month(p)


def clean(d, with_counts=False):
    """정제 규칙 적용: 결항·회항 제외, 지연값 결측 제외, 지연 24시간 이상 제외."""
    n0 = len(d)
    m = pd.Series(True, index=d.index)
    if config.EXCLUDE_CANCELLED:
        m &= d.CANCELLED == 0
    canc = int(d.CANCELLED.sum())
    if config.EXCLUDE_DIVERTED:
        m &= d.DIVERTED == 0
    s1 = d[m]
    div = int(((d.CANCELLED == 0) & (d.DIVERTED == 1)).sum())
    s2 = s1.dropna(subset=["DEP_DELAY", "ARR_DELAY"])
    na = len(s1) - len(s2)
    big_mask = (s2.DEP_DELAY.abs() >= config.MAX_ABS_DELAY) | (s2.ARR_DELAY.abs() >= config.MAX_ABS_DELAY)
    s3 = s2[~big_mask].copy()
    if with_counts:
        return s3, dict(total=n0, canc=canc, div=div, na=na, big=int(big_mask.sum()), n=len(s3), flown=len(s1))
    return s3


def cut_sev(series, detail=False):
    e, l = ((config.SEV_EDGES_DETAIL, config.SEV_LABELS_DETAIL) if detail
            else (config.SEV_EDGES, config.SEV_LABELS))
    return pd.cut(series, e, labels=l)


def save(df, name, index=True):
    p = config.OUT_DIR / "tables"
    p.mkdir(parents=True, exist_ok=True)
    df.to_csv(p / name, index=index, encoding="utf-8-sig")
    return p / name


def weighted_quantile(counts, q):
    """{값: 건수} Series 에서 q 분위수."""
    d = counts.sort_index()
    c = d.cumsum() / d.sum()
    return d.index.values[np.searchsorted(c.values, q)]
