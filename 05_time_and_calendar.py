"""05. 시간대·당일 운항 순번·요일·월·일별 패턴 (Notion 페이지 2의 3~5절).

출력(outputs/tables):
  05_hour.csv           예정 출발 시각(시)별 출발 15분+ 비율, 평균 지연
  05_hour_airport.csv   상위 공항 x 시간대 출발 15분+ 비율 (셀 최소 건수 이상)
  05_order.csv          같은 기체의 당일 운항 순번별 평균 출발지연·15분+ 비율 (하루 5편 이상 기체)
  05_dow.csv            요일별 도착 15분+ 비율 (전체·블록별)
  05_month.csv          연월별 도착 15분+ 비율
  05_daily.csv          일별 도착 15분+ 비율, 평균+2SD/3SD 이상 여부
"""
import numpy as np
import pandas as pd
import config
import common


def add(a, b):
    return b if a is None else a.add(b, fill_value=0)


def main():
    hour = hour_ap = order = dow = None
    month, daily = [], []
    top_airports = None
    # 상위 공항은 전체 건수가 필요하므로 한 번 훑어서 정한다
    cnt = None
    for ym, blk, d in common.iter_months():
        cnt = add(cnt, common.clean(d).groupby("ORIGIN").size().rename("n").to_frame())
    top_airports = list(cnt.n.sort_values(ascending=False).head(config.HOUR_AIRPORT_TOPN).index)

    for ym, blk, d in common.iter_months():
        s = common.clean(d)
        h = np.minimum(s.CRS_DEP_TIME // 100, 23)
        t = pd.DataFrame({"h": h.values, "d15": (s.DEP_DELAY >= 15).values, "dep": s.DEP_DELAY.values})
        hour = add(hour, t.groupby("h").agg(n=("d15", "size"), d15=("d15", "sum"), dep=("dep", "sum")))

        m = s.ORIGIN.isin(top_airports)
        t2 = pd.DataFrame({"o": s.ORIGIN[m].values, "h": h[m].values, "d15": (s.DEP_DELAY[m] >= 15).values})
        hour_ap = add(hour_ap, t2.groupby(["o", "h"]).agg(n=("d15", "size"), d15=("d15", "sum")))

        # 당일 운항 순번: 정제된 운항편에서 같은 기체·같은 날짜를 예정 출발시각 순으로 센다
        f = s[s.TAIL_NUM.notna()].sort_values(["TAIL_NUM", "FL_DATE", "CRS_DEP_TIME"], kind="mergesort")
        f = f.assign(ord=f.groupby(["TAIL_NUM", "FL_DATE"]).cumcount() + 1)
        f["cnt"] = f.groupby(["TAIL_NUM", "FL_DATE"]).ord.transform("max")
        f = f[f.cnt >= 5]
        f["ord"] = f.ord.clip(upper=config.ORDER_CAP)
        t3 = pd.DataFrame({"o": f.ord.values, "dep": f.DEP_DELAY.values, "d15": (f.DEP_DELAY >= 15).values})
        order = add(order, t3.groupby("o").agg(n=("d15", "size"), d15=("d15", "sum"), dep=("dep", "sum")))
        order_tail_days = f[["TAIL_NUM", "FL_DATE"]].drop_duplicates().shape[0]
        order.attrs["tail_days"] = order.attrs.get("tail_days", 0) + order_tail_days

        a15 = (s.ARR_DELAY >= 15)
        dw = pd.DataFrame({"w": s.DAY_OF_WEEK.values, "b": blk + 1, "a15": a15.values})
        dow = add(dow, dw.groupby(["b", "w"]).agg(n=("a15", "size"), a15=("a15", "sum")))
        month.append(dict(ym=ym, n=len(s), a15=int(a15.sum())))
        dd = pd.DataFrame({"date": s.FL_DATE.values, "a15": a15.values}).groupby("date").agg(n=("a15", "size"), a15=("a15", "sum"))
        daily.append(dd)
        print(ym, end=" ", flush=True)
    print()

    h = hour.copy()
    h["출발 15분+(%)"] = h.d15 / h.n * 100
    h["출발지연 평균(분)"] = h.dep / h.n
    common.save(h[["n", "출발 15분+(%)", "출발지연 평균(분)"]].round(2), "05_hour.csv")

    ha = hour_ap[hour_ap.n >= config.HOUR_AIRPORT_MIN_CELL]
    piv = (ha.d15 / ha.n * 100).unstack("h").round(1)
    common.save(piv, "05_hour_airport.csv")

    o = order.copy()
    o["출발 15분+(%)"] = o.d15 / o.n * 100
    o["출발지연 평균(분)"] = o.dep / o.n
    common.save(o[["n", "출발 15분+(%)", "출발지연 평균(분)"]].round(2), "05_order.csv")
    print("같은 기체 패널(기체-일):", order.attrs["tail_days"])

    dw = dow.copy(); dw["rate"] = dw.a15 / dw.n * 100
    wk = dw.rate.unstack("b").round(2)
    tot = dow.groupby("w")[["n", "a15"]].sum()
    wk.insert(0, "전체", (tot.a15 / tot.n * 100).round(2))
    wk.index.name = "요일(1=월)"
    common.save(wk, "05_dow.csv")

    mo = pd.DataFrame(month).set_index("ym")
    mo["도착 15분+(%)"] = (mo.a15 / mo.n * 100).round(2)
    common.save(mo, "05_month.csv")

    dy = pd.concat(daily).groupby(level=0).sum()
    dy["rate"] = dy.a15 / dy.n * 100
    mu, sd = dy.rate.mean(), dy.rate.std()
    dy["2SD 이상"] = dy.rate > mu + 2 * sd
    dy["3SD 이상"] = dy.rate > mu + 3 * sd
    common.save(dy.round(2), "05_daily.csv")
    print(f"일별 평균 {mu:.2f}% SD {sd:.2f} / 2SD 초과 {int(dy['2SD 이상'].sum())}일, 3SD 초과 {int(dy['3SD 이상'].sum())}일")
    print(dy.sort_values("rate", ascending=False).head(10).round(2).to_string())
    print(h.round(2).to_string()); print(o.round(2).to_string()); print(wk.to_string())


if __name__ == "__main__":
    main()
