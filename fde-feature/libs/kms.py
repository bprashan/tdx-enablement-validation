import subprocess
import re
import os
from utils import set_environment_variables
import time


def is_vault_installed():
    """Check if Vault is already installed."""
    try:
        result = subprocess.run(["vault", "--version"], capture_output=True, text=True, check=True)
        print(f"Vault is already installed: {result.stdout}")
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False

def setup_vault():
    """Install HashiCorp Vault if it is not already installed."""
    if is_vault_installed():
        print("HashiCorp Vault is already installed. Skipping installation.")
        return

    try:
        # Update the package list
        subprocess.run(["sudo", "apt-get", "update"], check=True)

        # Install necessary dependencies
        subprocess.run(["sudo", "apt-get", "install", "-y", "gnupg", "software-properties-common"], check=True)

        # Add the HashiCorp GPG key
        subprocess.run("curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor --batch --yes -o /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null", shell=True, capture_output=True, text=True)

        subprocess.run('echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list', shell=True, capture_output=True, text=True)

        # Update the package list again
        subprocess.run(["sudo", "apt-get", "update"], check=True)

        # Install Vault
        subprocess.run(["sudo", "apt-get", "install", "-y", "vault"], check=True)

        print("HashiCorp Vault installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

def kill_existing_vault_process(port=8200):
    """Check if any process is listening on the specified port and kill it."""
    check_command = ["sudo", "lsof", "-i", f":{port}"]
    check_process = subprocess.run(check_command, capture_output=True, text=True)

    if check_process.returncode == 0:
        # Extract the PID and kill the process
        pid = re.search(r'\n(\S+)\s+(\d+)', check_process.stdout).group(2)
        kill_command = ["sudo", "kill", "-9", pid]
        kill_process = subprocess.run(kill_command, capture_output=True, text=True)

        if kill_process.returncode == 0:
            print(f"Successfully killed the existing Vault process with PID: {pid}")
        else:
            print("Failed to kill the existing Vault process.")
            print(kill_process.stderr)
    else:
        print(f"No existing Vault process found on port {port}.")

def start_vault_server():
    """Kill any existing Vault process and start the Vault server in development mode."""
    kill_existing_vault_process()

    # Generate a random token using openssl
    result = subprocess.run(['openssl', 'rand', '-hex', '16'], capture_output=True, text=True)
    vault_root_token = result.stdout.strip()

    # Start the Vault server in development mode with the generated token
    subprocess.Popen(['vault', 'server', '-dev', '-dev-root-token-id', vault_root_token])
    print(f"Vault server started with root token: {vault_root_token}")
    time.sleep(5)  # Wait for the server to start

    # Set the environment variable VAULT_ROOT_TOKEN
    set_environment_variables(key="VAULT_ROOT_TOKEN", data=vault_root_token)

def login_to_vault(root_token):
    """Log in to Vault using the root token."""

    set_environment_variables(key="VAULT_ADDR", data='http://127.0.0.1:8200')
    login_command = ["vault", "login", root_token]
    login_process = subprocess.run(login_command, capture_output=True, text=True)

    if login_process.returncode == 0:
        print("Successfully logged in to Vault.")
        return True
    else:
        print("Failed to log in to Vault.")
        print(login_process.stderr)
        return False

def enable_secrets_engine():
    """Enable the KV secrets engine at the specified path."""
    enable_command = ["vault", "secrets", "enable", "-path=keybroker", "kv"]
    enable_process = subprocess.run(enable_command, capture_output=True, text=True)

    if enable_process.returncode == 0:
        print("Successfully enabled the KV secrets engine at path 'keybroker'.")
    else:
        print("Failed to enable the KV secrets engine.")
        print(enable_process.stderr)

def setup_kms_environment():
    setup_vault()
    start_vault_server()
    root_token = os.environ['VAULT_ROOT_TOKEN']
    if login_to_vault(root_token):
        enable_secrets_engine()
