# Vietnamese NLP Pipeline (VOZ + YouTube)

Pipeline nay su dung du lieu da crawl san tu:
- `yt_comments.csv`
- `voz_threads_comments.csv`

## Chuc nang

1. Tien xu ly van ban tieng Viet
- chuyen chu thuong
- xoa URL, dau cau, ky tu dac biet
- chuan hoa teencode/viet tat theo tu dien quy tac
- sua loi chinh ta pho bien theo rule-based map
- tach tu (underthesea)
- loai stopwords
- lemmatization + light stemming rule-based

2. EDA
- thong ke so mau theo nguon
- thong ke do dai van ban
- top token pho bien
- xuat bieu do

3. Ma hoa du lieu
- One-hot (binary CountVectorizer)
- Count Vectorizer
- N-grams (1-2)
- Co-occurrence matrix
- Hashing Vectorizer
- TF-IDF
- Word Embedding (Word2Vec)

4. Baseline ML
- Naive Bayes
- Logistic Regression
- Linear SVM

## Cai dat

```bash
python -m pip install -r requirements.txt
```

## Chay pipeline

```bash
python src/run_nlp_pipeline.py
```

## Dau ra

Tat ca file ket qua nam trong thu muc `outputs/`:
- `cleaned_dataset.csv`
- `eda_summary.json`
- `eda_source_distribution.png`
- `eda_token_length_hist.png`
- `cooccurrence_matrix.csv`
- `vectorizer_shapes.json`
- `baseline_results.csv`

## Luu y

- Bai toan baseline trong script hien tai la phan loai nguon van ban (`youtube` vs `voz`) de co nhanh bo danh gia supervised.
- Neu ban co nhan muc tieu khac (cam xuc/chu de), chi can thay cot `source` bang cot nhan moi.
