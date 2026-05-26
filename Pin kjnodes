import os
import subprocess

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

# === pin KJNodes to 1.2.0 ===================================================
print("\n" + "=" * 60)
print(" pin ComfyUI-KJNodes to 1.2.0")
print("=" * 60)
cm_cli = os.path.join(custom_nodes, "ComfyUI-Manager", "cm-cli.py")
if os.path.exists(cm_cli):
    cm_env = os.environ.copy()
    cm_env["COMFYUI_PATH"] = COMFY_DIR
    # cm-cli.py imports ComfyUI's own `utils` package, so ComfyUI's root
    # must be on PYTHONPATH and used as the working directory.
    existing_pp = cm_env.get("PYTHONPATH", "")
    cm_env["PYTHONPATH"] = COMFY_DIR + (os.pathsep + existing_pp if existing_pp else "")
    print("Pinning comfyui-kjnodes to 1.2.0 ...")
    subprocess.run(
        [py, cm_cli, "install", "comfyui-kjnodes@1.2.0"],
        env=cm_env, cwd=COMFY_DIR, check=False,
    )
else:
    print(f"cm-cli.py not found at {cm_cli} - skipping KJNodes pin")

print("\n" + "=" * 60)
print(" DONE  --  restart ComfyUI for the version change to apply")
print("=" * 60)
