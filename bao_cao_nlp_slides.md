---
marp: true
theme: default
paginate: true
style: |
  section {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 22px;
    color: #1a1a2e;
    background: #ffffff;
  }
  section.cover {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
    color: #ffffff;
  }
  section.cover h1 { font-size: 38px; color: #e94560; margin-bottom: 8px; }
  section.cover p  { color: #a8b2d8; font-size: 18px; }
  h1 { color: #0f3460; font-size: 30px; border-bottom: 3px solid #e94560; padding-bottom: 6px; }
  h2 { color: #16213e; font-size: 22px; }
  table { width: 100%; border-collapse: collapse; font-size: 18px; }
  th { background: #0f3460; color: #fff; padding: 6px 10px; }
  td { padding: 5px 10px; border-bottom: 1px solid #ddd; }
  tr:nth-child(even) td { background: #f0f4ff; }
  code { background: #f4f6ff; border-radius: 4px; padding: 1px 5px; color: #e94560; }
  blockquote { border-left: 4px solid #e94560; padding-left: 12px; color: #555; font-style: italic; }
  .highlight { color: #e94560; font-weight: bold; }
---

<!-- _class: cover -->

# Chuẩn hoá văn bản tiếng Việt<br>& Tiền xử lý dữ liệu NLP

**Nguồn dữ liệu:** VOZ Forum + YouTube Comments

> Xây dựng pipeline từ dữ liệu thô → baseline phân loại văn bản

---

# Agenda

1. 🎯 Mục tiêu & bối cảnh bài toán
2. 📦 Thu thập & tổng quan dữ liệu
3. ⚙️ Pipeline tiền xử lý
4. 🔤 Mã hoá văn bản (5 phương pháp)
5. 📊 Baseline & kết quả đánh giá
6. ⚠️ Hạn chế & hướng phát triển

---

# 1. Mục tiêu đề tài

- **Thu thập** dữ liệu bình luận tiếng Việt từ 2 nguồn (VOZ, YouTube)
- **Chuẩn hoá** văn bản mạng xã hội:
  - Teencode, viết tắt, chữ không dấu
  - Ký tự nhiễu: emoji, HTML tag, URL, timestamp
- **Tiền xử lý NLP**: tokenisation, chuẩn hoá từ vựng, phát hiện ngôn ngữ
- **So sánh** 5 phương pháp mã hoá văn bản
- **Huấn luyện & đánh giá** mô hình baseline (3 thuật toán)

---

# 2. Bối cảnh bài toán

**Tại sao văn bản mạng xã hội tiếng Việt khó xử lý?**

| Vấn đề | Ví dụ thực tế |
|--------|---------------|
| Teencode / viết tắt | `ko` → không, `đc` → được, `mn` → mọi người |
| Chữ không dấu | `khong` → không, `duoc` → được |
| Lặp ký tự | `đẹppppp` → đẹpp |
| HTML / URL | `<br>`, `https://...` |
| Trộn Anh-Việt | *"video này hay quá lol"* |
| Đại từ chat | `a` → anh, `e` → em, `t` → tôi |

> Nếu không chuẩn hoá → tách từ sai → từ vựng phân mảnh → mô hình kém

---

# 3. Dữ liệu đầu vào

**File nguồn:**
- `yt_comments.csv` — bình luận YouTube
- `voz_threads_comments.csv` — bài viết / bình luận VOZ

**Sau tiền xử lý:**

| Chỉ số | Giá trị |
|--------|---------|
| Tổng mẫu hợp lệ | **6 905** |
| YouTube | 6 787 (98.3%) |
| VOZ | 118 (1.7%) |
| Tiếng Việt (`vi`) | 6 845 (99.1%) |
| Tiếng Anh (`en`) | 57 (0.8%) |
| Mixed | 3 (0.1%) |
| Độ dài TB | **9.95 token/mẫu** |

> ⚠️ **Mất cân bằng lớn** giữa 2 nguồn — cần lưu ý khi diễn giải kết quả

---

# 4. Kiến trúc pipeline tổng quát

```
Dữ liệu thô (yt_comments + voz)
        │
        ▼
[1] Chuẩn hoá Unicode NFC + lower-case
        │
        ▼
[2] Làm sạch: HTML / URL / mention / hashtag / timestamp
        │
        ▼
[3] Phát hiện ngôn ngữ  →  vi / en / mixed
        │
        ▼
[4] Chuẩn hoá cụm từ + đại từ chat  (chỉ vi/mixed)
        │
        ▼
[5] Ánh xạ teencode / viết tắt  (safe_map + vi_only_map)
        │
        ▼
[6] Tách câu  →  Tách từ  (underthesea / pyvi / basic)
        │
        ▼
[7] Hậu xử lý token: lọc nhiễu, hậu tố, token quá ngắn
        │
        ▼
  cleaned_dataset_fixed.csv
```

---

# 5. Từ điển chuẩn hoá teencode

Tách thành **2 bản đồ** để tránh phá câu tiếng Anh:

| Bản đồ | Áp dụng khi | Ví dụ |
|--------|------------|-------|
| `safe_map` (23+ mục) | Mọi ngôn ngữ | `ko→không`, `dc→được`, `ae→anh em` |
| `vi_only_map` (9 mục) | Chỉ `vi` / `mixed` | `t→tôi`, `a→anh`, `e→em` |

**Một số mục tiêu biểu:**

```
ko, kg, hk, hok  →  không        dc, đc, dk  →  được
mn, mng          →  mọi người    cx, cug     →  cũng
youtobe          →  youtube      oke, okie   →  ổn
ntn              →  như thế nào  ae          →  anh em
```

---

# 6. Phát hiện ngôn ngữ

Dùng **rule-based heuristic** (không cần model):

```python
# Có ký tự có dấu tiếng Việt (à, ă, â, đ, ê, ô, ơ, ư…)?
has_vi = bool(VI_CHAR_PAT.search(text))

# Đếm từ tiếng Anh phổ biến
en_word_count = sum(1 for w in words if w in EN_STOPWORDS)

# Quy tắc phân loại
if has_vi and en_word_count < 3:   return "vi"
if not has_vi and en_count >= 2:   return "en"
if has_vi and en_count >= 3:       return "mixed"
```

**Kết quả:** 99.1% vi → phù hợp với đặc trưng dữ liệu

---

# 7. Tokenisation

**Thứ tự ưu tiên (tự động fallback):**

```
1. underthesea  →  word_tokenize(sent, format="text")
2. pyvi         →  ViTokenizer.tokenize(sent)
3. basic        →  sent.split()
```

**Quy trình:** Tách câu trước → tách từ từng câu → clean token

**Vấn đề thường gặp & cách xử lý:**

| Vấn đề | Ví dụ | Cách xử lý |
|--------|-------|-----------|
| Token dính hậu tố chat | `khỏe_nha` | Cắt hậu tố `_nha`, `_nhé`, `_ạ`… |
| Token lặp ký tự | `đẹppppp` | Regex `(.)\\1{2,}` → `đẹpp` |
| Token merge qua dấu chấm | `sang_năm` | Ánh xạ → `sang` |
| Đại từ đơn chữ cái ASCII | `a`, `e` | Lọc nếu `len ≤ 1 and isascii()` |

---

# 8. Ví dụ chuẩn hoá thực tế

**Input gốc:**
> *"Mn oi ko đeo dưởng khí sao mà giỏi z vl ae oi"*

**Sau chuẩn hoá từng bước:**

| Bước | Kết quả |
|------|---------|
| Lower + Unicode NFC | `mn oi ko đeo dưởng khí sao mà giỏi z vl ae oi` |
| Cụm từ + đại từ | `mọi người ơi ko đeo dưỡng khí sao mà giỏi vậy rất anh em ơi` |
| Ánh xạ teencode | `mọi người ơi không đeo dưỡng khí sao mà giỏi vậy rất anh em ơi` |
| Tách từ (underthesea) | `mọi_người ơi không đeo dưỡng_khí sao mà giỏi vậy rất anh_em ơi` |
| Hậu xử lý | `mọi_người không đeo dưỡng_khí sao mà giỏi vậy rất anh_em` |

---

# 9. EDA sau tiền xử lý

**Thống kê tổng quan:**

| Chỉ số | Giá trị |
|--------|---------|
| Tổng mẫu cuối | 6 905 |
| Độ dài trung bình | 9.95 token/mẫu |
| Tổng token có dấu gạch dưới | 9 313 |
| Số loại token ghép (unique) | 3 508 |

**Top token xuất hiện nhiều nhất:**

> `không` · `có` · `là` · `em` · `chị` · `ăn` · `quá` · `ngon` · `xem` · `được` · `mà` · `con` · `cô` · `nhìn`

→ Token cảm xúc, ngữ khí chiếm tần suất cao → phù hợp bài toán phân tích cảm xúc

---

# 10. Mã hoá văn bản – Tổng quan

| Phương pháp | Features | Đặc điểm |
|-------------|----------|-----------|
| **One-Hot** (Binary BoW) | 3 000 | Không quan tâm tần suất |
| **Count Vectorizer** | 6 000 | Bảo toàn tần suất từ |
| **N-grams (1,2)** | 12 000 | Bắt được cụm 2 từ |
| **Hashing Vectorizer** | 16 384 | Nhanh, không cần `fit` |
| **TF-IDF (1,2)** | 12 000 | Giảm trọng số từ quá phổ biến |

> ℹ️ `HashingVectorizer` không cần `fit()` — dùng `transform()` trực tiếp cho cả train lẫn test

---

# 11. Mô hình baseline & thiết lập đánh giá

**3 thuật toán được đánh giá:**
- 🔵 **Naive Bayes** (`MultinomialNB`) — nhanh, phù hợp dữ liệu sparse
- 🟢 **Logistic Regression** (`max_iter=1200`) — ổn định, diễn giải được
- 🔴 **Linear SVM** (`LinearSVC`) — mạnh với không gian cao chiều

**Thiết lập:**

```python
train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
```

**Metrics báo cáo:** Accuracy · Precision · Recall · **F1-weighted** *(ưu tiên)*

---

# 12. Kết quả baseline

| Biểu diễn | Mô hình | Accuracy | F1-weighted |
|------------|---------|----------|-------------|
| **One-Hot** | **LinearSVM** | **0.9906** | **0.9889** |
| TF-IDF | LinearSVM | 0.9899 | 0.9878 |
| One-Hot | NaiveBayes | 0.9884 | 0.9873 |
| N-grams(1,2) | LinearSVM | 0.9877 | 0.9867 |
| Count | LinearSVM | 0.9870 | 0.9861 |
| TF-IDF | LogisticReg | 0.9863 | 0.9850 |
| Hashing | LinearSVM | 0.9856 | 0.9843 |

> 🏆 **One-Hot + LinearSVM** đứng đầu — Accuracy 0.9906, F1 0.9889

---

# 13. Phân tích kết quả

**Nhận xét:**

- **LinearSVM** cho kết quả tốt nhất và ổn định nhất trên mọi biểu diễn
- **Naive Bayes** cạnh tranh tốt — phù hợp dữ liệu text sparse nhiều chiều
- **Logistic Regression** kết quả tốt nhưng chậm hơn SVM
- One-Hot và TF-IDF cho kết quả tương đương → từ vựng phân biệt nguồn tốt

**Lưu ý quan trọng:**

> ⚠️ Bài toán là **phân loại nguồn** (`youtube` vs `voz`) — nhãn dễ phân biệt do phong cách viết khác nhau. Kết quả cao **không phản ánh** hiệu năng với bài toán cảm xúc/chủ đề thực tế.

---

# 14. Error analysis

**Nhóm lỗi còn lại:**

| Nhóm | Mô tả |
|------|-------|
| văn bản không dấu cực đoan | Tokeniser không nhận diện → tách sai |
| Pha Anh-Việt cao | Token nhiễu tiếng Anh lọt qua |
| Teencode mới | Không có trong `normalization_map.json` |
| Nhãn lệch | VOZ chiếm < 2% → model thiên lệch |

---

# 15. Hạn chế hiện tại

- 📉 **Mất cân bằng nghiêm trọng**: YouTube 98.3% vs VOZ 1.7%
- 🔤 **Văn bản không dấu** chưa được phục hồi tự động
- 📚 **Từ điển teencode** chưa đủ — thiếu slang mới
- 🏷️ **Chưa có nhãn nghiệp vụ** (cảm xúc / chủ đề) → chỉ đánh giá proxy
- 🤖 **Chưa thử pre-trained embedding** (PhoBERT, fastText-vi)

---

# 16. Hướng phát triển

**Ngắn hạn:**
- Thu thập thêm dữ liệu VOZ để cân bằng nhãn
- Tích hợp bước **phục hồi dấu** (VnCoreNLP accent restoration)
- Mở rộng `normalization_map.json` theo domain

**Dài hạn:**
- Gán nhãn **sentiment / topic** để đánh giá bài toán thực tế
- Benchmark với:
  - **fastText** (embedding tiếng Việt)
  - **PhoBERT** fine-tuning
  - SVM với `class_weight='balanced'`
- Đóng gói pipeline thành REST API hoặc Python package

---

# 17. Kết luận

✅ Đã xây dựng pipeline **thu thập → chuẩn hoá → mã hoá → đánh giá** hoàn chỉnh

✅ Xử lý tốt các đặc thù tiếng Việt mạng xã hội: teencode, đại từ chat, token nhiễu

✅ **5 phương pháp mã hoá** + **3 mô hình baseline** → tổng 15 kịch bản đánh giá

✅ Best accuracy: **0.9906** (One-Hot + LinearSVM)

✅ Pipeline sẵn sàng mở rộng sang nhãn sentiment / topic

---

# File đầu ra

| File | Mô tả |
|------|-------|
| `outputs/cleaned_dataset.csv` | Dữ liệu gốc sau bootstrap |
| `outputs/cleaned_dataset_fixed.csv` | Dữ liệu đã tiền xử lý đầy đủ |
| `outputs/pipeline_report.json` | Báo cáo thống kê pipeline |
| `outputs/pipeline_report.png` | Biểu đồ phân bố dữ liệu |
| `outputs/baseline_results.csv` | Kết quả đánh giá 15 kịch bản |
| `src/nlp_pipeline/nlp_pipeline.ipynb` | Notebook pipeline (10 cells) |
| `src/nlp_pipeline/baseline_eval.ipynb` | Notebook baseline (10 cells) |

---

# Q&A

## Xin cảm ơn thầy/cô và các bạn đã lắng nghe!

Sẵn sàng trao đổi thêm về:

- 🔧 Chi tiết kỹ thuật pipeline
- 📊 Cách diễn giải kết quả với dữ liệu lệch nhãn
- 🚀 Hướng mở rộng sang PhoBERT / sentiment analysis
