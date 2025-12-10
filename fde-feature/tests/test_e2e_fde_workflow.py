import os
import sys
import pytest
import random
import string
import subprocess
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '../libs'))
from fde import *
from kbs import run_kbs, check_error_messages, get_docker_logs
from utils import set_environment_variables, run_command, get_ip_address, manage_qcow2_image
from kms import login_to_vault

# @pytest.mark.usefixtures("setup_environment")
# class TestClass:

def generate_random_token( length=24):
    return 'hvs.' + ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def encrypt_base_image( skip_encrypt_image_path=False, extra_args=None):
    """Encrypts the base image to get the QUOTE."""
    assert encrypt_image(skip_encrypt_image_path=skip_encrypt_image_path, extra_args=extra_args), "Failed to encrypt the base image to get the QUOTE"

def fetch_td_quote():
    """Fetches the TD quote and encryption keys, and sets them as environment variables."""
    quote = get_td_measurement()
    quote_set_success = set_environment_variables(key="QUOTE", data=quote)
    return quote_set_success

def run_command_with_unset_env( cmd, unset_var):
    """Runs a command with a specified environment variable unset."""
    original_env = os.environ.copy()
    if unset_var in os.environ:
        del os.environ[unset_var]
    try:
        result = subprocess.Popen(cmd, env=os.environ)
        return result.returncode
    finally:
        os.environ.clear()
        os.environ.update(original_env)

def run_command_with_forbidden_param( command, forbidden_param):
    """Run the command with a forbidden parameter."""
    # Add the forbidden parameter to the command
    command_with_forbidden = command + forbidden_param

    # Run the command
    result = subprocess.run(command_with_forbidden)
    return result.returncode

def test_e2e_fde_workflow():
    """Tests the end-to-end FDE workflow."""
    encrypt_base_image()
    quote_set_success = fetch_td_quote()
    assert quote_set_success(), "Failed to generate TD measurement"
    assert store_key_in_kbs(), "Failed to store encryption key in KBS"
    assert verify_td_encrypted_image(), "TD encrypted image verification failed"

def test_e2e_fde_workflow_with_r_and_b_arg():
    """Tests the end-to-end FDE workflow with -r and -b arguments."""
    assert run_kbs(), "Failed to run KBS"
    encrypt_base_image(extra_args=["-r", "5GB", "-b", "1GB"])
    quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
    assert quote_set_success, "Failed to generate TD measurement"
    assert keys_set_success, "Failed to generate encryption keys"
    time.sleep(5)
    assert encrypt_and_verify_image(), "TD encrypted image verification failed"

def test_e2e_fde_workflow_with_r_and_b_default():
    """Tests the end-to-end FDE workflow with -r and -b arguments."""
    assert run_kbs(), "Failed to run KBS"
    encrypt_base_image()
    quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
    assert quote_set_success, "Failed to generate TD measurement"
    assert keys_set_success, "Failed to generate encryption keys"
    time.sleep(5)
    assert encrypt_and_verify_image(), "TD encrypted image verification failed"

def test_e2e_fde_workflow_with_r_usergiven():
    """Tests the end-to-end FDE workflow with -r and -b arguments."""
    assert run_kbs(), "Failed to run KBS"
    encrypt_base_image(extra_args=["-r", "6GB"])
    quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
    assert quote_set_success, "Failed to generate TD measurement"
    assert keys_set_success, "Failed to generate encryption keys"
    time.sleep(5)
    assert encrypt_and_verify_image(), "TD encrypted image verification failed"

def test_e2e_fde_workflow_with_b_usergiven():
    """Tests the end-to-end FDE workflow with -r and -b arguments."""
    assert run_kbs(), "Failed to run KBS"
    encrypt_base_image(extra_args=["-b", "3GB"])
    quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
    assert quote_set_success, "Failed to generate TD measurement"
    assert keys_set_success, "Failed to generate encryption keys"
    time.sleep(5)
    assert encrypt_and_verify_image(), "TD encrypted image verification failed"

def test_e2e_fde_workflow_with_r_and_b_kb():
    """Tests the end-to-end FDE workflow with -r and -b arguments."""
    assert run_kbs(), "Failed to run KBS"
    encrypt_base_image(extra_args=["-r", "6000000KB", "-b", "3000000KB"])
    quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
    assert quote_set_success, "Failed to generate TD measurement"
    assert keys_set_success, "Failed to generate encryption keys"
    time.sleep(5)
    assert encrypt_and_verify_image(), "TD encrypted image verification failed"

def test_e2e_fde_workflow_with_r_and_b_mb():
    """Tests the end-to-end FDE workflow with -r and -b arguments."""
    assert run_kbs(), "Failed to run KBS"
    encrypt_base_image(extra_args=["-r", "6000MB", "-b", "3000MB"])
    quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
    assert quote_set_success, "Failed to generate TD measurement"
    assert keys_set_success, "Failed to generate encryption keys"
    time.sleep(5)
    assert encrypt_and_verify_image(), "TD encrypted image verification failed"

def test_e2e_fde_workflow_with_r_and_b_negative():
    """Tests the end-to-end FDE workflow with -r and -b negative arguments."""
    assert run_kbs(), "Failed to run KBS"
    assert encrypt_image("GET_QUOTE", skip_encrypt_image_path=False, extra_args=["-r", "-10GB", "-b", "-2GB"]), "Expected failure when using negative values for -r and -b arguments"

def test_e2e_fde_workflow_with_r_negative():
    """Tests the end-to-end FDE workflow with -r negative arguments."""
    assert run_kbs(), "Failed to run KBS"
    assert encrypt_image("GET_QUOTE", skip_encrypt_image_path=False, extra_args=["-r", "-10GB"]), "Expected failure when using negative values for -r arguments"

def test_e2e_fde_workflow_with_b_negative():
    """Tests the end-to-end FDE workflow with -b negative arguments."""
    assert run_kbs(), "Failed to run KBS"
    assert encrypt_image("GET_QUOTE", skip_encrypt_image_path=False, extra_args=["-b", "-2GB"]), "Expected failure when using negative values for -b arguments"

def test_e2e_fde_workflow_with_skip_e_arg():
    """Tests the end-to-end FDE workflow with -skip-e ENCRYPTED IMAGE PATH argument."""
    assert run_kbs(), "Failed to run KBS"
    encrypt_base_image(skip_encrypt_image_path=True)
    quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
    assert quote_set_success, "Failed to generate TD measurement"
    assert keys_set_success, "Failed to generate encryption keys"
    assert encrypt_and_verify_image(skip_encrypt_image_path=True), "TD encrypted image verification failed"

def test_e2e_fde_workflow_intel():
    """Tests the end-to-end FDE workflow."""
    assert run_kbs(), "Failed to run KBS"
    encrypt_base_image()
    quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
    assert quote_set_success, "Failed to generate TD measurement"
    assert keys_set_success, "Failed to generate encryption keys"
    assert launch_and_verify_encrypted_image(), "TD encrypted image verification failed"

def test_fde_workflow_with_incorrect_vault_token():
    """Tests the FDE workflow with an incorrect Vault token."""
    original_root_token = os.environ["VAULT_ROOT_TOKEN"]
    set_environment_variables(key="VAULT_ROOT_TOKEN", data="********************************")
    try:
        assert run_kbs(), "Failed to run KBS"
        encrypt_base_image()
        quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
        assert quote_set_success, "Failed to generate TD measurement"
        assert not keys_set_success, "Expecting an error when retrieving encryption keys due to an invalid vault token."
        assert check_error_messages(get_docker_logs()) is True, "Expecting kbs container logs to have error messages, but it looks clean"
    finally:
        set_environment_variables(key="VAULT_ROOT_TOKEN", data=original_root_token)

def test_fde_workflow_with_kv_secret_engine_disabled():
    """Tests the FDE workflow with the KV secret engine disabled."""
    disable_command = ["vault", "secrets", "disable", "keybroker"]
    enable_command = ["vault", "secrets", "enable", "-path=keybroker", "kv"]
    try:
        run_command(disable_command)
        assert run_kbs(), "Failed to run KBS"
        encrypt_base_image()
        quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
        assert quote_set_success, "Failed to generate TD measurement"
        assert not keys_set_success, "Expecting an error when retrieving encryption keys with the KV secret engine disabled."
        assert check_error_messages(get_docker_logs()) is True, "Expecting kbs container logs to have error messages, but it looks clean"
    finally:
        run_command(enable_command)

@pytest.mark.parametrize("kbs_url", [
    f"http://{get_ip_address()}:9443",  # Insecure URL
    "https://incorrect-url:9443"        # Incorrect URL
])
def test_fde_workflow_with_various_kbs_urls( kbs_url: str):
    """Tests the FDE workflow with various KBS URLs."""
    assert run_kbs(), "Failed to run KBS"
    original_kbs_url = os.environ["KBS_URL"]
    set_environment_variables(key="KBS_URL", data=kbs_url)
    try:
        encrypt_base_image()
        quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
        assert quote_set_success, "Failed to generate TD measurement"
        assert not keys_set_success, f"Unexpected success for URL: {kbs_url}"
    finally:
        set_environment_variables(key="KBS_URL", data=original_kbs_url)


def test_fde_workflow_with_incorrect_vault_token_and_corrupted_cert():
    """Tests the FDE workflow with an incorrect Vault token followed by a correct Vault token, without deleting the certificate file"""
    original_root_token = os.environ["VAULT_ROOT_TOKEN"]
    set_environment_variables(key="VAULT_ROOT_TOKEN", data="********************************")
    try:
        assert run_kbs(), "Failed to run KBS"
        encrypt_base_image()
        quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
        assert quote_set_success, "Failed to generate TD measurement"
        assert not keys_set_success, "Expecting an error when retrieving encryption keys due to an invalid vault token."
        assert check_error_messages(get_docker_logs()) is True, "Expecting kbs container logs to have error messages, but it looks clean"

        set_environment_variables(key="VAULT_ROOT_TOKEN", data=original_root_token)
        assert run_kbs(), "Failed to run KBS"
        quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
        assert quote_set_success, "Failed to generate TD measurement"
        assert not keys_set_success, "Expecting an error when retrieving encryption keys due to an invalid vault token."
        assert check_error_messages(get_docker_logs()) is True, "Expecting kbs container logs to have error messages, but it looks clean"
    finally:
        set_environment_variables(key="VAULT_ROOT_TOKEN", data=original_root_token)


def test_fde_workflow_with_vault_login_with_incorrect_token():
    """Tests the FDE workflow with vault login authentication with incorrect Vault token """
    for i in range(5):
        invalid_token = generate_random_token()
        result = login_to_vault(invalid_token)
        assert not result, f"Iteration {i+1}: Expected an error when trying to login with invalid token '{invalid_token}'"

def test_fde_workflow_with_missing_parameters_retrieve_encryption_key():
    """Tests the FDE workflow with missing parameters for retrieving the encryption key."""
    cmd = [
        './fde-binaries/target/release/fde-key-gen',
        '--kbs-env-file-path', os.environ.get("KBS_ENV", ""),
        '--kbs-url', os.environ.get("KBS_URL", ""),
        '--kbs-cert-path', os.environ.get("KBS_CERT_PATH", ""),
        '--quote-b64', os.environ.get("QUOTE", ""),
        '--pk-kr-path', os.environ.get("PK_KR_PATH", ""),
        '--sk-kr-path', os.environ.get("SK_KR_PATH", "")
    ]
    for unset_var in ["KBS_ENV", "KBS_URL", "KBS_CERT_PATH", "QUOTE", "PK_KR_PATH", "SK_KR_PATH"]:
        returncode = run_command_with_unset_env(cmd, unset_var)
        assert returncode != 0, "Retrieve encryption key command unexpectedly succeeded with {unset_var} unset"

def test_fde_workflow_with_missing_forbidden_parameters_encrypt_image():
    """Tests the FDE workflow with missing parameters for encrypting the image."""
    get_quote_cmd = [
        'sudo', 'tools/image/fde-encrypt_image.sh', "GET_QUOTE",
        '-c', os.environ.get("KBS_CERT_PATH", ""),
        '-f', os.environ.get("PK_KR_PATH", ""),
        '-d', os.environ.get("TMP_K_RFS_PATH", ""),
        '-p', os.environ.get("BASE_IMAGE_PATH", "")
    ]

    for unset_var in ["TMP_K_RFS_PATH", "KBS_CERT_PATH", "BASE_IMAGE_PATH", "PK_KR_PATH"]:
        returncode = run_command_with_unset_env(get_quote_cmd, unset_var)
        assert returncode != 0, "Encrypt base image command unexpectedly succeeded with {unset_var} unset"

    # Test each forbidden parameter individually
    get_quote_forbidden_params = [
        ['-u', 'http://example.com'],
        ['-k', 'key'],
        ['-i', 'id']
    ]

    for param in get_quote_forbidden_params:
        print(f"Running command with forbidden parameter: {param}")
        print(f"Command: {get_quote_cmd + param}")
        returncode = run_command_with_forbidden_param(get_quote_cmd, param)
        assert returncode != 0, f"Encrypt base image command unexpectedly succeeded with forbidden parameter {get_quote_forbidden_params[0]}"
    
    td_fde_boot_cmd = [
        'sudo', 'tools/image/fde-encrypt_image.sh', "TD_FDE_BOOT",
        '-d', os.environ.get("TMP_K_RFS_PATH", ""),
        '-p', os.environ.get("ENCRYPTED_IMAGE_PATH", ""),
        '-u', os.environ.get("KBS_URL", ""),
        '-k', os.environ.get("k_RFS", ""),
        '-i', os.environ.get("ID_k_RFS", "")
    ]

    for unset_var in ["TMP_K_RFS_PATH", "ENCRYPTED_IMAGE_PATH", "KBS_URL", "k_RFS", "ID_k_RFS"]:
        returncode = run_command_with_unset_env(td_fde_boot_cmd, unset_var)
        assert returncode != 0, "Encrypt base image command unexpectedly succeeded with {unset_var} unset"

    # Test each forbidden parameter individually
    td_fde_boot_forbidden_params = [
        ['-c', 'tls.crt'],
        ['-r', '4GB'],
        ['-b', '1GB'],
        ['-f', os.environ.get("PK_KR_PATH", "")]
    ]

    for param in td_fde_boot_forbidden_params:
        print(f"Running command with forbidden parameter: {param}")
        print(f"Command: {td_fde_boot_cmd + param}")
        returncode = run_command_with_forbidden_param(td_fde_boot_cmd, param)
        assert returncode != 0, f"Encrypt base image command unexpectedly succeeded with forbidden parameter {td_fde_boot_forbidden_params[0]}"

def test_fde_workflow_with_invalid_quote():
    """Tests the FDE workflow with an invalid quote."""
    original_quote = ""
    try:
        assert run_kbs(), "Failed to run KBS"
        encrypt_base_image()
        quote = get_td_measurement()
        assert set_environment_variables(key="QUOTE", data=quote), "Failed to generate TD measurement"
        original_quote = os.environ["QUOTE"]
        characters = string.ascii_letters + string.digits + '+/'
        set_environment_variables(key="QUOTE", data=''.join(random.choices(characters, k=6675)) + '=')
        encryption_keys=retrieve_encryption_key()
        assert not set_environment_variables(data=encryption_keys), "Expecting an error when retrieving encryption keys with invalid quote."
    finally:
        set_environment_variables(key="QUOTE", data=original_quote)

def test_fde_workflow_with_invalid_encryption_key():
    """Tests the FDE workflow with an invalid encryption key."""
    original_fde_key = ""
    try:
        assert run_kbs(), "Failed to run KBS"
        encrypt_base_image()
        quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
        assert quote_set_success, "Failed to generate TD measurement"
        assert keys_set_success, "Failed to generate encryption keys"
        original_fde_key = os.environ["k_RFS"]
        characters = '0123456789abcdef'
        set_environment_variables(key="k_RFS", data=''.join(random.choices(characters, k=64)))
        assert not encrypt_and_verify_image(), "Expecting an error when encrypting base image with invalid FDE_KEY"
    finally:
        set_environment_variables(key="k_RFS", data=original_fde_key)

def test_fde_workflow_with_incorrect_cred_encrypted_image():
    """Tests the FDE workflow with incorrect credentials for the encrypted image."""
    assert run_kbs(), "Failed to run KBS"
    encrypt_base_image()
    quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
    assert quote_set_success, "Failed to generate TD measurement"
    assert keys_set_success, "Failed to generate encryption keys"
    assert encrypt_image("TD_FDE_BOOT"), "Failed to encrypt the base image"
    assert not verify_td_encrypted_image("sshpass -p 456123 ssh -o StrictHostKeyChecking=no -p 10022 root@localhost 'sudo blkid'"), "Expecting an error when login to encrypted image with invalid credentials."
    assert not verify_td_encrypted_image("sshpass -p 123456 ssh -o StrictHostKeyChecking=no -p 10022 root123@localhost 'sudo blkid'"), "Expecting an error when login to encrypted image with invalid credentials."

def test_fde_workflow_with_concurrent_encryption_attempt():
    """Tests the FDE workflow with concurrent encryption attempts."""
    assert run_kbs(), "Failed to run KBS"
    results = {}
    for i in range(2):
        results[f"run_{i}"] = encrypt_base_image()
    # Ensure only one run has a return code of 0
    print(results)
    success_count = sum(1 for result in results.values() if result == 0)
    assert success_count != 1, "Expected exactly one successful run, but found {success_count}"

def test_fde_workflow_with_recover_fde_key_loss():
    """Tests the FDE workflow with recovery from FDE key loss."""
    # Run the KBS service
    assert run_kbs(), "Failed to run KBS"
    
    # Encrypt the base image
    encrypt_base_image()
    
    # Fetch TD quote and encryption keys
    quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
    assert quote_set_success, "Failed to generate TD measurement"
    assert keys_set_success, "Failed to generate encryption keys"

    # copy encrypted image to a image directory
    os.makedirs('image', exist_ok=True)
    os.system(f"cp {os.environ['ENCRYPTED_IMAGE_PATH']} image/")
    os.system(f"cp {os.environ['OVMF_PATH']} image/")

    # Verify the encrypted image
    assert encrypt_and_verify_image(), "TD encrypted image verification failed"

    print(f"current FDE KEY : {os.environ["k_RFS"]}")
    # Retrieve the FDE key again to ensure it matches the original
    set_environment_variables(data=retrieve_encryption_key())

    set_environment_variables(key="ENCRYPTED_IMAGE_PATH", data=os.path.join(os.getcwd(), 'image', os.environ["ENCRYPTED_IMAGE_PATH"].split('/')[-1]))
    set_environment_variables(key="OVMF_PATH", data=os.path.join(os.getcwd(), 'image', os.environ["OVMF_PATH"].split('/')[-1]))

    print(f"new FDE KEY : {os.environ["k_RFS"]}")
    assert encrypt_and_verify_image(), "TD encrypted image verification failed"

def test_fde_workflow_with_verify_encrypt_image_at_rest():
    """Tests the FDE workflow with verification of the encrypted image at rest."""
    # Run the KBS service
    assert run_kbs(), "Failed to run KBS"
    
    # Encrypt the base image
    encrypt_base_image()
    
    # Fetch TD quote and encryption keys
    quote_set_success, keys_set_success = fetch_td_quote_and_encryption_keys()
    assert quote_set_success, "Failed to generate TD measurement"
    assert keys_set_success, "Failed to generate encryption keys"
    
    # Manage the QCOW2 image and check for specific content in the output
    result = manage_qcow2_image(os.environ["ENCRYPTED_IMAGE_PATH"], 'rootfs', 1)
    expected_text = "unknown filesystem type 'crypto_LUKS'"
    assert expected_text in result, "Expected encrypted image cannot be mounted directly"
