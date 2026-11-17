# 党课题库（网页版）

在线地址：**https://chenantailing-cell.github.io/communist-party/**

按四种题型浏览（单选 / 多选 / 填空 / 判断），每种题型内的小题按题目背景的历史时间先后排列；「时间轴」视图把四类混一起按年代串。

## 目录

```
index.html          入口页
assets/app.js       前端逻辑：读取、排序、渲染、标记复习
data/manifest.json  名单：网页要加载哪些套（只追加）
data/corrections.json  修正：按 id 改答案/补时间，不动已上传的套题
data/sets/<setId>.json 一套题一个文件，文件名 = 日期 + 序号
data/concepts.json  「概念」分类：十一课的概念条目，按课次
source/md2json.py   把 markdown 题库转成 sets/*.json
source/党课题库.md   题库源文件（唯一手工维护的地方）
source/concepts2json.py  概念 md → data/concepts.json
source/概念.md      概念源文件（按课次手工维护）
CHANGELOG.md        每套一行流水账
```

## 加一套新题（三步）

1. 在 `source/党课题库.md` 里继续往下录，每题末尾写一行 `**时间：** 1945年4月 七大`。
2. 转换（在仓库根执行，需要 Python 3）：

   ```bash
   python source/md2json.py source/党课题库.md \
     --set 2026-11-22-02 --title "第二套" \
     --out data/sets --manifest data/manifest.json
   ```

   脚本会把新文件名追加进 `data/manifest.json`，已有套题文件不动。
3. `git add -A && git commit -m "新增：2026-11-22-02" && git push`。

## 加概念（按课次，十一课）

「概念」是独立分类，存在 `data/concepts.json`，不混进任何一套题，也不动已有套题。

1. 在 `source/概念.md` 里按课次加一节 `## 第X课 课名`，每条概念一个 `### 第 N 条`：

   ```markdown
   ## 第一课 党的性质与指导思想

   ### 第 1 条

   **概念：** 党的性质

   **释义：** 中国共产党是中国工人阶级的先锋队……

   **补充：** （补充释义必须整体用（）括起）

   **时间：** 2022年10月 现行党章      ← 可省略

   **标签：** 党章、性质                ← 可省略，课次标签自动加
   ```

2. 转换（在 `site/` 下执行）：

   ```bash
   python source/concepts2json.py source/概念.md --out data/concepts.json
   ```

3. 网页「概念」标签页按课次顺序显示，条目 id 形如 `concept-01-001`，直接可追溯到课次。

校验：同课内概念重名、条号重复、缺释义、补充没用（）括起，转换会报错且不写入；跨课重名只提示，留到最后统一合并时确认。

## 发布（本机网络受限，走 API）

这台机器上 `github.com` 不可达（`git push` / SSH / 网页全被挡），只有 `api.github.com` 通，所以发布用 API 直推：

```bash
set GITHUB_TOKEN=github_pat_xxx
python source/publish.py --repo chenantailing-cell/communist-party --root . --enable-pages --message "新增：2026-11-22-02"
```

`publish.py` 会把当前目录所有文件打成一次提交推到 `main`（已存在分支时基于它更新，不会丢历史）。
在**网络正常**的机器上也可以照常 `git push`，两条路等价。

## 本地预览

```bash
python -m http.server 8123
# 浏览器打开 http://127.0.0.1:8123/
```

## 说明

- 静态站：不能在线改答案。发现错题改 `data/corrections.json`（按 id 覆盖字段），旧套题保持原样。
- 「标记复习」存在浏览器本地（localStorage），换设备不跟随。
