"""
query.py
========
对 build_index.py 生成的索引做检索，支持写文章时快速从237本书的划线里
按主题挖相关片段（对应 VISION.md 的 "Evidence First" 原则——
每条建议都能查到具体出处：书名/作者/章节/划线时间）。

放置位置：reading-brain/scripts/query.py

用法：
    cd reading-brain
    python3 scripts/query.py "爱情" --top 20
    python3 scripts/query.py "孤独" --top 20 --json > 孤独_相关笔记.json

评分方式：
  lexical_score = 字符级 TF-IDF 余弦相似度（字面关键词命中）
  topic_score   = LSA 潜在语义空间的余弦相似度（弱语义联想，见 build_index.py 顶部说明）
  combined      = lexical_weight * lexical_score + (1 - lexical_weight) * topic_score
                  默认 lexical_weight=0.6。查询词越短、越具体（比如"爱情"这种
                  2字词），字面匹配已经很强，可以适当调高 lexical_weight（甚至到 1.0）
                  减少联想带来的噪声；查询词是比较抽象的主题描述时，可以调低一些
                  让联想层发挥更多作用，但也要自己甄别结果。
"""

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
from scipy import sparse
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parent.parent  # reading-brain/
INDEX_DIR = BASE_DIR / "output" / "retrieval_index"


def load_index():
    with open(INDEX_DIR / "vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)
    with open(INDEX_DIR / "svd.pkl", "rb") as f:
        svd = pickle.load(f)
    tfidf_matrix = sparse.load_npz(INDEX_DIR / "tfidf_matrix.npz")
    lsa_matrix = np.load(INDEX_DIR / "lsa_matrix.npy")
    with open(INDEX_DIR / "entries_meta.json", encoding="utf-8") as f:
        meta = json.load(f)
    return vectorizer, svd, tfidf_matrix, lsa_matrix, meta


def search(query, top=20, lexical_weight=0.6, dedup=True):
    vectorizer, svd, tfidf_matrix, lsa_matrix, meta = load_index()

    q_tfidf = vectorizer.transform([query])
    lexical_scores = cosine_similarity(q_tfidf, tfidf_matrix)[0]

    q_lsa = svd.transform(q_tfidf)
    topic_scores = cosine_similarity(q_lsa, lsa_matrix)[0]

    combined = lexical_weight * lexical_scores + (1 - lexical_weight) * topic_scores
    order = np.argsort(-combined)

    results = []
    seen_text = set()
    for i in order:
        if combined[i] <= 0:
            break
        m = meta[i]
        if dedup and m["text"] in seen_text:
            continue
        seen_text.add(m["text"])
        results.append(
            {
                "combined": float(combined[i]),
                "lexical": float(lexical_scores[i]),
                "topic": float(topic_scores[i]),
                **m,
            }
        )
        if len(results) >= top:
            break
    return results


def print_results(results, query):
    print(f"\n=== 查询: {query!r} ，共 {len(results)} 条结果 ===\n")
    for r in results:
        print(
            f"[{r['combined']:.3f}  字面{r['lexical']:.3f} / 联想{r['topic']:.3f}] "
            f"《{r['book_title']}》 {r.get('author') or ''}"
        )
        print(f"    {r['text']}")
        meta_line = []
        if r.get("chapter"):
            meta_line.append(f"章节 {r['chapter']}")
        if r.get("timestamp"):
            meta_line.append(f"划线时间 {r['timestamp']}")
        if meta_line:
            print(f"    ({' · '.join(meta_line)})")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--lexical-weight", type=float, default=0.6)
    parser.add_argument("--json", action="store_true", help="以 JSON 输出，方便喂给下一步处理")
    args = parser.parse_args()

    results = search(args.query, top=args.top, lexical_weight=args.lexical_weight)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_results(results, args.query)
