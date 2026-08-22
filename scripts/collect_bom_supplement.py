#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, hashlib, html, json, re, shutil, urllib.parse, urllib.request
from html.parser import HTMLParser
from pathlib import Path

UA = "Mozilla/5.0 cad-bom-supplement/1.0"


def safe_name(s: str) -> str:
    s = urllib.parse.unquote(str(s))
    return re.sub(r"[^A-Za-z0-9._+()-]+", "_", s.strip())[:180] or "part"


def encode_url(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(urllib.parse.unquote(p.path), safe="/%:@!$&'()*+,;=-._~")
    query = urllib.parse.quote(urllib.parse.unquote(p.query), safe="=&?/:;+,%@-._~")
    return urllib.parse.urlunsplit((p.scheme, p.netloc, path, query, p.fragment))


def req(url: str):
    return urllib.request.Request(encode_url(url), headers={"User-Agent": UA, "Accept": "*/*", "Accept-Language":"zh-CN,zh;q=0.9,en;q=0.7"})


def get_text(url: str) -> str:
    with urllib.request.urlopen(req(url), timeout=120) as r:
        raw = r.read()
    for enc in ("utf-8","gb18030","latin1"):
        try: return raw.decode(enc)
        except UnicodeDecodeError: pass
    return raw.decode("utf-8", errors="replace")


def download(url: str, dest: Path) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req(url), timeout=240) as r, tmp.open("wb") as f:
        final_url = r.geturl(); ctype = r.headers.get("Content-Type","")
        shutil.copyfileobj(r, f, length=1024*1024)
    tmp.replace(dest)
    return {"final_url": final_url, "content_type": ctype, "bytes": dest.stat().st_size}


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.items=[]; self.href=None; self.txt=[]
    def handle_starttag(self, tag, attrs):
        if tag.lower()=="a": self.href=dict(attrs).get("href"); self.txt=[]
    def handle_data(self,data):
        if self.href is not None: self.txt.append(data)
    def handle_endtag(self,tag):
        if tag.lower()=="a" and self.href is not None:
            self.items.append((self.href," ".join(self.txt).strip())); self.href=None; self.txt=[]


def discover(page: str, exts: list[str]) -> list[tuple[str,str]]:
    text=get_text(page); parser=Links(); parser.feed(text)
    exts=tuple(x.lower() for x in exts); out=[]; seen=set()
    for href,label in parser.items:
        href=html.unescape(href or "").strip(); label=html.unescape(label or "").strip()
        if any(e in (href+" "+label).lower() for e in exts):
            u=urllib.parse.urljoin(page,href)
            if u.startswith(("http://","https://")) and u not in seen:
                seen.add(u); out.append((u,label))
    # JSON/script embedded absolute and escaped URLs
    candidates = re.findall(r'https?:(?:\\/\\/|//)[^"\'<>\s]+', text)
    for raw in candidates:
        u=html.unescape(raw.replace("\\/","/"))
        if any(e in u.lower() for e in exts) and u not in seen:
            seen.add(u); out.append((u,Path(urllib.parse.urlsplit(u).path).name))
    # quoted relative CAD URLs in scripts
    for raw in re.findall(r'["\']([^"\']+\.(?:stp|step|dwg|dxf|x_t|igs|iges)(?:\?[^"\']*)?)["\']', text, flags=re.I):
        u=urllib.parse.urljoin(page, html.unescape(raw).replace("\\/","/"))
        if u not in seen:
            seen.add(u); out.append((u,Path(urllib.parse.urlsplit(u).path).name))
    return out


def fname(url,label,idx):
    m=re.search(r'([^/\\]+\.(?:stp|step|dwg|dxf|x_t|igs|iges|zip))', label or "", re.I)
    if m: return safe_name(m.group(1))
    p=Path(urllib.parse.unquote(urllib.parse.urlsplit(url).path)).name
    return safe_name(p or f"cad_{idx:03d}.bin")


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",required=True); ap.add_argument("--sources",default="cad-libraries/bom-supplement-sources.json")
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    src=json.loads(Path(a.sources).read_text(encoding="utf-8")); report=[]
    for page in src["pages"]:
        vendor,name,url=page["vendor"],page["name"],page["url"]
        dest=out/safe_name(vendor)/safe_name(name); dest.mkdir(parents=True,exist_ok=True)
        rec={"vendor":vendor,"name":name,"page":url,"status":"pending","files":[]}
        print(f"[page] {vendor} {name}",flush=True)
        try:
            links=discover(url,page.get("extensions",[".stp",".step"]))[:int(page.get("max_files",30))]
            rec["discovered"]=len(links); ok=0
            for i,(u,label) in enumerate(links,1):
                target=dest/fname(u,label,i); fr={"url":u,"label":label,"file":target.name}
                try:
                    meta=download(u,target)
                    if target.stat().st_size < 1024 and "text/html" in meta["content_type"].lower():
                        raise RuntimeError("small HTML landing page, not CAD")
                    fr.update({"status":"downloaded","sha256":sha256(target),**meta}); ok+=1
                except Exception as e:
                    target.unlink(missing_ok=True); fr.update({"status":"error","error":str(e)})
                    print(f"WARN {u}: {e}",flush=True)
                rec["files"].append(fr)
            rec.update({"status":"ok","downloaded":ok})
        except Exception as e:
            rec.update({"status":"error","error":str(e)})
        report.append(rec)
    (out/"SUPPLEMENT-REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    total=sum(1 for p in out.rglob("*") if p.is_file() and p.suffix.lower() in {".stp",".step",".dwg",".dxf",".x_t",".igs",".iges"})
    print(f"SUPPLEMENT DONE: {total} CAD files",flush=True)

if __name__=="__main__": main()
