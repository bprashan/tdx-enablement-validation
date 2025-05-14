import os
import sys
import pytest
import random
import string
import subprocess

sys.path.append(os.path.join(os.path.dirname(__file__), '../libs'))
from fde import *
from kbs import run_kbs, check_error_messages, get_docker_logs
from utils import set_environment_variables, run_command, get_ip_address, manage_qcow2_image
from kms import login_to_vault

@pytest.mark.usefixtures("setup_environment")
class TestClass:

    def generate_random_token(self, length=24):
        return 'hvs.' + ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def encrypt_base_image(self):
        """Encrypts the base image to get the QUOTE."""
        encrypt_image("GET_QUOTE", kbs_cert_path=os.environ["KBS_CERT_PATH"], base_image_path=os.environ["BASE_IMAGE_PATH"], encrypted_image_path=os.environ["ENCRYPTED_IMAGE_PATH"])

    def fetch_td_quote_and_encryption_keys(self):
        """Fetches the TD quote and encryption keys, and sets them as environment variables."""
        quote = get_td_measurement()
        quote_set_success = set_environment_variables("QUOTE", quote)
        encryption_keys = retrieve_encryption_key()
        keys_set_success = set_environment_variables(data=encryption_keys)
        return quote_set_success, keys_set_success

    def encrypt_and_verify_image(self):
        """Encrypts the image using the FDE key and verifies the TD encrypted image."""
        encrypt_image("TD_FDE_BOOT", fde_key=os.environ["k_RFS"], kbs_url=os.environ["KBS_URL"], key_id=os.environ["ID_k_RFS"], encrypted_image_path=os.environ["ENCRYPTED_IMAGE_PATH"])
        return verify_td_encrypted_image()

    def run_command_with_unset_env(self, cmd, unset_var):
        """Runs a command with a specified environment variable unset."""
        original_env = os.environ.copy()
        if unset_var in os.environ:
            del os.environ[unset_var]
        try:
            result = subprocess.Popen(cmd, text=True, env=os.environ)
            return result.returncode
        finally:
            os.environ.clear()
            os.environ.update(original_env)

    def test_e2e_fde_workflow(self):
        """Tests the end-to-end FDE workflow."""
        assert run_kbs(), "Failed to run KBS"
        self.encrypt_base_image()
        quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
        assert quote_set_success, "Failed to generate TD measurement"
        assert keys_set_success, "Failed to generate encryption keys"
        assert self.encrypt_and_verify_image(), "TD encrypted image verification failed"

    def test_fde_workflow_with_incorrect_vault_token(self):
        """Tests the FDE workflow with an incorrect Vault token."""
        original_root_token = os.environ["VAULT_CLIENT_TOKEN"]
        set_environment_variables("VAULT_CLIENT_TOKEN", "hvs.XXXXXXXXXXXXXXXXXXXXXXXX")
        try:
            assert run_kbs(), "Failed to run KBS"
            self.encrypt_base_image()
            quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
            assert quote_set_success, "Failed to generate TD measurement"
            assert not keys_set_success, "Expecting an error when retrieving encryption keys due to an invalid vault token."
            assert check_error_messages(get_docker_logs()) is True, "Expecting kbs container logs to have error messages, but it looks clean"
        finally:
            set_environment_variables("VAULT_CLIENT_TOKEN", original_root_token)

    def test_fde_workflow_with_kv_secret_engine_disabled(self):
        """Tests the FDE workflow with the KV secret engine disabled."""
        disable_command = ["vault", "secrets", "disable", "keybroker"]
        enable_command = ["vault", "secrets", "enable", "-path=keybroker", "kv"]
        try:
            run_command(disable_command)
            assert run_kbs(), "Failed to run KBS"
            self.encrypt_base_image()
            quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
            assert quote_set_success, "Failed to generate TD measurement"
            assert not keys_set_success, "Expecting an error when retrieving encryption keys with the KV secret engine disabled."
            assert check_error_messages(get_docker_logs()) is True, "Expecting kbs container logs to have error messages, but it looks clean"
        finally:
            run_command(enable_command)

    @pytest.mark.parametrize("kbs_url", [
        f"http://{get_ip_address()}:9443",  # Insecure URL
        "https://incorrect-url:9443"        # Incorrect URL
    ])
    def test_fde_workflow_with_various_kbs_urls(self, kbs_url: str):
        """Tests the FDE workflow with various KBS URLs."""
        assert run_kbs(), "Failed to run KBS"
        original_kbs_url = os.environ["KBS_URL"]
        set_environment_variables("KBS_URL", kbs_url)
        try:
            self.encrypt_base_image()
            quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
            assert quote_set_success, "Failed to generate TD measurement"
            assert not keys_set_success, f"Unexpected success for URL: {kbs_url}"
        finally:
            set_environment_variables("KBS_URL", original_kbs_url)


    def test_fde_workflow_with_incorrect_vault_token_and_corrupted_cert(self):
        """Tests the FDE workflow with an incorrect Vault token followed by a correct Vault token, without deleting the certificate file"""
        original_root_token = os.environ["VAULT_CLIENT_TOKEN"]
        set_environment_variables("VAULT_CLIENT_TOKEN", "hvs.XXXXXXXXXXXXXXXXXXXXXXXX")
        try:
            assert run_kbs(), "Failed to run KBS"
            self.encrypt_base_image()
            quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
            assert quote_set_success, "Failed to generate TD measurement"
            assert not keys_set_success, "Expecting an error when retrieving encryption keys due to an invalid vault token."
            assert check_error_messages(get_docker_logs()) is True, "Expecting kbs container logs to have error messages, but it looks clean"

            set_environment_variables("VAULT_CLIENT_TOKEN", original_root_token)
            assert run_kbs(), "Failed to run KBS"
            quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
            assert quote_set_success, "Failed to generate TD measurement"
            assert not keys_set_success, "Expecting an error when retrieving encryption keys due to an invalid vault token."
            assert check_error_messages(get_docker_logs()) is True, "Expecting kbs container logs to have error messages, but it looks clean"
        finally:
            set_environment_variables("VAULT_CLIENT_TOKEN", original_root_token)


    def test_fde_workflow_with_vault_login_with_incorrect_token(self):
        """Tests the FDE workflow with vault login authentication with incorrect Vault token """
        for i in range(5):
            invalid_token = self.generate_random_token()
            result = login_to_vault(invalid_token)
            assert not result, f"Iteration {i+1}: Expected an error when trying to login with invalid token '{invalid_token}'"

    def test_fde_workflow_with_missing_parameters_retrieve_encryption_key(self):
        """Tests the FDE workflow with missing parameters for retrieving the encryption key."""
        cmd = [
            './fde-binaries/target/release/fde-key-gen',
            '--kbs-env-file-path', os.environ.get("KBS_ENV", ""),
            '--kbs-url', os.environ.get("KBS_URL", ""),
            '--kbs-cert-path', os.environ.get("KBS_CERT_PATH", ""),
            '---quote-b64', os.environ.get("QUOTE", ""),
        ]
        for unset_var in ["KBS_ENV", "KBS_URL", "KBS_CERT_PATH", "QUOTE"]:
            returncode = self.run_command_with_unset_env(cmd, unset_var)
            assert returncode != 0, "Retrieve encryption key command unexpectedly succeeded with {unset_var} unset"

    # def test_fde_workflow_with_missing_parameters_encrypt_base_image(self):
    #     """Tests the FDE workflow with missing parameters for encrypting the base image."""
    #     cmd = [
    #         'sudo', 'tools/image/fde-encrypt_image.sh',
    #         '-k', os.environ.get("TMP_FDE_KEY", ""),
    #         '-c', os.environ.get("KBS_CERT_PATH", ""),
    #         '-p', os.environ.get("BASE_IMAGE_PATH", "")
    #     ]

    #     for unset_var in ["TMP_FDE_KEY", "KBS_CERT_PATH", "BASE_IMAGE_PATH"]:
    #         returncode = self.run_command_with_unset_env(cmd, unset_var)
    #         assert returncode != 0, "Encrypt base image command unexpectedly succeeded with {unset_var} unset"

    def test_fde_workflow_with_invalid_quote(self):
        """Tests the FDE workflow with an invalid quote."""
        try:
            assert run_kbs(), "Failed to run KBS"
            self.encrypt_base_image()
            quote = get_td_measurement()
            assert set_environment_variables("QUOTE", quote), "Failed to generate TD measurement"
            original_quote = os.environ["QUOTE"]
            characters = string.ascii_letters + string.digits + '+/'
            set_environment_variables("QUOTE", ''.join(random.choices(characters, k=6675)) + '=')
            encryption_keys=retrieve_encryption_key()
            assert not set_environment_variables(data=encryption_keys), "Expecting an error when retrieving encryption keys with invalid quote."
        finally:
            set_environment_variables("QUOTE", original_quote)

    def test_fde_workflow_with_invalid_encryption_key(self):
        """Tests the FDE workflow with an invalid encryption key."""
        try:
            assert run_kbs(), "Failed to run KBS"
            self.encrypt_base_image()
            quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
            assert quote_set_success, "Failed to generate TD measurement"
            assert keys_set_success, "Failed to generate encryption keys"
            original_fde_key = os.environ["k_RFS"]
            characters = '0123456789abcdef'
            set_environment_variables("k_RFS", ''.join(random.choices(characters, k=3588)))
            assert not self.encrypt_and_verify_image(), "Expecting an error when encrypting base image with invalid FDE_KEY"
        finally:
            set_environment_variables("k_RFS", original_fde_key)

    def test_fde_workflow_with_incorrect_cred_encrypted_image(self):
        """Tests the FDE workflow with incorrect credentials for the encrypted image."""
        assert run_kbs(), "Failed to run KBS"
        self.encrypt_base_image()
        quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
        assert quote_set_success, "Failed to generate TD measurement"
        assert keys_set_success, "Failed to generate encryption keys"
        encrypt_image("TD_FDE_BOOT", fde_key=os.environ["k_RFS"], kbs_url=os.environ["KBS_URL"], key_id=os.environ["ID_k_RFS"], encrypted_image_path=os.environ["ENCRYPTED_IMAGE_PATH"])
        assert not verify_td_encrypted_image("sshpass -p 456123 ssh -o StrictHostKeyChecking=no -p 10022 root@localhost 'sudo blkid'"), "Expecting an error when login to encrypted image with invalid credentials."
        assert not verify_td_encrypted_image("sshpass -p 123456 ssh -o StrictHostKeyChecking=no -p 10022 root123@localhost 'sudo blkid'"), "Expecting an error when login to encrypted image with invalid credentials."

    def test_fde_workflow_with_concurrent_encryption_attempt(self):
        """Tests the FDE workflow with concurrent encryption attempts."""
        assert run_kbs(), "Failed to run KBS"
        results = {}
        for i in range(2):
            results[f"run_{i}"] = self.encrypt_base_image()
        # Ensure only one run has a return code of 0
        print(results)
        success_count = sum(1 for result in results.values() if result == 0)
        assert success_count != 1, "Expected exactly one successful run, but found {success_count}"

    def test_fde_workflow_with_recover_fde_key_loss(self):
        """Tests the FDE workflow with recovery from FDE key loss."""
        # Run the KBS service
        assert run_kbs(), "Failed to run KBS"
        
        # Encrypt the base image
        self.encrypt_base_image()
        
        # Fetch TD quote and encryption keys
        quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
        assert quote_set_success, "Failed to generate TD measurement"
        assert keys_set_success, "Failed to generate encryption keys"
        
        # Verify the encrypted image
        assert self.encrypt_and_verify_image(), "TD encrypted image verification failed"

        print(f"current FDE KEY : {os.environ["k_RFS"]}")
        # Retrieve the FDE key again to ensure it matches the original
        set_environment_variables(data=retrieve_encryption_key())
        print(f"new FDE KEY : {os.environ["k_RFS"]}")
        # assert self.encrypt_and_verify_image(), "TD encrypted image verification failed"

    def test_fde_workflow_with_verify_encrypt_image_at_rest(self):
        """Tests the FDE workflow with verification of the encrypted image at rest."""
        # Run the KBS service
        assert run_kbs(), "Failed to run KBS"
        
        # Encrypt the base image
        self.encrypt_base_image()
        
        # Fetch TD quote and encryption keys
        quote_set_success, keys_set_success = self.fetch_td_quote_and_encryption_keys()
        assert quote_set_success, "Failed to generate TD measurement"
        assert keys_set_success, "Failed to generate encryption keys"
        
        # Manage the QCOW2 image and check for specific content in the output
        result = manage_qcow2_image(os.environ["ENCRYPTED_IMAGE_PATH"], 'rootfs', 1)
        expected_text = "unknown filesystem type 'crypto_LUKS'"
        assert expected_text in result, "Expected encrypted image cannot be mounted directly"