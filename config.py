"""EDA 공통 설정. 팀에서 정한 규칙을 바꾸면 이 파일만 고치면 된다.

경로는 환경변수로 바꿀 수 있다.
  BTS_RAW_DIR   : 월별 BTS zip 파일이 있는 폴더 (기본: ./raw_data/bts_ontime)
  BTS_DATA_DIR  : 01번이 만드는 월별 정리 파일 폴더 (기본: ./data)
  BTS_OUT_DIR   : 결과 표(CSV) 저장 폴더 (기본: ./outputs)
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_DIR = Path(os.environ.get("BTS_RAW_DIR", ROOT / "raw_data" / "bts_ontime"))
DATA_DIR = Path(os.environ.get("BTS_DATA_DIR", ROOT / "data"))
OUT_DIR = Path(os.environ.get("BTS_OUT_DIR", ROOT / "outputs"))

# ---------------------------------------------------------------- 분석 기간
# 36개월(2023-09 ~ 2026-08). 12개월씩 3개 블록으로 나눠 안정성을 확인한다.
BLOCK_MONTHS = 12

# ---------------------------------------------------------------- 정제 규칙
EXCLUDE_CANCELLED = True    # 결항 제외 (지연값이 없음)
EXCLUDE_DIVERTED = True     # 회항 제외 (도착 지연이 정의되지 않음)
MAX_ABS_DELAY = 1440        # 출발·도착 지연의 절댓값이 24시간(1440분) 이상이면 제외

# ---------------------------------------------------------------- 지연 기준·구간
DELAY_MIN = 15              # BTS 지연 기준(분 이상). 보조 라벨: 15/30/60
LONG_DELAY_MIN = 60         # 장시간 지연 기준
THRESHOLDS = [1, 5, 15, 30, 60]

# 심각도 구간 (경계는 팀 확정 전 제안값): 0분 이하 / 1~14 / 15~29 / 30~59 / 60~119 / 120 이상
SEV_EDGES = [-1e9, 0, 14, 29, 59, 119, 1e9]
SEV_LABELS = ["0분 이하", "1~14분", "15~29분", "30~59분", "60~119분", "120분 이상"]
# 세부 확인용 구간 (120분 이상을 둘로 나눔)
SEV_EDGES_DETAIL = [-1e9, 0, 14, 29, 59, 119, 239, 1e9]
SEV_LABELS_DETAIL = ["0분 이하", "1~14분", "15~29분", "30~59분", "60~119분", "120~239분", "240분 이상"]

# 비행거리 구간(마일)
DIST_EDGES = [-1, 499, 999, 1499, 2499, 1e9]
DIST_LABELS = ["500 미만", "500~999", "1000~1499", "1500~2499", "2500 이상"]

# ---------------------------------------------------------------- 공항·항공사·시간대
AIRPORT_MIN_FLIGHTS = 10_000     # 공항 비교에 쓰는 최소 출발 건수 (36개월 합)
HOUR_AIRPORT_TOPN = 30           # 공항×시간대 비교에 쓰는 상위 공항 수
HOUR_AIRPORT_MIN_CELL = 1_000    # 공항·시간대 셀 최소 건수
ORDER_CAP = 10                   # 당일 운항 순번을 이 값 이상이면 묶음

# ---------------------------------------------------------------- 알려진 원본 오류 보정
# 2026-04 BTS zip에는 NK 항공편 2건의 도착 예정시각(CRS_ARR_TIME)이 잘못 들어 있어
# 도착 지연이 1,258분·1,315분으로 계산된다. 이전에 받은 CSV 값으로 고친다.
PATCHES = [
    dict(FL_DATE="2026-04-03", OP_UNIQUE_CARRIER="NK", OP_CARRIER_FL_NUM=1603, ORIGIN="DTW", DEST="ORD",
         set=dict(CRS_ARR_TIME=307, ARR_DELAY=38.0, CARRIER_DELAY=38.0)),
    dict(FL_DATE="2026-04-16", OP_UNIQUE_CARRIER="NK", OP_CARRIER_FL_NUM=1, ORIGIN="DTW", DEST="ORD",
         set=dict(CRS_ARR_TIME=228, ARR_DELAY=23.0, CARRIER_DELAY=23.0)),
]

# 열 이름 변환 (BTS zip의 열 이름 -> 이 프로젝트에서 쓰는 이름)
RENAME = {
    "Year": "YEAR", "Month": "MONTH", "DayOfWeek": "DAY_OF_WEEK", "FlightDate": "FL_DATE",
    "Reporting_Airline": "OP_UNIQUE_CARRIER", "Tail_Number": "TAIL_NUM",
    "Flight_Number_Reporting_Airline": "OP_CARRIER_FL_NUM",
    "OriginAirportID": "ORIGIN_AIRPORT_ID", "Origin": "ORIGIN",
    "DestAirportID": "DEST_AIRPORT_ID", "Dest": "DEST",
    "CRSDepTime": "CRS_DEP_TIME", "DepTime": "DEP_TIME", "DepDelay": "DEP_DELAY", "DepDel15": "DEP_DEL15",
    "TaxiOut": "TAXI_OUT", "WheelsOff": "WHEELS_OFF", "WheelsOn": "WHEELS_ON", "TaxiIn": "TAXI_IN",
    "CRSArrTime": "CRS_ARR_TIME", "ArrTime": "ARR_TIME", "ArrDelay": "ARR_DELAY", "ArrDel15": "ARR_DEL15",
    "Cancelled": "CANCELLED", "CancellationCode": "CANCELLATION_CODE", "Diverted": "DIVERTED",
    "CRSElapsedTime": "CRS_ELAPSED_TIME", "ActualElapsedTime": "ACTUAL_ELAPSED_TIME",
    "AirTime": "AIR_TIME", "Distance": "DISTANCE",
    "CarrierDelay": "CARRIER_DELAY", "WeatherDelay": "WEATHER_DELAY", "NASDelay": "NAS_DELAY",
    "SecurityDelay": "SECURITY_DELAY", "LateAircraftDelay": "LATE_AIRCRAFT_DELAY",
}
CAUSE_COLS = ["CARRIER_DELAY", "WEATHER_DELAY", "NAS_DELAY", "SECURITY_DELAY", "LATE_AIRCRAFT_DELAY"]
