import shutil
import os
import sys
import fileinput
from utils import run_command, clone_repo, set_environment_variables
sys.path.insert(1, os.path.join(os.getcwd(), 'configuration'))
import configuration

def update_canonical_tdx_repository():
    """copy a patch file, and apply the patch."""
    patch_files = ['patches/boot_direct_sh.patch']

    # Copy the patch files to the destination directory and apply patch
    for file in patch_files:
        shutil.copy(file, configuration.canonical_tdx_dir)
        print(f"Copied {file} to {configuration.canonical_tdx_dir}")
        run_command(["git", "apply", os.path.basename(file)], cwd=f"{os.getcwd()}/{configuration.canonical_tdx_dir}")
        print(f"Applied patch: {file}")
    
    # Update TDX_SETUP_ATTESTATION in setup-tdx-config
    sed_command = f'sed -i "s/^TDX_SETUP_ATTESTATION=0$/TDX_SETUP_ATTESTATION=1/" {configuration.canonical_tdx_dir}/setup-tdx-config'
    run_command(sed_command, shell=True)
    print("Updated TDX_SETUP_ATTESTATION to 1 in setup-tdx-config")

def create_td_image():
    """Navigate to the guest-tools/image directory and run the create-td-image.sh script."""
    # Define the directory and script
    directory = f"{configuration.canonical_tdx_dir}/guest-tools/image"
    script = "sudo ./create-td-image.sh -v 24.04"

    # Run the script with sudo
    run_command([script], cwd=f"{os.getcwd()}/{directory}", shell=True)
    set_environment_variables(key="BASE_IMAGE_PATH", data=f"{os.getcwd()}/{directory}/tdx-guest-ubuntu-24.04-generic.qcow2")
    set_environment_variables(key="ENCRYPTED_IMAGE_PATH", data=f"{os.getcwd()}/tools/image/tdx-guest-ubuntu-encrypted.img")