import subprocess
import os
import sys
import socket
import shutil
import psutil
import time
sys.path.insert(1, os.path.join(os.getcwd(), 'configuration'))
import configuration

def run_command(command, shell=False, cwd=None):
    """Run a shell command."""
    try:
        print(f"Executing command : {command}")
        result = subprocess.run(command, shell=shell, check=True, capture_output=True, text=True, cwd=cwd)
        print(result.stdout.strip())
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Return code: {e.returncode}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return e.stderr

def run_command_with_popen(command, cwd=None, shell=False, timeout=600):
    """Run a command in a subprocess and print the output in real-time."""
    print(f"Executing command : {command}")
    process = subprocess.Popen(command, cwd=cwd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    output_lines = []
    start_time = time.time()
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
            output_lines.append(output.strip())
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            print("Timeout reached. Terminating process.")
            process.terminate()
            return -1, output_lines

    # Print any remaining errors
    stdout , stderr = process.communicate()
    if stderr:
        print(stderr.strip())
    return process.returncode, output_lines , stderr

def set_environment_variables(key=None, data=None):
    """Set environment variables for a specific key and from a string of key-value pairs.
       Returns True if the value is not empty, False otherwise."""
    if key and data:
        os.environ[key] = data.strip('"')
        print(f"Set environment variable: {key}={data.strip('\"')}")
        return bool(data.strip('"'))

    if data:
        if "error" in data.lower():
            print("Error detected!")
            return False
        elements = data.split()
        for element in elements:
            if '=' in element:
                key, value = element.split('=', 1)
                if not value.strip('"'):
                    print(f"Value for {key} is empty.")
                    return False
                os.environ[key] = value.strip('"')
                print(f"Set environment variable: {key}={value.strip('\"')}")
        return True

def get_ip_address():
    """Retrieve the actual IP address of the machine."""
    try:
        # Connect to an external server to get the local IP address
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
        return ip_address
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def clone_repo(repo_url, clone_dir, recurse_submodules = False, branch=None):
    """Clone a git repository into a specified directory."""
    if os.path.exists(clone_dir):
        shutil.rmtree(clone_dir)

    clone_command = ["git", "clone"]
    if recurse_submodules:
        clone_command.append("--recurse-submodules")
    if branch:
        clone_command.extend(["-b", branch])
    clone_command.extend([repo_url, clone_dir])

    run_command(clone_command)

def remove_host_from_known_hosts(host, port, known_hosts_file='/home/sdp/.ssh/known_hosts'):
    # Construct the host string
    host_string = f'[{host}]:{port}'

    # Run the ssh-keygen command to remove the host entry
    subprocess.run(['ssh-keygen', '-f', known_hosts_file, '-R', host_string])

    print(f"Removed {host_string} from {known_hosts_file}")

def delete_file(file_path):
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Successfully deleted the file: {file_path}")
        except Exception as e:
            print(f"Failed to delete the file: {file_path}. Reason: {e}")
    else:
        print(f"The file does not exist: {file_path}")

def delete_files_in_subdirectories(directory):
    """Deletes all files inside the specified directory and its subdirectories without deleting the folders."""
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")

def delete_directory_with_sudo(directory_path):
    if os.path.exists(directory_path):
        try:
            # Execute the command to remove the directory with sudo
            run_command(['sudo', 'rm', '-rf', directory_path])
            print(f"Successfully deleted the directory: {directory_path}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to delete the directory: {directory_path}. Reason: {e}")
    else:
        print(f"The directory does not exist: {directory_path}")

def find_and_kill_process(file_path):
    # Iterate over all running processes
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # Check if the process has the file open
            for file in proc.open_files():
                if file.path == file_path:
                    print(f"Killing process {proc.info['name']} (PID: {proc.info['pid']})")
                    proc.kill()
                    return
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    print(f"No process found using the file: {file_path}")

def kill_docker_vault():
    try:
        run_command(['sudo', 'kill', '-9' ,'$(sudo ps -aux | grep vault | awk \'{print $2}\')'])
        run_command(['docker', 'stop', configuration.container_name])
        run_command(['docker', 'rm', configuration.container_name])
        run_command(['sudo', 'docker', 'system', 'prune' ,'-af'])
    except subprocess.CalledProcessError as e:
        print(f"Failed to kill process: {e}")

def manage_qcow2_image(image_path, mount_point, partition):
    """
    Mounts and unmounts a QCOW2 image using qemu-nbd and mounts it to a specified directory.

    :param image_path: Path to the QCOW2 image file.
    :param mount_point: Directory where the partition will be mounted.
    :param partition: Partition number to mount.
    """
    try:
        os.makedirs(mount_point, exist_ok=True)
        run_command(['sudo', 'modprobe', 'nbd', 'max_part=8'])
        find_and_kill_process(image_path)
        time.sleep(5)
        run_command(['sudo', 'qemu-nbd', '--format=raw', '--connect=/dev/nbd0', image_path])
        return run_command(['sudo', 'mount', f'/dev/nbd0p{partition}', mount_point])
    finally:
        run_command(['sudo', 'umount', f'/dev/nbd0p{partition}', mount_point])
        run_command(['sudo', 'qemu-nbd', '--disconnect', '/dev/nbd0'])
        print(f"Partition /dev/nbd0p{partition} unmounted and NBD device disconnected")