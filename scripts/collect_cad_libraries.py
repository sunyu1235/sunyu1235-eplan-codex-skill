#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect CAD component libraries that do not require upstream login.

Design goals:
- no browser automation and no account/session cookies;
- prefer open-source/public Git repositories and anonymous vendor download URLs;
- keep upstream license/notices;
- build a cache for electrical-panel layout, not a general mechanical mega-library;
- fail soft on one source so the rest of the cache is still usable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = ROOT / "cad-libraries" / "sources.json"
UA = "sunyu1235-eplan-codex-skill-cad-collector/1.0"

CAD_EXTS = {
    ".step", ".stp", ".fcstd", ".stl", ".brep", ".iges", ".igs",
    ".dxf", ".dwg", ".ipt", ".iam", ".sldprt", ".sldasm", ".obj",
}
KEEP_NAMES = {
    "license", "license.txt", "license.md", "license-assets", "license-assets.txt",
    "copying", "copying.txt", "third_party_notices.md", "readme.md", "readme.txt",
}


def log(msg: str) -> None:
    print(msg, flush=True)


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    log("+ " + " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd, check=check, text=True)


def safe_name(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._+()-]+", "_", text.strip())
    return text[:160] or "part"


def request_bytes(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def request_json(url: str, timeout: int = 60):
    return json.loads(request_bytes(url, timeout=timeout).decode("utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sparse_clone(repo: str, sparse_paths: list[str], dest: Path, branch: str | None = None) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    clone = ["git", "clone", "--depth", "1", "--filter=blob:none", "--no-checkout"]
    if branch:
        clone += ["--branch", branch]
    clone += [repo, str(dest)]
    run(clone)
    run(["git", "sparse-checkout", "init", "--cone"], cwd=dest)
    run(["git", "sparse-checkout", "set", *sparse_paths], cwd=dest)
    run(["git", "checkout"], cwd=dest)
    shutil.rmtree(dest / ".git", ignore_errors=True)


def clone_full(repo: str, dest: Path, branch: str | None = None) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [repo, str(dest)]
    run(cmd)
    shutil.rmtree(dest / ".git", ignore_errors=True)


def prune_non_cad(root: Path) -> tuple[int, int]:
    """Keep CAD, text/license metadata, scripts and small JSON/YAML metadata."""
    kept = removed = 0
    text_exts = {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".py"}
    for p in sorted(root.rglob("*"), reverse=True):
        if p.is_dir():
            continue
        name = p.name.lower()
        ext = p.suffix.lower()
        keep = ext in CAD_EXTS or ext in text_exts or name in KEEP_NAMES or name.startswith("license")
        if keep:
            kept += 1
        else:
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
    for d in sorted([x for x in root.rglob("*") if x.is_dir()], key=lambda x: len(x.parts), reverse=True):
        try:
            d.rmdir()
        except OSError:
            pass
    return kept, removed


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=180) as r, tmp.open("wb") as f:
        shutil.copyfileobj(r, f, length=1024 * 1024)
    tmp.replace(dest)


def unpack_zip(zip_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)


def extract_parts(payload) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("items", "results", "parts", "data"):
        val = payload.get(key)
        if isinstance(val, list):
            return [x for x in val if isinstance(x, dict)]
        if isinstance(val, dict):
            nested = extract_parts(val)
            if nested:
                return nested
    return []


def pick_step_url(item: dict) -> str | None:
    for key in ("stepUrl", "step_url", "downloadUrl", "download_url", "url"):
        v = item.get(key)
        if isinstance(v, str) and (".step" in v.lower() or ".stp" in v.lower() or key in {"stepUrl", "step_url"}):
            return v
    for container_key in ("files", "downloads", "assets"):
        vals = item.get(container_key)
        if isinstance(vals, list):
            for v in vals:
                if isinstance(v, dict):
                    u = v.get("url") or v.get("downloadUrl")
                    n = str(v.get("name") or v.get("format") or "").lower()
                    if isinstance(u, str) and ("step" in n or ".stp" in u.lower() or ".step" in u.lower()):
                        return u
    return None


def collect_step_parts(base_api: str, queries: list[str], dest: Path, limit: int) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    catalog: list[dict] = []
    downloaded = 0
    for q in queries:
        qs = urllib.parse.urlencode({"q": q, "pageSize": limit})
        url = f"{base_api.rstrip('/')}/parts?{qs}"
        log(f"[step.parts] query: {q}")
        try:
            payload = request_json(url)
            items = extract_parts(payload)[:limit]
        except Exception as e:
            log(f"WARN step.parts query failed: {q}: {e}")
            catalog.append({"query": q, "error": str(e)})
            continue
        qdir = dest / safe_name(q)
        qdir.mkdir(exist_ok=True)
        for idx, item in enumerate(items, 1):
            u = pick_step_url(item)
            model = str(item.get("name") or item.get("title") or item.get("partNumber") or item.get("id") or f"part_{idx}")
            record = {"query": q, "model": model, "id": item.get("id"), "stepUrl": u}
            if not u:
                record["status"] = "no_step_url"
                catalog.append(record)
                continue
            ext = ".step" if ".step" in u.lower() else ".stp"
            target = qdir / f"{idx:02d}_{safe_name(model)}{ext}"
            try:
                download_file(u, target)
                record.update({"status": "downloaded", "file": str(target.relative_to(dest)), "sha256": sha256_file(target)})
                downloaded += 1
            except Exception as e:
                record.update({"status": "error", "error": str(e)})
                log(f"WARN step.parts download failed: {model}: {e}")
            catalog.append(record)
    (dest / "_catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"downloaded": downloaded, "catalog_records": len(catalog)}


def collect_vendor(entry: dict, dest_root: Path) -> dict:
    name = entry["name"]
    vendor = entry.get("vendor", "Vendor")
    url = entry["url"]
    dest = dest_root / safe_name(vendor) / safe_name(name)
    dest.mkdir(parents=True, exist_ok=True)
    parsed = urllib.parse.urlparse(url)
    filename = Path(parsed.path).name or "download.zip"
    if not filename.lower().endswith((".zip", ".stp", ".step")):
        filename += ".zip"
    archive = dest / safe_name(filename)
    log(f"[vendor] {vendor} {name}")
    download_file(url, archive)
    result = {"vendor": vendor, "name": name, "url": url, "archive": str(archive.relative_to(dest_root)), "sha256": sha256_file(archive)}
    if archive.suffix.lower() == ".zip":
        unpack_dir = dest / "unpacked"
        unpack_zip(archive, unpack_dir)
        result["unpacked"] = str(unpack_dir.relative_to(dest_root))
    return result


def count_cad(root: Path) -> int:
    return sum(1 for p in root.rglob("*") if p.is_file() and p.suffix.lower() in CAD_EXTS)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="cad-library-cache", help="output directory")
    ap.add_argument("--mode", choices=["starter", "expanded"], default="starter")
    ap.add_argument("--include-vendor", choices=["yes", "no"], default="yes")
    args = ap.parse_args()

    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    (out / "open-source").mkdir(parents=True)
    (out / "vendor-anonymous").mkdir(parents=True)

    sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    report = {
        "generated_unix": int(time.time()),
        "mode": args.mode,
        "policy": "no upstream login, no cookies, no browser automation",
        "sources": [],
    }

    for entry in sources.get("public_repositories", []):
        dest = out / "open-source" / safe_name(entry["name"])
        rec = {"name": entry["name"], "repo": entry["repo"], "license": entry.get("license"), "status": "pending"}
        try:
            if entry.get("sparse_paths"):
                sparse_clone(entry["repo"], entry["sparse_paths"], dest, entry.get("branch"))
            else:
                clone_full(entry["repo"], dest, entry.get("branch"))
            if entry.get("prune", True):
                kept, removed = prune_non_cad(dest)
                rec.update({"kept_files": kept, "removed_non_cad": removed})
            rec.update({"status": "ok", "cad_files": count_cad(dest)})
        except Exception as e:
            rec.update({"status": "error", "error": str(e)})
            log(f"WARN public repo failed: {entry['name']}: {e}")
        report["sources"].append(rec)

    sp = sources.get("step_parts_api", {})
    if sp.get("enabled", True):
        per_query = 5 if args.mode == "starter" else 20
        try:
            result = collect_step_parts(sp["base_api"], sp["queries"], out / "open-source" / "step.parts", per_query)
            report["sources"].append({"name": "step.parts API", "status": "ok", **result})
        except Exception as e:
            report["sources"].append({"name": "step.parts API", "status": "error", "error": str(e)})

    if args.include_vendor == "yes":
        for entry in sources.get("vendor_direct", []):
            rec = {"name": entry["name"], "vendor": entry.get("vendor"), "status": "pending", "redistribute": entry.get("redistribute", False)}
            try:
                rec.update(collect_vendor(entry, out / "vendor-anonymous"))
                rec["status"] = "ok"
            except Exception as e:
                rec.update({"status": "error", "error": str(e)})
                log(f"WARN vendor download failed: {entry['name']}: {e}")
            report["sources"].append(rec)

    shutil.copy2(SOURCES_FILE, out / "sources.json")
    (out / "COLLECTION-REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.txt").write_text(
        "This cache was built without logging in to upstream CAD sites.\n"
        "Open-source mirrors retain upstream license/readme files.\n"
        "vendor-anonymous/ contains files fetched from anonymous official download URLs;\n"
        "do not publish those files unless the vendor license explicitly permits redistribution.\n",
        encoding="utf-8",
    )

    total = count_cad(out)
    log(f"DONE: {total} CAD files in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
