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

def generate_rsa_key_pair(directory='data', key_size=3072):
    # Create the directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    # Paths for the private and public keys
    private_key_path = os.path.join(directory, 'sk_kr.pem')
    public_key_path = os.path.join(directory, 'pk_kr.pem')

    # Generate the RSA private key
    subprocess.run(['openssl', 'genrsa', '-out', private_key_path, str(key_size)])

    # Extract the public key from the private key
    subprocess.run(['openssl', 'rsa', '-in', private_key_path, '-outform', 'PEM', '-pubout', '-out', public_key_path])

    set_environment_variables(key="PK_KR_PATH", data=os.path.abspath(public_key_path))
    set_environment_variables(key="SK_KR_PATH", data=os.path.abspath(private_key_path))
    print(f"RSA key pair generated successfully in '{directory}'.")

def generate_tmp_fde_key(directory='data'):
    """Generate a temporary FDE key."""
    # Create the directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    # Generate 32 random bytes
    random_bytes = os.urandom(32)

    # Convert to hexadecimal format
    hex_string = binascii.hexlify(random_bytes).decode()

    # Write the hex string to the file
    with open('data/tmp_k_rfs', 'w') as file:
        file.write(hex_string)

    set_environment_variables(key="TMP_K_RFS_PATH", data=f"{os.getcwd()}/data/tmp_k_rfs")
    print("Hex string saved to data/tmp_k_rfs")

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

def setup_fde_environment():
    update_and_install_packages()
    dir_name = configuration.repo_url.split('/')[-1].replace('.git','')
    clone_repo(configuration.repo_url, dir_name , configuration.branch)
    os.chdir(os.path.expanduser('~') + "/" + configuration.folder_name + "/" + dir_name +"/full-disk-encryption")
    print(f"Changed working directory to {os.getcwd()}")
    build_project()
    print("Cloning and patching TDX repository")
    clone_and_patch_tdx_repository()
    print("Creating TD image")
    create_td_image()
    # generate_rsa_key_pair()
    # generate_tmp_fde_key()
    # setup_ovmf_tdx()

def before_testcase():
    generate_rsa_key_pair()
    generate_tmp_fde_key()
    setup_ovmf_tdx()

def parse_and_set_ovmf_and_image_path(console_output):
    """
    Parses the console output to extract OVMF_PATH and IMAGE_PATH,
    then sets them as environment variables.
    """
    # Define regex patterns to extract paths
    ovmf_pattern = r"OVMF_PATH:\s*(\S+)"
    image_pattern = r"IMAGE_PATH:\s*(\S+)"

    # Search for the patterns in the console output
    ovmf_match = re.search(ovmf_pattern, console_output)
    image_match = re.search(image_pattern, console_output)

    if not ovmf_match or not image_match:
        print("Error: Either OVMF or ENCRYPTED IMAGE paths not found in the console output.")
        sys.exit(1)

    ovmf_path = ovmf_match.group(1)
    image_path = image_match.group(1)

    if not (os.path.exists(ovmf_path) and os.path.exists(image_path)):
        print("Error:  Either OVMF or ENCRYPTED IMAGE paths do not exist on the filesystem.")
        print(f"OVMF_PATH: {ovmf_path} (exists: {os.path.exists(ovmf_path)})")
        print(f"ENCRYPTED_IMAGE_PATH: {image_path} (exists: {os.path.exists(image_path)})")
        sys.exit(1)

    # Set environment variables
    set_environment_variables(key="OVMF_PATH", data=ovmf_path)
    set_environment_variables(key="ENCRYPTED_IMAGE_PATH", data=image_path)


def encrypt_image(mode, skip_encrypt_image_path=False, extra_args=None):
    """Encrypt the image using the FDE key and KBS certificate path."""
    command = ["sudo", "tools/image/fde-encrypt_image.sh", mode]
    base_image_path=os.environ["BASE_IMAGE_PATH"]
    tmp_k_rfs_path=os.environ["TMP_K_RFS_PATH"]
    encrypted_image_path=os.environ["ENCRYPTED_IMAGE_PATH"]
    if not skip_encrypt_image_path:
        command.extend(["-e", encrypted_image_path])

    if mode == 'GET_QUOTE':
        kbs_cert_path=os.environ["KBS_CERT_PATH"]
        pr_kr_path=os.environ["PK_KR_PATH"]
        command.extend([
            "-c", kbs_cert_path,
            "-p", base_image_path,
            "-f", pr_kr_path,
            "-d", tmp_k_rfs_path,
    ])
        if extra_args:
            command.extend(extra_args)

    elif mode == 'TD_FDE_BOOT':
        fde_key=os.environ["k_RFS"]
        kbs_url=os.environ["KBS_URL"]
        key_id=os.environ["ID_k_RFS"]
        command.extend([
            "-p", encrypted_image_path,
            "-u", kbs_url,
            "-k", fde_key,
            "-i", key_id,
            "-d", tmp_k_rfs_path,
        ])
    else:
        raise ValueError("Invalid mode. Use 'GET_QUOTE' or 'TD_FDE_BOOT'.")

    retcode, output = run_command_with_popen(command)
    if retcode == 0:
        parse_and_set_ovmf_and_image_path("\n".join(output))
        return True
    else:
        print("Error during image encryption:")
        print("\n".join(output))
        return False

def launch_td_guest():
    """Launch the TD guest."""
    set_environment_variables("TD_IMG", os.environ["ENCRYPTED_IMAGE_PATH"])
    ovmf_path = os.getenv('OVMF_PATH')
    command = [f"canonical-tdx/guest-tools/run_td.sh -d false -f {ovmf_path}"]

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
        "KBS_ENV", "KBS_URL", "KBS_CERT_PATH", "QUOTE", "PK_KR_PATH", "SK_KR_PATH"
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
        '--pk-kr-path', os.environ["PK_KR_PATH"],
        '--sk-kr-path', os.environ["SK_KR_PATH"],
    ]

    return run_command(command)

def verify_td_encrypted_image(ssh_command=None):
    if not ssh_command:
        ssh_command = "sshpass -p 123456 ssh -o StrictHostKeyChecking=no -p 10022 root@localhost 'sudo blkid;uname -a;df -h | grep -E \'/boot | /rootfs-\'"
    result = execute_td_command(ssh_command)
    if result is not None and ' TYPE="crypto_LUKS" PARTLABEL="rootfs"' in result:
        return True
    else:
        return False