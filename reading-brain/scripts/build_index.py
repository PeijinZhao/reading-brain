"""
build_index.py
================
构建 Reading Brain 的检索索引层，对应 docs/ARCHITECTURE.md 管道图里
"审计+本地存储" 之后的两步：关键词检索 / 语义检索。

放置位置：reading-brain/scripts/build_index.py
读取：    output/entries.jsonl（Document_Reading_Brain 根目录下，你的解析
          工具本来就写在这里，不用手动挪）
写出：    reading-brain/output/retrieval_index/ 下的索引文件（跟你的原始
          输出分开放，不会互相干扰）

用法：
    cd reading-brain
    python3 scripts/build_index.py

依赖：scikit-learn, scipy, numpy（如果本地还没装： pip install scikit-learn scipy numpy）

—— 方法说明（请务必读一下，这决定了检索结果的能力边界）——

这一版没有用神经网络 embedding 模型（比如 BGE / OpenAI embedding），
而是用两层经典方法组合：

  1. 字符级 TF-IDF（analyzer="char"，2-4 gram）
     不需要分词器（不依赖 jieba），直接在字符层面统计，对中文短句
     稳定可靠。本质上是"增强关键词检索"——能找到包含查询词（或其
     子串）的划线，不会有前面用 char_wb 时因为边界填充符产生的
     "无关文本因为恰好同字结尾而被误判相关"的噪声（如果你看到旧版本
     结果里出现风马牛不相及的条目，就是那个问题，这一版已经修掉）。

  2. TruncatedSVD（潜在语义分析 / LSA）
     在 TF-IDF 矩阵上做降维，捕捉"经常一起出现的字"之间的关联，
     带来一部分"字面不同但主题相关"的联想能力。但受限于数据规模
     （4943条短文本）和方法本身，这个"联想"是统计共现意义上的，
     不是真正理解语义——比如查"亲密关系"时可能会联想到商业谈判里的
     "人际关系"，因为两者共享"关系"这个词，但主题其实不同。
     使用时建议同时看 lexical（字面）和 topic（联想）两个分数，
     topic 分数高但 lexical 很低的结果，自己再判断一下是否真的相关。

—— 如果之后想升级到真正的神经网络语义检索 ——
推荐模型：BAAI/bge-small-zh-v1.5（中文效果好、模型小、CPU可跑）
只需要在有网络权限的环境（你自己电脑的终端，不受这次云端沙盒的
网络限制）跑一次：
    pip install sentence-transformers
    然后用该模型对 entries.jsonl 里每条 text 生成向量，存成 .npy
把这个 .npy 换掉这里的 lsa_matrix.npy，就是"语义检索"层的真正升级版，
query.py 的检索逻辑基本不用改。这部分脚本如果你需要，告诉我，我再补一版。
"""

import json
import pickle
from pathlib import Path

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD

BASE_DIR = Path(__file__).resolve().parent.parent  # reading-brain/
PROJECT_DIR = BASE_DIR.parent                       # Document_Reading_Brain/
ENTRIES_PATH = PROJECT_DIR / "output" / "entries.jsonl"   # 你的解析工具实际写入的位置
OUT_DIR = BASE_DIR / "output" / "retrieval_index"          # 检索台自己的生成物，跟你的原始输出分开放


def load_entries():
    entries = []
    with open(ENTRIES_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    entries = load_entries()
    print(f"loaded {len(entries)} entries from {ENTRIES_PATH}")

    texts = [e["text"] for e in entries]

    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 4),
        max_features=60000,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(texts)
    print("tfidf matrix shape:", tfidf_matrix.shape)

    n_components = min(200, tfidf_matrix.shape[0] - 1, tfidf_matrix.shape[1] - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    lsa_matrix = svd.fit_transform(tfidf_matrix)
    print("lsa matrix shape:", lsa_matrix.shape)
    print("explained variance ratio (sum):", svd.explained_variance_ratio_.sum())

    with open(OUT_DIR / "vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    with open(OUT_DIR / "svd.pkl", "wb") as f:
        pickle.dump(svd, f)
    sparse.save_npz(OUT_DIR / "tfidf_matrix.npz", tfidf_matrix)
    np.save(OUT_DIR / "lsa_matrix.npy", lsa_matrix)

    meta = [
        {
            "idx": i,
            "entry_id": e["entry_id"],
            "text": e["text"],
            "book_title": e["book_title"],
            "author": e.get("author"),
            "chapter": e.get("chapter"),
            "timestamp": e.get("timestamp"),
            "source_path": e.get("source_path"),
        }
        for i, e in enumerate(entries)
    ]
    with open(OUT_DIR / "entries_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    print("index built ->", OUT_DIR)


if __name__ == "__main__":
    main()
