import subprocess
import os
import time
from utils import run_command, clone_repo, run_command_with_popen, remove_host_from_known_hosts, set_environment_variables
import re

def update_and_install_packages():
    """Update package lists and install specified packages."""
    update_command = ["sudo", "apt", "update"]
    install_command = [
        "sudo", "apt", "install", "-y", "build-essential", "pkg-config", "gpg", "wget", "openssl",
        "libcryptsetup-dev", "python3-venv", "libtdx-attest-dev", "sshpass"
    ]

    # Run the update command
    run_command(update_command)

    # Run the install command
    run_command(install_command)

def build_project():
    """Navigate to the full-disk-encryption directory and build the project."""
    run_command(["cargo", "build", "--release", "--manifest-path", "fde-binaries/Cargo.toml"])

def setup_fde_environment():
    repo_url = "https://github.com/IntelConfidentialComputing/TDXSampleUseCases.git"
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    update_and_install_packages()
    clone_repo(repo_url, repo_name, 'jkr0103/issues_fixes')
    fde_dir = os.path.join(repo_name, "full-disk-encryption")
    os.chdir(fde_dir)
    print(f"Changed working directory to {os.getcwd()}")
    build_project()

def encrypt_image(mode, encrypted_image_path=None, kbs_cert_path=None, base_image_path=None, fde_key=None, key_id=None, kbs_url=None):
    """Encrypt the image using the FDE key and KBS certificate path."""
    command = ["sudo", "tools/image/fde-encrypt_image.sh", mode]

    if mode == 'GET_QUOTE':
        command.extend([
            "-c", kbs_cert_path,
            "-p", base_image_path,
            "-e", encrypted_image_path
    ])
    elif mode == 'TD_FDE_BOOT':
        command.extend([
            "-e", encrypted_image_path,
            "-u", kbs_url,
            "-k", fde_key,
            "-i", key_id
        ])
    else:
        raise ValueError("Invalid mode. Use 'GET_QUOTE' or 'TD_FDE_BOOT'.")

    return run_command_with_popen(command)

def launch_td_guest():
    """Launch the TD guest."""
    set_environment_variables("TD_IMG", os.environ["ENCRYPTED_IMAGE_PATH"])
    command = ["tdx/guest-tools/run_td.sh -d false -f tools/image/OVMF_FDE.fd"]

    print("Launching TD guest...")
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return process

def execute_td_command(ssh_command, sleep_duration=120):
    """Execute the TD command and SSH command."""
    process = launch_td_guest()

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
    process = launch_td_guest()
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

def retrieve_encryption_key():
    """Retrieve the encryption key."""
    required_vars = [
        "KBS_ENV", "KBS_URL", "KBS_CERT_PATH", "QUOTE"
    ]

    for var in required_vars:
        if var not in os.environ:
            raise EnvironmentError(f"Environment variable {var} is not set")

    command = [
        './fde-binaries/target/release/fde-key-gen',
        '--kbs-env-file-path', os.environ["KBS_ENV"],
        '--kbs-url', os.environ["KBS_URL"],
        '--kbs-cert-path', os.environ["KBS_CERT_PATH"],
        '--quote-b64', os.environ["QUOTE"],
    ]

    return run_command(command)

def verify_td_encrypted_image(ssh_command=None):
    if not ssh_command:
        ssh_command = "sshpass -p 123456 ssh -o StrictHostKeyChecking=no -p 10022 root@localhost 'sudo blkid'"
    result = execute_td_command(ssh_command)
    if result is not None and 'TYPE="crypto_LUKS"' in result:
        return True
    else:
        return False