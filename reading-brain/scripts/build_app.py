"""
build_app.py
============
用最新的笔记数据重新生成桌面检索界面「阅读大脑检索台.html」。

数据来源（两处，不要搞混）：
  - output/entries.jsonl、output/books.jsonl —— 在 Document_Reading_Brain
    根目录下，你的解析工具本来就写在这里，笔记更新后重新跑一次解析，
    这两个文件自动是最新的，不用你手动挪动或复制。
  - reading-brain/output/graph_data.json、topics_data.json —— 这两个是
    检索台自己的生成物（图谱由脚本算，专题由我人工产出），跟你的原始
    解析输出分开放，不会被你重新解析笔记时覆盖掉。

什么时候需要跑这个：
  你的微信读书笔记更新之后 —— 更推荐直接跑 scripts/update.sh（一条命令
  依次完成 build_index.py → build_graph.py → build_app.py →
  check_updates.py，细节见 UPDATE_GUIDE.md）。如果只是想单独刷新检索台、
  不需要联动更新图谱，可以单跑这一个脚本：
  1. 先按原流程重新解析笔记（output/entries.jsonl 和 books.jsonl 自动更新）；
  2. 再跑：  cd reading-brain && python3 scripts/build_app.py
  桌面文件夹里的 阅读大脑检索台.html 就会更新为最新数据。

不需要任何第三方依赖（纯标准库），几秒跑完。
模板文件是 scripts/app_template.html，界面样式和功能都在里面，
想改界面直接改模板再重跑本脚本即可。

关于"图谱"和"专题"两个页签：
  - 图谱数据读取 reading-brain/output/graph_data.json —— 这个文件由
    scripts/build_graph.py 生成（需要先跑过 build_index.py，依赖
    scikit-learn）。笔记更新后想刷新图谱，顺序是：build_index.py →
    build_graph.py → build_app.py（update.sh 已经按这个顺序做了）。
    如果这个文件不存在，图谱页签会显示为空，不影响其他功能。
  - 专题数据读取 reading-brain/output/topics_data.json —— 这个是我
    （Claude）实际读过一批划线后人工产出的观点聚类分析，没法用脚本自动
    重新生成。如果你想更新或新增专题，需要重新来找我做这部分分析
    （scripts/check_updates.py 会帮你判断哪些新增划线可能值得更新），
    做完后把新的 topics_data.json 放到 reading-brain/output/ 下，
    再跑本脚本（或 update.sh）即可生效。如果文件不存在，专题页签会
    提示"还在生成中"，不影响其他功能。
"""
import json
from datetime import date
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent          # reading-brain/scripts/
BASE = SCRIPTS.parent                              # reading-brain/
PROJECT = BASE.parent                               # Document_Reading_Brain/
ENTRIES = PROJECT / "output" / "entries.jsonl"      # 你的解析工具实际写入的位置
BOOKS = PROJECT / "output" / "books.jsonl"
GRAPH_FILE = BASE / "output" / "graph_data.json"    # 检索台自己的生成物
TOPICS_FILE = BASE / "output" / "topics_data.json"
LINEAGE_FILE = BASE / "output" / "lineage_data.json"  # 思想脉络（影响/反驳/对话）数据，AI整理
MYNOTES_FILE = BASE / "output" / "mynotes.json"  # 我从对话里帮你并入的"我的笔记"（本地localStorage之外的永久层）
MYQ_FILE = BASE / "output" / "myquestions.json"  # 同上，"我的问题"的永久存档层
TEMPLATE = SCRIPTS / "app_template.html"
OUT = PROJECT / "阅读大脑检索台.html"               # Document_Reading_Brain/ 根目录


def load_jsonl(p):
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def main():
    books_raw = load_jsonl(BOOKS)
    entries_raw = load_jsonl(ENTRIES)

    book_idx = {}
    books = []
    for b in books_raw:
        book_idx[b["source_path"]] = len(books)
        books.append([
            b["title"],
            b.get("author") or "",
            b.get("progress") or "",
            b.get("reading_time") or "",
        ])

    entries = []
    seen = set()
    for e in entries_raw:
        bi = book_idx.get(e.get("source_path"))
        if bi is None:
            continue
        text = (e.get("text") or "").strip()
        if len(text) < 2:
            continue
        key = (bi, text)
        if key in seen:
            continue
        seen.add(key)
        entries.append([
            e["entry_id"], text, bi,
            e.get("chapter") or "", e.get("timestamp") or "",
        ])

    data_json = json.dumps({"books": books, "entries": entries},
                           ensure_ascii=False, separators=(",", ":"))
    data_json = data_json.replace("</", "<\\/")

    graph = json.loads(GRAPH_FILE.read_text(encoding="utf-8")) if GRAPH_FILE.exists() else {"nodes": [], "edges": []}
    graph_json = json.dumps(graph, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    topics = json.loads(TOPICS_FILE.read_text(encoding="utf-8")) if TOPICS_FILE.exists() else []
    topics_json = json.dumps(topics, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    lineage = json.loads(LINEAGE_FILE.read_text(encoding="utf-8")) if LINEAGE_FILE.exists() else {"types": {}, "edges": []}
    lineage_json = json.dumps(lineage, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    mynotes = json.loads(MYNOTES_FILE.read_text(encoding="utf-8")) if MYNOTES_FILE.exists() else []
    mynotes_json = json.dumps(mynotes, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    myq = json.loads(MYQ_FILE.read_text(encoding="utf-8")) if MYQ_FILE.exists() else []
    myq_json = json.dumps(myq, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("__DATA__", data_json)
    html = html.replace("__GRAPH__", graph_json)
    html = html.replace("__TOPICS__", topics_json)
    html = html.replace("__LINEAGE__", lineage_json)
    html = html.replace("__MYNOTES__", mynotes_json)
    html = html.replace("__MYQUESTIONS__", myq_json)
    html = html.replace("__NBOOKS__", str(len(books)))
    html = html.replace("__NENTRIES__", f"{len(entries):,}")
    html = html.replace("__BUILDDATE__", date.today().isoformat())

    OUT.write_text(html, encoding="utf-8")
    print(f"books: {len(books)}, entries: {len(entries)}")
    print(f"更新完成 -> {OUT}")


if __name__ == "__main__":
    main()
