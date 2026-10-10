# -*- coding: utf-8 -*-
"""最终校验：渲染、页数、墨迹覆盖、以及被 smart_cut 截断的文本可读性。"""
import io
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, r"C:\AP项目文档\简历")

from docx import Document
from PIL import Image

NODE = r"C:\Users\jaysguo\AppData\Local\Programs\DSH Desktop\DSH Desktop.exe"
CLI = r"C:\Users\jaysguo\AppData\Local\Programs\DSH Desktop\resources\office-cli.mjs"
DOC = os.environ.get("RESUME_DOC", r"C:\AP项目文档\简历\_试排_final.docx")
OUT = os.environ.get("RESUME_OUT", r"C:\AP项目文档\简历\_pv_verify")


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT, ignore_errors=True)
    time.sleep(0.3)
    env = dict(os.environ)
    env["ELECTRON_RUN_AS_NODE"] = "1"
    r = subprocess.run([NODE, CLI, "render", "--input", DOC, "--output-dir", OUT,
                        "--dpi", "72"], capture_output=True, env=env, text=True,
                       encoding="utf-8", errors="replace")
    js = [l for l in r.stdout.splitlines() if l.startswith("{")]
    info = json.loads(js[-1])
    print("pageCount =", info["pageCount"], " missingFonts =", info.get("missingFonts"))
    for i, im_info in enumerate(info["images"], 1):
        p = im_info["path"]
        im = Image.open(p).convert("L")
        w, h = im.size
        px = im.load()
        rows = [y for y in range(h) if any(px[x, y] < 240 for x in range(0, w, 2))]
        print(f"  page{i}: {w}x{h} first_ink={rows[0]} last_ink={rows[-1]} "
              f"(页高 {h})  余量={h - rows[-1]}pt")
    d = Document(DOC)
    out = io.open(r"C:\AP项目文档\简历\_final_content.txt", "w", encoding="utf-8")
    for i, p in enumerate(d.paragraphs):
        out.write(f"[{i:2d}] <{p.style.name}> {p.text}\n")
    out.close()


if __name__ == "__main__":
    main()
