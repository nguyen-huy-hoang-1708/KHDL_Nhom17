"""
BƯỚC 1 - THU THẬP DỮ LIỆU
Lấy dữ liệu theo giờ tại Hà Nội từ Open-Meteo (miễn phí, không cần API key):
  * Chất lượng không khí (mô hình CAMS): PM2.5, PM10, CO, NO2, SO2, O3
  * Khí tượng lịch sử (ERA5): nhiệt độ, độ ẩm, mưa, gió, áp suất, độ cao lớp biên
Dữ liệu được lưu dạng CSV vào data/raw/.
"""
import argparse
import time
from pathlib import Path

import pandas as pd
import requests

LAT, LON = 21.0285, 105.8542          # Hoàn Kiếm, Hà Nội
TZ = "Asia/Bangkok"                   # UTC+7
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
AIR_VARS = ["pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide",
            "sulphur_dioxide", "ozone"]

WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"
WEATHER_VARS = ["temperature_2m", "relative_humidity_2m", "dew_point_2m",
                "precipitation", "surface_pressure", "cloud_cover",
                "wind_speed_10m", "wind_direction_10m", "boundary_layer_height"]


def fetch(url: str, variables: list[str], start: str, end: str) -> pd.DataFrame:
    """Gọi API theo từng năm để tránh request quá lớn, có retry đơn giản."""
    frames = []
    for chunk_start in pd.date_range(start, end, freq="YS").union([pd.Timestamp(start)]):
        chunk_end = min(pd.Timestamp(f"{chunk_start.year}-12-31"), pd.Timestamp(end))
        params = {"latitude": LAT, "longitude": LON, "timezone": TZ,
                  "hourly": ",".join(variables),
                  "start_date": chunk_start.strftime("%Y-%m-%d"),
                  "end_date": chunk_end.strftime("%Y-%m-%d")}
        for attempt in range(3):
            try:
                r = requests.get(url, params=params, timeout=60)
                r.raise_for_status()
                break
            except requests.RequestException as e:
                print(f"  lỗi ({e}), thử lại...")
                time.sleep(3 * (attempt + 1))
        else:
            raise RuntimeError(f"Không tải được {url} cho {params['start_date']}")
        df = pd.DataFrame(r.json()["hourly"])
        print(f"  {params['start_date']} -> {params['end_date']}: {len(df)} dòng")
        frames.append(df)
        time.sleep(1)
    out = pd.concat(frames).drop_duplicates("time")
    out["time"] = pd.to_datetime(out["time"])
    return out.sort_values("time").reset_index(drop=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2022-08-01")
    p.add_argument("--end", default="2026-10-31")
    a = p.parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("Tải dữ liệu chất lượng không khí...")
    fetch(AIR_URL, AIR_VARS, a.start, a.end).to_csv(RAW_DIR / "air_quality_hourly.csv", index=False)
    print("Tải dữ liệu khí tượng...")
    fetch(WEATHER_URL, WEATHER_VARS, a.start, a.end).to_csv(RAW_DIR / "weather_hourly.csv", index=False)
    print(f"Đã lưu vào {RAW_DIR}")


if __name__ == "__main__":
    main()
