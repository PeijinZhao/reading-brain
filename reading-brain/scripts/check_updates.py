"""
check_updates.py
=================
笔记更新之后，"专题"页签（爱情/孤独/自由……11个主题的观点聚类）是我
实际读过一批划线人工产出的，没法用脚本自动重做。这个脚本做退而求其次
的事：告诉你新增了哪些划线、分布在哪些书里，帮你判断值不值得为此
回来找我更新专题 —— 而不是让你自己去 diff entries.jsonl。

做法（只做可靠的部分，不做不可靠的猜测）：
  1. 对比 output/entries.jsonl 和上次的"专题快照"
     （output/.topics_snapshot.json，由 snapshot_topics.py 生成），
     精确找出新增的划线，按书名分组展示。
  2. 检查这些新划线所在的书，是不是已经在 output/topics_data.json 的
     摘录来源里出现过——如果是，说明这本书已经被某个专题引用过，
     新增的内容大概率也相关，值得看看。这里只做"书名是否重合"的
     精确字符串匹配，是可以完全信任的判断。

  没做的事：没有尝试用 TF-IDF 相似度自动猜"这条新划线属于哪个专题"。
  试过这个方向，但测试发现短句 + 每个专题只有十几条摘录做参照的情况下，
  这种猜测经常错、而且错得很自信（比如会把一句量子计算机的划线判给
  "记忆"专题，只因为字面上都出现"计算机"三个字）。宁可少判断、把
  新增内容原样列出来给你自己扫一眼，也不做一个似是而非的自动分类，
  这也是 VISION.md 里 Evidence First 的原则。

用法：
    cd reading-brain
    python3 scripts/check_updates.py
依赖：无第三方依赖（纯标准库）。
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # reading-brain/
PROJECT_DIR = BASE_DIR.parent                       # Document_Reading_Brain/
ENTRIES_PATH = PROJECT_DIR / "output" / "entries.jsonl"   # 你的解析工具实际写入的位置
TOPICS_PATH = BASE_DIR / "output" / "topics_data.json"
SNAPSHOT_PATH = BASE_DIR / "output" / ".topics_snapshot.json"

SHOW_PER_BOOK = 3  # 每本书最多展示几条新划线内容


def load_jsonl(p):
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def books_already_in_topics():
    """返回 {书名: [出现过的专题名, ...]}，来自 topics_data.json 里摘录/反方来源的书名。"""
    if not TOPICS_PATH.exists():
        return {}
    topics = json.loads(TOPICS_PATH.read_text(encoding="utf-8"))
    mapping = {}
    for t in topics:
        name = t["title"]
        for s in t.get("stances", []):
            for q in s.get("quotes", []):
                mapping.setdefault(q.get("book", ""), set()).add(name)
            c = s.get("counter") or {}
            if c.get("book"):
                mapping.setdefault(c["book"], set()).add(name + "·反方")
    return {k: sorted(v) for k, v in mapping.items() if k}


def main():
    if not ENTRIES_PATH.exists():
        print(f"找不到 {ENTRIES_PATH}，确认笔记解析步骤先跑过。")
        return

    entries = load_jsonl(ENTRIES_PATH)
    current = {e["entry_id"]: e for e in entries}

    if not SNAPSHOT_PATH.exists():
        print("还没有建立专题快照基线。")
        print("如果 output/topics_data.json 目前就是最新版本，跑一次：")
        print("    python3 scripts/snapshot_topics.py")
        print("建立基线之后，以后每次笔记更新，这里就能告诉你新增了什么。")
        return

    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    baseline_ids = set(snapshot.get("entry_ids", []))
    snap_date = snapshot.get("date", "未知")

    new_ids = [eid for eid in current if eid not in baseline_ids]
    removed = baseline_ids - set(current)

    print(f"专题快照基线：{snap_date}（{len(baseline_ids)} 条划线）")
    print(f"当前笔记：{len(current)} 条划线")
    if removed:
        print(f"（基线里有 {len(removed)} 条现在找不到了，可能是笔记被改动/删除过，不影响下面统计）")

    if not new_ids:
        print("\n没有新增划线，专题页面仍然是最新的，不用回来找我更新。")
        return

    by_book = {}
    for eid in new_ids:
        e = current[eid]
        by_book.setdefault(e.get("book_title", "未知书名"), []).append(e)

    known = books_already_in_topics()

    print(f"\n自上次专题快照以来新增了 {len(new_ids)} 条划线，分布在 {len(by_book)} 本书：\n")

    flagged, plain = [], []
    for book in by_book:
        (flagged if book in known else plain).append(book)

    if flagged:
        print("这些书已经在专题页面里被引用过，新增内容可能跟对应专题相关，值得看看：\n")
        for book in flagged:
            items = by_book[book]
            themes = "、".join(known[book])
            print(f"《{book}》—— 已出现在【{themes}】，新增 {len(items)} 条：")
            for e in items[:SHOW_PER_BOOK]:
                text = e["text"].strip().replace("\n", " ")
                if len(text) > 44:
                    text = text[:44] + "…"
                print(f"    · {text}")
            if len(items) > SHOW_PER_BOOK:
                print(f"    …还有 {len(items) - SHOW_PER_BOOK} 条")
            print()

    if plain:
        print("这些书之前没被任何专题引用过，新增了划线（是否值得开新专题，自己看一眼）：\n")
        for book in plain:
            items = by_book[book]
            print(f"《{book}》 新增 {len(items)} 条")
        print()

    print("以上是完整、准确的新增清单（没有做自动归类猜测）。")
    print("挑一下觉得重要的，把书名或者新增划线发给我，我来判断要不要更新/新增专题。")
    print("专题更新完成后，记得跑一次 python3 scripts/snapshot_topics.py 把基线对齐，")
    print("下次就不会重复提示同一批划线了。")


if __name__ == "__main__":
    main()
