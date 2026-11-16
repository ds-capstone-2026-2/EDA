"""02. 데이터 정제 결과와 지연 기준별 비율 (Notion 페이지 1의 0·1단계).

출력(outputs/tables):
  02_cleaning_counts.csv   월별 정제 단계별 건수
  02_threshold_rates.csv   지연 기준(1/5/15/30/60분 이상)별 출발·도착 지연율 (전체·블록별)
  02_headline.csv          핵심 숫자 (N, 도착 15분+ 비율, 도착지연 중앙값)
"""
import numpy as np
import pandas as pd
import config
import common


def main():
    cnt, thr = [], []
    arr_counts = pd.Series(dtype="float64")
    for ym, blk, d in common.iter_months():
        s, c = common.clean(d, with_counts=True)
        c["ym"], c["block"] = ym, blk + 1
        cnt.append(c)
        row = dict(block=blk + 1, n=len(s))
        for t in config.THRESHOLDS:
            row[f"dep{t}"] = int((s.DEP_DELAY >= t).sum())
            row[f"arr{t}"] = int((s.ARR_DELAY >= t).sum())
        thr.append(row)
        arr_counts = arr_counts.add(s.ARR_DELAY.astype("int32").value_counts(), fill_value=0)
        # 검증: BTS 도착지연 15분 플래그는 ARR_DELAY>=15 와 같아야 한다
        flag = s.ARR_DEL15.astype(float)
        assert (flag == (s.ARR_DELAY >= 15).astype(float)).all(), f"{ym}: ARR_DEL15 불일치"
    cnt = pd.DataFrame(cnt)
    common.save(cnt.set_index("ym"), "02_cleaning_counts.csv")

    t = pd.DataFrame(thr)
    tot = t.drop(columns="block").sum()
    rates = pd.DataFrame({"전체": tot})
    for b, g in t.groupby("block"):
        rates[f"블록{b}"] = g.drop(columns="block").sum()
    n = rates.loc["n"]
    out = (rates.drop(index="n") / n * 100).round(2)
    out.loc["N(건)"] = n
    common.save(out, "02_threshold_rates.csv")

    med = common.weighted_quantile(arr_counts, 0.5)
    head = pd.Series({
        "원자료 행수": int(cnt.total.sum()),
        "결항": int(cnt.canc.sum()),
        "회항": int(cnt["div"].sum()),
        "지연값 결측": int(cnt.na.sum()),
        "24시간 이상 제외": int(cnt.big.sum()),
        "분석 N": int(cnt.n.sum()),
        "도착 15분+ 비율(%)": round(tot["arr15"] / tot["n"] * 100, 2),
        "도착 지연 중앙값(분)": med,
    })
    common.save(head.to_frame("값"), "02_headline.csv")
    print(head.to_string())
    print(out.to_string())


if __name__ == "__main__":
    main()
