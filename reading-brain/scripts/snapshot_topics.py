"""
snapshot_topics.py
===================
把当前 output/entries.jsonl 的划线列表记一份"快照"，作为专题分析
（output/topics_data.json）的基线版本。scripts/check_updates.py 靠对比
这份快照和最新笔记，判断"专题生成之后，笔记又新增了哪些、可能跟哪个
专题相关"。

什么时候跑这个：
  - 第一次拿到这一批脚本时，跑一次，把当前状态定为基线；
  - 以后每次拿到我（Claude）新做的 output/topics_data.json 之后，
    再跑一次，把基线对齐到那个版本。

不需要跑的情况：
  - 只是重新解析了笔记、跑了 build_index.py / build_graph.py / build_app.py，
    专题内容没换 —— 不用跑这个，check_updates.py 该提示新划线的还是会提示。

用法：
    cd reading-brain
    python3 scripts/snapshot_topics.py
"""
import json
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # reading-brain/
PROJECT_DIR = BASE_DIR.parent                       # Document_Reading_Brain/
ENTRIES_PATH = PROJECT_DIR / "output" / "entries.jsonl"   # 你的解析工具实际写入的位置
SNAPSHOT_PATH = BASE_DIR / "output" / ".topics_snapshot.json"


def main():
    if not ENTRIES_PATH.exists():
        print(f"找不到 {ENTRIES_PATH}，确认笔记解析步骤先跑过。")
        return

    ids = set()
    with open(ENTRIES_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ids.add(json.loads(line)["entry_id"])
    ids = sorted(ids)  # 去重（原始笔记里偶尔会有重复 entry_id），保证和 check_updates.py 的计数口径一致

    SNAPSHOT_PATH.write_text(
        json.dumps({"date": date.today().isoformat(), "entry_ids": ids}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"专题快照基线已更新：{len(ids)} 条划线，日期 {date.today().isoformat()}")
    print(f"-> {SNAPSHOT_PATH}")


if __name__ == "__main__":
    main()
