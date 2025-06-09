import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'libs'))
from rust import setup_rust
from kms import setup_kms_environment
from kbs import setup_kbs_environment
from fde import setup_fde_environment, before_testcase
from tdx import clone_and_patch_tdx_repository, create_td_image
from docker import setup_docker_environment
from utils import delete_directory_with_sudo, delete_files_in_subdirectories, run_command
sys.path.insert(1, os.path.join(os.getcwd(), 'configuration'))
import configuration

@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    print("Deleting TDXSampleUseCases directory")
    delete_directory_with_sudo(os.path.expanduser('~') + "/" + configuration.folder_name)

    print("Setting up Docker environment")
    setup_docker_environment()

    print("Setting up Rust environment")
    setup_rust()

    print("Setting up KMS environment")
    setup_kms_environment()

    print("Setting up KBS environment")
    setup_kbs_environment()

    print("Setting up FDE environment")
    setup_fde_environment()

    yield
    # Teardown logic after all tests
    print("Cleaning up after tests")
    dir_path = "TDXSampleUseCases/full-disk-encryption/ita-kbs/data"
    delete_files_in_subdirectories(dir_path)
    img_dir_path = os.path.abspath("TDXSampleUseCases/full-disk-encryption/tools/image")
    if os.path.exists(img_dir_path):
        command = ["sudo", "rm", "-rf", "tdx-guest*", "OVMF_*", "my_venv", "tmp_fde"]
        run_command(command, cwd=img_dir_path)

@pytest.fixture(scope="function",autouse=True)
def testase_setup():
    # Setup logic before each test
    print("Running before_testcase setup")
    before_testcase()
    yield
    # Cleanup logic after each test 
    print("Cleaning up test case environment")
    dir_path = "TDXSampleUseCases/full-disk-encryption/data"
    delete_files_in_subdirectories(dir_path)


# @pytest.fixture(autouse=True)
# def cleanup():
#     print("Cleaning up after tests")
#     dir_path = "TDXSampleUseCases/full-disk-encryption/ita-kbs/data"
#     delete_files_in_subdirectories(dir_path)
#     img_dir_path = os.path.abspath("TDXSampleUseCases/full-disk-encryption/tools/image")
#     if os.path.exists(img_dir_path):
#         command = ["sudo", "rm", "-rf", "tdx-guest*", "OVMF_*", "my_venv", "tmp_fde"]
#         run_command(command, cwd=img_dir_path)
