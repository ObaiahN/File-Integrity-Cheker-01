# fic.py  (File Integrity Checker)
import argparse, hashlib, json, os, sys
from pathlib import Path

def sha256sum(path: Path, block_size=1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(block_size):
            h.update(chunk)
    return h.hexdigest()

def walk_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file():
            yield p

def build_manifest(root: Path, ignore=None):
    root = root.resolve()
    ignore = set(map(lambda s: s.lower(), ignore or []))
    data = {}
    for p in walk_files(root):
        rel = p.relative_to(root).as_posix()
        if rel.lower() in ignore:
            continue
        data[rel] = {
            "sha256": sha256sum(p),
            "size": p.stat().st_size,
        }
    return {"root": str(root), "algorithm": "SHA-256", "files": data}

def save_manifest(manifest, out_path: Path):
    out_path.write_text(json.dumps(manifest, indent=2))

def load_manifest(path: Path):
    return json.loads(path.read_text())

def verify(root: Path, manifest: dict, ignore=None):
    root = root.resolve()
    ignore = set(map(lambda s: s.lower(), ignore or []))
    current = {}
    for p in walk_files(root):
        rel = p.relative_to(root).as_posix()
        if rel.lower() in ignore:
            continue
        current[rel] = {
            "sha256": sha256sum(p),
            "size": p.stat().st_size,
        }

    baseline = manifest["files"]
    baseline_set = set(baseline.keys())
    current_set  = set(current.keys())

    added    = sorted(current_set - baseline_set)
    removed  = sorted(baseline_set - current_set)
    common   = sorted(current_set & baseline_set)
    changed  = [f for f in common if current[f]["sha256"] != baseline[f]["sha256"]]

    return added, removed, changed

def main():
    ap = argparse.ArgumentParser(description="Simple File Integrity Checker (SHA-256).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_init = sub.add_parser("init", help="Create baseline manifest")
    ap_init.add_argument("folder", type=Path)
    ap_init.add_argument("manifest", type=Path)
    ap_init.add_argument("--ignore", nargs="*", default=[], help="Paths (relative) to ignore")

    ap_ver = sub.add_parser("verify", help="Verify folder against manifest")
    ap_ver.add_argument("folder", type=Path)
    ap_ver.add_argument("manifest", type=Path)
    ap_ver.add_argument("--ignore", nargs="*", default=[], help="Paths (relative) to ignore")

    args = ap.parse_args()

    # Always ignore the manifest file itself if it sits inside the folder
    extra_ignores = {args.manifest.name}

    if args.cmd == "init":
        manifest = build_manifest(args.folder, ignore=set(args.ignore) | extra_ignores)
        save_manifest(manifest, args.manifest)
        print(f"Baseline saved: {args.manifest} ({len(manifest['files'])} files)")

    elif args.cmd == "verify":
        if not args.manifest.exists():
            print("Manifest not found. Run 'init' first.")
            sys.exit(1)
        manifest = load_manifest(args.manifest)
        added, removed, changed = verify(args.folder, manifest, ignore=set(args.ignore) | extra_ignores)

        ok = not (added or removed or changed)
        print("Verification report")
        print("-------------------")
        print(f"Added:   {len(added)}")
        for f in added:   print(f"  + {f}")
        print(f"Removed: {len(removed)}")
        for f in removed: print(f"  - {f}")
        print(f"Changed: {len(changed)}")
        for f in changed: print(f"  * {f}")

        sys.exit(0 if ok else 2)

if _name_ == "_main_":
    main() 

out put: python fic.py verify demo manifest.json
Verification report
-------------------
Added:   0
Removed: 0
Changed: 0



