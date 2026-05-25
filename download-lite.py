import os
import shutil
import sys
import subprocess

# ======================================================================
# CONFIG  --  edit these if paths change
# ======================================================================
# auto-detect where ComfyUI is installed (varies by image)
COMFY_DIR = None
for _candidate in ["/workspace/runpod-slim/ComfyUI", "/workspace/ComfyUI", "/ComfyUI"]:
    if os.path.isdir(_candidate):
        COMFY_DIR = _candidate
        break
if COMFY_DIR is None:
    COMFY_DIR = "/workspace/runpod-slim/ComfyUI"  # fallback (default image path)
print(f"Using ComfyUI directory: {COMFY_DIR}")

# download.txt is expected to sit next to this script
list_file     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download.txt")

models_base   = os.path.join(COMFY_DIR, "models")
custom_nodes  = os.path.join(COMFY_DIR, "custom_nodes")
# ComfyUI runs inside a venv -- pip installs MUST target it.
# venv folder name varies by image; check the common ones.
COMFY_PYTHON = None
for _venv in [".venv-cu128", ".venv", "venv"]:
    _p = os.path.join(COMFY_DIR, _venv, "bin", "python")
    if os.path.exists(_p):
        COMFY_PYTHON = _p
        break
if COMFY_PYTHON is None:
    COMFY_PYTHON = os.path.join(COMFY_DIR, ".venv-cu128", "bin", "python")

# Paste your Hugging Face token here, OR leave "" to use the HF_TOKEN env var.
HF_TOKEN = ""

# Custom nodes to install (cloned into custom_nodes/).
# Dependencies are auto-handled: install.py is run if present,
# otherwise requirements.txt is pip-installed.
CUSTOM_NODES = [
    "https://github.com/giriss/comfy-image-saver",
    "https://github.com/SLAPaper/ComfyUI-Image-Selector",
    "https://github.com/comfyuistudio/ComfyUI-Studio-nodes",
]
# ======================================================================


def run(cmd, cwd=None):
    printable = " ".join(cmd)
    print(f"\n$ {printable}" + (f"   (in {cwd})" if cwd else ""))
    subprocess.run(cmd, cwd=cwd, check=False)


# --- pick the python that ComfyUI actually uses -----------------------------
if os.path.exists(COMFY_PYTHON):
    py = COMFY_PYTHON
    print(f"Using ComfyUI venv python: {py}")
else:
    py = sys.executable
    print(f"WARNING: venv python not found at {COMFY_PYTHON}")
    print(f"         Falling back to {py} -- node dependencies may install")
    print(f"         to the wrong environment. Check the .venv path above.")


# --- ask for HF token up front so the run is unattended afterwards ----------
# priority: hardcoded var -> env var -> interactive prompt
token = HF_TOKEN.strip() or os.environ.get("HF_TOKEN", "").strip()
if not token:
    import getpass
    try:
        token = getpass.getpass(
            "Enter your Hugging Face token (or press Enter to skip): "
        ).strip()
    except Exception:
        token = ""
token = token or None

if token:
    print("Hugging Face token set - downloads will be authenticated.")
else:
    print("No HF token - downloads will be unauthenticated (slower, rate-limited).")


# === Step 2: custom nodes ===================================================
print("\n" + "=" * 60)
print(" STEP 2: custom nodes")
print("=" * 60)
os.makedirs(custom_nodes, exist_ok=True)

for repo_url in CUSTOM_NODES:
    name = repo_url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    node_dir = os.path.join(custom_nodes, name)

    # clone (skip if already present)
    if os.path.isdir(node_dir):
        print(f"\n\u2714 Node already cloned, skipping clone: {name}")
    else:
        print(f"\n\u2b07 Cloning {name} ...")
        run(["git", "clone", "--recursive", repo_url, node_dir])

    if not os.path.isdir(node_dir):
        print(f"\u274c Clone failed, skipping deps for: {name}")
        continue

    # dependencies: install.py takes priority, else requirements.txt
    install_py = os.path.join(node_dir, "install.py")
    req_txt = os.path.join(node_dir, "requirements.txt")

    if os.path.exists(install_py):
        print(f"   running install.py for {name}")
        run([py, "install.py"], cwd=node_dir)
    elif os.path.exists(req_txt):
        print(f"   installing requirements.txt for {name}")
        run([py, "-m", "pip", "install", "-r", req_txt])
    else:
        print(f"   no install.py or requirements.txt for {name} (nothing to do)")


# === Step 2b: pin KJNodes to 1.2.0 ==========================================
# The runpod/comfyui image ships KJNodes at latest; this pins it to 1.2.0
# via ComfyUI-Manager, replicating the manual "Switch Ver" action.
print("\n" + "=" * 60)
print(" STEP 2b: pin ComfyUI-KJNodes to 1.2.0")
print("=" * 60)
cm_cli = os.path.join(custom_nodes, "ComfyUI-Manager", "cm-cli.py")
if os.path.exists(cm_cli):
    cm_env = os.environ.copy()
    cm_env["COMFYUI_PATH"] = COMFY_DIR
    print("Pinning comfyui-kjnodes to 1.2.0 ...")
    subprocess.run(
        [py, cm_cli, "install", "comfyui-kjnodes@1.2.0"],
        env=cm_env, check=False,
    )
else:
    print(f"cm-cli.py not found at {cm_cli} - skipping KJNodes pin")


# === Step 2c: install workflow ==============================================
# Copy the Jerry_base_new.json workflow into ComfyUI's workflows folder.
print("\n" + "=" * 60)
print(" STEP 2c: install workflow")
print("=" * 60)
WORKFLOW_URL = "https://raw.githubusercontent.com/jerrizzzler-byte/wan/main/Jerry_base_new.json"
workflows_dir = os.path.join(COMFY_DIR, "user", "default", "workflows")
os.makedirs(workflows_dir, exist_ok=True)
workflow_dest = os.path.join(workflows_dir, "Jerry_base_new.json")
print(f"Downloading workflow to {workflow_dest} ...")
_rc = subprocess.run(
    ["curl", "-sL", WORKFLOW_URL, "-o", workflow_dest], check=False
).returncode
if _rc == 0 and os.path.exists(workflow_dest) and os.path.getsize(workflow_dest) > 0:
    print("\u2705 Workflow installed.")
else:
    print("\u274c Failed to download workflow (ComfyUI will still run).")


# === Step 3: models =========================================================
print("\n" + "=" * 60)
print(" STEP 3: model downloads")
print("=" * 60)

# make sure huggingface_hub is installed in the ComfyUI env
try:
    from huggingface_hub import hf_hub_download
except ImportError:
    print("huggingface_hub not found. Installing...")
    subprocess.check_call([py, "-m", "pip", "install", "huggingface_hub"])
    from huggingface_hub import hf_hub_download

with open(list_file, "r") as f:
    lines = f.readlines()

for line in lines:
    line = line.strip()
    if not line or line.startswith("#"):
        continue  # skip empty lines or comments

    parts = line.split()
    if len(parts) < 2:
        print(f"Skipping invalid line (no folder specified): {line}")
        continue

    hf_url = parts[0]
    target_folder = parts[1].strip("/ ")
    new_filename = parts[2] if len(parts) > 2 else None  # optional custom filename

    dest_folder = os.path.join(models_base, target_folder)
    os.makedirs(dest_folder, exist_ok=True)

    # Parse Hugging Face repo info
    url_parts = hf_url.split("/")
    if "resolve" not in url_parts:
        print(f"Invalid Hugging Face URL: {hf_url}")
        continue

    idx = url_parts.index("resolve")
    repo_id = "/".join(url_parts[3:idx])              # org/repo
    revision = url_parts[idx + 1]                     # main or commit hash
    filename_in_repo = "/".join(url_parts[idx + 2:])  # path inside repo

    repo_name = repo_id.split("/")[-1]
    orig_basename = os.path.basename(filename_in_repo)
    ext = os.path.splitext(orig_basename)[1]          # keep .safetensors, .bin, etc.

    # Decide final name
    if new_filename:  # Force rename by user
        if not os.path.splitext(new_filename)[1]:
            final_name = new_filename + ext
        else:
            final_name = new_filename
    else:
        if orig_basename.startswith("diffusion_pytorch_model"):
            final_name = f"{repo_name}{ext}"
        else:
            final_name = orig_basename

    dest_path = os.path.join(dest_folder, final_name)

    # Skip if already downloaded
    if os.path.exists(dest_path):
        print(f"\u2714 Already exists, skipping: {dest_path}")
        continue

    # Download and save
    try:
        cached_file = hf_hub_download(
            repo_id=repo_id,
            filename=filename_in_repo,
            revision=revision,
            token=token,
        )
        shutil.copyfile(cached_file, dest_path)
        print(f"\u2705 Downloaded: {hf_url} \u2192 {dest_path}")
    except Exception as e:
        print(f"\u274c Failed to download {hf_url}: {e}")


print("\n" + "=" * 60)
print(" ALL DONE  --  restart ComfyUI to load new nodes & models")
print("=" * 60)
