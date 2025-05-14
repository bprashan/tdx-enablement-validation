import shutil
import os
import fileinput
from utils import run_command, clone_repo, set_environment_variables, run_command_with_popen

def clone_and_patch_tdx_repository():
    """Clone a Git repository, copy a patch file, and apply the patch."""
    repo_url = "https://github.com/canonical/tdx.git"
    patch_files = ['patches/run_td_sh.patch', 'patches/setup-tdx-config.patch']
    repo_name = repo_url.split('/')[-1].replace('.git', '')

    clone_repo(repo_url, repo_name, branch="3.1")

    # Copy the patch files to the destination directory and apply patch
    for file in patch_files:
        shutil.copy(file, repo_name)
        print(f"Copied {file} to {repo_name}")
        run_command(["git", "apply", os.path.basename(file)], cwd=f"{os.getcwd()}/{repo_name}")
        print(f"Applied patch: {file}")

def create_td_image():
    """Navigate to the guest-tools/image directory and run the create-td-image.sh script."""
    # Define the directory and script
    directory = "tdx/guest-tools/image"
    script = "sudo ./create-td-image.sh -v 24.04"

    # Run the script with sudo
    run_command([script], cwd=f"{os.getcwd()}/{directory}", shell=True)
    set_environment_variables(key="BASE_IMAGE_PATH", data=f"{os.getcwd()}/tdx/guest-tools/image/tdx-guest-ubuntu-24.04-generic.qcow2")
    set_environment_variables(key="ENCRYPTED_IMAGE_PATH", data=f"{os.getcwd()}/tools/image/tdx-guest-ubuntu-encrypted.img")