import subprocess
import os

def is_docker_installed():
    """Check if Docker is already installed."""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, check=True)
        print(f"Docker is already installed: {result.stdout}")
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False

def install_docker():
    """Install Docker using the official installation script."""
    if is_docker_installed():
        print("Docker is already installed. Skipping installation.")
        return
    try:
        # Download the Docker installation script
        subprocess.run(["curl", "-fsSL", "https://get.docker.com", "-o", "get-docker.sh"], check=True)

        # Run the Docker installation script
        subprocess.run(["sudo", "sh", "get-docker.sh"], check=True)

        print("Docker installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

def enable_docker_non_root():
    """Enable Docker for non-root users."""
    try:
        # Check if the docker group already exists
        result = subprocess.run(["getent", "group", "docker"], capture_output=True, text=True)
        if result.returncode != 0:
            # Create the docker group if it doesn't exist
            subprocess.run(["sudo", "groupadd", "docker"], check=True, capture_output=True, text=True)

        # Add the current user to the docker group
        print("Adding user")
        user = os.getenv("USER")
        print(f"Adding {user} to the group")
        subprocess.run(["sudo", "usermod", "-aG", "docker", user], check=True, capture_output=True, text=True)

        print("Docker enabled for non-root user.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

def remove_docker_container(container_id):
    """Stops and removes a Docker container."""
    try:
        # Stop the container
        subprocess.run(['docker', 'stop', container_id], check=True)
        print(f"Container {container_id} has been stopped.")
    except subprocess.CalledProcessError:
        print(f"Container {container_id} is not running or does not exist.")
        return  # Exit the function if the container is not running or does not exist

    try:
        # Remove the container
        subprocess.run(['docker', 'rm', container_id], check=True)
        print(f"Container {container_id} has been removed.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while removing the container: {e}")

def setup_docker_environment():
    install_docker()
    enable_docker_non_root()