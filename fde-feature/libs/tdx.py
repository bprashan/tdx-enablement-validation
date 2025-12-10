import shutil
import os
import sys
import fileinput
from utils import run_command, clone_repo, set_environment_variables
sys.path.insert(1, os.path.join(os.getcwd(), 'configuration'))
import configuration

def clone_and_patch_tdx_repository():
    """Clone a Git repository, copy a patch file, and apply the patch."""
    patch_files = ['patches/run_td_sh.patch', 'patches/setup-tdx-config.patch']

    clone_repo(repo_url=configuration.canonical_tdx_url, clone_dir = configuration.canonical_tdx_dir, branch=configuration.canonical_tdx_branch)

    # Copy the patch files to the destination directory and apply patch
    for file in patch_files:
        shutil.copy(file, configuration.canonical_tdx_dir)
        print(f"Copied {file} to {configuration.canonical_tdx_dir}")
        run_command(["git", "apply", os.path.basename(file)], cwd=f"{os.getcwd()}/{configuration.canonical_tdx_dir}")
        print(f"Applied patch: {file}")

def create_td_image():
    """Navigate to the guest-tools/image directory and run the create-td-image.sh script."""
    # Define the directory and script
    directory = "canonical-tdx/guest-tools/image"
    script = "sudo ./create-td-image.sh -v 24.04"

    # Run the script with sudo
    run_command([script], cwd=f"{os.getcwd()}/{directory}", shell=True)
    set_environment_variables(key="BASE_IMAGE_PATH", data=f"{os.getcwd()}/{directory}/tdx-guest-ubuntu-24.04-generic.qcow2")
    set_environment_variables(key="ENCRYPTED_IMAGE_PATH", data=f"{os.getcwd()}/{directory}/tdx-guest-ubuntu-encrypted.img")