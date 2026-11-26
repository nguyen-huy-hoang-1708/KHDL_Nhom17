"""
BƯỚC 3 - PHÂN TÍCH KHÁM PHÁ DỮ LIỆU (EDA)
Sinh các biểu đồ vào figures/ và bảng thống kê vào report/eda_summary.txt
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
sns.set_theme(style="whitegrid", font_scale=1.0)
plt.rcParams["figure.dpi"] = 120
SEASON_ORDER = ["Xuân", "Hè", "Thu", "Đông"]
MONTH_LABELS = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12"]


def save(name):
    plt.tight_layout()
    plt.savefig(FIG / f"{name}.png", bbox_inches="tight")
    plt.close()


def main():
    FIG.mkdir(exist_ok=True)
    h = pd.read_csv(ROOT / "data/processed/hourly_clean.csv", parse_dates=["time"], index_col="time")
    d = pd.read_csv(ROOT / "data/processed/daily_features.csv", parse_dates=["date"], index_col="date")
    out = []

    # 1. Thống kê mô tả
    cols = ["pm2_5", "pm10", "co", "no2", "temp", "humidity", "precipitation", "wind_speed", "blh"]
    out.append("THỐNG KÊ MÔ TẢ (dữ liệu ngày)\n" + d[cols].describe().round(2).to_string())

    # 2. Chuỗi thời gian PM2.5
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(d.index, d["pm2_5"], lw=.6, color="#888", label="Trung bình ngày")
    ax.plot(d.index, d["pm2_5"].rolling(30).mean(), lw=2, color="#c0392b", label="Trung bình trượt 30 ngày")
    ax.axhline(50, ls="--", color="k", lw=1, label="QCVN 05:2023 (50 µg/m³)")
    ax.set(title="Nồng độ PM2.5 tại Hà Nội theo thời gian", ylabel="PM2.5 (µg/m³)")
    ax.legend()
    save("01_pm25_timeseries")

    # 3. Phân phối PM2.5
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    sns.histplot(d["pm2_5"], kde=True, ax=ax[0], color="#2980b9")
    ax[0].set(title="Phân phối PM2.5 trung bình ngày", xlabel="µg/m³")
    sns.boxplot(data=d, x="season", y="pm2_5", order=SEASON_ORDER, ax=ax[1], palette="coolwarm", hue="season", legend=False)
    ax[1].set(title="PM2.5 theo mùa", xlabel="", ylabel="µg/m³")
    save("02_pm25_distribution_season")
    out.append(f"Độ lệch (skewness) PM2.5: {d['pm2_5'].skew():.2f}")

    # 4. Mẫu theo tháng và theo giờ
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    m = d.groupby("month")["pm2_5"].mean()
    ax[0].bar(MONTH_LABELS, m.values, color=["#c0392b" if v > 50 else "#27ae60" for v in m.values])
    ax[0].axhline(50, ls="--", color="k", lw=1)
    ax[0].set(title="PM2.5 trung bình theo tháng", ylabel="µg/m³")
    hh = h.assign(hour=h.index.hour, winter=h.index.month.isin([11, 12, 1, 2]))
    for w, lab in [(True, "Mùa khô (T11–T2)"), (False, "Các tháng khác")]:
        g = hh[hh.winter == w].groupby("hour")["pm2_5"].mean()
        ax[1].plot(g.index, g.values, marker="o", ms=3, label=lab)
    ax[1].set(title="Chu kỳ PM2.5 trong ngày", xlabel="Giờ", ylabel="µg/m³")
    ax[1].legend()
    save("03_pm25_month_hour")
    out.append("PM2.5 trung bình theo tháng:\n" + m.round(1).to_string())

    # 5. Heatmap tháng x năm
    pv = d.pivot_table(index=d.index.year, columns="month", values="pm2_5", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(11, 3.5))
    sns.heatmap(pv, annot=True, fmt=".0f", cmap="YlOrRd", ax=ax, cbar_kws={"label": "µg/m³"})
    ax.set(title="PM2.5 trung bình theo tháng và năm", xlabel="Tháng", ylabel="Năm")
    save("04_heatmap_year_month")

    # 6. Ma trận tương quan
    corr_cols = ["pm2_5", "pm10", "co", "no2", "so2", "o3", "temp", "humidity",
                 "precipitation", "pressure", "wind_speed", "wind_u", "wind_v", "blh", "cloud_cover"]
    c = d[corr_cols].corr(method="spearman")
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(c, annot=True, fmt=".2f", cmap="RdBu_r", center=0, ax=ax, annot_kws={"size": 7})
    ax.set(title="Ma trận tương quan Spearman (dữ liệu ngày)")
    save("05_correlation")
    out.append("Tương quan Spearman với PM2.5:\n" + c["pm2_5"].drop("pm2_5").sort_values().round(3).to_string())

    # 7. Quan hệ PM2.5 với các yếu tố khí tượng
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.8))
    for ax, (col, lab) in zip(axes, [("blh", "Độ cao lớp biên (m)"), ("temp", "Nhiệt độ (°C)"),
                                     ("wind_speed", "Tốc độ gió (km/h)"), ("precipitation", "Lượng mưa (mm/ngày)")]):
        sns.scatterplot(data=d, x=col, y="pm2_5", hue="season", hue_order=SEASON_ORDER,
                        palette="coolwarm", s=10, alpha=.6, ax=ax, legend=(col == "blh"))
        ax.set(xlabel=lab, ylabel="PM2.5")
    fig.suptitle("PM2.5 và các yếu tố khí tượng")
    save("06_pm25_vs_weather")

    # 8. Tự tương quan -> lý do dùng biến trễ
    from pandas.plotting import autocorrelation_plot
    fig, ax = plt.subplots(figsize=(10, 3.5))
    autocorrelation_plot(d["pm2_5"], ax=ax)
    ax.set(xlim=(0, 60), title="Tự tương quan của PM2.5 theo ngày (lag 0–60)")
    save("07_autocorrelation")
    out.append("Tự tương quan PM2.5: " + ", ".join(
        f"lag{k}={d['pm2_5'].autocorr(k):.2f}" for k in (1, 2, 3, 7, 14, 30)))

    # 9. Tỉ lệ ngày ô nhiễm theo mùa
    rate = (d["pm2_5"] > 50).groupby(d["season"]).mean().reindex(SEASON_ORDER) * 100
    out.append("Tỉ lệ ngày vượt QCVN theo mùa (%):\n" + rate.round(1).to_string())

    text = "\n\n".join(out)
    (ROOT / "report/eda_summary.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
