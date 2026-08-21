from pathlib import Path

path = Path(__file__).with_name("build_system.py")
source = path.read_text(encoding="utf-8")
old = '"immutable_core_sha256": core_sha256(html),'
new = '"immutable_core_sha256": core_sha256(start.read_text(encoding="utf-8")),'
if old not in source:
    raise SystemExit("core hash marker not found")
path.write_text(source.replace(old, new, 1), encoding="utf-8")
print({"patched": "core hash after write_text", "file": str(path)})
