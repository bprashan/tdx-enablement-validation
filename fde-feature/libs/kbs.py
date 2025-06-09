import subprocess
import os
from utils import get_ip_address, clone_repo, set_environment_variables, run_command
import shutil
import time
import sys
sys.path.insert(1, os.path.join(os.getcwd(), 'configuration'))
import configuration

ita_dir_folder_path = os.path.expanduser('~') + "/" + configuration.folder_name + "/" + configuration.ita_dir_name
class KBSEnvConfig:
    def __init__(self, **kwargs):
        self.config = {
            "LOG_LEVEL": "DEBUG",
            "KEY_MANAGER": "VAULT",
            "ADMIN_USERNAME": os.getenv("ADMIN_USERNAME", "test"),
            "ADMIN_PASSWORD": os.getenv("ADMIN_PASSWORD", "test@123456"),
            "TRUSTAUTHORITY_API_URL": "https://api.trustauthority.intel.com",
            "TRUSTAUTHORITY_API_KEY": os.getenv("TRUSTAUTHORITY_API_KEY", "ZBixzqA3As2abpQsxgWin2wprwwZ6kiWuJjkr0103"),
            "TRUSTAUTHORITY_BASE_URL": os.getenv("TRUSTAUTHORITY_BASE_URL", "https://portal.trustauthority.intel.com"),
            "SAN_LIST": f"{get_ip_address()}",
            "VAULT_SERVER_IP": "127.0.0.1",
            "VAULT_SERVER_PORT": 8200,
            "VAULT_CLIENT_TOKEN": os.environ['VAULT_ROOT_TOKEN']
        }
        self.config.update(kwargs)

    def create_env_file(self, file_name=ita_dir_folder_path+"/kbs.env"):
        #directory = os.path.expanduser('~') + "/" + configuration.folder_name  +"/" + configuration.ita_dir_name + file_name
        content = "\n".join([f"{key}={value}" for key, value in self.config.items()])
        with open(file_name, 'w') as file:
            file.write(content)

def build_kbs():
    run_command(['make docker'], shell=True, cwd=ita_dir_folder_path)

def setup_directories():
    """Create the required directories."""
    directories = [
        "data/users",
        "data/keys",
        "data/keys-transfer-policy",
        "data/certs/tls",
        "data/certs/signing-keys"
    ]

    for directory in directories:
        full_path = os.path.join(ita_dir_folder_path, directory)
        os.makedirs(full_path, exist_ok=True)
        print(f"Directory created: {full_path}")

def run_kbs_container(env_file):
    """Run the KBS Docker container with the specified environment file and container name."""
    # Stop and remove any existing container with the specified name
    try:
        subprocess.run(["docker", "rm", "-f", configuration.container_name], check=True)
        print(f"Existing Docker container '{configuration.container_name}' removed.")
    except subprocess.CalledProcessError:
        print(f"No existing Docker container named '{configuration.container_name}' to remove.")

    # Define the Docker run command
    command = [
        "docker", "run", "-d", "--restart", "unless-stopped", "--name", configuration.container_name,
        "--env-file", env_file,
        "--net=host",
        "-v", f"{ita_dir_folder_path}/data/certs:/etc/kbs/certs",
        "-v", "/etc/hosts:/etc/hosts",
        "-v", f"{ita_dir_folder_path}/data:/opt/kbs",
        "trustauthority/key-broker-service:v1.3.0"
    ]
    try:
        # Run the command
        subprocess.run(command, check=True)
        print(f"Docker container '{configuration.container_name}' started successfully.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while starting the Docker container '{configuration.container_name}': {e}")

def get_docker_logs():
    """Fetch and display logs for the specified Docker container."""
    result = subprocess.run(['docker', 'logs', configuration.container_name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.stdout.decode()

def setup_kbs_environment():
    clone_repo(configuration.kbs_url, configuration.ita_dir_name, configuration.kbs_branch)
    build_kbs()
    setup_directories()

def check_error_messages(logs):
    error_messages = ["error", "permission denied", "invalid token", "key create failed"]
    return any(msg in logs for msg in error_messages)

def run_kbs():
    env_file_path = f"{ita_dir_folder_path}/kbs.env"
    print(env_file_path)
    config = KBSEnvConfig(TRUSTAUTHORITY_API_KEY="aeKQBT22ux7tZVB1uLyQN58Z1M9J0Bwg8LAQgLpl")
    config.create_env_file(env_file_path)
    run_kbs_container(env_file_path)
    time.sleep(20)

    # Check for error messages in logs
    if check_error_messages(get_docker_logs()):
        print("Error detected in Docker logs. Exiting execution.")
        return False
    set_environment_variables(key="KBS_URL", data=f"https://{get_ip_address()}:9443")
    set_environment_variables(key="KBS_ENV", data=env_file_path)
    set_environment_variables(key="KBS_CERT_PATH", data=f"{ita_dir_folder_path}/data/certs/tls/tls.crt")
    return True