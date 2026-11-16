"""01. BTS 월별 zip -> 같은 형식의 월별 정리 파일.

- 입력: RAW_DIR 의 On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{YYYY}_{M}.zip
- 출력: DATA_DIR/months/YYYY_MM.(parquet | csv.gz)
- 하는 일: 필요한 열만 선택, 열 이름 통일, 자료형 정리, 알려진 원본 오류 보정(config.PATCHES)
- 계획 페이지의 0번(데이터 정제) 준비 단계

실행:  python 01_build_months.py
"""
import re
import zipfile
import pandas as pd
import config
import common

KEEP = list(config.RENAME.values())
INT_COLS = ["YEAR", "MONTH", "DAY_OF_WEEK", "CRS_DEP_TIME", "CRS_ARR_TIME", "ORIGIN_AIRPORT_ID", "DEST_AIRPORT_ID"]
FLOAT_COLS = ["DEP_DELAY", "ARR_DELAY", "TAXI_OUT", "TAXI_IN", "CRS_ELAPSED_TIME", "ACTUAL_ELAPSED_TIME", "AIR_TIME",
              "DISTANCE", "CARRIER_DELAY", "WEATHER_DELAY", "NAS_DELAY", "SECURITY_DELAY", "LATE_AIRCRAFT_DELAY",
              "DEP_TIME", "ARR_TIME", "WHEELS_OFF", "WHEELS_ON", "DEP_DEL15", "ARR_DEL15"]


def read_zip(path):
    with zipfile.ZipFile(path) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(name) as fh:
            raw = pd.read_csv(fh, usecols=list(config.RENAME.keys()), low_memory=False)
    df = raw.rename(columns=config.RENAME)[KEEP].copy()
    df["FL_DATE"] = pd.to_datetime(df["FL_DATE"], format="mixed").dt.normalize()
    for c in ["CANCELLED", "DIVERTED"]:
        df[c] = df[c].astype("int8")
    for c in INT_COLS:
        df[c] = df[c].astype("int32")
    df["OP_CARRIER_FL_NUM"] = df["OP_CARRIER_FL_NUM"].astype("Int32")  # 2024-08에 빈 값 1건
    for c in FLOAT_COLS:
        df[c] = df[c].astype("float32")
    return df


def apply_patches(df):
    n = 0
    for p in config.PATCHES:
        m = ((df.FL_DATE == pd.Timestamp(p["FL_DATE"])) & (df.OP_UNIQUE_CARRIER == p["OP_UNIQUE_CARRIER"]) &
             (df.OP_CARRIER_FL_NUM == p["OP_CARRIER_FL_NUM"]) & (df.ORIGIN == p["ORIGIN"]) & (df.DEST == p["DEST"]))
        for k, v in p["set"].items():
            df.loc[m, k] = v
        n += int(m.sum())
    return n


def main():
    zips = []
    for p in sorted(config.RAW_DIR.glob("*.zip")):
        m = re.search(r"_(\d{4})_(\d{1,2})\.zip$", p.name)
        if m:
            zips.append((int(m.group(1)), int(m.group(2)), p))
    zips.sort()
    if not zips:
        raise SystemExit(f"zip 파일이 없습니다: {config.RAW_DIR}")
    print("월 개수:", len(zips))
    for y, m, p in zips:
        df = read_zip(p)
        if not (df.YEAR.eq(y) & df.MONTH.eq(m)).all():
            raise SystemExit(f"{p.name}: 파일 이름과 데이터의 연·월이 다릅니다")
        npatch = apply_patches(df)
        out = common.write_month(df, y, m)
        print(f"{y}-{m:02d} rows={len(df):,} 보정={npatch}건 -> {out.name}", flush=True)


if __name__ == "__main__":
    main()
