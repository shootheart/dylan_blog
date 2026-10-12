#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
照片书处理器 —— 照片书（photobook）的唯一工具。

你手写 albums/<name>/source.md（元数据 + 组标题 + 组说明 + 图片顺序），
本脚本把它转成 Hugo 能直接用的文章 md，并负责压缩原图。

source.md、原图、.build/ 全部不进 git；git 里只保留
content/photobook/<name>.md 这一个产物。

两条独立命令：
    python3 album-build.py <name>              build（默认）解析 source.md -> 正式 md，秒级
    python3 album-build.py images <name>        只压缩图片 -> .build/，分钟级

build 只读原图的尺寸与 EXIF，不需要先跑 images。

source.md 固定格式：

    ---
    title: "正定"
    date: 2026-10-07T00:00:00+08:00
    description: "正定古城"
    cover: IMG_20260101_133717.jpg
    ---

    这里可以写前言，会保留到正式文章的正文。

    ## 夜骑

    > 这一组的说明文字，所有照片共用。

    ![](IMG_20260101_133717.jpg "单张标题")
    > 这一张自己的补充文字，可多段。
    <!-- exif: 手动覆盖 EXIF（可省略） -->

    ![](IMG_20260101_144714.jpg)

规则：
    ## 任意级别标题      开一个新 group，标题文字即 groups.<id>.title
    > 引用块（标题之后）  group 说明
    > 引用块（图片之后）  该照片的文字
    ![](文件 "标题")      一张照片，顺序即页面与灯箱顺序
    exif                 一律自动从 EXIF 生成，可用 <!-- exif: ... --> 覆盖

用法见 README 注释与 album-build.py --help。
"""
import json
import os
import posixpath
import re
import sys
from urllib.parse import quote

import yaml
from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG_EXT = (".jpg", ".jpeg", ".png")
TIERS = ("tiny", "small", "large")

# EXIF 标签
T_ORIENT = 274
T_MAKE = 271
T_MODEL = 272
T_EXIF_IFD = 0x8769
T_EXPOSURE = 33434
T_FNUMBER = 33437
T_ISO = 34855
T_FOCAL = 37386


# ================================================================ 配置

def load_cfg():
    with open(os.path.join(ROOT, "photobook.yml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def paths(cfg, album):
    albums_dir = os.path.join(ROOT, cfg.get("albums_dir", "albums"))
    base = os.path.join(albums_dir, album)          # source.md 所在目录
    src = os.path.join(base, cfg.get("source_file", "source.md"))
    photos = os.path.join(base, "photos")
    md = os.path.join(ROOT, cfg.get("content_dir", "content/photobook"),
                      "%s.md" % album)
    out = os.path.join(ROOT, cfg.get("output_dir", ".build/photobook"), album)
    return src, photos, base, md, out


# ================================================================ 图片工具

def _read_exif(img):
    """IFD0 + Exif 子 IFD 合并后的标签字典"""
    try:
        flat = img._getexif()
        if flat:
            return flat
    except Exception:
        pass
    try:
        data = dict(img.getexif())
        try:
            data.update(dict(img.getexif().get_ifd(T_EXIF_IFD)))
        except Exception:
            pass
        return data
    except Exception:
        return {}


def _num(v):
    if v is None:
        return None
    try:
        if isinstance(v, (tuple, list)) and len(v) == 2:
            den = float(v[1])
            return float(v[0]) / den if den else None
        return float(v)
    except Exception:
        return None


def exif_line(exif):
    """把 EXIF 拼成 '相机 · 焦距 · 光圈 · 快门 · ISO'"""
    if not exif:
        return ""

    def g(tag):
        v = exif.get(tag)
        return v.strip() if isinstance(v, str) else v

    parts = []
    make = str(g(T_MAKE) or "").strip()
    model = str(g(T_MODEL) or "").strip()
    if make and model.lower().startswith(make.lower()):
        model = model[len(make):].strip()
    cam = " ".join(x for x in (make, model) if x)
    if cam:
        parts.append(cam)

    focal = _num(g(T_FOCAL))
    if focal:
        f = round(focal)
        parts.append("%dmm" % f if f >= 10 else "%.0fmm" % (f * 10))

    fnum = _num(g(T_FNUMBER))
    if fnum:
        parts.append("f/%g" % fnum)

    exp = _num(g(T_EXPOSURE))
    if exp:
        if exp >= 1:
            parts.append(("%gs" % round(exp, 1)).replace(".0s", "s"))
        else:
            parts.append("1/%ds" % round(1 / exp))

    iso = _num(g(T_ISO))
    if iso:
        parts.append("ISO %d" % round(iso))
    return " · ".join(parts)


def exif_of_file(path):
    try:
        with Image.open(path) as img:
            return exif_line(_read_exif(img))
    except Exception:
        return ""


def oriented_size(path):
    """按 EXIF 方向摆正后的 (宽, 高)，只读文件头不解码"""
    with Image.open(path) as img:
        w, h = img.size
        try:
            o = img.getexif().get(T_ORIENT)
        except Exception:
            o = None
    if o in (5, 6, 7, 8):
        w, h = h, w
    return w, h


def fit(w, h, maxdim):
    """等比缩放到长边不超过 maxdim（与 images 命令共用，保证文件名一致）"""
    m = max(w, h)
    if m <= maxdim:
        return w, h
    r = maxdim / float(m)
    return max(1, int(w * r + 0.5)), max(1, int(h * r + 0.5))


def list_photos(base):
    """递归列出相册目录下所有图片，返回相对相册目录的 posix 路径（已排序）

    基准与 source.md 一致，所以这里的路径可以直接抄进 source.md。
    """
    if not os.path.isdir(base):
        return []
    out = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.lower().endswith(IMG_EXT):
                rel = os.path.relpath(os.path.join(root, f), base)
                out.append(rel.replace(os.sep, "/"))
    return sorted(out)


def resolve_target(base, albums_dir, raw):
    """解析 source.md 里的图片引用。

    相对路径的基准是 source.md 所在目录（与普通 markdown 一致）：
        ![](photos/a.jpg)      正确写法
        ![](a.jpg)             自动回退到 photos/a.jpg（简写）
        ![](../shared/a.jpg)   相册目录之外的共享图库（不能跳出 albums/）
    绝对路径与外链也支持：
        ![](/data/photos/a.jpg)          本机绝对路径
        ![](~/Pictures/a.jpg)            家目录
        ![](https://.../a.jpg)           直接引用，不压缩不上传

    返回 dict：
        kind = "url"  -> {"kind", "url"}
        kind = "file" -> {"kind", "path", "rel", "sub", "name"}
    """
    p = raw.strip().replace("\\", "/")
    if URL_RE.match(p) or p.startswith("//"):
        return {"kind": "url", "url": raw.strip()}
    if p.startswith("~/"):
        p = os.path.expanduser(p)
    if os.path.isabs(p):
        fp = os.path.normpath(p)
        if not os.path.exists(fp):
            raise FileNotFoundError(p)
        # 外部绝对路径：OSS 侧按平铺存放
        return {"kind": "file", "path": fp, "rel": None, "sub": "",
                "name": os.path.splitext(os.path.basename(fp))[0]}
    if p == "":
        raise ValueError("图片路径为空")

    n = posixpath.normpath(p)
    root = os.path.normpath(albums_dir)
    cand = os.path.normpath(os.path.join(base, *n.split("/")))
    if not (cand == root or cand.startswith(root + os.sep)):
        raise ValueError("相对路径不能跳出 albums/ 目录")
    if not os.path.exists(cand):
        fb = os.path.normpath(os.path.join(base, "photos", *n.split("/")))
        if os.path.exists(fb):
            cand = fb
        else:
            raise FileNotFoundError(p)
    rel = os.path.relpath(cand, base).replace(os.sep, "/")
    sub = posixpath.dirname(rel)
    if sub == ".." or sub.startswith("../") or sub.startswith("/"):
        sub = ""                     # 相册目录之外：OSS 侧平铺存放
    return {"kind": "file", "path": cand, "rel": rel, "sub": sub,
            "name": os.path.splitext(os.path.basename(rel))[0]}


def url_for(prefix, album, tier, sub, name, w, h):
    """构造 OSS URL，保留子目录结构；顶层文件不产生多余斜杠。

    文件名含空格或非 ASCII 时做百分号编码（OSS 上存的仍是原名）。
    """
    slash = (sub + "/") if sub else ""
    fname = "%s_%dx%d.jpg" % (name, w, h)
    return "%s/%s/%s/%s" % (prefix,
                           quote(album, safe=""),
                           tier,
                           quote(slash + fname, safe="/-_.~"))


URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")


# ================================================================ markdown 解析

TOP_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*)\s*:(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
QUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
IMAGE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]*)\)\s*$")
INNER_TITLE_RE = re.compile(r'\s+"([^"]*)"$')
EXIF_RE = re.compile(r"^<!--\s*exif\s*:\s*(.*?)\s*-->$", re.I)
GROUP_ID_RE = re.compile(r"^(.*?)\s*\{#([^}\s]+)\}\s*$")


def _unquote(p):
    """去掉路径外层的引号或尖括号"""
    p = p.strip()
    if len(p) >= 2 and p[0] == p[-1] and p[0] in "\"'":
        return p[1:-1].strip()
    if p.startswith("<") and p.endswith(">"):
        return p[1:-1].strip()
    return p


def split_image_inner(inner):
    """拆分 markdown 图片的括号内部分 -> (路径, 标题)

    支持：
        a.jpg                -> ("a.jpg", "")
        a.jpg "标题 带空格"   -> ("a.jpg", "标题 带空格")
        <my photo.jpg>       -> ("my photo.jpg", "")
        "a b.jpg"            -> ("a b.jpg", "")
    """
    inner = inner.strip()
    m = INNER_TITLE_RE.search(inner)
    if m:
        return _unquote(inner[:m.start()]), m.group(1)
    return _unquote(inner), ""


def split_front_matter(text):
    """返回 (front matter 行列表 or None, 正文行列表)"""
    lines = text.splitlines()
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start >= len(lines) or lines[start].strip() != "---":
        return None, lines
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "---":
            return lines[start + 1:i], lines[i + 1:]
    return None, lines


def drop_top_key(fm_lines, key):
    """删除一个顶层字段（含其缩进块）"""
    out, i, n = [], 0, len(fm_lines)
    while i < n:
        m = TOP_KEY_RE.match(fm_lines[i])
        if m and m.group(1) == key:
            i += 1
            while i < n and (not fm_lines[i].strip() or fm_lines[i][0].isspace()):
                i += 1
            continue
        out.append(fm_lines[i])
        i += 1
    return out


def parse_source(text, base, albums_dir):
    """解析 source.md -> (fm_lines, fm_dict, prose, groups, photos, errors, warns)"""
    fm_lines, body = split_front_matter(text)
    if fm_lines is None:
        return None, None, [], {}, [], ["front matter 未找到（应以 --- 开头并有闭合的 --- ）"], []

    try:
        fm = yaml.safe_load("\n".join(fm_lines)) or {}
    except Exception as e:
        return fm_lines, None, [], {}, [], ["front matter 不是合法 YAML：%s" % e], []
    if not isinstance(fm, dict):
        return fm_lines, None, [], {}, [], ["front matter 顶层必须是字典"], []

    groups, photos, prose = {}, [], []
    errors, warns = [], []
    cur_group = None
    last_photo = None
    seen_heading = False
    prose_mode = True          # 还没遇到任何结构化内容，仍在前言区
    qbuf, qowner = [], None

    def owner_now():
        if last_photo is not None:
            return ("photo", last_photo)
        if cur_group is not None:
            return ("group", cur_group)
        return None

    def flush_quote():
        nonlocal qbuf, qowner
        if qbuf and qowner:
            body_txt = "\n".join(qbuf).strip("\n")
            if body_txt.strip():
                kind, owner = qowner
                key = "text"
                target = owner if kind == "photo" else groups.get(owner, {})
                old = (target.get(key) or "").strip()
                target[key] = (old + "\n" + body_txt).strip() if old else body_txt
        qbuf, qowner = [], None

    for lineno, raw in enumerate(body, 1):
        line = raw.rstrip()
        s = line.strip()

        if not s:
            if prose_mode and prose:
                prose.append("")     # 保留段落分隔
            continue

        m = IMAGE_RE.match(s)
        if m:
            flush_quote()
            alt, inner = m.group(1), m.group(2).strip()
            path, title = split_image_inner(inner)
            if not path:
                continue                  # ![]() 占位
            try:
                tgt = resolve_target(base, albums_dir, path)
            except FileNotFoundError:
                errors.append("第 %d 行：找不到图片 %s" % (lineno, path))
                continue
            except ValueError as e:
                errors.append("第 %d 行：%s（%s）" % (lineno, e, path))
                continue
            ph = {"file": path, "_t": tgt}
            t = title or alt
            if t:
                ph["alt"] = t
            if cur_group:
                ph["group"] = cur_group
            photos.append(ph)
            last_photo = ph
            prose_mode = False
            continue

        m = EXIF_RE.match(s)
        if m:
            flush_quote()
            if last_photo is not None:
                last_photo["exif"] = m.group(1).strip()
            else:
                warns.append("第 %d 行：exif 注释必须紧跟在某张图片后面，已忽略" % lineno)
            continue

        m = HEADING_RE.match(s)
        if m:
            flush_quote()
            last_photo = None
            seen_heading = True
            text = m.group(2).strip()
            mid = GROUP_ID_RE.match(text)
            gid, gtitle = (mid.group(2), mid.group(1)) if mid else (text, text)
            gid = gid.strip()
            if not gid:
                errors.append("第 %d 行：标题不能为空" % lineno)
                continue
            if gid in groups:
                gid2 = "%s-%d" % (gid, len(groups) + 1)
                warns.append("第 %d 行：group id「%s」重复，已改为「%s」" % (lineno, gid, gid2))
                gid = gid2
            groups[gid] = {"title": gtitle}
            cur_group = gid
            prose_mode = False
            continue

        m = QUOTE_RE.match(line)
        if m:
            own = owner_now()
            if own is None:
                errors.append("第 %d 行：引用块必须跟在某个标题或某张图片后面" % lineno)
                qbuf, qowner = [], None
                continue
            if qowner is not None and qowner != own:
                flush_quote()
            if qowner is None:
                qowner = own
            qbuf.append(m.group(1).strip())
            continue

        flush_quote()
        if seen_heading or last_photo is not None:
            warns.append("第 %d 行：固定格式下这里只接受 `>` 或图片，已忽略：%s"
                         % (lineno, s[:40]))
        elif prose_mode:
            prose.append(line)
        else:
            prose_mode = False

    flush_quote()

    # 丢掉没有任何照片的空 group
    used = set(p.get("group") for p in photos if p.get("group"))
    for gid in list(groups):
        if gid not in used:
            warns.append("跳过空 group「%s」" % groups[gid].get("title") or gid)
            groups.pop(gid)

    return fm_lines, fm, prose, groups, photos, errors, warns


# ================================================================ build

def render_article(src_text, doc, prose):
    fm_lines, _ = split_front_matter(src_text)
    kept = drop_top_key(fm_lines, "cover")

    blocks = []
    if doc.get("featuredImage"):
        blocks.append("featuredImage: %s" % json.dumps(doc["featuredImage"]))
    if doc.get("groups"):
        blocks.append(yaml.safe_dump({"groups": doc["groups"]}, allow_unicode=True,
                                     sort_keys=False, default_flow_style=False,
                                     width=10000).rstrip("\n"))
    blocks.append(yaml.safe_dump({"photos": doc["photos"]}, allow_unicode=True,
                                 sort_keys=False, default_flow_style=False,
                                 width=10000).rstrip("\n"))

    lines = ["---"] + kept
    for b in blocks:
        lines.extend(b.split("\n"))
    lines.append("---")
    lines.extend(prose)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n"


def skeleton_hint(album, filenames):
    lines = [
        "        ---",
        '        title: ""',
        "        date: %s" % "2026-01-01T00:00:00+08:00",
        '        description: ""',
        '        hiddenFromSearch: true',
        "        lightgallery: true",
        "        ---",
        "",
        "        ## 第一组",
        "",
        "> 这一组的说明文字。",
        "",
    ]
    for f in filenames[:6]:
        lines.append('        ![](%s)' % f)
    if len(filenames) > 6:
        lines.append("        # ... 还有 %d 张" % (len(filenames) - 6))
    return "\n".join(lines)


def build_album(cfg, album):
    src, _photos_dir, base, md_path, _ = paths(cfg, album)
    albums_dir = os.path.join(ROOT, cfg.get("albums_dir", "albums"))
    local_files = list_photos(base)          # 只用于「未使用文件」提示

    if not os.path.exists(src):
        print("[error] 找不到 %s" % src)
        if local_files:
            print("        该相册目录下已有这些照片，可照抄下面的骨架创建：\n")
            print(skeleton_hint(album, local_files))
        else:
            print("        先把原图放进 %s/photos/ 再创建 source.md" % base)
        return False

    with open(src, encoding="utf-8") as f:
        src_text = f.read()

    fm_lines, fm, prose, groups, photos, errors, warns = parse_source(
        src_text, base, albums_dir)
    if errors:
        for e in errors:
            print("[error] %s: %s" % (src, e))
        if local_files:
            print("        该相册目录下现有：%s"
                  % ", ".join(local_files[:10]))
        print("        已放弃写入，正式 md 未改动")
        return False
    for w in warns:
        print("[warn] %s: %s" % (src, w))
    if not photos:
        print("[error] %s: 没有解析到任何图片" % src)
        return False

    prefix = str(cfg["url_prefix"]).rstrip("/")
    large_max = int(cfg["sizes"]["large"]["max"])

    seen = set()
    for p in photos:
        t = p["_t"]
        key = t["url"] if t["kind"] == "url" else t["path"]
        if key in seen:
            print("[error] %s: 图片重复出现：%s" % (src, p["file"]))
            print("        已放弃写入，正式 md 未改动")
            return False
        seen.add(key)
        g = p.get("group")
        if g and g not in groups:
            print("[error] %s: %s 引用了未定义的 group「%s」" % (src, p["file"], g))
            return False

    cover = str(fm.get("cover") or "").strip()
    featured = None
    cover_tgt = None
    if cover:
        try:
            cover_tgt = resolve_target(base, albums_dir, cover)
        except (ValueError, FileNotFoundError) as e:
            print("[error] %s: cover %s" % (src, e))
            print("        已放弃写入，正式 md 未改动")
            return False
        if cover_tgt["kind"] == "url":
            print("[warn] cover 是外链 URL，列表页会直接引用它")
            featured = cover_tgt["url"]
        else:
            ckey = cover_tgt["path"]
            if ckey not in seen:
                print("[info] 封面 %s 不在文章的图片里，只用作列表页封面" % cover)
            cmax = int(cfg["sizes"]["small"]["max"])
            cw, ch = fit(*oriented_size(cover_tgt["path"]), cmax)
            featured = url_for(prefix, album, "small",
                               cover_tgt["sub"], cover_tgt["name"], cw, ch)

    out_photos = []
    for p in photos:
        t = p["_t"]
        item = {}
        if t["kind"] == "url":
            # 外链：直接引用，不压缩不上传；尺寸未知则不输出
            item["tiny"] = item["small"] = item["large"] = t["url"]
        else:
            w, h = oriented_size(t["path"])
            for tier in TIERS:
                maxdim = int(cfg["sizes"][tier]["max"])
                tw, th = fit(w, h, maxdim)
                item[tier] = url_for(prefix, album, tier,
                                     t["sub"], t["name"], tw, th)
            lw, lh = fit(w, h, large_max)
            item["width"], item["height"] = lw, lh
        if p.get("group"):
            item["group"] = p["group"]
        if p.get("alt"):
            item["alt"] = p["alt"]
        if p.get("text"):
            item["text"] = p["text"]
        ex = p.get("exif")
        if ex:
            item["exif"] = ex
        else:
            if t["kind"] == "file":
                auto = exif_of_file(t["path"])
                if auto:
                    item["exif"] = auto
        out_photos.append(item)

    doc = {"photos": out_photos}
    if groups:
        doc["groups"] = groups
    if featured:
        doc["featuredImage"] = featured

    text = render_article(src_text, doc, prose)
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(text)

    print("[ok] %s: %d 张，%d 个组 -> %s"
          % (album, len(out_photos), len(groups), md_path))

    used_rel = set()
    for p in photos:
        if p["_t"]["kind"] == "file" and p["_t"].get("rel"):
            used_rel.add(p["_t"]["rel"])
    if cover_tgt and cover_tgt["kind"] == "file" and cover_tgt.get("rel"):
        used_rel.add(cover_tgt["rel"])
    unused = [f for f in local_files if f not in used_rel]
    if unused:
        print("[hint] 相册目录下有 %d 张没写进 source.md：%s"
              % (len(unused), ", ".join(unused[:8])))
    return True


# ================================================================ images

def images_album(cfg, album, force=False):
    src, _pd, base, _md, out = paths(cfg, album)
    albums_dir = os.path.join(ROOT, cfg.get("albums_dir", "albums"))

    # 处理集合 = source.md 里引用的图片（相对/绝对路径）+ cover
    targets_in = []
    if not os.path.exists(src):
        print("[hint] %s 不存在，只处理相册目录下的图片" % src)
        for rel in list_photos(base):
            targets_in.append((os.path.join(base, *rel.split("/")),
                               posixpath.dirname(rel),
                               posixpath.splitext(posixpath.basename(rel))[0]))
    else:
        with open(src, encoding="utf-8") as f:
            _fm, fm, _prose, _groups, photos, errors, _warns = parse_source(
                f.read(), base, albums_dir)
        if errors:
            for e in errors:
                print("[error] %s: %s" % (src, e))
            print("        图片不处理，请先修好 source.md")
            return False
        for p in photos:
            t = p["_t"]
            if t["kind"] == "file":
                targets_in.append((t["path"], t["sub"], t["name"]))
        cv = str((fm or {}).get("cover") or "").strip()
        if cv:
            try:
                ct = resolve_target(base, albums_dir, cv)
            except (ValueError, FileNotFoundError):
                ct = None
            if ct and ct["kind"] == "file":
                targets_in.append((ct["path"], ct["sub"], ct["name"]))

    if not targets_in:
        print("[skip] %s: 没有需要压缩的图片" % album)
        return False

    total = 0
    done = set()
    for fpath, sub, base_name in targets_in:
        if fpath in done:
            continue
        done.add(fpath)
        targets = []
        for tier in TIERS:
            maxdim = int(cfg["sizes"][tier]["max"])
            dst_dir = os.path.join(out, tier, sub) if sub else os.path.join(out, tier)
            os.makedirs(dst_dir, exist_ok=True)
            targets.append((tier, dst_dir, base_name, maxdim,
                            int(cfg["sizes"][tier]["quality"])))
        w0, h0 = oriented_size(fpath)
        if not force and all(
                os.path.exists(os.path.join(d, "%s_%dx%d.jpg" % (b, *fit(w0, h0, md_))))
                for _t, d, b, md_, _q in targets):
            continue
        with Image.open(fpath) as raw:
            im = ImageOps.exif_transpose(raw).convert("RGB")
            ow, oh = im.size
            for _tier, dst_dir, base_, maxdim, quality in targets:
                w, h = fit(ow, oh, maxdim)
                final = os.path.join(dst_dir, "%s_%dx%d.jpg" % (base_, w, h))
                if not force and os.path.exists(final):
                    continue
                work = im.resize((w, h), Image.LANCZOS)
                tmp = final + ".part"
                work.save(tmp, format="JPEG", quality=quality,
                          optimize=True, progressive=True)
                os.replace(tmp, final)
                total += os.path.getsize(final)
        im.close()
    print("[ok] %s: 压缩完成，本轮新增 %.1f MB -> %s"
          % (album, total / 1024.0 / 1024.0, out))
    print("       上传：ossutil cp -r %s oss://your-bucket/photobook/ --update" % out)
    return True


# ================================================================ CLI

USAGE = """用法:
    python3 album-build.py [build] <album>...   解析 source.md -> content/photobook/<album>.md
    python3 album-build.py [build]             处理全部相册
    python3 album-build.py images <album>...   只压缩原图 -> .build/
    python3 album-build.py images              压缩全部相册
    python3 album-build.py -f images <album>   强制重新压缩
"""


def main():
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print(USAGE)
        return

    mode = "build"
    if args and args[0] in ("build", "images"):
        mode = args.pop(0)
    force = False
    if "-f" in args:
        force = True
        args.remove("-f")
    albums = args

    cfg = load_cfg()
    if not albums:
        albums_dir = os.path.join(ROOT, cfg.get("albums_dir", "albums"))
        albums = [d for d in sorted(os.listdir(albums_dir))
                  if os.path.isdir(os.path.join(albums_dir, d))] \
            if os.path.isdir(albums_dir) else []
    if not albums:
        print("没有找到相册。新建：")
        print("  mkdir -p albums/<name>/photos && touch albums/<name>/source.md")
        return

    for a in albums:
        if mode == "images":
            images_album(cfg, a, force=force)
        else:
            build_album(cfg, a)


if __name__ == "__main__":
    main()