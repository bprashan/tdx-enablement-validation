import subprocess
import os
import time
from utils import run_command, clone_repo, run_command_with_popen, remove_host_from_known_hosts, set_environment_variables
import re
import binascii
import urllib.request
import sys
from tdx import clone_and_patch_tdx_repository, create_td_image
sys.path.insert(1, os.path.join(os.getcwd(), 'configuration'))
import configuration

def add_intel_sgx_repository():
    """Add Intel SGX repository to apt sources and update package lists."""
    # Add the repository to sources list
    repo_entry = "deb [signed-by=/etc/apt/keyrings/intel-sgx-keyring.asc arch=amd64] https://download.01.org/intel-sgx/sgx_repo/ubuntu noble main"
    add_repo_command = f"echo '{repo_entry}' | sudo tee /etc/apt/sources.list.d/intel-sgx.list"
    run_command(add_repo_command, shell=True)
    
    # Download the GPG key
    wget_command = ["wget", "https://download.01.org/intel-sgx/sgx_repo/ubuntu/intel-sgx-deb.key"]
    run_command(wget_command)
    
    # Create keyrings directory
    mkdir_command = ["sudo", "mkdir", "-p", "/etc/apt/keyrings"]
    run_command(mkdir_command)
    
    # Add the key to keyrings
    add_key_command = "cat intel-sgx-deb.key | sudo tee /etc/apt/keyrings/intel-sgx-keyring.asc > /dev/null"
    run_command(add_key_command, shell=True)
    
    # Update package lists
    update_command = ["sudo", "apt-get", "update"]
    run_command(update_command)
    
    print("Intel SGX repository added successfully.")

def install_required_packages():
    """Install specified packages."""
    install_command = [
        "sudo", "apt", "install", "-y",  "allow-downgrades", "pkg-config", "gpg", "wget", "openssl",
        "libcryptsetup-dev", "python3-venv", "libtdx-attest-dev", "sshpass", "qemu-system-x86",
        "libtss2-dev", "build-essential"
    ]

    # Run the install command
    run_command(install_command)

def build_project():
    """Navigate to the full-disk-encryption directory and build the project."""
    run_command(["cargo", "build", "--release", "--manifest-path", "fde-binaries/Cargo.toml"])


def generate_encryption_key_and_id():
    """Generate encryption key (k_RFS) and corresponding key ID (ID_K_RFS)."""
    # Generate k_RFS: 32 random bytes in hex format
    result = subprocess.run(['openssl', 'rand', '-hex', '32'], capture_output=True, text=True)
    k_rfs = result.stdout.strip()
    
    # Generate ID_K_RFS: keybroker/key/ + 32 random bytes in hex format
    result = subprocess.run(['openssl', 'rand', '-hex', '32'], capture_output=True, text=True)
    id_k_rfs = f"keybroker/key/{result.stdout.strip()}"
    
    # Set environment variables
    set_environment_variables(key="k_RFS", data=k_rfs)
    set_environment_variables(key="ID_k_RFS", data=id_k_rfs)
    
    print(f"Generated encryption key (k_RFS): {k_rfs}")
    print(f"Generated key ID (ID_K_RFS): {id_k_rfs}")


def setup_ovmf_tdx(directory='data'):
    url = "https://launchpad.net/~kobuk-team/+archive/ubuntu/tdx-release/+files/ovmf_2024.02-3+tdx1.0_all.deb"
    extract_dir =os.path.join(directory, "ovmf-extracted")

    # Ensure the download directory exists
    os.makedirs(directory, exist_ok=True)

    # Extract the file name from the URL
    file_name = url.split('/')[-1]
    file_path = os.path.join(directory, file_name)

    # Download the .deb file
    urllib.request.urlretrieve(url, file_path)
    print(f"Downloaded {file_name} to {directory}")

    #Ensure the extraction directory exists
    os.makedirs(extract_dir, exist_ok=True)

    #Extract the .deb file
    subprocess.run(['dpkg-deb', '-x', file_path, extract_dir])
    print(f"Extracted {file_name} to {extract_dir}")

def create_fde_setup_config_file():
    """Create the setup_config.sh file with environment variable placeholders."""
    # Create the reference-values directory
    ref_values_dir = configuration.trustee_reference_value_dir
    os.makedirs(ref_values_dir, exist_ok=True)
    print(f"Created directory: {ref_values_dir}")
    
    # Get current working directory and construct file path
    setup_config_path = os.path.join(os.getcwd(), configuration.trustee_config_file)
    
    # Get system IP
    result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
    system_ip = result.stdout.strip().split()[0] if result.stdout.strip() else ""
    
    # Set SYSTEM_IP environment variable
    set_environment_variables(key="SYSTEM_IP", data=system_ip)
    
    # Set NO_PROXY with system IP and trustee services
    no_proxy = f"{system_ip},trustee-as,trustee-kbs,trustee-vault"
    set_environment_variables(key="NO_PROXY", data=no_proxy)
    
    # Create the config file content
    config_content = f"""#!/bin/bash

export SETUP_CONFIG_FILE="{setup_config_path}"
export SYSTEM_IP="{system_ip}"
export NO_PROXY="{no_proxy}"
export VAULT_ROOT_TOKEN=
export KBS_PORT=
export KBS_URL=
export KBS_CERT_PATH=
export SK_KBS_ADMIN=
export UUID=
export label=
"""
    
    # Write the config file
    with open(setup_config_path, 'w') as f:
        f.write(config_content)
    
    # Make the file executable
    os.chmod(setup_config_path, 0o755)
    
    # Set environment variable
    set_environment_variables(key="SETUP_CONFIG_FILE", data=setup_config_path)
    
    print(f"Created setup config file at: {setup_config_path}")
    print(f"Set SYSTEM_IP to: {system_ip}")
    print(f"Set NO_PROXY to: {no_proxy}")
    return setup_config_path


def setup_fde_environment():
    add_intel_sgx_repository()
    install_required_packages()
    clone_repo(repo_url = configuration.repo_url, clone_dir = configuration.repo_name, branch = configuration.branch, recurse_submodules = True)
    os.chdir(os.path.join(configuration.dir_name))
    print(f"Changed working directory to {os.getcwd()}")
    create_fde_setup_config_file()
    build_project()
    setup_ovmf_tdx()
    generate_encryption_key_and_id()


def copy_boot_files_to_canonical_tdx():
    """Copy initrd.img-24.04 and vmlinuz-24.04 from tools/image/ to canonical-tdx/guest-tools/image/."""
    import shutil
    
    # Source directory (relative to current working directory)
    source_dir = "tools/image"
    
    # Destination directory
    dest_dir = "canonical-tdx/guest-tools/image"
    
    # Files to copy
    files_to_copy = ["initrd.img-24.04", "vmlinuz-24.04"]
    
    # Ensure destination directory exists
    os.makedirs(dest_dir, exist_ok=True)
    
    for file_name in files_to_copy:
        source_file = os.path.join(source_dir, file_name)
        dest_file = os.path.join(dest_dir, file_name)
        
        if os.path.exists(source_file):
            shutil.copy2(source_file, dest_file)
            print(f"Copied {file_name} from {source_dir} to {dest_dir}")
        else:
            print(f"Warning: {source_file} not found. Skipping.")
    
    print("Boot files copy completed.")


def parse_and_update_encryption_output(console_output):
    """
    Parses the console output to extract UUID, label, OVMF_PATH and IMAGE_PATH,
    then sets them as environment variables and updates the setup config file.
    """
    # Define regex patterns to extract values
    uuid_pattern = r"export UUID=([a-f0-9\-]+)"
    label_pattern = r"export label=(\S+)"
    ovmf_pattern = r"OVMF_PATH:\s*(\S+)"
    image_pattern = r"IMAGE_PATH:\s*(\S+)"

    # Search for the patterns in the console output
    uuid_match = re.search(uuid_pattern, console_output)
    label_match = re.search(label_pattern, console_output)
    ovmf_match = re.search(ovmf_pattern, console_output)
    image_match = re.search(image_pattern, console_output)

    if not ovmf_match or not image_match:
        print("Error: Either OVMF or ENCRYPTED IMAGE paths not found in the console output.")
        sys.exit(1)

    ovmf_path = ovmf_match.group(1)
    image_path = image_match.group(1)

    if not (os.path.exists(ovmf_path) and os.path.exists(image_path)):
        print("Error: Either OVMF or ENCRYPTED IMAGE paths do not exist on the filesystem.")
        print(f"OVMF_PATH: {ovmf_path} (exists: {os.path.exists(ovmf_path)})")
        print(f"ENCRYPTED_IMAGE_PATH: {image_path} (exists: {os.path.exists(image_path)})")
        sys.exit(1)

    # Set environment variables for paths
    set_environment_variables(key="OVMF_PATH", data=ovmf_path)
    set_environment_variables(key="ENCRYPTED_IMAGE_PATH", data=image_path)
    
    # Get setup config file path
    setup_config_file = os.environ.get('SETUP_CONFIG_FILE')
    
    # Set UUID if found
    if uuid_match:
        uuid = uuid_match.group(1)
        set_environment_variables(key="UUID", data=uuid)
        print(f"Set UUID: {uuid}")
        
        # Update setup config file with UUID
        if setup_config_file and os.path.exists(setup_config_file):
            sed_uuid_command = f'sed -i "/^export UUID=/c\\\\export UUID=\\"{uuid}\\"" "{setup_config_file}"'
            run_command(sed_uuid_command, shell=True)
            print(f"Updated UUID in {setup_config_file}")
    else:
        print("Warning: UUID not found in the console output.")
    
    # Set label if found
    if label_match:
        label = label_match.group(1)
        set_environment_variables(key="label", data=label)
        print(f"Set label: {label}")
        
        # Update setup config file with label
        if setup_config_file and os.path.exists(setup_config_file):
            sed_label_command = f'sed -i "/^export label=/c\\\\export label=\\"{label}\\"" "{setup_config_file}"'
            run_command(sed_label_command, shell=True)
            print(f"Updated label in {setup_config_file}")
    else:
        print("Warning: label not found in the console output.")


def encrypt_image(skip_encrypt_image_path=False, extra_args=None):
    """Encrypt the image using the FDE key and KBS certificate path."""
    command = ["sudo", "tools/image/fde-encrypt_image.sh"]
    base_image_path=os.environ["BASE_IMAGE_PATH"]
    encrypted_image_path=os.environ["ENCRYPTED_IMAGE_PATH"]
    if not skip_encrypt_image_path:
        command.extend(["-e", encrypted_image_path])

    kbs_cert_path=os.environ["KBS_CERT_PATH"]
    pr_kr_path=os.environ["PK_KR_PATH"]
    fde_key=os.environ["k_RFS"]
    kbs_url=os.environ["KBS_URL"]
    key_id=os.environ["ID_K_RFS"]

    command.extend([
        "-c", kbs_cert_path,
        "-p", base_image_path,
        "-k", fde_key,
        "-i", key_id,
        "-u", kbs_url,
    ])
    if extra_args:
        command.extend(extra_args)

    retcode, output, error = run_command_with_popen(command)
    if retcode == 0:
        parse_and_update_encryption_output("\n".join(output))
        copy_boot_files_to_canonical_tdx()
        return True
    else:
        if (configuration.Error_r_negative in error and \
            extra_args[extra_args.index('-r') + 1][0] == '-') or \
            (configuration.Error_b_negative in error and \
             extra_args[extra_args.index('-b') + 1][0] == '-'):
            return True
        print("Error during image encryption:")
        print("\n".join(output))
        return False

def launch_td_guest(mode):
    """Launch the TD guest."""
    set_environment_variables("TD_IMG", os.environ["ENCRYPTED_IMAGE_PATH"])
    set_environment_variables("TD_BOOT_MODE", mode)
    ovmf_path = os.getenv('OVMF_PATH')
    command = [f"canonical-tdx/guest-tools/direct-boot/boot_direct.sh 24.04 -d false -f {ovmf_path}"]

    print("Launching TD guest...")
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return process

def execute_td_command(ssh_command, sleep_duration=120):
    """Execute the TD command and SSH command."""
    process = launch_td_guest("TD_FDE_BOOT")

    print(f"Sleeping for {sleep_duration} seconds to allow the TD guest to boot...")
    time.sleep(sleep_duration)

    if process.poll() is None:
        print("TD guest is still running.")
        remove_host_from_known_hosts('localhost', 10022)
        result = run_command(ssh_command, shell=True)

        if result:
            print(result)
            print('Shutting down the TD guest...')
            remove_host_from_known_hosts('localhost', 10022)
            safe_shut_down_command = "sshpass -p 123456 ssh -o StrictHostKeyChecking=no -p 10022 root@localhost 'sudo shutdown now'"
            run_command(safe_shut_down_command, shell=True)
            return result
    else:
        print("TD guest boot failure...")

def extract_quote(output):
    pattern = r'export QUOTE="([^"]+)"'
    match = re.search(pattern, output)
    if match:
        return match.group(1)
    else:
        raise ValueError("QUOTE not found in the output.")

def get_td_measurement():
    """Get the TD measurement"""
    process = launch_td_guest("GET_QUOTE")
    # Capture the output and error
    stdout, stderr = process.communicate()
    # Check the return code
    if process.returncode == 0:
        print("Command executed successfully.")
        print("Output:\n", stdout)
    else:
        print("Error executing command.")
        print("Error message:\n", stderr)

    return extract_quote(stdout)

def store_key_in_kbs():
    """Store the encryption key in KBS."""
    required_vars = [
        "SK_KBS_ADMIN", "KBS_URL", "KBS_CERT_PATH", "QUOTE", "ID_k_RFS", "k_RFS"
    ]

    for var in required_vars:
        if var not in os.environ:
            raise EnvironmentError(f"Environment variable {var} is not set")

    command = [
        './fde-binaries/target/release/fde-kbs-store-key',
        '--sk-kbs-admin-path', os.environ["SK_KBS_ADMIN"],
        '--kbs-url', os.environ["KBS_URL"],
        '--kbs-cert-path', os.environ["KBS_CERT_PATH"],
        '--quote-b64', os.environ["QUOTE"],
        '--k-rfs-id', os.environ["ID_k_RFS"],
        '--k-rfs', os.environ["k_RFS"]
    ]

    result = run_command(command)
    
    if result:
        print("Successfully stored encryption key in KBS")
    else:
        print("Failed to store encryption key in KBS")
    
    return result


def verify_td_encrypted_image(ssh_command=None):
    if not ssh_command:
        ssh_command = "sshpass -p 123456 ssh -o StrictHostKeyChecking=no -p 10022 root@localhost 'df -h | grep '/boot' | grep -v '/boot/';df -h | grep 'rootfs';cat /etc/os-release;uname -r;sudo blkid'"
    result = execute_td_command(ssh_command)
    if result is not None and \
        configuration.fde_check in result and \
        configuration.os_name_2404 in result and \
        configuration.ubuntu_kernel_version in result:
        return True
    else:
        return False