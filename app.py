"""
DASHBOARD – Phân tích & dự báo PM2.5 Hà Nội
Chạy:  streamlit run app.py
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import live  # noqa: E402

st.set_page_config(page_title="PM2.5 Hà Nội – Nhóm 17", page_icon="🌫️", layout="wide")
LIMIT = 50
SEASONS = ["Xuân", "Hè", "Thu", "Đông"]
LABELS = {"pm2_5": "PM2.5 (µg/m³)", "pm10": "PM10 (µg/m³)", "co": "CO (µg/m³)", "no2": "NO₂ (µg/m³)",
          "so2": "SO₂ (µg/m³)", "o3": "O₃ (µg/m³)", "temp": "Nhiệt độ (°C)", "humidity": "Độ ẩm (%)",
          "precipitation": "Lượng mưa (mm)", "pressure": "Áp suất (hPa)", "cloud_cover": "Mây (%)",
          "wind_speed": "Tốc độ gió (km/h)", "blh": "Độ cao lớp biên (m)", "dew_point": "Điểm sương (°C)"}

st.markdown("""
<style>
.block-container {padding-top: 1.6rem;}
div[data-testid="stMetric"] {background: rgba(128,128,128,.08); border-radius: 10px; padding: 12px 16px;}
.level-card {border-radius: 14px; padding: 18px 22px; color: #111;}
.level-card h2 {margin: 0; color: #111;}
</style>""", unsafe_allow_html=True)


# ---------------------------------------------------------------- dữ liệu
@st.cache_data
def load_daily():
    return pd.read_csv(ROOT / "data/processed/daily_features.csv", parse_dates=["date"], index_col="date")


@st.cache_data
def load_hourly():
    return pd.read_csv(ROOT / "data/processed/hourly_clean.csv", parse_dates=["time"], index_col="time")


@st.cache_resource
def load_models():
    return joblib.load(ROOT / "models/regressor.joblib"), joblib.load(ROOT / "models/classifier.joblib")


@st.cache_data(ttl=3600, show_spinner="Đang lấy dữ liệu mới nhất từ Open-Meteo…")
def load_live():
    return live.fetch_recent_daily()


d, h = load_daily(), load_hourly()
reg, clf = load_models()
summary = json.load(open(ROOT / "report/results_summary.json", encoding="utf-8"))

# ---------------------------------------------------------------- sidebar
st.sidebar.title("🌫️ PM2.5 Hà Nội")
st.sidebar.caption("Project Nhập môn Khoa học dữ liệu – Nhóm 17")
page = st.sidebar.radio("Trang", ["🏠 Tổng quan", "🔮 Dự báo ngày mai", "📊 Khám phá dữ liệu",
                                  "🤖 Mô hình", "🧪 Mô phỏng What-if", "🗂️ Dữ liệu"])
st.sidebar.divider()
st.sidebar.markdown(f"**Dữ liệu:** {d.index.min():%d/%m/%Y} – {d.index.max():%d/%m/%Y}  \n"
                    f"**Số ngày:** {len(d):,}  \n**Nguồn:** Open-Meteo (CAMS, ERA5)")


def level_badge(pm):
    name, color, advice = live.vn_aqi_level(pm)
    return name, color, advice


# ================================================================= TỔNG QUAN
if page == "🏠 Tổng quan":
    st.title("Phân tích & dự báo bụi mịn PM2.5 tại Hà Nội")
    st.write("Ứng dụng quy trình Khoa học dữ liệu trên hơn 4 năm dữ liệu chất lượng không khí và khí tượng "
             "theo giờ: **thu thập → làm sạch → khám phá → xây dựng đặc trưng → mô hình hoá → triển khai**.")

    c = st.columns(4)
    c[0].metric("PM2.5 trung bình", f"{d.pm2_5.mean():.1f} µg/m³", f"{d.pm2_5.mean()/15:.1f}× ngưỡng WHO",
                delta_color="inverse")
    c[1].metric("Ngày vượt QCVN (>50)", f"{(d.pm2_5 > LIMIT).mean():.0%}")
    worst = d.pm2_5.idxmax()
    c[2].metric("Ngày ô nhiễm nhất", f"{worst:%d/%m/%Y}", f"{d.pm2_5.max():.0f} µg/m³", delta_color="inverse")
    c[3].metric("Sai số dự báo (MAE)", "10.8 µg/m³", "-17% so với baseline", delta_color="inverse")

    st.subheader("Diễn biến PM2.5")
    rng = st.slider("Khoảng thời gian", d.index.min().date(), d.index.max().date(),
                    (d.index.min().date(), d.index.max().date()), format="DD/MM/YYYY")
    s = d.loc[str(rng[0]):str(rng[1])]
    fig = go.Figure()
    fig.add_bar(x=s.index, y=s.pm2_5, name="Trung bình ngày",
                marker_color=[live.vn_aqi_level(v)[1] for v in s.pm2_5], opacity=.75)
    fig.add_scatter(x=s.index, y=s.pm2_5.rolling(30, min_periods=1).mean(), name="Trung bình 30 ngày",
                    line=dict(color="#333", width=2))
    fig.add_hline(y=LIMIT, line_dash="dash", annotation_text="QCVN 05:2023")
    fig.update_layout(height=420, yaxis_title="µg/m³", legend=dict(orientation="h", y=1.08), margin=dict(t=30))
    st.plotly_chart(fig, width="stretch")
    st.caption("Màu cột theo mức VN_AQI: xanh = Tốt, vàng = Trung bình, cam = Kém, đỏ = Xấu.")

    st.subheader("Quy trình thực hiện")
    cols = st.columns(5)
    for col, (icon, t, desc) in zip(cols, [
        ("📥", "Thu thập", "API Open-Meteo, 37k bản ghi/giờ, 15 biến"),
        ("🧹", "Tiền xử lý", "Nội suy thiếu, kẹp ngoại lai IQR, gộp theo ngày"),
        ("🔍", "EDA", "Mùa vụ, chu kỳ ngày, tương quan, tự tương quan"),
        ("⚙️", "Mô hình", "Ridge, Logistic, Random Forest, Gradient Boosting"),
        ("🚀", "Triển khai", "Dashboard + dự báo thời gian thực")]):
        col.markdown(f"### {icon}\n**{t}**  \n{desc}")


# ================================================================= DỰ BÁO
elif page == "🔮 Dự báo ngày mai":
    st.title("🔮 Dự báo PM2.5 ngày mai")
    st.write("Lấy dữ liệu 14 ngày gần nhất + hôm nay từ Open-Meteo, tính đặc trưng giống hệt lúc huấn luyện "
             "rồi đưa vào mô hình tốt nhất.")
    if st.button("🔄 Cập nhật dữ liệu"):
        load_live.clear()
    try:
        recent = load_live()
        r = live.predict_tomorrow(recent, reg, clf)
    except Exception as e:  # mất mạng / API lỗi
        st.error(f"Không lấy được dữ liệu thời gian thực: {e}")
        st.stop()

    name, color, advice = level_badge(r["pm25_pred"])
    c1, c2 = st.columns([1, 1.3])
    with c1:
        g = go.Figure(go.Indicator(
            mode="gauge+number", value=r["pm25_pred"], number={"suffix": " µg/m³"},
            title={"text": f"PM2.5 dự báo ngày {r['target_date']:%d/%m/%Y}"},
            gauge={"axis": {"range": [0, 160]}, "bar": {"color": "#222", "thickness": .25},
                   "steps": [{"range": [0, 25], "color": "#00e400"}, {"range": [25, 50], "color": "#ffd000"},
                             {"range": [50, 80], "color": "#ff7e00"}, {"range": [80, 160], "color": "#ff0000"}],
                   "threshold": {"line": {"color": "black", "width": 3}, "value": LIMIT}}))
        g.update_layout(height=320, margin=dict(t=60, b=10))
        st.plotly_chart(g, width="stretch")
    with c2:
        st.markdown(f"<div class='level-card' style='background:{color}'>"
                    f"<div>Mức chất lượng không khí dự kiến</div><h2>{name}</h2><div>{advice}</div></div>",
                    unsafe_allow_html=True)
        st.write("")
        m = st.columns(2)
        m[0].metric("Xác suất vượt QCVN", f"{r['prob_polluted']:.0%}")
        m[1].metric("PM2.5 hôm nay", f"{r['today']['pm2_5']:.1f} µg/m³",
                    f"{r['pm25_pred'] - r['today']['pm2_5']:+.1f} ngày mai", delta_color="inverse")
        t = r["today"]
        st.caption(f"Thời tiết hôm nay: {t['temp']:.1f}°C · độ ẩm {t['humidity']:.0f}% · gió {t['wind_speed']:.1f} km/h"
                   f" · mưa {t['precipitation']:.1f} mm · lớp biên {t['blh']:.0f} m")

    st.subheader("14 ngày gần đây và dự báo")
    hist = recent["pm2_5"].dropna()
    fig = go.Figure()
    fig.add_scatter(x=hist.index, y=hist.values, mode="lines+markers", name="Đã quan trắc / phân tích")
    fig.add_scatter(x=[hist.index[-1], pd.Timestamp(r["target_date"])], y=[hist.iloc[-1], r["pm25_pred"]],
                    mode="lines+markers", name="Dự báo", line=dict(dash="dash", color="#e67e22"),
                    marker=dict(size=[6, 14]))
    fig.add_hline(y=LIMIT, line_dash="dot", annotation_text="QCVN")
    fig.update_layout(height=360, yaxis_title="µg/m³", margin=dict(t=20))
    st.plotly_chart(fig, width="stretch")
    st.info("Lưu ý: số liệu 'hôm nay' gồm phần đã xảy ra và phần dự báo cho các giờ còn lại. "
            "Kết quả chỉ mang tính tham khảo cho mục đích học tập.")


# ================================================================= EDA
elif page == "📊 Khám phá dữ liệu":
    st.title("📊 Khám phá dữ liệu")
    f1, f2, f3 = st.columns(3)
    years = f1.multiselect("Năm", sorted(d.index.year.unique()), default=sorted(d.index.year.unique()))
    seasons = f2.multiselect("Mùa", SEASONS, default=SEASONS)
    var = f3.selectbox("Biến phân tích", list(LABELS), format_func=LABELS.get)
    s = d[d.index.year.isin(years) & d.season.isin(seasons)]
    hs = h[h.index.year.isin(years)]
    if s.empty:
        st.warning("Không có dữ liệu với bộ lọc này."); st.stop()

    t1, t2, t3, t4, t5 = st.tabs(["Phân phối", "Theo thời gian", "Năm × tháng", "Tương quan", "Quan hệ 2 biến"])
    with t1:
        a, b = st.columns(2)
        a.plotly_chart(px.histogram(s, x=var, nbins=50, marginal="box", labels=LABELS,
                                    title=f"Phân phối {LABELS[var]}"), width="stretch")
        b.plotly_chart(px.box(s, x="season", y=var, color="season", category_orders={"season": SEASONS},
                              labels=LABELS, title="Theo mùa"), width="stretch")
        st.dataframe(s[var].describe().to_frame().T.round(2), width="stretch")
    with t2:
        a, b = st.columns(2)
        mo = s.groupby("month")[var].mean().reset_index()
        a.plotly_chart(px.bar(mo, x="month", y=var, labels={**LABELS, "month": "Tháng"},
                              title="Trung bình theo tháng"), width="stretch")
        hh = hs.assign(hour=hs.index.hour, nhom=np.where(hs.index.month.isin([11, 12, 1, 2]),
                                                          "Mùa khô (T11–T2)", "Các tháng khác"))
        hr = hh.groupby(["hour", "nhom"])[var].mean().reset_index()
        b.plotly_chart(px.line(hr, x="hour", y=var, color="nhom", markers=True,
                               labels={**LABELS, "hour": "Giờ", "nhom": ""}, title="Chu kỳ trong ngày"),
                       width="stretch")
        dw = s.groupby("dayofweek")[var].mean().rename(index=dict(enumerate(["T2", "T3", "T4", "T5", "T6", "T7", "CN"])))
        st.plotly_chart(px.bar(dw, labels={"value": LABELS[var], "dayofweek": "Thứ"},
                               title="Theo thứ trong tuần").update_layout(showlegend=False), width="stretch")
    with t3:
        pv = s.pivot_table(index=s.index.year, columns="month", values=var, aggfunc="mean")
        st.plotly_chart(px.imshow(pv, text_auto=".0f", color_continuous_scale="YlOrRd", aspect="auto",
                                  labels=dict(x="Tháng", y="Năm", color=LABELS[var])), width="stretch")
    with t4:
        method = st.radio("Phương pháp", ["spearman", "pearson"], horizontal=True)
        corr = s[list(LABELS)].corr(method=method)
        st.plotly_chart(px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                                  aspect="auto", height=600), width="stretch")
        st.caption("Gió, mưa và độ cao lớp biên tương quan âm với PM2.5: không khí càng xáo trộn, bụi càng phát tán.")
    with t5:
        a, b = st.columns(2)
        x = a.selectbox("Trục X", [k for k in LABELS if k != "pm2_5"], index=list(LABELS).index("wind_speed") - 1,
                        format_func=LABELS.get)
        y = b.selectbox("Trục Y", list(LABELS), format_func=LABELS.get)
        st.plotly_chart(px.scatter(s.reset_index(), x=x, y=y, color="season", category_orders={"season": SEASONS},
                                   trendline="lowess" if len(s) > 20 else None, opacity=.6, labels=LABELS,
                                   hover_data=["date"]), width="stretch")


# ================================================================= MÔ HÌNH
elif page == "🤖 Mô hình":
    st.title("🤖 Kết quả mô hình")
    st.write(f"Chia theo thời gian: **train** {summary['n_train']} ngày (trước {summary['split_date']}), "
             f"**test** {summary['n_test']} ngày. Tinh chỉnh bằng TimeSeriesSplit 5 fold.")
    test = d[d.index >= summary["split_date"]]
    X = test[reg["features"]]
    t1, t2 = st.tabs(["📈 Hồi quy – PM2.5 ngày mai", "🚦 Phân loại – vượt QCVN"])
    with t1:
        rr = pd.read_csv(ROOT / "report/results_regression.csv")
        a, b = st.columns([1, 1.2])
        a.dataframe(rr.style.highlight_min(["MAE", "RMSE"], color="#c8f7c5").highlight_max(["R2"], color="#c8f7c5"),
                    hide_index=True, width="stretch")
        b.plotly_chart(px.bar(rr, x="MAE", y="Mô hình", orientation="h", text="MAE", height=230)
                       .update_layout(margin=dict(t=10, b=10)), width="stretch")
        pred = reg["model"].predict(X)
        fig = go.Figure()
        fig.add_scatter(x=test.index, y=test.target_pm25_next, name="Thực tế", line=dict(color="#333"))
        fig.add_scatter(x=test.index, y=pred, name=f"Dự báo ({summary['best_regressor']})", line=dict(color="#e67e22"))
        fig.add_hline(y=LIMIT, line_dash="dot")
        fig.update_layout(height=380, title="Dự báo vs thực tế trên tập test", yaxis_title="µg/m³")
        st.plotly_chart(fig, width="stretch")
        a, b = st.columns(2)
        err = pd.DataFrame({"Thực tế": test.target_pm25_next, "Dự báo": pred})
        a.plotly_chart(px.scatter(err, x="Thực tế", y="Dự báo", opacity=.6, trendline="ols", title="Thực tế vs dự báo"),
                       width="stretch")
        imp = pd.Series(summary["top_features"]).sort_values()
        b.plotly_chart(px.bar(imp, orientation="h", title="Độ quan trọng đặc trưng (permutation)",
                              labels={"value": "Mức tăng MAE", "index": ""}).update_layout(showlegend=False),
                       width="stretch")
    with t2:
        rc = pd.read_csv(ROOT / "report/results_classification.csv")
        st.dataframe(rc.style.highlight_max(["Accuracy", "Precision", "Recall", "F1", "ROC-AUC"], color="#c8f7c5"),
                     hide_index=True, width="stretch")
        prob = clf["model"].predict_proba(test[clf["features"]])[:, 1]
        thr = st.slider("Ngưỡng xác suất để cảnh báo", 0.05, 0.95, 0.5, 0.05,
                        help="Giảm ngưỡng → bắt được nhiều ngày ô nhiễm hơn (Recall↑) nhưng báo nhầm nhiều hơn (Precision↓)")
        yt, yp = test.target_polluted_next.astype(int), (prob >= thr).astype(int)
        tp, fp = int(((yp == 1) & (yt == 1)).sum()), int(((yp == 1) & (yt == 0)).sum())
        fn, tn = int(((yp == 0) & (yt == 1)).sum()), int(((yp == 0) & (yt == 0)).sum())
        m = st.columns(4)
        m[0].metric("Accuracy", f"{(tp + tn) / len(yt):.3f}")
        m[1].metric("Precision", f"{tp / max(tp + fp, 1):.3f}")
        m[2].metric("Recall", f"{tp / max(tp + fn, 1):.3f}")
        m[3].metric("F1", f"{2 * tp / max(2 * tp + fp + fn, 1):.3f}")
        cm = pd.DataFrame([[tn, fp], [fn, tp]], index=["Thực tế: Đạt", "Thực tế: Ô nhiễm"],
                          columns=["Dự báo: Đạt", "Dự báo: Ô nhiễm"])
        st.plotly_chart(px.imshow(cm, text_auto=True, color_continuous_scale="Blues",
                                  title=f"Ma trận nhầm lẫn – {summary['best_classifier']}"), width="stretch")


# ================================================================= WHAT-IF
elif page == "🧪 Mô phỏng What-if":
    st.title("🧪 Mô phỏng: điều kiện hôm nay → PM2.5 ngày mai")
    st.write("Chọn một ngày làm mốc, sau đó thay đổi các yếu tố để xem mô hình phản ứng thế nào. "
             "Đây là cách kiểm tra mô hình có học được quy luật hợp lý hay không.")
    day = st.date_input("Ngày mốc", d.index.max().date(), min_value=d.index.min().date(),
                        max_value=d.index.max().date(), format="DD/MM/YYYY")
    base = d.loc[str(day)].copy() if str(day) in d.index.strftime("%Y-%m-%d") else d.iloc[-1].copy()
    c = st.columns(3)
    pm = c[0].slider("PM2.5 hôm nay (µg/m³)", 0.0, 150.0, float(round(base.pm2_5, 1)))
    wind = c[1].slider("Tốc độ gió (km/h)", 0.0, 35.0, float(round(base.wind_speed, 1)))
    blh = c[2].slider("Độ cao lớp biên (m)", 100.0, 1200.0, float(round(base.blh)))
    c = st.columns(3)
    rain = c[0].slider("Lượng mưa (mm)", 0.0, 100.0, float(round(base.precipitation, 1)))
    temp = c[1].slider("Nhiệt độ (°C)", 5.0, 40.0, float(round(base.temp, 1)))
    hum = c[2].slider("Độ ẩm (%)", 30.0, 100.0, float(round(base.humidity)))

    x = base.copy()
    ratio = pm / base.pm2_5 if base.pm2_5 > 0 else 1
    x["pm2_5"], x["pm2_5_max"] = pm, base.pm2_5_max * ratio
    x["pm2_5_diff1"] = pm - base.pm2_5_lag1
    x["pm2_5_roll3"] = (pm + base.pm2_5_lag1 + base.pm2_5_lag2) / 3
    x["pm2_5_roll7"] = base.pm2_5_roll7 + (pm - base.pm2_5) / 7
    k = wind / base.wind_speed if base.wind_speed > 0 else 1
    x["wind_speed"], x["wind_u"], x["wind_v"] = wind, base.wind_u * k, base.wind_v * k
    x["blh"], x["blh_min"] = blh, base.blh_min * blh / base.blh
    x["rain_3d"] = base.rain_3d - base.precipitation + rain
    x["precipitation"], x["temp"], x["humidity"] = rain, temp, hum

    X0, X1 = base[reg["features"]].to_frame().T.astype(float), x[reg["features"]].to_frame().T.astype(float)
    p0, p1 = reg["model"].predict(X0)[0], reg["model"].predict(X1)[0]
    pr = clf["model"].predict_proba(X1)[:, 1][0]
    name, color, advice = level_badge(p1)
    a, b, cc = st.columns(3)
    a.metric("Dự báo với số liệu gốc", f"{p0:.1f} µg/m³")
    b.metric("Dự báo sau khi thay đổi", f"{p1:.1f} µg/m³", f"{p1 - p0:+.1f}", delta_color="inverse")
    cc.metric("Xác suất vượt QCVN", f"{pr:.0%}")
    st.markdown(f"<div class='level-card' style='background:{color}'><b>{name}</b> – {advice}</div>",
                unsafe_allow_html=True)

    st.subheader("Độ nhạy theo tốc độ gió")
    winds = np.linspace(1, 35, 35)
    rows = []
    for w in winds:
        xi = X1.copy(); kk = w / max(wind, .1)
        xi["wind_speed"], xi["wind_u"], xi["wind_v"] = w, X1.wind_u * kk, X1.wind_v * kk
        rows.append(reg["model"].predict(xi)[0])
    st.plotly_chart(px.line(x=winds, y=rows, labels={"x": "Tốc độ gió (km/h)", "y": "PM2.5 dự báo (µg/m³)"})
                    .add_hline(y=LIMIT, line_dash="dot"), width="stretch")


# ================================================================= DỮ LIỆU
else:
    st.title("🗂️ Dữ liệu")
    which = st.radio("Bảng", ["Theo ngày (đã tạo đặc trưng)", "Theo giờ (đã làm sạch)"], horizontal=True)
    df = d if which.startswith("Theo ngày") else h
    st.write(f"{df.shape[0]:,} dòng × {df.shape[1]} cột")
    st.dataframe(df.round(2), width="stretch", height=480)
    st.download_button("⬇️ Tải CSV", df.to_csv().encode("utf-8"), file_name="pm25_hanoi.csv", mime="text/csv")
    with st.expander("Nhật ký tiền xử lý"):
        st.text((ROOT / "report/preprocess_log.txt").read_text(encoding="utf-8"))
