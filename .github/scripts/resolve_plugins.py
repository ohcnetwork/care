#!/usr/bin/env python3
import hashlib
import json
import os
import subprocess
import sys

plugs_raw = os.environ.get("ADDITIONAL_PLUGS", "[]")
try:
    plugs = json.loads(plugs_raw)
except json.JSONDecodeError:
    sys.stdout.write("no-plugins")
    sys.exit(0)

if not plugs:
    sys.stdout.write("no-plugins")
    sys.exit(0)

resolved = []
for p in plugs:
    ver = p.get("version") or "@main"
    pkg = p.get("package_name")
    if not pkg:
        sys.stderr.write(f"plugin entry {p!r} is missing 'package_name'\n")
        sys.exit(1)
    if ver.startswith("@"):
        ref = ver[1:]
        git_url = pkg.removeprefix("git+")
        try:
            out = subprocess.run(  # noqa: S603
                ["git", "ls-remote", git_url, ref],  # noqa: S607
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
            sha = out.stdout.split()[0] if out.stdout else ref
        except Exception as exc:
            sys.stderr.write(
                f"warning: git ls-remote failed for {git_url!r} ({exc}); using ref name as cache key\n"
            )
            sha = ref
        resolved.append(f"{pkg}@{sha}")
    else:
        resolved.append(f"{pkg}{ver}")

h = hashlib.sha256(json.dumps(sorted(resolved)).encode()).hexdigest()[:16]
print(h, end="")  # noqa: T201
