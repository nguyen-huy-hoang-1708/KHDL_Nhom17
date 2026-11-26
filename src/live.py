"""
Lấy dữ liệu GẦN NHẤT (14 ngày qua + hôm nay) từ Open-Meteo để dự báo PM2.5 ngày mai
bằng mô hình đã huấn luyện. Hôm nay gồm số liệu đã xảy ra + dự báo cho các giờ còn lại.
"""
import numpy as np
import pandas as pd
import requests

from collect_data import AIR_URL, AIR_VARS, LAT, LON, TZ, WEATHER_VARS
from preprocess import add_features, rename_columns, to_daily

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _get(url, variables, past_days=14):
    r = requests.get(url, params={"latitude": LAT, "longitude": LON, "timezone": TZ,
                                  "hourly": ",".join(variables), "past_days": past_days,
                                  "forecast_days": 1}, timeout=30)
    r.raise_for_status()
    df = pd.DataFrame(r.json()["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def fetch_recent_daily() -> pd.DataFrame:
    air = _get(AIR_URL, AIR_VARS)
    wea = _get(FORECAST_URL, WEATHER_VARS)
    df = rename_columns(air.merge(wea, on="time").set_index("time").sort_index())
    df = df.interpolate(method="time", limit_direction="both")
    return add_features(to_daily(df), dropna=False)


def predict_tomorrow(daily: pd.DataFrame, reg: dict, clf: dict) -> dict:
    row = daily.dropna(subset=reg["features"]).iloc[[-1]]
    pm = float(reg["model"].predict(row[reg["features"]])[0])
    prob = float(clf["model"].predict_proba(row[clf["features"]])[:, 1][0])
    return {"base_date": row.index[0].date(), "target_date": (row.index[0] + pd.Timedelta(days=1)).date(),
            "pm25_pred": max(pm, 0.0), "prob_polluted": prob, "today": row.iloc[0].to_dict()}


def vn_aqi_level(pm25: float):
    """Phân mức theo ngưỡng PM2.5 trung bình 24h dùng trong VN_AQI (QĐ 1459/QĐ-TCMT)."""
    levels = [(25, "Tốt", "#00e400", "Không ảnh hưởng tới sức khoẻ."),
              (50, "Trung bình", "#ffd000", "Nhóm nhạy cảm nên hạn chế ở ngoài lâu."),
              (80, "Kém", "#ff7e00", "Nhóm nhạy cảm cần hạn chế ra ngoài; người bình thường có thể bị ảnh hưởng."),
              (150, "Xấu", "#ff0000", "Mọi người nên hạn chế hoạt động ngoài trời, đeo khẩu trang lọc bụi mịn."),
              (250, "Rất xấu", "#8f3f97", "Nên ở trong nhà, đóng cửa, dùng máy lọc không khí."),
              (np.inf, "Nguy hại", "#7e0023", "Cảnh báo khẩn cấp: tránh mọi hoạt động ngoài trời.")]
    for upper, name, color, advice in levels:
        if pm25 <= upper:
            return name, color, advice
