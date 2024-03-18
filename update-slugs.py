"""update slugs from old format to new

Reorganizes files to the new slug layout of github.com/org/r/repo

instead of github.com/Org/RePo

log-paths are updated in-place in result files
"""

import glob
import os
import sys

if len(sys.argv) >= 2:
    run_dir = sys.argv[1]
else:
    run_dir = "runs"

for host in os.listdir(run_dir):
    path = os.path.join(run_dir, host)
    if os.path.isfile(path):
        continue
    for org in os.listdir(path):
        if len(org) == 1:
            print(f"already processed {org}")
            continue
        path = os.path.join(run_dir, host, org)
        if os.path.isfile(path):
            continue
        repos = os.listdir(path)
        if set(repos).issubset({"results", "logs", "notebooks"}):
            print(f"just results: {path}")
            continue
        for repo in repos:
            old_slug = os.path.join(host, org, repo)
            src = os.path.join(run_dir, old_slug)
            if not os.path.isdir(src):
                # e.g. .DS_Store
                continue
            new_slug = os.path.join(host, org[0], org, repo).lower()
            dest = os.path.join(run_dir, new_slug)
            parent = os.path.dirname(dest)
            try:
                os.makedirs(parent)
            except FileExistsError:
                pass
            print(f"moving {src} -> {dest}")
            os.rename(src, dest)
            old_logs_path = os.path.join(old_slug, "logs")
            new_logs_path = os.path.join(new_slug, "logs")
            for results_file in glob.glob(os.path.join(dest, "results", "*")):
                with open(results_file) as f:
                    before = f.read()
                after = before.replace(old_logs_path, new_logs_path)
                if after != before:
                    print(
                        f"rewriting {old_logs_path}->{new_logs_path} in {results_file}"
                    )
                    with open(results_file, "w") as f:
                        f.write(after)
