"""
BƯỚC 2 - TIỀN XỬ LÝ & XÂY DỰNG ĐẶC TRƯNG
  1. Ghép 2 bảng theo thời gian
  2. Xử lý giá trị thiếu (nội suy theo thời gian) và giá trị ngoại lai (IQR clipping)
  3. Tổng hợp dữ liệu giờ -> ngày
  4. Tạo đặc trưng: mùa vụ, biến trễ (lag), trung bình trượt, vector gió
  5. Tạo biến mục tiêu: PM2.5 trung bình NGÀY HÔM SAU (hồi quy) và
     nhãn "ngày ô nhiễm" PM2.5 > 50 µg/m³ theo QCVN 05:2023/BTNMT (phân loại)
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
PM25_LIMIT = 50  # µg/m³, giới hạn trung bình 24h theo QCVN 05:2023/BTNMT


def load_and_merge() -> pd.DataFrame:
    air = pd.read_csv(RAW / "air_quality_hourly.csv", parse_dates=["time"])
    wea = pd.read_csv(RAW / "weather_hourly.csv", parse_dates=["time"])
    df = air.merge(wea, on="time", how="inner").set_index("time").sort_index()
    return rename_columns(df)


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"carbon_monoxide": "co", "nitrogen_dioxide": "no2",
                            "sulphur_dioxide": "so2", "ozone": "o3",
                            "temperature_2m": "temp", "relative_humidity_2m": "humidity",
                            "dew_point_2m": "dew_point", "surface_pressure": "pressure",
                            "wind_speed_10m": "wind_speed", "wind_direction_10m": "wind_dir",
                            "boundary_layer_height": "blh"})


def clean(df: pd.DataFrame, report: list) -> pd.DataFrame:
    report.append(f"Số dòng sau khi ghép: {len(df)}")
    report.append("Tỉ lệ thiếu trước xử lý (%):\n" +
                  (df.isna().mean() * 100).round(2).to_string())
    dup = df.index.duplicated().sum()
    df = df[~df.index.duplicated()]
    report.append(f"Số dòng trùng thời gian bị loại: {dup}")

    # Thiếu dữ liệu: nội suy tuyến tính theo thời gian cho khoảng trống ngắn (<= 6h),
    # khoảng trống dài hơn dùng giá trị trung bình cùng giờ trong cùng tháng.
    df = df.interpolate(method="time", limit=6)
    for c in df.columns[df.isna().any()]:
        fill = df.groupby([df.index.month, df.index.hour])[c].transform("mean")
        df[c] = df[c].fillna(fill)
    report.append(f"Số ô còn thiếu sau xử lý: {int(df.isna().sum().sum())}")

    # Ngoại lai: kẹp các chất ô nhiễm ở ngưỡng Q3 + 3*IQR (giữ lại các đợt ô nhiễm thật,
    # chỉ loại giá trị cực đoan bất thường)
    for c in ["pm2_5", "pm10", "co", "no2", "so2", "o3"]:
        q1, q3 = df[c].quantile([.25, .75])
        upper = q3 + 3 * (q3 - q1)
        n = int((df[c] > upper).sum())
        df[c] = df[c].clip(upper=upper)
        report.append(f"Ngoại lai {c}: {n} giá trị > {upper:.1f} đã được kẹp")
    return df


def to_daily(df: pd.DataFrame) -> pd.DataFrame:
    # Gió là đại lượng vector -> đổi sang thành phần u, v trước khi lấy trung bình
    rad = np.deg2rad(df["wind_dir"])
    df = df.assign(wind_u=-df["wind_speed"] * np.sin(rad),
                   wind_v=-df["wind_speed"] * np.cos(rad))
    agg = {c: "mean" for c in df.columns if c not in ("precipitation", "wind_dir")}
    agg["precipitation"] = "sum"
    daily = df.resample("D").agg(agg)
    daily["pm2_5_max"] = df["pm2_5"].resample("D").max()
    daily["temp_range"] = df["temp"].resample("D").max() - df["temp"].resample("D").min()
    daily["blh_min"] = df["blh"].resample("D").min()
    return daily.drop(columns=["wind_dir"], errors="ignore")


def add_features(d: pd.DataFrame, dropna: bool = True) -> pd.DataFrame:
    d = d.copy()
    d["month"] = d.index.month
    d["dayofweek"] = d.index.day_of_week
    d["is_weekend"] = (d["dayofweek"] >= 5).astype(int)
    d["season"] = d["month"].map(lambda m: "Đông" if m in (12, 1, 2) else
                                 "Xuân" if m in (3, 4) else
                                 "Hè" if m in (5, 6, 7, 8) else "Thu")
    # mã hoá chu kỳ cho tháng
    d["month_sin"] = np.sin(2 * np.pi * d["month"] / 12)
    d["month_cos"] = np.cos(2 * np.pi * d["month"] / 12)
    # biến trễ và trung bình trượt của PM2.5
    for k in (1, 2, 3, 7):
        d[f"pm2_5_lag{k}"] = d["pm2_5"].shift(k)
    d["pm2_5_roll3"] = d["pm2_5"].rolling(3).mean()
    d["pm2_5_roll7"] = d["pm2_5"].rolling(7).mean()
    d["pm2_5_diff1"] = d["pm2_5"] - d["pm2_5_lag1"]
    d["rain_3d"] = d["precipitation"].rolling(3).sum()
    # BIẾN MỤC TIÊU: giá trị của ngày mai
    d["target_pm25_next"] = d["pm2_5"].shift(-1)
    d["target_polluted_next"] = (d["target_pm25_next"] > PM25_LIMIT).astype(float)
    d.loc[d["target_pm25_next"].isna(), "target_polluted_next"] = np.nan
    return d.dropna() if dropna else d


def main():
    PROC.mkdir(parents=True, exist_ok=True)
    report = []
    hourly = clean(load_and_merge(), report)
    hourly.to_csv(PROC / "hourly_clean.csv")
    daily = add_features(to_daily(hourly))
    daily.to_csv(PROC / "daily_features.csv", index_label="date")
    report.append(f"Bảng ngày cuối cùng: {daily.shape[0]} ngày x {daily.shape[1]} cột "
                  f"({daily.index.min().date()} -> {daily.index.max().date()})")
    report.append(f"Tỉ lệ ngày ô nhiễm (PM2.5 > {PM25_LIMIT}): "
                  f"{daily['target_polluted_next'].mean():.1%}")
    text = "\n\n".join(report)
    (ROOT / "report" / "preprocess_log.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
