import subprocess
import sys
import re
import os
from utils import set_environment_variables, run_command
from docker import remove_docker_container, run_docker_container, verify_docker_container, get_build_args
import time
sys.path.insert(1, os.path.join(os.getcwd(), 'configuration'))
import configuration


def create_docker_network():
    """Create the trustee-net Docker network if it doesn't exist."""
    # Check if network exists
    check_command = ["docker", "network", "ls", "--filter", "name=trustee-net", "--format", "{{.Name}}"]
    result = subprocess.run(check_command, capture_output=True, text=True)
    
    if "trustee-net" in result.stdout:
        print("Docker network 'trustee-net' already exists.")
        return
    
    # Create network
    create_command = ["docker", "network", "create", "trustee-net"]
    create_process = subprocess.run(create_command, capture_output=True, text=True)
    
    if create_process.returncode == 0:
        print("Successfully created Docker network 'trustee-net'.")
    else:
        print("Failed to create Docker network.")
        print(create_process.stderr)


def start_vault_container():
    """Start Vault in a Docker container in development mode."""
    # Remove existing container if it exists
    remove_docker_container("trustee-vault")
    
    # Generate a random 128-bit token using openssl
    result = subprocess.run(['openssl', 'rand', '-hex', '16'], capture_output=True, text=True)
    vault_root_token = result.stdout.strip()
    
    # Set the environment variable VAULT_ROOT_TOKEN
    set_environment_variables(key="VAULT_ROOT_TOKEN", data=vault_root_token)
    
    # Get environment variables including proxy settings
    env_vars = get_build_args()
    env_vars['VAULT_DEV_ROOT_TOKEN_ID'] = vault_root_token
    env_vars['VAULT_DEV_LISTEN_ADDRESS'] = '0.0.0.0:8200'
    env_vars['VAULT_ADDR'] = 'http://127.0.0.1:8200'
    env_vars['VAULT_TOKEN'] = vault_root_token
    
    # Add IPC_LOCK capability
    extra_flags = ["--cap-add=IPC_LOCK"]
    
    # Command to start vault and enable secrets engine
    command_args = [
        "sh", "-c",
        "docker-entrypoint.sh server -dev & until vault status >/dev/null 2>&1; do sleep 1; done; vault secrets enable -version=1 -path=keybroker kv 2>/dev/null || true && wait"
    ]
    
    # Start the container using the common function
    success = run_docker_container(
        container_name="trustee-vault",
        image_tag="hashicorp/vault:1.20",
        network="trustee-net",
        environment_vars=env_vars,
        extra_flags=extra_flags,
        command_args=command_args
    )
    
    if success:
        print(f"Vault container started successfully with root token: {vault_root_token}")
        print("Vault will automatically enable KV secrets engine at path 'keybroker'")
        time.sleep(5)  # Wait for the container to start and initialize
        return True
    else:
        return False

def update_env_file():
    """Update the environment file with VAULT_ROOT_TOKEN and VAULT_ADDR."""
    vault_token = os.environ.get('VAULT_ROOT_TOKEN')
    
    if not vault_token :
        print("Error: VAULT_ROOT_TOKEN not set.")
        return
    
    # Check if the file exists
    env_file_path = os.environ.get('SETUP_CONFIG_FILE')
    if not os.path.exists(env_file_path):
        print(f"Warning: Environment file not found at {env_file_path}")
        return
    
    # Update VAULT_ROOT_TOKEN
    sed_token_command = f'sed -i "/^export VAULT_ROOT_TOKEN=/c\\\\export VAULT_ROOT_TOKEN=\\"{vault_token}\\"" "{env_file_path}"'
    run_command(sed_token_command, shell=True)
    
    print(f"Updated environment file at {env_file_path}")


def setup_kms_environment():
    """Set up the KMS environment with Vault running in a Docker container."""
    create_docker_network()
    
    if start_vault_container():
        update_env_file()

