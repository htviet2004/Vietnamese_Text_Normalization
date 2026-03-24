# Chuẩn hoá văn bản tiếng Việt – NLP Pipeline (VOZ + YouTube)

Pipeline tiền xử lý và đánh giá baseline cho dữ liệu bình luận tiếng Việt thu thập từ hai nguồn: **YouTube** và **VOZ**.

---

## Cấu trúc thư mục

```
NLP/
├── outputs/                        # Kết quả xuất ra
│   ├── cleaned_dataset.csv         # Dữ liệu gốc sau bootstrap
│   ├── cleaned_dataset_fixed.csv   # Dữ liệu đã tiền xử lý đầy đủ
│   ├── pipeline_report.json        # Báo cáo thống kê pipeline
│   ├── pipeline_report.png         # Biểu đồ phân bố dữ liệu
│   └── baseline_results.csv        # Kết quả đánh giá baseline
├── resources/
│   ├── normalization_map.json      # Từ điển chuẩn hoá teencode / viết tắt
│   └── vietnamese_stopwords.txt    # Danh sách stopwords tiếng Việt
├── src/nlp_pipeline/
│   ├── nlp_pipeline.ipynb          # Notebook tiền xử lý (10 cells)
│   └── baseline_eval.ipynb         # Notebook đánh giá baseline (10 cells)
├── yt_comments.csv                 # Dữ liệu thô YouTube (input)
├── voz_threads_comments.csv        # Dữ liệu thô VOZ (input)
└── requirements.txt
```

---

## Yêu cầu

```bash
pip install -r requirements.txt
```

Các thư viện chính: `pandas`, `scikit-learn`, `matplotlib`, `underthesea` (hoặc `pyvi`).

---

## Cách chạy

### 1. Tiền xử lý văn bản

Mở và chạy toàn bộ **`src/nlp_pipeline/nlp_pipeline.ipynb`** (theo thứ tự từ trên xuống).

- Nếu `outputs/cleaned_dataset.csv` **chưa tồn tại**, notebook sẽ tự tổng hợp từ `yt_comments.csv` + `voz_threads_comments.csv`.
- Kết quả xuất ra `outputs/cleaned_dataset_fixed.csv` và `outputs/pipeline_report.*`.

### 2. Đánh giá baseline

Mở và chạy toàn bộ **`src/nlp_pipeline/baseline_eval.ipynb`** (sau khi bước 1 hoàn thành).

- Đọc `outputs/cleaned_dataset_fixed.csv`.
- Kết quả xuất ra `outputs/baseline_results.csv`.

---

## Tính năng pipeline

### Tiền xử lý văn bản (`nlp_pipeline.ipynb`)

| Bước | Mô tả |
|------|-------|
| 1 | Chuẩn hoá Unicode NFC, chuyển chữ thường |
| 2 | Loại bỏ HTML tag, URL, mention, hashtag, timestamp |
| 3 | Phát hiện ngôn ngữ (`vi` / `en` / `mixed`) |
| 4 | Chuẩn hoá cụm từ (phrase normalisation) |
| 5 | Chuẩn hoá đại từ chat (`a→anh`, `e→em`, …) |
| 6 | Ánh xạ teencode / viết tắt từ từ điển |
| 7 | Tách câu → tách từ (`underthesea` / `pyvi` / basic) |
| 8 | Hậu xử lý token (lọc nhiễu, hậu tố, token quá ngắn) |
| 9 | Tùy chọn lọc stopwords (mặc định tắt) |

### Mã hoá văn bản (`baseline_eval.ipynb`)

| Biểu diễn | Mô tả |
|------------|-------|
| One-Hot | Binary `CountVectorizer` (3 000 features) |
| CountVectorizer | Bag-of-Words tần suất (6 000 features) |
| N-grams (1,2) | Unigram + bigram (12 000 features) |
| Hashing | `HashingVectorizer` không cần fit (2¹⁴ buckets) |
| TF-IDF | Unigram + bigram có trọng số (12 000 features) |

### Mô hình baseline

- Naive Bayes (`MultinomialNB`)
- Logistic Regression (`max_iter=1200`)
- Linear SVM (`LinearSVC`)

**Metrics:** Accuracy, Precision/Recall/F1 (weighted)

---

## Kết quả nổi bật

| Biểu diễn | Mô hình | Accuracy | F1-weighted |
|------------|---------|----------|-------------|
| One-Hot | LinearSVM | **0.9906** | **0.9889** |
| TF-IDF | LinearSVM | 0.9899 | 0.9878 |
| One-Hot | NaiveBayes | 0.9884 | 0.9873 |

> **Bài toán phân loại:** nguồn văn bản (`youtube` vs `voz`).  
> Nếu có nhãn nghiệp vụ khác (cảm xúc / chủ đề), thay cột `source` bằng cột nhãn mới là đủ.

---

## Ghi chú

- **Mất cân bằng nhãn**: YouTube (~6 787) >> VOZ (~118) → kết quả metric có thể lạc quan, cần diễn giải cẩn thận.
- **Tokenizer**: ưu tiên `underthesea` → `pyvi` → `basic split()` (tự động fallback).
- **Stopwords**: mặc định **không lọc** để giữ toàn bộ ngữ nghĩa; bật cờ `remove_stopwords=True` khi cần tối ưu mô hình.
- **Từ điển chuẩn hoá**: tách thành `safe_map` (dùng mọi ngôn ngữ) và `vi_only_map` (chỉ áp dụng khi ngôn ngữ là `vi`/`mixed`) để tránh phá câu tiếng Anh.
