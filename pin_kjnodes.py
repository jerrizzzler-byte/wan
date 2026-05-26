import os
import subprocess

# Pin ComfyUI-KJNodes to registry version 1.2.0 by checking out the exact
# git commit (5b15f29, "version 1.2.0", dated 2025-12-09).
# This avoids ComfyUI-Manager's cm-cli.py entirely.

KJNODES_REPO   = "https://github.com/kijai/ComfyUI-KJNodes"
KJNODES_COMMIT = "5b15f292ac3edd1f54536733033555139c9eea12"  # = version 1.2.0

# --- auto-detect ComfyUI directory ------------------------------------------
COMFY_DIR = None
for _candidate in ["/workspace/runpod-slim/ComfyUI", "/workspace/ComfyUI", "/ComfyUI"]:
    if os.path.isdir(_candidate):
        COMFY_DIR = _candidate
        break
if COMFY_DIR is None:
    COMFY_DIR = "/workspace/runpod-slim/ComfyUI"
print(f"Using ComfyUI directory: {COMFY_DIR}")

custom_nodes = os.path.join(COMFY_DIR, "custom_nodes")
kj_dir = os.path.join(custom_nodes, "ComfyUI-KJNodes")

# --- pick the ComfyUI venv python -------------------------------------------
py = None
for _venv in [".venv-cu128", ".venv", "venv"]:
    _p = os.path.join(COMFY_DIR, _venv, "bin", "python")
    if os.path.exists(_p):
        py = _p
        break
if py is None:
    import sys
    py = sys.executable
print(f"Using python: {py}")


def run(cmd, cwd=None):
    print(f"\n$ {' '.join(cmd)}" + (f"   (in {cwd})" if cwd else ""))
    subprocess.run(cmd, cwd=cwd, check=False)


print("\n" + "=" * 60)
print(" pin ComfyUI-KJNodes to 1.2.0  (commit 5b15f29)")
print("=" * 60)

os.makedirs(custom_nodes, exist_ok=True)

# clone KJNodes if it's not already there
if not os.path.isdir(kj_dir):
    print("KJNodes not present - cloning ...")
    run(["git", "clone", KJNODES_REPO, kj_dir])
else:
    print("KJNodes already present.")

if not os.path.isdir(os.path.join(kj_dir, ".git")):
    print("ERROR: KJNodes folder exists but is not a git repo - cannot pin.")
else:
    # make sure the target commit is available, then check it out
    run(["git", "fetch", "--all"], cwd=kj_dir)
    run(["git", "checkout", KJNODES_COMMIT], cwd=kj_dir)

    # install KJNodes dependencies for this version
    req = os.path.join(kj_dir, "requirements.txt")
    if os.path.exists(req):
        print("Installing KJNodes requirements ...")
        run([py, "-m", "pip", "install", "-r", req])

print("\n" + "=" * 60)
print(" DONE  --  KJNodes pinned to 1.2.0. Restart ComfyUI to load it.")
print("=" * 60)
