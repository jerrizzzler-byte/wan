import os
import shutil
import sys
import subprocess

# ======================================================================
# download-preloaded.py
# Dedicated installer for the PRE-LOADED ComfyUI template (the one whose
# real install lives at /ComfyUI and bridges /workspace/ComfyUI for models).
# All paths are HARDCODED for this template -- no auto-detection.
#   - custom nodes  -> /ComfyUI/custom_nodes      (ComfyUI's primary path)
#   - workflow      -> /ComfyUI/user/default/workflows
#   - models        -> /workspace/ComfyUI/models  (persistent volume)
# ======================================================================
COMFY_DIR     = "/ComfyUI"
custom_nodes  = "/ComfyUI/custom_nodes"
workflows_dir = "/ComfyUI/user/default/workflows"
models_base   = "/workspace/ComfyUI/models"
py            = "/opt/venv/bin/python3"

# download.txt is expected to sit next to this script
list_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download.txt")

# Paste your Hugging Face token here, OR leave "" to use the HF_TOKEN env var.
HF_TOKEN = ""

# System libraries needed by some ComfyUI nodes (MediaPipe / OpenGL / etc.)
APT_PACKAGES = [
    "git",
    "libgles2", "libegl1", "libgl1", "libglib2.0-0t64",
    "libsm6", "libxext6", "libxrender1", "libglvnd0",
]

# Custom nodes to install (cloned into /ComfyUI/custom_nodes).
CUSTOM_NODES = [
    "https://github.com/kijai/ComfyUI-WanVideoWrapper",
    "https://github.com/Fannovel16/comfyui_controlnet_aux",
    "https://github.com/rgthree/rgthree-comfy",
    "https://github.com/yolain/ComfyUI-Easy-Use",
    "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite",
    "https://github.com/kijai/ComfyUI-segment-anything-2",
    "https://github.com/Fannovel16/ComfyUI-Frame-Interpolation",
    "https://github.com/chflame163/ComfyUI_LayerStyle_Advance",
    "https://github.com/giriss/comfy-image-saver",
    "https://github.com/SLAPaper/ComfyUI-Image-Selector",
    "https://github.com/un-seen/comfyui-tensorops",
    "https://github.com/MinorBoy/ComfyUI_essentials_mb",
    "https://github.com/comfyuistudio/ComfyUI-Studio-nodes",
]
# ======================================================================


def run(cmd, cwd=None):
    printable = " ".join(cmd)
    print(f"\n$ {printable}" + (f"   (in {cwd})" if cwd else ""))
    subprocess.run(cmd, cwd=cwd, check=False)


# --- sanity check on the python -----------------------------------------
if not os.path.exists(py):
    print(f"WARNING: {py} not found - falling back to {sys.executable}")
    py = sys.executable
print(f"Using python: {py}")
print(f"ComfyUI dir : {COMFY_DIR}")
print(f"Models dir  : {models_base}")


# --- ask for HF token up front so the run is unattended afterwards ------
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


# === Step 1: system packages ============================================
print("\n" + "=" * 60)
print(" STEP 1: system packages")
print("=" * 60)
run(["apt", "update"])
run(["apt", "install", "-y"] + APT_PACKAGES)


# === Step 2: custom nodes ===============================================
print("\n" + "=" * 60)
print(" STEP 2: custom nodes")
print("=" * 60)
os.makedirs(custom_nodes, exist_ok=True)

for repo_url in CUSTOM_NODES:
    name = repo_url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    node_dir = os.path.join(custom_nodes, name)

    if os.path.isdir(node_dir):
        print(f"\n\u2714 Node already cloned, skipping clone: {name}")
    else:
        print(f"\n\u2b07 Cloning {name} ...")
        run(["git", "clone", "--recursive", repo_url, node_dir])

    if not os.path.isdir(node_dir):
        print(f"\u274c Clone failed, skipping deps for: {name}")
        continue

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


# === Step 2b: pin KJNodes to 1.2.0 ======================================
# This template pre-installs KJNodes in /ComfyUI/custom_nodes. We pin THAT
# existing copy (the one ComfyUI actually loads) to version 1.2.0 by
# checking out the exact git commit (5b15f29, "version 1.2.0").
print("\n" + "=" * 60)
print(" STEP 2b: pin ComfyUI-KJNodes to 1.2.0")
print("=" * 60)
KJNODES_REPO   = "https://github.com/kijai/ComfyUI-KJNodes"
KJNODES_COMMIT = "5b15f292ac3edd1f54536733033555139c9eea12"  # = version 1.2.0
kj_dir = os.path.join(custom_nodes, "ComfyUI-KJNodes")

if not os.path.isdir(kj_dir):
    print("KJNodes not present - cloning ...")
    run(["git", "clone", KJNODES_REPO, kj_dir])
else:
    print(f"KJNodes already present at {kj_dir}")

if not os.path.isdir(os.path.join(kj_dir, ".git")):
    print("ERROR: KJNodes folder exists but is not a git repo - cannot pin.")
else:
    run(["git", "fetch", "--all"], cwd=kj_dir)
    run(["git", "checkout", KJNODES_COMMIT], cwd=kj_dir)
    kj_req = os.path.join(kj_dir, "requirements.txt")
    if os.path.exists(kj_req):
        print("Installing KJNodes requirements ...")
        run([py, "-m", "pip", "install", "-r", kj_req])


# === Step 2c: install workflow ==========================================
print("\n" + "=" * 60)
print(" STEP 2c: install workflow")
print("=" * 60)
WORKFLOW_URL = "https://raw.githubusercontent.com/jerrizzzler-byte/wan/main/Jerry_base_fixed.json"
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


# === Step 3: models =====================================================
print("\n" + "=" * 60)
print(" STEP 3: model downloads")
print("=" * 60)

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
        continue

    parts = line.split()
    if len(parts) < 2:
        print(f"Skipping invalid line (no folder specified): {line}")
        continue

    hf_url = parts[0]
    target_folder = parts[1].strip("/ ")
    new_filename = parts[2] if len(parts) > 2 else None

    dest_folder = os.path.join(models_base, target_folder)
    os.makedirs(dest_folder, exist_ok=True)

    url_parts = hf_url.split("/")
    if "resolve" not in url_parts:
        print(f"Invalid Hugging Face URL: {hf_url}")
        continue

    idx = url_parts.index("resolve")
    repo_id = "/".join(url_parts[3:idx])
    revision = url_parts[idx + 1]
    filename_in_repo = "/".join(url_parts[idx + 2:])

    repo_name = repo_id.split("/")[-1]
    orig_basename = os.path.basename(filename_in_repo)
    ext = os.path.splitext(orig_basename)[1]

    if new_filename:
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

    if os.path.exists(dest_path):
        print(f"\u2714 Already exists, skipping: {dest_path}")
        continue

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
