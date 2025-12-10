import subprocess
import os
import time

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

def build_docker_image(context_dir, dockerfile_path, image_tag, build_args=None):
    """
    Common function to build a Docker image.
    
    Args:
        context_dir: The build context directory
        dockerfile_path: Path to the Dockerfile (relative to context_dir)
        image_tag: Tag for the resulting image
        build_args: Dictionary of build arguments (e.g., proxy settings)
    """
    print(f"Building Docker image: {image_tag}")
    
    command = [
        "docker", "build",
        "--ulimit", "nofile=90000:90000",
        "-f", dockerfile_path,
        "-t", image_tag
    ]
    
    # Add build arguments
    if build_args:
        for key, value in build_args.items():
            if value:  # Only add if value is not None or empty
                command.extend(["--build-arg", f"{key}={value}"])
    
    command.append(".")
    
    result = subprocess.run(command, cwd=context_dir, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"Successfully built Docker image: {image_tag}")
        return True
    else:
        print(f"Failed to build Docker image: {image_tag}")
        print(result.stderr)
        return False


def run_docker_container(container_name, image_tag, network, environment_vars=None, 
                         volumes=None, ports=None, command_args=None, extra_flags=None):
    """
    Common function to run a Docker container.
    
    Args:
        container_name: Name for the container
        image_tag: Docker image to run
        network: Docker network to attach to
        environment_vars: Dictionary of environment variables
        volumes: List of volume mounts (format: "host_path:container_path:mode")
        ports: List of port mappings (format: "host_port:container_port")
        command_args: List of command arguments to pass to the container
        extra_flags: List of additional docker run flags
    """
    print(f"Starting Docker container: {container_name}")
    
    # Remove existing container if it exists
    remove_docker_container(container_name)
    
    command = [
        "docker", "run", "-d",
        "--name", container_name,
        "--network", network,
        "--restart", "unless-stopped",
        "--ulimit", "nofile=90000:90000"
    ]
    
    # Add port mappings
    if ports:
        for port in ports:
            command.extend(["-p", port])
    
    # Add volumes
    if volumes:
        for volume in volumes:
            command.extend(["-v", volume])
    
    # Add environment variables
    if environment_vars:
        for key, value in environment_vars.items():
            if value:  # Only add if value is not None or empty
                command.extend(["-e", f"{key}={value}"])
    
    # Add extra flags if provided
    if extra_flags:
        command.extend(extra_flags)
    
    # Add image tag
    command.append(image_tag)
    
    # Add command arguments
    if command_args:
        command.extend(command_args)
    
    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"Successfully started container: {container_name}")
        print(f"Container ID: {result.stdout.strip()}")
        return True
    else:
        print(f"Failed to start container: {container_name}")
        print(result.stderr)
        return False


def verify_docker_container(container_name, expected_log_patterns, wait_time=5):
    """
    Common function to verify a Docker container is running correctly by checking logs.
    
    Args:
        container_name: Name of the container to check
        expected_log_patterns: List of strings that should appear in logs
        wait_time: Time to wait before checking logs
    
    Returns:
        True if all expected patterns are found, False otherwise
    """
    print(f"Waiting {wait_time} seconds for container to start...")
    time.sleep(wait_time)
    
    print(f"Verifying {container_name} deployment...")
    result = subprocess.run(['docker', 'logs', container_name], 
                          capture_output=True, text=True)
    
    logs = result.stdout + result.stderr
    print(f"Container logs:\n{logs}")
    
    all_found = True
    for pattern in expected_log_patterns:
        if pattern in logs:
            print(f"✓ Found expected pattern: {pattern}")
        else:
            print(f"✗ Missing expected pattern: {pattern}")
            all_found = False
    
    return all_found

def get_build_args():
    """Get common build arguments including proxy settings."""
    build_args = {}
    
    http_proxy = os.getenv('HTTP_PROXY')
    https_proxy = os.getenv('HTTPS_PROXY')
    no_proxy = os.getenv('NO_PROXY')
    
    if http_proxy:
        build_args['http_proxy'] = http_proxy
    if https_proxy:
        build_args['https_proxy'] = https_proxy
    if no_proxy:
        build_args['no_proxy'] = no_proxy
    
    return build_args

def setup_docker_environment():
    install_docker()
    enable_docker_non_root()

