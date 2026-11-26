# BÁO CÁO PROJECT – NHẬP MÔN KHOA HỌC DỮ LIỆU
## Phân tích và dự báo nồng độ bụi mịn PM2.5 tại Hà Nội

**Sinh viên / Nhóm:** ……………… **MSSV:** ……………… **GVHD:** ………………

---

## 1. Giới thiệu
Ô nhiễm không khí, đặc biệt là bụi mịn PM2.5 (đường kính ≤ 2,5 µm), là vấn đề môi trường nghiêm trọng tại Hà Nội. PM2.5 có thể đi sâu vào phổi và máu, liên quan tới bệnh hô hấp và tim mạch. Việc hiểu được quy luật biến động và dự báo trước mức ô nhiễm giúp người dân chủ động phòng tránh.

**Mục tiêu:**
- Thu thập và làm sạch dữ liệu chất lượng không khí + khí tượng Hà Nội trong hơn 4 năm.
- Phân tích khám phá để tìm quy luật theo thời gian và mối quan hệ với thời tiết.
- Xây dựng mô hình dự báo PM2.5 ngày hôm sau (hồi quy) và cảnh báo ngày vượt quy chuẩn (phân loại).

## 2. Dữ liệu
### 2.1. Nguồn và phương pháp thu thập
- Open-Meteo Air Quality API (mô hình CAMS của Copernicus) – 6 chất ô nhiễm theo giờ.
- Open-Meteo Historical Weather API (tái phân tích ERA5) – 9 biến khí tượng theo giờ.
- Thu thập bằng `requests` (script `src/collect_data.py`), chia theo từng năm, có cơ chế thử lại.
- Phạm vi: 01/08/2022 – 31/10/2026, 37.272 bản ghi/giờ mỗi bảng.

### 2.2. Mô tả biến
| Biến | Ý nghĩa | Đơn vị |
|---|---|---|
| pm2_5, pm10 | Bụi mịn, bụi thô | µg/m³ |
| co, no2, so2, o3 | Khí ô nhiễm | µg/m³ |
| temp, dew_point | Nhiệt độ, điểm sương | °C |
| humidity | Độ ẩm tương đối | % |
| precipitation | Lượng mưa | mm |
| pressure | Áp suất bề mặt | hPa |
| cloud_cover | Độ che phủ mây | % |
| wind_speed, wind_dir | Tốc độ, hướng gió ở 10 m | km/h, độ |
| blh | Độ cao lớp biên khí quyển | m |

## 3. Tiền xử lý dữ liệu
(chi tiết: `report/preprocess_log.txt`)
1. **Ghép bảng** theo cột thời gian (inner join) → 37.272 dòng, không có dòng trùng lặp.
2. **Giá trị thiếu:** các chất ô nhiễm thiếu 0,21%; `blh` thiếu 11,72%. Xử lý: nội suy tuyến tính theo thời gian cho khoảng trống ≤ 6 giờ; khoảng trống dài hơn điền bằng trung bình cùng (tháng, giờ).
3. **Ngoại lai:** dùng ngưỡng Q3 + 3·IQR (nới rộng so với 1,5·IQR để giữ lại các đợt ô nhiễm thật). Ví dụ PM2.5: 289 giá trị > 147,7 µg/m³ bị kẹp lại.
4. **Tổng hợp theo ngày:** lấy trung bình (mưa lấy tổng); gió được đổi sang hai thành phần vector u, v trước khi lấy trung bình (vì không thể lấy trung bình trực tiếp hướng gió 350° và 10°).
5. **Xây dựng đặc trưng:**
   - Thời gian: tháng (mã hoá sin/cos), thứ trong tuần, cuối tuần, mùa.
   - Biến trễ PM2.5: lag 1, 2, 3, 7 ngày; trung bình trượt 3 và 7 ngày; chênh lệch so với hôm qua.
   - Biến khác: PM2.5 cực đại trong ngày, biên độ nhiệt, BLH nhỏ nhất, tổng mưa 3 ngày.
6. **Biến mục tiêu:** `target_pm25_next` = PM2.5 trung bình ngày hôm sau; `target_polluted_next` = 1 nếu giá trị đó > 50 µg/m³ (QCVN 05:2023/BTNMT).

Kết quả: bảng 1.545 ngày × 35 cột; 33,9% số ngày bị xếp là "ô nhiễm".

## 4. Phân tích khám phá (EDA)
(chi tiết: `report/eda_summary.txt`, hình trong `figures/`)

- **Hình 1 – Chuỗi thời gian:** PM2.5 trung bình ngày 45,2 µg/m³ – gần ngưỡng 50 của QCVN và gấp 3 lần khuyến nghị 15 µg/m³ của WHO.
- **Hình 2 – Phân phối:** lệch phải (skewness = 0,98): đa số ngày ở mức 30–56 µg/m³ nhưng có đuôi dài các đợt ô nhiễm nặng (tối đa 128 µg/m³). Tỉ lệ ngày vượt chuẩn cao nhất vào mùa Xuân (43,9%) và Đông (39,6%), thấp nhất mùa Hè (26,7%).
- **Hình 3 – Theo tháng / giờ:** cao nhất tháng 4 (57,6) và tháng 1 (53,2). Trong ngày, PM2.5 thấp nhất lúc 11–15h (lớp biên phát triển, không khí xáo trộn mạnh) và cao nhất 19–22h (giờ tan tầm + lớp biên thấp về đêm). Mùa khô có thêm đỉnh nhỏ lúc 7h (giờ cao điểm sáng).
- **Hình 4 – Heatmap năm × tháng:** cho phép so sánh xu hướng giữa các năm.
- **Hình 5 – Tương quan Spearman:**
  - Tương quan âm mạnh nhất: **tốc độ gió (−0,61)**, mây (−0,32), **độ cao lớp biên (−0,31)**, mưa (−0,27) → gió và mưa giúp phát tán, rửa trôi bụi.
  - Tương quan dương mạnh với PM10 (0,91), CO (0,68), NO₂ (0,68), SO₂ (0,67) → cùng nguồn phát thải (giao thông, đốt nhiên liệu).
- **Hình 6 – PM2.5 vs thời tiết:** xác nhận trực quan các mối quan hệ trên.
- **Hình 7 – Tự tương quan:** lag-1 = 0,67, lag-2 = 0,37, giảm nhanh sau 3 ngày → PM2.5 có "quán tính" ngắn hạn, lý giải việc dùng biến trễ 1–3 ngày.

## 5. Mô hình hoá
### 5.1. Thiết lập thực nghiệm
- **Chia dữ liệu theo thời gian** (không xáo trộn, tránh rò rỉ tương lai): train 08/2022 – 06/2025 (1.058 ngày), test 07/2025 – 10/2026 (487 ngày).
- **Tinh chỉnh siêu tham số:** GridSearchCV với `TimeSeriesSplit(5)` trên tập train.
- **Baseline:** "persistence" – dự báo ngày mai bằng giá trị hôm nay.
- **Mô hình:** Ridge / Logistic Regression (tuyến tính, có chuẩn hoá), Random Forest, Histogram Gradient Boosting. Bài toán phân loại dùng `class_weight="balanced"` do mất cân bằng nhãn (34% / 66%).
- **Độ đo:** hồi quy – MAE, RMSE, R²; phân loại – Accuracy, Precision, Recall, F1, ROC-AUC.

### 5.2. Kết quả hồi quy
| Mô hình | MAE | RMSE | R² |
|---|---|---|---|
| Baseline | 13,06 | 17,23 | 0,313 |
| Ridge Regression | 11,37 | 14,62 | 0,505 |
| Random Forest | 10,86 | 14,39 | 0,520 |
| **Gradient Boosting** | **10,80** | 14,40 | **0,520** |

Mô hình tốt nhất giảm MAE ~17% so với baseline. Hình 8–9 cho thấy mô hình bắt đúng xu hướng nhưng thường dự báo thấp các đỉnh ô nhiễm đột biến.

### 5.3. Kết quả phân loại
| Mô hình | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| Baseline | 0,754 | 0,704 | 0,704 | 0,704 | – |
| **Logistic Regression** | 0,776 | 0,691 | **0,837** | **0,757** | **0,852** |
| Random Forest | 0,778 | 0,713 | 0,783 | 0,746 | 0,847 |
| Gradient Boosting | 0,774 | 0,688 | 0,837 | 0,756 | 0,848 |

Với bài toán cảnh báo, **Recall** quan trọng hơn (bỏ sót ngày ô nhiễm nguy hiểm hơn báo nhầm). Logistic Regression đạt Recall 0,84 – phát hiện được 84% số ngày ô nhiễm – và tốt ngang các mô hình phức tạp hơn.

### 5.4. Diễn giải mô hình (Hình 10)
Permutation importance cho thấy các đặc trưng quan trọng nhất: PM2.5 cực đại và trung bình hôm nay, mức thay đổi so với hôm qua, **thành phần gió bắc–nam (wind_v)**, tốc độ gió và mùa (month_sin). Điều này khớp với EDA: PM2.5 có quán tính ngắn hạn và gió là yếu tố khí tượng chi phối.

## 6. Thảo luận và hạn chế
- Dữ liệu PM2.5 là **dữ liệu mô hình (CAMS)** chứ không phải số đo trạm quan trắc; độ phân giải ~40 km nên không phản ánh khác biệt giữa các quận và có thể làm "phẳng" chu kỳ mùa so với số đo thực tế.
- Mô hình chỉ dùng thời tiết **hôm nay**; trong thực tế có thể dùng thêm **dự báo thời tiết ngày mai** để cải thiện đáng kể.
- R² ≈ 0,52: còn nhiều biến động do các yếu tố chưa có trong dữ liệu (đốt rơm rạ, sự kiện, phát thải công nghiệp, vận chuyển ô nhiễm xuyên biên giới).

## 7. Hướng phát triển
- Bổ sung số đo trạm thực tế (OpenAQ, IQAir, Sở TN&MT Hà Nội) và so sánh với CAMS.
- Thêm biến dự báo thời tiết, dữ liệu cháy (NASA FIRMS), mật độ giao thông.
- Thử mô hình chuỗi thời gian (SARIMAX, Prophet, LSTM) và dự báo nhiều ngày.
- Xây dựng dashboard cảnh báo (Streamlit).

## 8. Kết luận
Project đã thực hiện trọn vẹn quy trình Khoa học dữ liệu trên hơn 4 năm dữ liệu thực tế của Hà Nội. Kết quả cho thấy PM2.5 có quy luật rõ theo giờ và mùa, chịu ảnh hưởng mạnh của gió, mưa và độ cao lớp biên. Mô hình học máy dự báo PM2.5 ngày hôm sau với sai số trung bình ~10,8 µg/m³ và phát hiện được 84% số ngày vượt quy chuẩn, tốt hơn rõ rệt so với phương pháp cơ sở.

## Tài liệu tham khảo
1. Open-Meteo – Air Quality API & Historical Weather API. https://open-meteo.com
2. Copernicus Atmosphere Monitoring Service (CAMS). https://atmosphere.copernicus.eu
3. Hersbach, H. et al. (2020). The ERA5 global reanalysis. *Q. J. R. Meteorol. Soc.*
4. Bộ TN&MT (2023). QCVN 05:2023/BTNMT – Quy chuẩn kỹ thuật quốc gia về chất lượng không khí.
5. WHO (2021). WHO global air quality guidelines.
6. Pedregosa, F. et al. (2011). Scikit-learn: Machine Learning in Python. *JMLR* 12.
