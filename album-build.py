#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
照片书图片处理器 —— 替代 hugophotoswipe，只做「压缩 + 生成元数据」。

读取 photobook.yml 的配置，把 albums/<name>/photos/ 里的原图压成
tiny/small/large 三档（EXIF 自动旋转，手机竖拍可摆正），并把
captions.yaml 中的组说明与单张说明写进
content/photobook/<name>.md 的 front matter。

用法:
    cd ~/dylan_blog
    python3 album-build.py                  # 处理全部相册
    python3 album-build.py kyoto-autumn     # 只处理一个相册
    python3 album-build.py -f kyoto-autumn  # 强制重建（忽略已有产物）
    python3 album-build.py --init           # 只把 EXIF 回填进 captions.yaml

产物:
    .build/photobook/<name>/{tiny,small,large}/*.jpg   待上传 OSS
    content/photobook/<name>.md                         front matter 里的
                                                       photos / groups

EXIF:
    python3 album-build.py --init kyoto-autumn
        扫描 photos/，把每张照片的 EXIF 拼成
            "Canon EOS R5 · 35mm · f/2.0 · 1/200s · ISO 400"
        直接写回 captions.yaml（已填过的不动，注释与排版保留）。
        文件不存在时自动创建骨架。

    也可以在 captions.yaml 里写 exif: auto，让 build 时再从 EXIF 解析。
"""
import json
import os
import re
import sys

import yaml
from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
TIERS = ("tiny", "small", "large")
IMG_EXT = (".jpg", ".jpeg", ".png")

# EXIF 标签
T_MAKE = 271
T_MODEL = 272
T_EXIF_IFD = 0x8769
T_EXPOSURE = 33434
T_FNUMBER = 33437
T_ISO = 34855
T_FOCAL = 37386


# ---------------------------------------------------------------- EXIF

def _read_exif(img):
    """返回 IFD0 + Exif 子 IFD 合并后的标签字典，失败返回 {}"""
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
    """EXIF 数值可能是 IFDRational 或 (num, den) 元组"""
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
    """把 EXIF 标签拼成 '相机 · 焦距 · 光圈 · 快门 · ISO'"""
    if not exif:
        return ""

    def g(tag):
        v = exif.get(tag)
        return v.strip() if isinstance(v, str) else v

    parts = []

    make = str(g(T_MAKE) or "").strip()
    model = str(g(T_MODEL) or "").strip()
    if make and model.lower().startswith(make.lower()):
        # 避免 "Canon Canon EOS R5" / "Nikon NIKON Z 9"
        model = model[len(make):].strip()
    cam = " ".join(x for x in (make, model) if x)
    if cam:
        parts.append(cam)

    focal = _num(g(T_FOCAL))
    if focal:
        focal = round(focal)
        parts.append("%dmm" % focal if focal >= 10 else "%.0fmm" % (focal * 10))

    fnum = _num(g(T_FNUMBER))
    if fnum:
        parts.append("f/%g" % fnum)

    exp = _num(g(T_EXPOSURE))
    if exp:
        if exp >= 1:
            s = "%gs" % round(exp, 1)
            parts.append(s[:-2] + "s" if s.endswith(".0s") else s)
        else:
            parts.append("1/%ds" % round(1 / exp))

    iso = _num(g(T_ISO))
    if iso:
        parts.append("ISO %d" % round(iso))

    return " · ".join(parts)


def exif_of_file(path):
    """读一张图的 EXIF 并拼成字符串，无可用信息返回 ''"""
    try:
        with Image.open(path) as img:
            return exif_line(_read_exif(img))
    except Exception:
        return ""


# ---------------------------------------------------------------- captions 回填

def _indent_of(lines):
    for l in lines:
        if l.strip() and l[0].isspace():
            return " " * (len(l) - len(l.lstrip()))
    return "  "


def merge_exif(text, missing):
    """把缺失的 exif 写进 captions.yaml 文本，尽量不破坏原有排版与注释。

    missing: [(filename, exif_string), ...]
    """
    lines = text.splitlines() if text else []

    for fname, value in missing:
        quoted = json.dumps(value, ensure_ascii=False)
        head = re.compile(r"^%s\s*:(.*)$" % re.escape(fname))
        hits = [i for i, l in enumerate(lines) if head.match(l)]
        if len(hits) > 1:
            print("[warn] %s: 在 captions.yaml 里出现了 %d 次，"
                  "请只保留一处（已改写最后一处）" % (fname, len(hits)))
        idx = hits[-1] if hits else None

        if idx is None:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append("%s:" % fname)
            lines.append("  exif: %s" % quoted)
            continue

        raw = head.match(lines[idx]).group(1)
        cm = re.match(r"^(.*?)\s+#(.*)$", raw)      # 拆出行内注释
        inline = cm.group(1).strip() if cm else raw.strip()
        comment = "  #" + cm.group(2) if cm else ""

        if inline:
            if inline in ("{}", "{ }"):        # 05.jpg: {}  → 展开成块
                lines[idx] = "%s:" % fname
                lines.insert(idx + 1, "  exif: %s%s" % (quoted, comment))
            else:
                print("[warn] %s: 行内写法 '%s: %s' 无法安全改写，"
                      "请改成块状后重跑" % (fname, fname, inline))
            continue

        # 块尾：下一个顶格非空行或文件结尾
        end = idx + 1
        while end < len(lines):
            l = lines[end]
            if l.strip() and not l[0].isspace():
                break
            end += 1

        exif_re = re.compile(r"^(\s*)exif\s*:")
        patched = False
        for i in range(idx + 1, end):
            m = exif_re.match(lines[i])
            if m:
                lines[i] = "%sexif: %s" % (m.group(1), quoted)
                patched = True
                break
        if not patched:
            lines.insert(end, "%sexif: %s" % (_indent_of(lines[idx + 1:end]), quoted))

    return "\n".join(lines).rstrip("\n") + "\n"


def cmd_init(cfg, album):
    """只把 EXIF 回填进 captions.yaml，不压缩图片、不生成 data"""
    adir = os.path.join(ROOT, cfg.get("albums_dir", "albums"), album)
    photosd = os.path.join(adir, "photos")
    capfile = os.path.join(adir, "captions.yaml")

    if not os.path.isdir(photosd):
        print("[skip] %s: 没有 photos 目录" % album)
        return

    files = [f for f in sorted(os.listdir(photosd)) if f.lower().endswith(IMG_EXT)]
    if not files:
        print("[skip] %s: photos 目录为空" % album)
        return

    text = "" if not os.path.exists(capfile) else \
        open(capfile, encoding="utf-8").read()
    try:
        data = yaml.safe_load(text) or {}
    except Exception as e:
        print("[error] %s: captions.yaml 解析失败 %s" % (capfile, e))
        return
    if not isinstance(data, dict):
        print("[error] %s: 顶层必须是字典" % capfile)
        return

    missing = []
    no_exif = []
    for fname in files:
        entry = data.get(fname)
        cur = entry.get("exif") if isinstance(entry, dict) else None
        cur = "" if cur is None else str(cur).strip()
        if cur and cur.lower() != "auto":
            continue                      # 已填过，不动
        line = exif_of_file(os.path.join(photosd, fname))
        if line:
            missing.append((fname, line))
        else:
            no_exif.append(fname)

    done = len(files) - len(missing) - len(no_exif)
    print("[info] %s: 共 %d 张，已填 %d 张，"
          "可从 EXIF 填充 %d 张，无 EXIF %d 张"
          % (album, len(files), done, len(missing), len(no_exif)))
    if no_exif:
        print("       无 EXIF（截图 / 已去除元数据的图）：%s"
              % ", ".join(no_exif))

    if not missing:
        print("[skip] %s: captions.yaml 无需改动 -> %s" % (album, capfile))
        return

    out = merge_exif(text, missing)
    with open(capfile, "w", encoding="utf-8") as f:
        f.write(out)
    print("[ok] %s: 回填 %d 张的 exif -> %s"
          % (album, len(missing), capfile))


# ---------------------------------------------------------------- front matter

# 由脚本托管的顶层字段（每次 build 会被整段重写）
MANAGED_KEYS = ("photos", "groups")
# 已废弃的顶层字段（旧的 photoData，切换到 front matter 后无用了）
DROP_KEYS = ("photoData",)

TOP_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*)\s*:(.*)$")


def _in_block(fm, i, n):
    """从 i 开始，判断是否仍在同一个 YAML 顶层区块内。

    区块包含：空行、缩进行、以及与父键同缩进的序列项（`- xxx`）。
    返回该区块结束后的行号。
    """
    while i < n:
        l = fm[i]
        if not l.strip() or l[0].isspace() or l.startswith("-"):
            i += 1
            continue
        break
    return i


def split_front_matter(text):
    """返回 (front matter 行列表 or None, 正文行列表)"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, lines
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], lines[i + 1:]
    return None, lines


def sync_front_matter(md_path, doc):
    """把 doc 里的 groups / photos 写进 markdown 的 front matter。

    只替换 photos: 与 groups: 两段以及 DROP_KEYS 里的单行，
    其余 front matter 字段、注释、缩进、空行、正文全部原样保留。
    """
    text = open(md_path, encoding="utf-8").read()
    fm, body = split_front_matter(text)
    if fm is None:
        raise ValueError("front matter 未找到（首行必须是 ---，且有闭合的 --- ）")

    # 1)剔除旧区块
    kept, i, n = [], 0, len(fm)
    while i < n:
        m = TOP_KEY_RE.match(fm[i])
        if m and (m.group(1) in MANAGED_KEYS or m.group(1) in DROP_KEYS):
            i = _in_block(fm, i + 1, n)
            continue
        kept.append(fm[i])
        i += 1

    # 2) 追加新区块
    block = ""
    if doc.get("groups"):
        block += yaml.safe_dump({"groups": doc["groups"]}, allow_unicode=True,
                                sort_keys=False, default_flow_style=False,
                                width=10000)
    block += yaml.safe_dump({"photos": doc["photos"]}, allow_unicode=True,
                            sort_keys=False, default_flow_style=False,
                            width=10000)

    new_fm = kept + block.rstrip("\n").split("\n")
    while new_fm and not new_fm[-1].strip():
        new_fm.pop()

    out = "\n".join(["---"] + new_fm + ["---"] + body)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(out if out.endswith("\n") else out + "\n")


# ---------------------------------------------------------------- 主流程

def resolve_md(content_dir, album):
    """定位相册页markdown。

    优先扁平写法 content/photobook/<album>.md（与 content/posts 一致），
    兼容旧的 page bundle 写法 content/photobook/<album>/index.md。
    两者都不存在时返回扁平路径，供报错提示。
    """
    flat = os.path.join(content_dir, "%s.md" % album)
    bundled = os.path.join(content_dir, album, "index.md")
    if os.path.exists(flat):
        return flat
    if os.path.exists(bundled):
        return bundled
    return flat


def build(cfg, album, force=False):
    albums_dir = os.path.join(ROOT, cfg.get("albums_dir", "albums"))
    out_root = os.path.join(ROOT, cfg.get("output_dir", ".build/photobook"))
    content_dir = os.path.join(ROOT, cfg.get("content_dir", "content/photobook"))
    prefix = str(cfg["url_prefix"]).rstrip("/")
    sizes = cfg["sizes"]

    adir = os.path.join(albums_dir, album)
    photosd = os.path.join(adir, "photos")
    capfile = os.path.join(adir, "captions.yaml")
    md_path = resolve_md(content_dir, album)
    if not os.path.exists(capfile):
        print("[hint] %s: 还没有 captions.yaml，"
              "可用 python3 album-build.py --init %s 自动创建并填充 exif"
              % (capfile, album))
    if not os.path.exists(md_path):
        print("[error] 找不到 %s" % md_path)
        print("        请先手动创建该文件并写好 title / date / description，"
              "脚本只会写入 photos 与 groups")
        return
    caps = {}
    if os.path.exists(capfile):
        with open(capfile, encoding="utf-8") as f:
            caps = yaml.safe_load(f) or {}

    if not os.path.isdir(photosd):
        print("[skip] %s: 没有 photos 目录" % album)
        return

    files = [f for f in sorted(os.listdir(photosd)) if f.lower().endswith(IMG_EXT)]
    if not files:
        print("[skip] %s: photos 目录为空" % album)
        return

    # ---- 组说明（可选；只限相册内） ----
    groups = {}
    if isinstance(caps.get("groups"), dict):
        for gid, g in caps["groups"].items():
            if not isinstance(g, dict):
                continue
            node = {}
            if g.get("title"):
                node["title"] = str(g["title"]).strip()
            if g.get("text"):
                node["text"] = str(g["text"]).strip()
            if node:
                groups[str(gid)] = node

    photos = []
    grand = 0
    for fname in files:
        src = os.path.join(photosd, fname)
        stem = os.path.splitext(fname)[0]

        targets = {}
        for t in TIERS:
            maxdim = int(sizes[t]["max"])
            dst_dir = os.path.join(out_root, album, t)
            os.makedirs(dst_dir, exist_ok=True)
            targets[t] = (
                os.path.join(dst_dir, "%s_%d.jpg" % (stem, maxdim)),
                maxdim,
                int(sizes[t]["quality"]),
            )

        pending = [t for t in TIERS if force or not os.path.exists(targets[t][0])]
        im = None
        if pending:
            with Image.open(src) as raw:
                # EXIF 自动旋转：手机竖拍的照片在这里摆正
                im = ImageOps.exif_transpose(raw).convert("RGB")
                for t in pending:
                    dst, maxdim, quality = targets[t]
                    work = im.copy()
                    work.thumbnail((maxdim, maxdim), Image.LANCZOS)
                    work.save(dst, quality=quality, optimize=True, progressive=True)

        urls = {}
        dims = {}
        for t in TIERS:
            dst = targets[t][0]
            with Image.open(dst) as out:
                dims[t] = out.size
            urls[t] = "%s/%s/%s/%s_%d.jpg" % (
                prefix, album, t, stem, int(sizes[t]["max"]))
        grand += sum(os.path.getsize(targets[t][0]) for t in TIERS)
        if im is not None:
            im.close()

        item = {
            "tiny": urls["tiny"],
            "small": urls["small"],
            "large": urls["large"],
            "width": dims["large"][0],
            "height": dims["large"][1],
        }

        # ---- 单张说明（全部可选） ----
        c = caps.get(fname)
        if isinstance(c, dict):
            grp = c.get("group")
            if grp:
                item["group"] = str(grp).strip()
            for key, field in (("title", "alt"), ("text", "text"), ("exif", "exif")):
                v = c.get(key)
                if v is None:
                    continue
                v = str(v).strip()
                if not v:
                    continue
                if key == "exif" and v.lower() == "auto":
                    v = exif_of_file(src)
                if v:
                    item[field] = v

        if "group" in item and item["group"] not in groups:
            print("[warn] %s/%s: captions.yaml 里没有 groups.%s 的定义，忽略归组"
                  % (album, fname, item["group"]))
            item.pop("group")

        photos.append(item)

    doc = {"groups": groups, "photos": photos}
    try:
        sync_front_matter(md_path, doc)
    except ValueError as e:
        print("[error] %s: %s" % (md_path, e))
        return
    print("[ok] %s: %d 张，压缩后共 %.1f MB -> %s (front matter)"
          % (album, len(photos), grand / 1024.0 / 1024.0, md_path))


def main():
    args = sys.argv[1:]
    force = "-f" in args
    init = "--init" in args
    args = [a for a in args if a not in ("-f", "--init")]

    with open(os.path.join(ROOT, "photobook.yml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    albums_dir = os.path.join(ROOT, cfg.get("albums_dir", "albums"))
    if not args and os.path.isdir(albums_dir):
        args = [d for d in sorted(os.listdir(albums_dir))
                if os.path.isdir(os.path.join(albums_dir, d))]

    if not args:
        print("没有找到相册。新建一个相册目录：")
        print("  mkdir -p albums/<name>/photos && touch albums/<name>/captions.yaml")
        return

    for a in args:
        cmd_init(cfg, a) if init else build(cfg, a, force=force)


if __name__ == "__main__":
    main()