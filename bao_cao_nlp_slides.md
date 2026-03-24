---
marp: true
theme: default
paginate: true
title: Bao cao de tai NLP tieng Viet
---

# Chuẩn hóa văn bản tiếng Việt và tiền xử lý dữ liệu NLP

- Nguồn dữ liệu: VOZ + YouTube
- Mục tiêu: làm sạch dữ liệu tiếng Việt, mã hóa văn bản, xây dựng baseline
- Nhóm bài toán chọn để đánh giá: phân loại nguồn văn bản (youtube vs voz)

---

# Agenda

- Bối cảnh và mục tiêu
- Dữ liệu và cách thu thập
- Pipeline tiền xử lý
- Mã hóa văn bản
- Baseline và đánh giá
- Hạn chế, cải tiến và kết luận

---

# 1. Mục tiêu đề tài

- Crawl dữ liệu bình luận/bài viết tiếng Việt từ 2 nguồn
- Chuẩn hóa văn bản mạng xã hội: teencode, viết tắt, không dấu, ký tự nhiễu
- Tiền xử lý phục vụ NLP: tokenization, stopword, chuẩn hóa từ vựng
- So sánh các phương pháp mã hóa văn bản
- Huấn luyện và đánh giá mô hình baseline

---

# 2. Bối cảnh bài toán

- Văn bản mạng xã hội tiếng Việt có nhiều nhiễu:
  - Teencode, viết tắt, không dấu
  - Emoji, HTML tag, URL, ký tự đặc biệt
  - Trộn tiếng Anh và tiếng Việt
- Nếu không chuẩn hóa tốt:
  - Tách từ sai
  - Từ vựng phân mảnh
  - Mô hình học kém ổn định

---

# 3. Dữ liệu đầu vào

- File nguồn sử dụng:
  - yt_comments.csv
  - voz_threads_comments.csv
- Sau bootstrap + làm sạch: 6905 mẫu
- Phân bố nguồn:
  - YouTube: 6787
  - VOZ: 118
- Phân bố ngôn ngữ sau detect:
  - vi: 6845
  - en: 57
  - mixed: 3

Ghi chú: dữ liệu mất cân bằng mạnh giữa 2 nguồn.

---

# 4. Quy mô dữ liệu sau xử lý

- Tổng mẫu sau tiền xử lý: 6905
- Tỷ lệ ngôn ngữ:
  - Tiếng Việt: 6845 (99.1%)
  - Tiếng Anh: 57 (0.8%)
  - Mixed: 3 (0.1%)
- Độ dài trung bình: 9.95 token/mẫu

Ý nghĩa: dữ liệu đủ lớn để benchmark baseline dạng sparse feature.

---

# 5. Kiến trúc pipeline tổng quát

- Chuẩn hóa unicode (NFC), lower-case
- Làm sạch HTML/URL/mention/hashtag/timestamp
- Phát hiện ngôn ngữ (vi, en, mixed)
- Chuẩn hóa teencode + viết tắt bằng normalization_map
- Tách câu trước khi tách từ
- Tokenize bằng underthesea (vi), split cho en
- Hậu xử lý token nhiễu
- Tùy chọn lọc stopwords cho mục tiêu modeling

---

# 6. Luồng xử lý chi tiết

1. Nhập dữ liệu gốc (YouTube + VOZ)
2. Tạo cột source và raw_text
3. Phát hiện ngôn ngữ từng dòng
4. Chuẩn hóa teencode + viết tắt
5. Tách câu -> tách từ
6. Hậu xử lý token (lọc nhiễu, hậu tố)
7. Xuất cleaned_dataset_fixed.csv
8. Chạy EDA + baseline

---

# 7. Chuẩn hóa từ điển tiếng Việt

- Từ điển map đã mở rộng:
  - safe map: 159 mục
  - vi-only map: 10 mục
- Ví dụ chuẩn hóa:
  - ko, k, hk, hok -> không
  - đc, dc, dk -> được
  - ae -> anh em
  - mn -> mọi người
  - youtobe -> youtube
- Tách riêng map vi-only để tránh phá câu tiếng Anh (ví dụ t -> tôi)

  ---

  # 8. Ví dụ chuẩn hóa thực tế

  - Input:
    - Không đeo dưởng khí sao mà giỏi quá các bạn
  - Sau chuẩn hóa:
    - không đeo dưỡng_khí sao mà giỏi quá các bạn
  - Token:
    - [không, đeo, dưỡng_khí, sao, mà, giỏi, quá, các, bạn]

  Điểm chính: giữ đủ token, không làm mất nghĩa ngữ cảnh.

---

  # 9. Xử lý lỗi tách từ thường gặp

- Vấn đề gặp thực tế:
  - Token merge sai qua dấu chấm: sang_năm
  - Token chat bị dính hậu tố: khỏe_nha
  - Mất từ do lọc quá sớm
- Cách khắc phục:
  - Tách câu trước tokenize
  - Chuẩn hóa cụm từ trước tokenize
  - Giữ token đầy đủ mặc định, chỉ lọc stopwords khi cần mô hình

Ví dụ cải thiện:
- Input: Không đeo dưởng khí sao mà giỏi quá các bạn
- Token sau sửa: [không, đeo, dưỡng_khí, sao, mà, giỏi, quá, các, bạn]

---

# 10. Stopwords: khi nào dùng, khi nào không

- Trong bước kiểm tra chất lượng tách từ:
  - Giữ full token (không loại stopwords)
- Trong bước huấn luyện baseline:
  - Có thể bật remove_stopwords để giảm nhiễu
- Bài học:
  - Nên tách 2 mục tiêu: phân tích ngôn ngữ vs tối ưu mô hình

---

# 11. EDA sau tiền xử lý

- Số mẫu cuối: 6905
- Độ dài token trung bình: 9.95 token/mẫu
- Tổng số token có dấu gạch dưới: 9313
- Số loại token ghép: 3508

Top token xuất hiện nhiều (tham khảo):
- chị, ăn, không, quá, em, quỳnh, mà, cô, là, có, nhìn, được, con, ngon, xem

---

# 12. Ý nghĩa EDA

- Token ghép nhiều -> dữ liệu hội thoại tự nhiên, giàu ngữ cảnh
- Tần suất cao của token cảm xúc/ngữ khí (quá, ngon, xem...)
- Phân bố nguồn lệch -> cần lưu ý khi diễn giải độ chính xác
- Ngôn ngữ gần như tiếng Việt thuần sau bước chuẩn hóa

---

# 13. Các file output chính

- outputs/cleaned_dataset.csv
- outputs/cleaned_dataset_fixed.csv
- outputs/pipeline_report.json
- outputs/pipeline_report.png
- outputs/baseline_results.csv

Mục tiêu: đảm bảo tính tái lập và truy vết toàn bộ pipeline.

---

# 14. Mã hóa văn bản đã thực hiện

- One-Hot (binary CountVectorizer)
- Count Vectorizer
- N-grams (1,2)
- Hashing Vectorizer
- TF-IDF
- Co-occurrence matrix (đã có trong pipeline phân tích)
- Word Embedding (đã có trong pipeline trước đó)

Ghi chú: bản đánh giá hiện tại tập trung nhóm vectorizer sparse cho baseline ổn định.

---

# 15. So sánh nhanh các kỹ thuật mã hóa

- One-Hot:
  - Đơn giản, mạnh cho baseline
- Count:
  - Bảo toàn tần suất từ
- N-gram:
  - Bắt được cụm 2 từ
- TF-IDF:
  - Giảm ảnh hưởng từ quá phổ biến
- Hashing:
  - Nhanh, tiết kiệm bộ nhớ
- Embedding:
  - Biểu diễn ngữ nghĩa tốt hơn (khi mở rộng mô hình)

---

# 16. Co-occurrence matrix dùng để làm gì

- Phân tích từ đồng xuất hiện trong cùng ngữ cảnh
- Hỗ trợ khám phá chủ đề và cụm từ
- Có thể dùng cho:
  - trực quan hóa mạng từ
  - feature engineering bổ sung
  - kiểm tra chất lượng chuẩn hóa từ điển

---

# 17. Baseline mô hình

- Naive Bayes
- Logistic Regression
- Linear SVM

Nhãn bài toán: source (youtube, voz)
- Đây là baseline kỹ thuật để so sánh pipeline xử lý và biểu diễn dữ liệu
- Có thể thay bằng nhãn nghiệp vụ khác (sentiment/topic) khi có dữ liệu gán nhãn

---

# 18. Thiết lập đánh giá

- Chia tập train/test có stratify theo source
- Metrics báo cáo:
  - Accuracy
  - Precision weighted
  - Recall weighted
  - F1-weighted
- Tiêu chí chọn mô hình: ưu tiên F1-weighted, sau đó Accuracy

---

# 19. Kết quả đánh giá (baseline)

Top kết quả (outputs/baseline_results.csv):
- OneHot + LinearSVM:
  - Accuracy: 0.9906
  - F1-weighted: 0.9889
- TFIDF + LinearSVM:
  - Accuracy: 0.9899
  - F1-weighted: 0.9878
- OneHot + NaiveBayes:
  - Accuracy: 0.9884
  - F1-weighted: 0.9873

Nhận xét nhanh:
- LinearSVM cho hiệu năng tốt và ổn định nhất trên dữ liệu hiện tại.

---

# 20. Bảng top mô hình (rút gọn)

- OneHot + LinearSVM: F1 = 0.9889
- TFIDF + LinearSVM: F1 = 0.9878
- OneHot + NaiveBayes: F1 = 0.9873
- Ngrams(1,2) + LinearSVM: F1 = 0.9867
- Count + LinearSVM: F1 = 0.9861

Kết luận: mô hình tuyến tính trên đặc trưng sparse phù hợp với tập dữ liệu này.

---

# 21. Giải thích kết quả

- OneHot/TF-IDF + LinearSVM mạnh với dữ liệu text sparse
- Naive Bayes vẫn cạnh tranh tốt trên dữ liệu từ vựng cao chiều
- Dữ liệu lệch nhãn lớn (youtube >> voz) làm kết quả có thể lạc quan

Điểm cần lưu ý:
- Bài toán hiện tại là phân loại nguồn, chưa phản ánh đầy đủ bài toán cảm xúc/chủ đề.

---

# 22. Error analysis ngắn

- Nhóm lỗi còn lại:
  - Comment không dấu khó tách từ chính xác
  - Comment pha Anh-Việt
  - Từ lóng mới chưa có trong normalization_map
- Tác động:
  - Tăng số token hiếm
  - Giảm tính nhất quán giữa các biến thể từ

---

# 23. Hạn chế hiện tại

- Mất cân bằng dữ liệu rất lớn giữa YouTube và VOZ
- Còn câu tiếng Anh/mixed trong tập dữ liệu
- Văn bản không dấu, teencode cực đoan vẫn gây nhiễu tách từ
- Chưa có bộ nhãn nghiệp vụ (positive/negative/topic) để đánh giá thực tế hơn

---

# 24. Hướng phát triển

- Tăng dữ liệu VOZ để cân bằng nhãn
- Bổ sung bước phục hồi dấu tiếng Việt cho text không dấu
- Thiết kế bộ từ điển domain-specific theo chủ đề
- Thu thập/gán nhãn sentiment hoặc topic để đánh giá đúng bài toán NLP ứng dụng
- Thử mô hình nâng cao:
  - fastText
  - PhoBERT fine-tuning
  - SVM với class_weight

---

# 25. Kế hoạch triển khai tiếp theo

- Giai đoạn 1: cân bằng dữ liệu + lọc chất lượng comment
- Giai đoạn 2: gán nhãn sentiment/topic
- Giai đoạn 3: benchmark baseline vs PhoBERT
- Giai đoạn 4: đóng gói pipeline thành script tái sử dụng

Mục tiêu: chuyển từ demo kỹ thuật sang bài toán NLP ứng dụng thực tế.

---

# 26. Kết luận

- Đã hoàn thành pipeline thu thập và chuẩn hóa dữ liệu tiếng Việt từ 2 nguồn
- Đã thực hiện đầy đủ các nhóm mã hóa văn bản quan trọng
- Baseline cho kết quả cao trên bài toán phân loại nguồn (best Accuracy 0.9906)
- Pipeline sẵn sàng mở rộng sang bài toán có nhãn thực tế (sentiment/topic)

---

# 27. Tài nguyên kết quả

- outputs/cleaned_dataset.csv
- outputs/cleaned_dataset_fixed.csv
- outputs/pipeline_report.json
- outputs/pipeline_report.png
- outputs/baseline_results.csv
- src/run_nlp_pipeline.py
- src/run_baseline_eval.py

Xin cảm ơn.

---

# Q&A

Xin cảm ơn thầy/cô và các bạn.
Sẵn sàng trao đổi thêm về:
- Chi tiết pipeline
- Cách mở rộng dữ liệu
- Cách chuyển sang bài toán sentiment/topic
