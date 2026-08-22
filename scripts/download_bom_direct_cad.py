#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, shutil, urllib.parse, urllib.request
from pathlib import Path

UA='Mozilla/5.0 bom-direct-cad/1.0'

def enc(url:str)->str:
    p=urllib.parse.urlsplit(url)
    path=urllib.parse.quote(urllib.parse.unquote(p.path),safe="/%:@!$&'()*+,;=-._~")
    query=urllib.parse.quote(urllib.parse.unquote(p.query),safe="=&?/:;+,%@-._~")
    return urllib.parse.urlunsplit((p.scheme,p.netloc,path,query,p.fragment))

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); manifest=json.loads(Path(a.manifest).read_text(encoding='utf-8')); root=Path(a.out); root.mkdir(parents=True,exist_ok=True)
    report=[]
    for x in manifest['files']:
        dest=root/x['vendor']/x['filename']; dest.parent.mkdir(parents=True,exist_ok=True)
        rec=dict(x)
        try:
            req=urllib.request.Request(enc(x['url']),headers={'User-Agent':UA,'Accept':'*/*'})
            with urllib.request.urlopen(req,timeout=180) as r, dest.open('wb') as f:
                shutil.copyfileobj(r,f,1024*1024); rec['final_url']=r.geturl(); rec['content_type']=r.headers.get('Content-Type','')
            rec.update(status='downloaded',bytes=dest.stat().st_size,sha256=sha256(dest),path=str(dest.relative_to(root)))
            if dest.stat().st_size < 1024: raise RuntimeError('download too small')
        except Exception as e:
            dest.unlink(missing_ok=True); rec.update(status='error',error=str(e))
        report.append(rec); print(rec['model'],rec['status'],rec.get('bytes',''),flush=True)
    (root/'DIRECT-CAD-REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if not all(r['status']=='downloaded' for r in report): raise SystemExit(2)

if __name__=='__main__': main()
