# Phân tích và dự báo nồng độ bụi mịn PM2.5 tại Hà Nội

Project môn **Nhập môn Khoa học dữ liệu** – áp dụng đầy đủ quy trình Data Science trên dữ liệu thật:
**thu thập → làm sạch → khám phá (EDA) → xây dựng đặc trưng → mô hình hoá → đánh giá → diễn giải**.

## Câu hỏi nghiên cứu
1. Nồng độ PM2.5 ở Hà Nội biến động thế nào theo mùa, theo tháng, theo giờ trong ngày?
2. Yếu tố khí tượng nào (gió, mưa, độ cao lớp biên, độ ẩm…) ảnh hưởng mạnh nhất đến PM2.5?
3. Có thể dự báo PM2.5 của **ngày mai** từ dữ liệu hôm nay không? (hồi quy)
4. Có thể cảnh báo trước một ngày "ô nhiễm" (PM2.5 > 50 µg/m³ – QCVN 05:2023/BTNMT) không? (phân loại)

## Dữ liệu
| Nguồn | Nội dung | Độ phân giải |
|---|---|---|
| [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) (mô hình CAMS) | PM2.5, PM10, CO, NO₂, SO₂, O₃ | theo giờ |
| [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) (ERA5) | nhiệt độ, độ ẩm, điểm sương, mưa, áp suất, mây, gió, độ cao lớp biên | theo giờ |

Vị trí: Hoàn Kiếm (21.03°N, 105.85°E). Thời gian: 01/08/2022 – 31/10/2026 (~37.000 bản ghi/giờ → 1.545 ngày). Miễn phí, không cần API key.

## Cấu trúc
```
├── src/
│   ├── collect_data.py   # B1: gọi API, lưu data/raw/
│   ├── preprocess.py     # B2: ghép bảng, xử lý thiếu/ngoại lai, tổng hợp ngày, tạo đặc trưng
│   ├── eda.py            # B3: thống kê mô tả + 7 biểu đồ
│   └── train.py          # B4: hồi quy + phân loại, tinh chỉnh, đánh giá, độ quan trọng đặc trưng
├── notebooks/PM25_HaNoi.ipynb   # notebook trình bày (đã chạy sẵn)
├── data/raw, data/processed     # dữ liệu
├── figures/                     # 11 biểu đồ
├── models/                      # mô hình tốt nhất (.joblib)
├── report/                      # BaoCao.md + log, bảng kết quả
├── requirements.txt
└── run_all.sh
```

## Cách chạy
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run_all.sh            # hoặc chạy từng file trong src/ theo thứ tự
```

## Kết quả chính (tập test 01/07/2025 – 30/10/2026, 487 ngày)
| Hồi quy | MAE | RMSE | R² |
|---|---|---|---|
| Baseline (ngày mai = hôm nay) | 13.06 | 17.23 | 0.31 |
| Ridge Regression | 11.37 | 14.62 | 0.51 |
| Random Forest | 10.86 | 14.39 | 0.52 |
| **Gradient Boosting** | **10.80** | 14.40 | **0.52** |

| Phân loại (> 50 µg/m³) | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| Baseline | 0.754 | 0.704 | 0.704 | 0.704 | – |
| **Logistic Regression** | 0.776 | 0.691 | **0.837** | **0.757** | **0.852** |
| Random Forest | 0.778 | 0.713 | 0.783 | 0.746 | 0.847 |
| Gradient Boosting | 0.774 | 0.688 | 0.837 | 0.756 | 0.848 |
