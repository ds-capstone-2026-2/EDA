"""04. 공항·항공사별 지연 (Notion 페이지 2의 1·2절).

출력(outputs/tables):
  04_airport_origin.csv   출발공항별 건수·출발/도착 지연율·평균 (최소 AIRPORT_MIN_FLIGHTS 건)
  04_airport_dest.csv     도착공항별 도착 지연율
  04_airline.csv          항공사별 건수·지연율·평균·집중도(최대 공항 비중)·공항구성 보정 기대율
  04_airline_by_block.csv 항공사별 블록별 도착 15분+ 비율
"""
import pandas as pd
import config
import common


def agg(s, key):
    t = pd.DataFrame({
        "k": s[key].values,
        "d15": (s.DEP_DELAY >= 15).values, "a15": (s.ARR_DELAY >= 15).values,
        "a60": (s.ARR_DELAY >= 60).values, "dep": s.DEP_DELAY.values, "arr": s.ARR_DELAY.values})
    return t.groupby("k").agg(n=("a15", "size"), d15=("d15", "sum"), a15=("a15", "sum"),
                              a60=("a60", "sum"), dep=("dep", "sum"), arr=("arr", "sum"))


def add(a, b):
    return b if a is None else a.add(b, fill_value=0)


def main():
    org = dst = car = car_org = None
    car_blk = {}
    for ym, blk, d in common.iter_months():
        s = common.clean(d)
        org, dst, car = add(org, agg(s, "ORIGIN")), add(dst, agg(s, "DEST")), add(car, agg(s, "OP_UNIQUE_CARRIER"))
        t = s.groupby(["OP_UNIQUE_CARRIER", "ORIGIN"]).size().rename("n").to_frame()
        car_org = add(car_org, t)
        b = agg(s, "OP_UNIQUE_CARRIER")[["n", "a15"]]
        car_blk[blk] = add(car_blk.get(blk), b)
        print(ym, end=" ", flush=True)
    print()

    def rates(t):
        o = pd.DataFrame({"건수": t.n.astype(int)})
        o["출발 15분+(%)"] = t.d15 / t.n * 100
        o["도착 15분+(%)"] = t.a15 / t.n * 100
        o["도착 60분+(%)"] = t.a60 / t.n * 100
        o["출발지연 평균(분)"] = t.dep / t.n
        o["도착지연 평균(분)"] = t.arr / t.n
        return o.round(2)

    big_o = org[org.n >= config.AIRPORT_MIN_FLIGHTS]
    big_d = dst[dst.n >= config.AIRPORT_MIN_FLIGHTS]
    common.save(rates(big_o).sort_values("출발 15분+(%)", ascending=False), "04_airport_origin.csv")
    common.save(rates(big_d).sort_values("도착 15분+(%)", ascending=False), "04_airport_dest.csv")
    print(f"분석 공항 {len(big_o)}개, 출발 건수 비중 {big_o.n.sum()/org.n.sum()*100:.1f}%")

    # 항공사: 집중도 + 공항구성 보정 기대율
    ap_rate = org.a15 / org.n  # 공항 평균 도착 15분+ 비율(출발공항 기준)
    r = rates(car)
    co = car_org.reset_index()
    co["rate"] = co.ORIGIN.map(ap_rate)
    g = co.groupby("OP_UNIQUE_CARRIER")
    r["최대 공항 비중(%)"] = (g.n.max() / g.n.sum() * 100).round(1)
    r["공항구성 보정 기대율(%)"] = ((co.n * co.rate).groupby(co.OP_UNIQUE_CARRIER).sum() / g.n.sum() * 100).round(2)
    r["실제-기대(%p)"] = (r["도착 15분+(%)"] - r["공항구성 보정 기대율(%)"]).round(2)
    common.save(r.sort_values("도착 15분+(%)", ascending=False), "04_airline.csv")

    bl = pd.DataFrame({f"블록{b+1}": v.a15 / v.n * 100 for b, v in sorted(car_blk.items())}).round(2)
    common.save(bl, "04_airline_by_block.csv")
    print(r.sort_values("도착 15분+(%)", ascending=False).to_string())


if __name__ == "__main__":
    main()
