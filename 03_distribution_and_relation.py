"""03. 지연시간 분포·출발-도착 관계·원인 (Notion 페이지 1의 2~5단계).

출력(outputs/tables):
  03_severity_share.csv       심각도 구간별 비행 비중 vs 지연분 비중 (도착)
  03_dist_stats.csv           출발·도착 지연 평균·중앙값·왜도·분위수, 상위 10% 비행의 지연분 비중
  03_dep_to_arr.csv           출발지연 구간별 도착 15분+ 비율
  03_recovery.csv             출발지연 구간별 회복(DEP-ARR) 평균·중앙값
  03_by_distance.csv          비행거리 구간별 지연율
  03_cause_share.csv          원인별 지연분 비중 (도착지연 15분+ 비행)
"""
import numpy as np
import pandas as pd
import config
import common


def vc_stats(vc):
    """{값: 건수} 로 평균·중앙값·왜도·분위수 계산 (메모리 절약)."""
    vc = vc.sort_index()
    x, w = vc.index.values.astype(float), vc.values.astype(float)
    n = w.sum()
    mean = (x * w).sum() / n
    sd = np.sqrt((w * (x - mean) ** 2).sum() / (n - 1))
    skew = (w * ((x - mean) / sd) ** 3).sum() / n
    q = {f"p{int(p*100)}": common.weighted_quantile(vc, p) for p in (0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99)}
    pos = np.clip(x, 0, None) * w
    cum = np.cumsum(w) / n
    top10_share = pos[cum > 0.9].sum() / pos.sum()
    return dict(n=int(n), mean=mean, sd=sd, skew=skew, **q, top10_delay_share=top10_share)


def main():
    sev = pd.DataFrame()
    dep_vc = pd.Series(dtype="float64"); arr_vc = pd.Series(dtype="float64")
    dep_bin = pd.DataFrame(); rec = {}; dist = pd.DataFrame(); cause = pd.Series(dtype="float64")
    for ym, blk, d in common.iter_months():
        s = common.clean(d)
        dep = s.DEP_DELAY.astype("int32"); arr = s.ARR_DELAY.astype("int32")
        dep_vc = dep_vc.add(dep.value_counts(), fill_value=0)
        arr_vc = arr_vc.add(arr.value_counts(), fill_value=0)

        # 2단계: 도착지연 심각도 구간별 비행 수 / 지연분 합 (양수 지연만 합산)
        b = common.cut_sev(arr, detail=True)
        g = pd.DataFrame({"b": b, "m": arr.clip(lower=0)}).groupby("b", observed=False).m.agg(["size", "sum"])
        sev = g if len(sev) == 0 else sev.add(g, fill_value=0)

        # 3~4단계: 출발지연 구간별 도착 15분+ , 회복
        db = common.cut_sev(dep)
        r = (dep - arr)
        t = pd.DataFrame({"db": db, "late": (arr >= config.DELAY_MIN).astype(int), "rec": r})
        tg = t.groupby("db", observed=False).agg(n=("late", "size"), late=("late", "sum"), rec_sum=("rec", "sum"))
        dep_bin = tg if dep_bin.empty else dep_bin.add(tg, fill_value=0)
        for lab, grp in t.groupby("db", observed=False):
            vc = grp.rec.value_counts()
            rec[lab] = vc if lab not in rec else rec[lab].add(vc, fill_value=0)

        # 거리 구간
        dd = pd.cut(s.DISTANCE, config.DIST_EDGES, labels=config.DIST_LABELS)
        tt = pd.DataFrame({"dd": dd, "d15": (s.DEP_DELAY >= 15).astype(int), "a15": (arr >= 15).astype(int),
                           "a60": (arr >= 60).astype(int)})
        tg2 = tt.groupby("dd", observed=False).agg(n=("a15", "size"), d15=("d15", "sum"), a15=("a15", "sum"), a60=("a60", "sum"))
        dist = tg2 if len(dist) == 0 else dist.add(tg2, fill_value=0)

        # 5단계: 원인별 지연분 (도착지연 15분+)
        c = s.loc[arr >= 15, config.CAUSE_COLS].sum()
        cause = cause.add(c, fill_value=0)
        print(ym, end=" ", flush=True)
    print()

    # 심각도 구간 (6구간·세부 7구간 모두 저장)
    sev["비행 비중(%)"] = sev["size"] / sev["size"].sum() * 100
    sev["지연분 비중(%)"] = sev["sum"] / sev["sum"].sum() * 100
    sev = sev.rename(columns={"size": "비행 수", "sum": "지연분 합"}).round(2)
    common.save(sev, "03_severity_share.csv")

    st = pd.DataFrame({"출발지연": vc_stats(dep_vc), "도착지연": vc_stats(arr_vc)}).round(3)
    common.save(st, "03_dist_stats.csv")

    dep_bin["도착 15분+ 비율(%)"] = dep_bin.late / dep_bin.n * 100
    dep_bin["회복 평균(분)"] = dep_bin.rec_sum / dep_bin.n
    dep_bin["회복 중앙값(분)"] = pd.Series({k: common.weighted_quantile(v, 0.5) for k, v in rec.items()})
    common.save(dep_bin.round(2), "03_dep_to_arr.csv")
    common.save(dep_bin[["n", "회복 평균(분)", "회복 중앙값(분)"]].round(2), "03_recovery.csv")

    dist["출발 15분+(%)"] = dist.d15 / dist.n * 100
    dist["도착 15분+(%)"] = dist.a15 / dist.n * 100
    dist["도착 60분+(%)"] = dist.a60 / dist.n * 100
    common.save(dist.round(2), "03_by_distance.csv")

    cs = (cause / cause.sum() * 100).round(2).to_frame("지연분 비중(%)")
    cs["지연분 합(분)"] = cause
    common.save(cs, "03_cause_share.csv")
    print(st.to_string()); print(sev.to_string()); print(dep_bin.to_string()); print(cs.to_string())


if __name__ == "__main__":
    main()
