"""
build_graph.py
===============
生成"书籍相似度图谱"数据（图谱页签用）。基于 build_index.py 已经算好的
字符级 TF-IDF 向量，把每本书的划线聚合成一个向量，计算书与书之间的
余弦相似度，每本书保留最相似的几个邻居作为图谱的边。

放置位置：reading-brain/scripts/build_graph.py
依赖：先跑过 scripts/build_index.py（需要它生成的 retrieval_index/）
用法：
    cd reading-brain
    python3 scripts/build_graph.py
输出：output/graph_data.json，之后跑 scripts/build_app.py 会自动把它嵌入桌面检索台。

这是"哪些书在讨论相近的东西"的粗粒度关联，基于用词统计相似度，
不是真正的观点关系（支持/冲突/延伸……）。那一层需要真正读懂内容去
判断，没法用脚本自动生成，见"专题"页签的做法（那部分是通过对话
让AI实际阅读一批划线后人工产出的，无法用本脚本复现）。
"""
import json
import pickle
from pathlib import Path

import numpy as np
from scipy import sparse
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parent.parent  # reading-brain/
PROJECT_DIR = BASE_DIR.parent                       # Document_Reading_Brain/
INDEX_DIR = BASE_DIR / "output" / "retrieval_index"
ENTRIES_PATH = PROJECT_DIR / "output" / "entries.jsonl"   # 你的解析工具实际写入的位置
BOOKS_PATH = PROJECT_DIR / "output" / "books.jsonl"
OUT_PATH = BASE_DIR / "output" / "graph_data.json"

TOP_K = 4
MIN_SIM = 0.06


def main():
    with open(INDEX_DIR / "vectorizer.pkl", "rb") as f:
        pickle.load(f)  # not needed directly, just checking the index exists
    tfidf = sparse.load_npz(INDEX_DIR / "tfidf_matrix.npz")

    books_raw = [json.loads(l) for l in open(BOOKS_PATH, encoding="utf-8") if l.strip()]
    entries_raw = [json.loads(l) for l in open(ENTRIES_PATH, encoding="utf-8") if l.strip()]
    assert len(entries_raw) == tfidf.shape[0], "entries.jsonl 和索引条数对不上，请先重新跑 build_index.py"

    book_idx = {b["source_path"]: i for i, b in enumerate(books_raw)}
    n_books = len(books_raw)

    book_rows = [[] for _ in range(n_books)]
    for row, e in enumerate(entries_raw):
        bi = book_idx.get(e.get("source_path"))
        if bi is not None:
            book_rows[bi].append(row)

    book_vecs = sparse.lil_matrix((n_books, tfidf.shape[1]))
    counts = np.zeros(n_books, dtype=int)
    for bi, rows in enumerate(book_rows):
        counts[bi] = len(rows)
        if rows:
            book_vecs[bi] = tfidf[rows].sum(axis=0)
    book_vecs = book_vecs.tocsr()
    norms = np.sqrt(book_vecs.multiply(book_vecs).sum(axis=1))
    norms = np.asarray(norms).ravel()
    norms[norms == 0] = 1
    book_vecs = book_vecs.multiply(1 / norms[:, None]).tocsr()

    sim = cosine_similarity(book_vecs)
    np.fill_diagonal(sim, 0)

    edges = []
    seen_pairs = set()
    for i in range(n_books):
        if counts[i] == 0:
            continue
        order = np.argsort(-sim[i])[:TOP_K]
        for j in order:
            j = int(j)
            if i == j or sim[i, j] < MIN_SIM or counts[j] == 0:
                continue
            pair = (min(i, j), max(i, j))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            edges.append([int(pair[0]), int(pair[1]), round(float(sim[i, j]), 4)])

    nodes = [
        {"id": i, "title": b["title"], "author": b.get("author") or "", "n": int(counts[i])}
        for i, b in enumerate(books_raw)
    ]

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"nodes": nodes, "edges": edges}, f, ensure_ascii=False)
    print(f"books: {n_books}, edges: {len(edges)} -> {OUT_PATH}")
    print("接下来跑 python3 scripts/build_app.py 让图谱生效")


if __name__ == "__main__":
    main()
