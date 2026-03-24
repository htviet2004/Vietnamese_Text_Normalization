"""
PHÂN TÍCH cleaned_dataset.csv — 4 Vấn Đề Thực Tế
===================================================

Sau khi đọc toàn bộ 4300 rows của cleaned_dataset.csv, mình tìm ra:

╔══════════════════════════════════════════════════════════════════╗
║  VẤN ĐỀ 1 — DẤU GẠCH DƯỚI _                                   ║
║  Phần lớn là ĐÚNG, một số trường hợp sai                       ║
╚══════════════════════════════════════════════════════════════════╝

underthesea dùng _ để đánh dấu từ ghép tiếng Việt. Đây là hành vi ĐÚNG:
  ✓ quảng_cáo, gia_đình, sức_khỏe, cảm_ơn, anh_em, bình_thường
  ✓ cuộc_sống, thành_công, hạnh_phúc, thu_nhập, công_việc

Các trường hợp SAI (kết hợp nhầm do text chưa được khôi phục dấu):
  ✗ a_chua (57 rows) — "a chua" = "a chưa", chua không dấu -> ghép nhầm
  ✗ sang_năm (2 rows) — "Sang. Năm mới" bị merge qua dấu chấm
  ✗ nha_a (4 rows)   — "nha a Sang" bị merge
  ✗ video_a (7 rows) — "video a Sang" bị merge

Nguyên nhân: tokenizer nhận input chưa tách câu đúng cách.

╔══════════════════════════════════════════════════════════════════╗
║  VẤN ĐỀ 2 — don't -> "don tôi"                                ║
║  268 comment tiếng Anh (5.6%) bị xử lý nhầm                   ║
╚══════════════════════════════════════════════════════════════════╝

Chuỗi xử lý sai:
  "don't" -> xóa apostrophe -> "don t" -> map 't' -> 'tôi' -> "don tôi"
  "it's"  -> "it s" -> "it s" (may mắn 's' không trong map)

Nguyên nhân: normalization_map.json có entry 't' -> 'toi' (tôi)
Map này hợp lý cho tiếng Việt ("t hay ăn" = "tôi hay ăn")
Nhưng phá tiếng Anh.

FIX: Phát hiện ngôn ngữ trước khi áp map.

╔══════════════════════════════════════════════════════════════════╗
║  VẤN ĐỀ 3 — Văn bản KHÔNG DẤU chưa được khôi phục            ║
║  146 rows bị ảnh hưởng                                         ║
╚══════════════════════════════════════════════════════════════════╝

Ví dụ thực tế trong data:
  "cai gi ko noi dc thi nen cat video khuc do di sang oi"
  "da tung di vao suoi, nuoc suoi lanh kinh luon"
  "Sang lam video voi may anh lam phim coi hap dan qua"

Các text này:
  1. Không có ký tự có dấu tiếng Việt
  2. Pipeline hiện tại không khôi phục dấu -> từ ghép không được nhận dạng đúng
  3. underthesea sẽ tokenize sai (không nhận ra từ tiếng Việt không dấu)

FIX cần thiết:
  Option A: Dùng thư viện khôi phục dấu (visen, vinorm) — cần cài thêm
  Option B: Chỉ áp normalization_map (ko->không, dc->được) — đã làm một phần
  Option C: Flag các row này để xử lý riêng hoặc bỏ qua

╔══════════════════════════════════════════════════════════════════╗
║  VẤN ĐỀ 4 — Tách câu trước khi tokenize                       ║
║  Gây ra các lỗi sang_năm, nha_a, video_a                       ║
╚══════════════════════════════════════════════════════════════════╝

"Em không có bỏ qua quảng cáo nha a Sang. Năm mới chúc..."
                                              ^
                    Dấu chấm không ngăn tokenizer ghép "Sang" với "Năm"

FIX: sent_tokenize (tách câu) trước word_tokenize.
"""

from __future__ import annotations

import re
import unicodedata
import html as html_module
import json
import ast
import logging
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ═══════════════════════════════════════════════════════════════════════════════
# PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

HTML_TAG      = re.compile(r"<[^>]+>")
URL_PAT       = re.compile(r"https?://\S+|www\.\S+")
MENTION       = re.compile(r"@[\w_]+")
HASHTAG       = re.compile(r"#[\w_]+")
TIMESTAMP     = re.compile(r"\b\d{1,2}:\d{2}\b")
REPEATED      = re.compile(r"(.)\1{2,}")
MULTI_SP      = re.compile(r"\s+")
SENT_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀÁẢÃẠĂẮẶẲẴÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ])")
VI_CHAR_PAT   = re.compile(r"[àáảãạăắặẳẵâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵÀÁẢÃẠĂẮẶẲẴÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ]")
EN_WORD_PAT   = re.compile(r"\b[a-zA-Z]{2,}\b")

UNICODE_KEEP  = re.compile(
    r"[^\u0041-\u007A\u00C0-\u024F\u1E00-\u1EFF\u0300-\u036F"
    r"\u0110\u0111\u0128\u0129\u01A0\u01A1\u01AF\u01B0"
    r"0-9\s\.!\?…]",
    re.UNICODE,
)

# ═══════════════════════════════════════════════════════════════════════════════
# LANGUAGE DETECTION — FIX cho vấn đề don't -> tôi
# ═══════════════════════════════════════════════════════════════════════════════

# Stopwords tiếng Anh thường gặp (dùng để phát hiện EN comment)
EN_STOPWORDS = {
    "the", "is", "are", "was", "were", "have", "has", "had",
    "this", "that", "these", "those", "you", "your", "with",
    "from", "they", "them", "their", "what", "which", "who",
    "will", "would", "could", "should", "can", "not", "don",
    "fish", "why", "how", "when", "where", "then", "than",
    "all", "for", "and", "but", "or", "so", "if", "it",
}

def detect_language(text: str) -> str:
    """
    Phát hiện ngôn ngữ đơn giản dựa trên ký tự tiếng Việt và từ tiếng Anh.
    Trả về: 'vi', 'en', hoặc 'mixed'
    """
    if not text or len(text.strip()) < 3:
        return "vi"

    has_vi = bool(VI_CHAR_PAT.search(text))

    # Đếm từ tiếng Anh
    words_lower = text.lower().split()
    en_word_count = sum(1 for w in words_lower if w in EN_STOPWORDS)
    total_words = len(words_lower)

    if has_vi and en_word_count < 3:
        return "vi"
    if not has_vi and en_word_count >= 2:
        return "en"
    if has_vi and en_word_count >= 3:
        return "mixed"
    return "vi"

# ═══════════════════════════════════════════════════════════════════════════════
# NORMALIZATION MAP — tách riêng VI và EN
# ═══════════════════════════════════════════════════════════════════════════════

# Map chỉ áp dụng cho text tiếng Việt (tránh làm hỏng tiếng Anh)
VI_ONLY_MAP: Dict[str, str] = {
    # Từ ngắn 1-2 ký tự — nguy hiểm cho tiếng Anh
    "t":   "tôi",      # "t hay ăn" -> "tôi hay ăn"
    "a":   "anh",
    "e":   "em",
    "m":   "mình",
    "k":   "không",
    "r":   "rồi",
    "j":   "gì",
    "v":   "vậy",
    "h":   "giờ",
}

# Map an toàn cho cả VI và EN (từ dài hơn, không trùng EN)
SAFE_MAP: Dict[str, str] = {
    "ko":    "không",    "kg":    "không",   "khg":   "không",
    "hok":   "không",    "hong":  "không",   "hông":  "không",
    "hem":   "không",    "hk":    "không",
    "dc":    "được",     "đc":    "được",    "dk":    "được",    "đk": "được",
    "bik":   "biết",     "bít":   "biết",
    "mik":   "mình",     "mk":    "mình",
    "thui":  "thôi",     "thoy":  "thôi",
    "cx":    "cũng",     "cug":   "cũng",
    "chx":   "chưa",
    "z":     "vậy",      "zậy":   "vậy",
    "đr":    "rồi",      "rùi":   "rồi",
    "ntn":   "như thế nào",
    "mn":    "mọi người","mng":   "mọi người",
    "ae":    "anh em",
    "yt":    "youtube",  "youtobe": "youtube",
    "vl":    "rất",      "vcl":   "rất",
    "bt":    "bình thường",
    "nma":   "nhưng mà",
    "đag":   "đang",     "đangg": "đang",
    "okie":  "ổn",       "oke":   "ổn",      "okela": "ổn",
    "iu":    "yêu",
    "ny":    "người yêu",
    "nv":    "nhân viên",
    "cmt":   "bình luận","ib":    "nhắn tin",
}

def load_normalization_map(path: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Đọc external map và phân loại:
    - safe_map: áp dụng cho mọi ngôn ngữ
    - vi_only_map: chỉ áp dụng cho text tiếng Việt

    FIX: Entry 't' -> 'tôi' chỉ áp dụng cho VI text
    FIX: Tất cả target về dạng có dấu NFC
    """
    NODIAC = {
        "khong": "không", "duoc": "được", "roi": "rồi", "thoi": "thôi",
        "vay": "vậy", "biet": "biết", "minh": "mình", "cung": "cũng",
        "chua": "chưa", "dang": "đang", "rat": "rất", "gi": "gì",
        "de": "để", "toi": "tôi", "yeu": "yêu",
        "nhu the nao": "như thế nào", "nhan tin": "nhắn tin",
        "nhan vien": "nhân viên", "nhung ma": "nhưng mà",
        "binh thuong": "bình thường", "nguoi yeu": "người yêu",
        "dien thoai": "điện thoại", "voi": "với", "ok": "ổn",
        "video": "video", "youtube": "youtube",
        "hom": "hôm", "nay": "nay", "qua": "quá", "lam": "làm",
        "noi": "nói", "ve": "về", "neu": "nếu", "vi": "vì",
        "day": "đây", "do": "đó", "sao": "sao", "tai": "tại",
        "van": "vẫn", "toi": "tôi", "anh": "anh", "em": "em",
        "co": "có", "la": "là", "thay": "thấy", "nhe": "nhé",
        "nha": "nha", "luon": "luôn", "them": "thêm", "truoc": "trước",
        "sau": "sau", "gio": "giờ", "vui": "vui", "buon": "buồn",
    }
    # Từ ngắn nguy hiểm (1-2 ký tự) — chỉ áp dụng cho VI
    DANGEROUS_SHORT = {"t", "k", "r", "j", "v", "h", "g", "m", "n"}

    safe: Dict[str, str] = {**SAFE_MAP}
    vi_only: Dict[str, str] = {**VI_ONLY_MAP}

    if not path.exists():
        return safe, vi_only

    raw = json.loads(path.read_text(encoding="utf-8"))
    for k, v in raw.items():
        k_nfc = unicodedata.normalize("NFC", str(k).strip().lower())
        v_nfc = unicodedata.normalize("NFC", str(v).strip().lower())
        if not v_nfc:
            continue  # Bỏ entry rỗng (từ tục)
        v_fixed = NODIAC.get(v_nfc, v_nfc)
        if k_nfc in DANGEROUS_SHORT:
            vi_only[k_nfc] = v_fixed
        else:
            # Không override built-in safe map (built-in đã có dấu đúng)
            safe.setdefault(k_nfc, v_fixed)

    log.info("Norm map — safe: %d, vi_only: %d", len(safe), len(vi_only))
    return safe, vi_only

# ═══════════════════════════════════════════════════════════════════════════════
# STOPWORDS
# ═══════════════════════════════════════════════════════════════════════════════

STOPWORD_WHITELIST: Set[str] = {
    "không", "có", "được", "đã", "đang", "rất", "và", "là",
    "rồi", "ra", "lên", "về", "từ", "gì", "ai", "hay", "hoặc",
    "mà", "thì", "nên", "với", "do", "bị", "cho", "khi", "vì", "nếu",
}

def load_stopwords(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    raw = {l.strip().lower() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}
    removed = raw & STOPWORD_WHITELIST
    if removed:
        log.info("Giữ lại %d từ quan trọng không filter: %s", len(removed), sorted(removed))
    return raw - STOPWORD_WHITELIST

# ═══════════════════════════════════════════════════════════════════════════════
# SENTENCE SPLITTING — FIX cho vấn đề sang_năm, nha_a
# ═══════════════════════════════════════════════════════════════════════════════

def split_sentences(text: str) -> List[str]:
    """
    FIX: Tách câu trước khi tokenize để tránh ghép nhầm qua dấu chấm.
    "nha a Sang. Năm mới" -> ["nha a Sang", "Năm mới"]
    """
    # Tách tại . ! ? theo sau bởi chữ hoa hoặc chữ Việt có dấu
    parts = re.split(r"(?<=[.!?…])\s+", text)
    return [p.strip() for p in parts if p.strip()]

# ═══════════════════════════════════════════════════════════════════════════════
# TEXT CLEANING
# ═══════════════════════════════════════════════════════════════════════════════

def extract_from_html(text: str) -> str:
    """Xử lý HTML tag và entity — đặc biệt quan trọng cho YT comments."""
    if "<" not in text:
        return text
    try:
        from bs4 import BeautifulSoup  # type: ignore
        return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    except ImportError:
        return HTML_TAG.sub(" ", text)

def remove_noise(text: str) -> str:
    """Thứ tự đúng: HTML → URL → timestamp → mention → repeated → ký tự lạ."""
    text = extract_from_html(text)
    text = URL_PAT.sub(" ", text)
    text = TIMESTAMP.sub(" ", text)
    text = MENTION.sub(" ", text)
    text = HASHTAG.sub(" ", text)
    text = REPEATED.sub(r"\1\1", text)
    text = UNICODE_KEEP.sub(" ", text)
    text = MULTI_SP.sub(" ", text).strip()
    return text

def apply_phrase_norm(text: str) -> str:
    replacements = [
        (re.compile(r"\bvẫn\s+đề\b"),       "vấn đề"),
        (re.compile(r"\bko\s+sao\b"),        "không sao"),
        (re.compile(r"\bko\s+vấn\s+đề\b"),  "không vấn đề"),
        (re.compile(r"\byou\s*tube\b", re.I), "youtube"),
        (re.compile(r"\ba\s+chua\b"), "anh chưa"),
        (re.compile(r"\ba\s+sang\b"), "anh sang"),
        (re.compile(r"\be\s+sang\b"), "em sang"),
        (re.compile(r"\bnha\s+a\b"), "nha anh"),
        (re.compile(r"\bvideo\s+a\b"), "video anh"),
        (re.compile(r"\bae\s+oi\b"), "anh em ơi"),
    ]
    for pat, rep in replacements:
        text = pat.sub(rep, text)
    return text


def normalize_chat_pronouns(text: str) -> str:
    """Mở rộng đại từ viết tắt để tokenizer không làm rơi token quan trọng."""
    replacements = [
        (re.compile(r"\ba\b"), "anh"),
        (re.compile(r"\be\b"), "em"),
        (re.compile(r"\bm\b"), "mình"),
        (re.compile(r"\bt\b"), "tôi"),
    ]
    out = text
    for pat, rep in replacements:
        out = pat.sub(rep, out)
    return out

def apply_word_norm(text: str, safe_map: Dict[str, str], vi_only_map: Dict[str, str], lang: str) -> str:
    words = text.split()
    result = []
    for w in words:
        key = w.strip()
        # Áp safe map cho tất cả
        mapped = safe_map.get(key, w)
        # Chỉ áp vi_only_map nếu là text tiếng Việt
        if lang in ("vi", "mixed"):
            mapped = vi_only_map.get(key, mapped)
        result.append(mapped)
    return " ".join(result)

# ═══════════════════════════════════════════════════════════════════════════════
# TOKENIZATION — FIX: tách câu trước, xử lý EN riêng
# ═══════════════════════════════════════════════════════════════════════════════

_TOKENIZER: str | None = None

def _init_tokenizer() -> str:
    global _TOKENIZER
    if _TOKENIZER:
        return _TOKENIZER
    try:
        import underthesea  # type: ignore
        _TOKENIZER = "underthesea"
        log.info("Tokenizer: underthesea")
    except ImportError:
        try:
            from pyvi import ViTokenizer  # type: ignore
            _TOKENIZER = "pyvi"
            log.info("Tokenizer: pyvi")
        except ImportError:
            _TOKENIZER = "basic"
            log.warning("Tokenizer: split() — cài underthesea để tốt hơn")
    return _TOKENIZER

def tokenize_vi(text: str) -> List[str]:
    """
    FIX: Tokenize từng câu riêng để tránh kết hợp sai qua dấu câu.
    """
    tok = _init_tokenizer()
    sentences = split_sentences(text)
    all_tokens: List[str] = []

    for sent in sentences:
        if not sent.strip():
            continue
        if tok == "underthesea":
            from underthesea import word_tokenize  # type: ignore
            result = word_tokenize(sent, format="text")
            all_tokens.extend(result.split())
        elif tok == "pyvi":
            from pyvi import ViTokenizer  # type: ignore
            result = ViTokenizer.tokenize(sent)
            all_tokens.extend(result.split())
        else:
            all_tokens.extend(sent.split())
    return all_tokens

def tokenize_en(text: str) -> List[str]:
    """Tokenize text tiếng Anh: chỉ split, không dùng VI tokenizer."""
    # Xử lý contraction: don't -> dont, it's -> its
    text = re.sub(r"'s\b", "", text)
    text = re.sub(r"n't\b", "nt", text)
    text = re.sub(r"'re\b|'ve\b|'ll\b|'d\b", "", text)
    return text.split()

# ═══════════════════════════════════════════════════════════════════════════════
# NOISE TOKENS & PARTICLES
# ═══════════════════════════════════════════════════════════════════════════════

NOISE_TOKENS: Set[str] = {
    "href", "http", "https", "www", "com", "amp", "quot",
    "br", "nbsp", "html", "css",
}
PARTICLE_TOKENS: Set[str] = {"ạ", "à", "ơ", "ơi", "nha", "nhé", "nhỉ", "hả", "ha", "ư", "nè"}
IMPORTANT_SHORT: Set[str] = {
    "ở", "đi", "về", "lên", "ra", "vô", "vào",
    "đã", "sẽ", "là", "và", "có", "cho",
    "từ", "với", "do", "bị", "hay", "rất", "quá",
    "mà", "thì", "nên", "hoặc", "gì", "ai",
}

def clean_token(tok: str, lang: str) -> str:
    tok = tok.strip().lower()
    if not tok:
        return ""
    if tok in IMPORTANT_SHORT:
        return tok
    if tok in NOISE_TOKENS or tok in PARTICLE_TOKENS:
        return ""
    if tok.isdigit():
        return ""
    tok = tok.strip("_")
    tok = REPEATED.sub(r"\1\1", tok)

    # Tách hậu tố cảm thán thường bị dính sau tokenize, ví dụ: khỏe_nha -> khỏe
    for suffix in ("_nha", "_nhé", "_nhe", "_ha", "_hả", "_ạ", "_ơi"):
        if tok.endswith(suffix) and len(tok) > len(suffix) + 1:
            tok = tok[: -len(suffix)]

    # Xóa token ASCII 1 ký tự (không áp với tiếng Việt)
    if len(tok) <= 1 and tok.isascii():
        return ""
    # Với tiếng Anh: lọc thêm stop words ngắn không có nghĩa
    if lang == "en" and tok in {"a", "i", "s", "nt", "dont", "im", "its", "thats"}:
        return ""

    # Sửa một số merge sai hay gặp do dữ liệu mạng xã hội.
    if tok in {"sang_năm", "sang_nam"}:
        return "sang"
    return tok

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def preprocess_text(
    text: str,
    safe_map: Dict[str, str],
    vi_only_map: Dict[str, str],
    stopwords: Set[str],
    remove_stopwords: bool = False,
) -> Tuple[str, List[str], str]:
    """
    Trả về (clean_text, tokens, lang).

    Thứ tự pipeline (đã fix):
      1. unicode NFC + html unescape
      2. detect language (trước khi xóa ký tự)
      3. remove noise (HTML, URL, timestamp)
      4. phrase normalization
      5. word normalization (áp map theo lang)
      6. tokenize (theo lang)
    7. clean tokens
    8. (tùy chọn) filter stopwords cho mục tiêu modeling
    """
    if not isinstance(text, str):
        text = "" if pd.isna(text) else str(text)
    if not text.strip():
        return "", [], "vi"

    # Bước 1: Unicode
    text = unicodedata.normalize("NFC", html_module.unescape(text)).lower().strip()

    # Bước 2: Detect lang (dựa trên text gốc trước khi xóa ký tự)
    lang = detect_language(text)

    # Bước 3: Remove noise
    text = remove_noise(text)

    # Bước 4: Phrase norm
    if lang in ("vi", "mixed"):
        text = apply_phrase_norm(text)
        text = normalize_chat_pronouns(text)

    # Bước 5: Word norm (theo lang)
    text = apply_word_norm(text, safe_map, vi_only_map, lang)

    # Bước 6: Tokenize
    if lang == "en":
        tokens = tokenize_en(text)
    else:
        tokens = tokenize_vi(text)

    # Bước 7: Clean tokens
    tokens = [clean_token(t, lang) for t in tokens]
    tokens = [t for t in tokens if t]

    # Bước 8: Chỉ lọc stopwords khi được yêu cầu.
    if remove_stopwords:
        tokens = [t for t in tokens if t not in stopwords]

    return " ".join(tokens), tokens, lang


# ═══════════════════════════════════════════════════════════════════════════════
# HÀM FIX cleaned_dataset.csv hiện tại
# ═══════════════════════════════════════════════════════════════════════════════

def fix_cleaned_dataset(
    input_csv: Path,
    output_csv: Path,
    safe_map: Dict[str, str],
    vi_only_map: Dict[str, str],
    stopwords: Set[str],
    remove_stopwords: bool = False,
) -> pd.DataFrame:
    """
    Đọc cleaned_dataset.csv hiện tại và xử lý lại với pipeline đã fix.
    Thêm cột 'lang' để biết ngôn ngữ.
    Lọc bỏ comment tiếng Anh (tùy chọn).
    """
    df = pd.read_csv(input_csv, encoding="utf-8-sig")
    log.info("Đọc %d rows từ %s", len(df), input_csv)

    results = [
        preprocess_text(
            t,
            safe_map,
            vi_only_map,
            stopwords,
            remove_stopwords=remove_stopwords,
        )
        for t in df["raw_text"].tolist()
    ]
    df["clean_text"] = [r[0] for r in results]
    df["tokens"]     = [r[1] for r in results]
    df["token_len"]  = df["tokens"].apply(len)
    df["lang"]       = [r[2] for r in results]

    log.info("Phân bố ngôn ngữ: %s", df["lang"].value_counts().to_dict())

    # Thống kê cải thiện
    en_rows = (df["lang"] == "en").sum()
    log.info("Comment tiếng Anh (có thể lọc): %d (%.1f%%)", en_rows, en_rows/len(df)*100)

    # Lọc bỏ text rỗng sau clean
    before = len(df)
    df = df[df["clean_text"].str.strip() != ""].reset_index(drop=True)
    log.info("Sau lọc empty: %d rows (dropped %d)", len(df), before - len(df))

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    log.info("Đã lưu: %s", output_csv)
    return df


def analyze_underscore_tokens(df: pd.DataFrame) -> Dict:
    """Thống kê token có dấu gạch dưới: phân loại đúng/sai."""
    counter: Counter = Counter()
    for toks in df["tokens"]:
        if isinstance(toks, list):
            for t in toks:
                if "_" in str(t):
                    counter[t] += 1

    return {
        "total_underscore_types": len(counter),
        "total_underscore_occurrences": sum(counter.values()),
        "top_30": counter.most_common(30),
    }


def generate_report(df: pd.DataFrame, output_dir: Path) -> None:
    """Tạo báo cáo phân tích."""
    report = {
        "total_rows": len(df),
        "source_distribution": df["source"].value_counts().to_dict(),
        "lang_distribution": df["lang"].value_counts().to_dict(),
        "avg_token_len": float(df["token_len"].mean()),
        "underscore_analysis": analyze_underscore_tokens(df),
    }

    (output_dir / "pipeline_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Plot
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    df["source"].value_counts().plot(kind="bar", ax=axes[0], color=["#2E86AB", "#F18F01"])
    axes[0].set_title("Phân bố theo nguồn")
    axes[0].tick_params(axis="x", rotation=0)

    df["lang"].value_counts().plot(kind="bar", ax=axes[1], color=["#3B7A57", "#E84855", "#F4A261"])
    axes[1].set_title("Phân bố ngôn ngữ")
    axes[1].tick_params(axis="x", rotation=0)

    df["token_len"].plot(kind="hist", bins=40, ax=axes[2], color="#6A4C93")
    axes[2].set_title("Phân bố số token")

    plt.tight_layout()
    plt.savefig(output_dir / "pipeline_report.png", dpi=150)
    plt.close()


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════════════════════

def demo(safe_map, vi_only_map, stopwords):
    """Test các trường hợp đã phát hiện trong cleaned_dataset."""
    cases = [
        # VẤN ĐỀ 1: a_chua -> cần khôi phục dấu trước tokenize
        ("vi",    "Có a chua đi vs ae vui thích xem",
                  "a chua = a chưa, cần map chua->chưa trước tokenize"),
        # VẤN ĐỀ 2: sang_năm do không tách câu
        ("vi",    "Em không có bỏ qua quảng cáo nha a Sang. Năm mới chúc các anh",
                  "Dấu chấm gây merge Sang+Năm"),
        # VẤN ĐỀ 3: don't -> don tôi
        ("en",    "<a href='x&amp;t=100'>23:36</a> sharks don't live on the river",
                  "EN comment: don't không được map t->tôi"),
        # VẤN ĐỀ 4: Text không dấu
        ("vi",    "cai gi ko noi dc thi nen cat video khuc do di sang oi",
                  "Text không dấu — map từng từ"),
        # Bình thường
        ("vi",    "vcl chạy tốn vậy cơ à",  "vcl -> rất ✓"),
        ("vi",    "ko xem đc video nào",     "ko, đc -> không, được ✓"),
    ]

    print("\n" + "=" * 80)
    print("DEMO: Kết quả sau fix")
    print("=" * 80)
    for expected_lang, text, note in cases:
        clean, tokens, lang = preprocess_text(text, safe_map, vi_only_map, stopwords)
        print(f"\n[{note}]")
        print(f"  INPUT : {text[:80]}")
        print(f"  LANG  : {lang} (expected: {expected_lang})")
        print(f"  CLEAN : {clean[:80]}")
        print(f"  TOKENS: {tokens}")
    print("=" * 80)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    parser = argparse.ArgumentParser(description="Fix Vietnamese NLP Pipeline")
    parser.add_argument("--input-csv",    default="outputs/cleaned_dataset.csv")
    parser.add_argument("--output-csv",   default="cleaned_dataset_fixed.csv")
    parser.add_argument("--norm-map",     default="resources/normalization_map.json")
    parser.add_argument("--stopwords",    default="resources/vietnamese_stopwords.txt")
    parser.add_argument("--output-dir",   default="outputs")
    parser.add_argument("--remove-stopwords", action="store_true")
    parser.add_argument("--demo",         action="store_true")
    args = parser.parse_args()

    input_csv = Path(args.input_csv)
    if not input_csv.is_absolute():
        input_csv = project_root / input_csv

    norm_map = Path(args.norm_map)
    if not norm_map.is_absolute():
        norm_map = project_root / norm_map

    stopwords_path = Path(args.stopwords)
    if not stopwords_path.is_absolute():
        stopwords_path = project_root / stopwords_path

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_map, vi_only_map = load_normalization_map(norm_map)
    stopwords = load_stopwords(stopwords_path)

    if args.demo:
        demo(safe_map, vi_only_map, stopwords)
    else:
        if not input_csv.exists():
            yt_csv = project_root / "yt_comments.csv"
            voz_csv = project_root / "voz_threads_comments.csv"

            if yt_csv.exists() and voz_csv.exists():
                log.warning(
                    "Không tìm thấy %s. Tự tạo input từ yt_comments.csv và voz_threads_comments.csv.",
                    input_csv,
                )

                yt_df = pd.read_csv(yt_csv)
                voz_df = pd.read_csv(voz_csv)

                yt_boot = pd.DataFrame(
                    {
                        "source": "youtube",
                        "raw_text": yt_df.get("text", pd.Series(dtype=str)).astype(str),
                    }
                )
                voz_boot = pd.DataFrame(
                    {
                        "source": "voz",
                        "raw_text": voz_df.get("text", pd.Series(dtype=str)).astype(str),
                    }
                )

                boot_df = pd.concat([yt_boot, voz_boot], ignore_index=True)
                boot_df = boot_df.dropna(subset=["raw_text"])
                boot_df = boot_df[boot_df["raw_text"].str.strip() != ""]

                input_csv.parent.mkdir(parents=True, exist_ok=True)
                boot_df.to_csv(input_csv, index=False, encoding="utf-8-sig")
                log.info("Đã tạo input bootstrap: %s (%d rows)", input_csv, len(boot_df))
            else:
                raise FileNotFoundError(
                    f"Không tìm thấy input CSV: {input_csv}. "
                    "Hãy truyền --input-csv hoặc chuẩn bị yt_comments.csv và voz_threads_comments.csv."
                )
        df = fix_cleaned_dataset(
            input_csv  = input_csv,
            output_csv = output_dir / args.output_csv,
            safe_map   = safe_map,
            vi_only_map= vi_only_map,
            stopwords  = stopwords,
            remove_stopwords=args.remove_stopwords,
        )
        generate_report(df, output_dir)
        print(f"\nHoàn thành. Rows: {len(df)}")
        print(df[["raw_text", "clean_text", "lang"]].head(10).to_string())