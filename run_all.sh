#!/usr/bin/env bash
# Chạy toàn bộ pipeline: thu thập -> tiền xử lý -> EDA -> mô hình
set -e
cd "$(dirname "$0")"
python src/collect_data.py
python src/preprocess.py
python src/eda.py
python src/train.py
