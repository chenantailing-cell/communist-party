#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把本地站点目录整体推送为一个新的 commit（走 GitHub Git Data API，不需要 git 客户端）。

用法：
    set GITHUB_TOKEN=...            # 或 --token
    python publish.py --repo chenantailing-cell/communist-party --root . --enable-pages

--root 指向站点根（含 index.html）；--enable-pages 顺便打开 GitHub Pages（main 分支根目录）。
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
SKIP_DIRS = {".git", "__pycache__"}
SKIP_FILES = {"党课题库.md.bak"}


def call(method, path, token, payload=None, accept="application/vnd.github+json"):
    url = API + path
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "dangke-publish")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, (json.loads(body) if body.strip() else None)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}


def collect(root):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name in SKIP_FILES:
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel.startswith("预览") or rel.endswith(".png"):
                continue
            files.append((rel, full))
    return sorted(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--root", default=".")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--message", default="更新党课题库站点")
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    ap.add_argument("--enable-pages", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = collect(os.path.abspath(args.root))
    print("待推送 %d 个文件：" % len(files))
    for rel, full in files:
        print("  %-34s %8d B" % (rel, os.path.getsize(full)))
    if args.dry_run:
        return 0
    if not args.token:
        print("缺少 token：设置 GITHUB_TOKEN 或传 --token", file=sys.stderr)
        return 2

    owner_repo = args.repo
    # 1) 现有分支
    st, ref = call("GET", "/repos/%s/git/ref/heads/%s" % (owner_repo, args.branch), args.token)
    parent_sha = base_tree = None
    if st == 200 and isinstance(ref, dict):
        parent_sha = ref["object"]["sha"]
        st2, commit = call("GET", "/repos/%s/git/commits/%s" % (owner_repo, parent_sha), args.token)
        if st2 == 200:
            base_tree = commit["tree"]["sha"]
        print("已有分支 %s @ %s" % (args.branch, parent_sha[:10]))
    else:
        # 空仓库：Git Data API 建 blob 会 409，先用 Contents API 打一个首提交（README）当底座
        print("仓库为空（HTTP %s），先用 Contents API 建立首个提交…" % st)
        bootstrap = os.path.join(os.path.abspath(args.root), "README.md")
        if not os.path.exists(bootstrap):
            bootstrap = os.path.join(os.path.abspath(args.root), "index.html")
        with open(bootstrap, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        st3, out3 = call("PUT", "/repos/%s/contents/%s" % (owner_repo, os.path.basename(bootstrap)),
                         args.token, {"message": "bootstrap: " + args.message, "content": b64})
        if st3 not in (200, 201):
            print("bootstrap 失败：%s" % out3, file=sys.stderr)
            return 3
        parent_sha = out3["commit"]["sha"]
        base_tree = out3["commit"]["tree"]["sha"]
        print("bootstrap commit %s" % parent_sha[:10])

    # 2) 上传 blob
    tree_items = []
    for rel, full in files:
        with open(full, "rb") as f:
            content = base64.b64encode(f.read()).decode("ascii")
        st, blob = call("POST", "/repos/%s/git/blobs" % owner_repo, args.token,
                        {"content": content, "encoding": "base64"})
        if st != 201:
            print("blob 失败 %s: %s" % (rel, blob), file=sys.stderr)
            return 3
        tree_items.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print("  blob ✓ %s" % rel)

    # 3) tree / commit / ref
    payload = {"tree": tree_items}
    if base_tree:
        payload["base_tree"] = base_tree
    st, tree = call("POST", "/repos/%s/git/trees" % owner_repo, args.token, payload)
    if st != 201:
        print("tree 失败：%s" % tree, file=sys.stderr)
        return 4

    commit_payload = {"message": args.message, "tree": tree["sha"]}
    if parent_sha:
        commit_payload["parents"] = [parent_sha]
    st, commit = call("POST", "/repos/%s/git/commits" % owner_repo, args.token, commit_payload)
    if st != 201:
        print("commit 失败：%s" % commit, file=sys.stderr)
        return 5
    print("commit %s" % commit["sha"][:10])

    if parent_sha:
        st, out = call("PATCH", "/repos/%s/git/refs/heads/%s" % (owner_repo, args.branch),
                       args.token, {"sha": commit["sha"], "force": False})
    else:
        st, out = call("POST", "/repos/%s/git/refs" % owner_repo, args.token,
                       {"ref": "refs/heads/%s" % args.branch, "sha": commit["sha"]})
    if st not in (200, 201):
        print("更新分支失败：%s" % out, file=sys.stderr)
        return 6
    print("分支 %s 已指向新 commit" % args.branch)

    if args.enable_pages:
        st, out = call("POST", "/repos/%s/pages" % owner_repo, args.token,
                       {"source": {"branch": args.branch, "path": "/"}})
        if st in (201, 204):
            print("GitHub Pages 已开启")
        elif st == 409:
            print("GitHub Pages 已存在，跳过")
        else:
            print("开启 Pages 返回 %s：%s" % (st, out))

    owner = owner_repo.split("/")[0]
    name = owner_repo.split("/")[1]
    print("完成后约 1 分钟可访问：https://%s.github.io/%s/" % (owner.lower(), name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
