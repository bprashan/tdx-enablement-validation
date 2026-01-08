import pytest
import os
from libs.rust import setup_rust
from libs.kms import setup_kms_environment
from libs.docker import setup_docker_environment
from libs.kbs import setup_kbs_environment
from libs.fde import setup_fde_environment
from libs.tdx import update_canonical_tdx_repository, create_td_image
from libs.utils import delete_directory_with_sudo, delete_files_in_subdirectories, run_command, kill_docker_vault

@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    print("Deleting fde directory")
    fde_path = os.path.join(os.path.dirname(__file__), "fde")
    delete_directory_with_sudo(fde_path)

    print("Setting up Docker environment")
    setup_docker_environment()

    print("Setting up Rust environment")
    setup_rust()

    print("Setting up FDE environment")
    setup_fde_environment()

    print("Setting up KMS environment")
    setup_kms_environment()

    print("Setting up KBS environment")
    setup_kbs_environment()

    print("Cloning and patching TDX repository")
    update_canonical_tdx_repository()

    print("Creating TD image")
    create_td_image()

    yield
    # Cleanup after test session
    # print("Cleaning up after tests")
    # dir_path = "TDXSampleUseCases/full-disk-encryption/ita-kbs/data"
    # delete_files_in_subdirectories(dir_path)
    # img_dir_path = os.path.abspath("TDXSampleUseCases/full-disk-encryption/tools/image")
    # if os.path.exists(img_dir_path):
    #     command = ["sudo", "rm", "-rf", "tdx-guest*", "OVMF_*", "my_venv", "tmp_fde"]
    #     run_command(command, cwd=img_dir_path)
    # kill_docker_vault()

# @pytest.fixture(autouse=True)
# def cleanup():
#     print("Cleaning up after tests")
#     dir_path = "TDXSampleUseCases/full-disk-encryption/ita-kbs/data"
#     delete_files_in_subdirectories(dir_path)
#     img_dir_path = os.path.abspath("TDXSampleUseCases/full-disk-encryption/tools/image")
#     if os.path.exists(img_dir_path):
#         command = ["sudo", "rm", "-rf", "tdx-guest*", "OVMF_*", "my_venv", "tmp_fde"]
#         run_command(command, cwd=img_dir_path)
