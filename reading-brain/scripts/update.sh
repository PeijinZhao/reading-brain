#!/usr/bin/env bash
# update.sh —— 一条命令：从 Obsidian 笔记一路刷新到检索台
#
# 数据源（你的 Obsidian 笔记库）：默认读桌面上的「Obsidian Vault」。
# 如果哪天把库挪了地方，改下面这一行，或运行前设环境变量 READING_BRAIN_SOURCE。
SOURCE="${READING_BRAIN_SOURCE:-$HOME/Desktop/Obsidian Vault}"
#
# 依次执行：
#   0. 解析 Obsidian 笔记 -> output/entries.jsonl, books.jsonl
#   1. build_index.py      重建检索索引（关键词 + 联想）
#   2. build_graph.py       重建书籍关系图谱
#   3. build_app.py          重新生成桌面检索台 HTML
#   4. check_updates.py     提示新增划线是否影响已有专题
#
# 用法：  cd reading-brain/scripts && ./update.sh
#（若提示无执行权限，先跑一次 chmod +x update.sh）

set -e
cd "$(dirname "$0")"
PROJECT="$(cd ../.. && pwd)"   # Document_Reading_Brain/

echo "== 0/5 解析 Obsidian 笔记 =="
if [ ! -d "$SOURCE" ]; then
  echo "找不到笔记库：$SOURCE"
  echo "把 update.sh 顶部的 SOURCE 改成你的 Obsidian 库路径，或设 READING_BRAIN_SOURCE 环境变量。"
  exit 1
fi
( cd "$PROJECT" && python3 -m reading_brain.cli --source "$SOURCE" --output output )

echo ""
echo "== 1/5 重建检索索引 =="
python3 build_index.py

echo ""
echo "== 2/5 重建书籍关系图谱 =="
python3 build_graph.py

echo ""
echo "== 3/5 重新生成检索台 =="
python3 build_app.py

echo ""
echo "== 4/5 检查专题分析是否需要更新 =="
python3 check_updates.py || true

echo ""
echo "全部完成 -> 打开 Document_Reading_Brain 文件夹下的「阅读大脑检索台.html」查看最新结果。"
