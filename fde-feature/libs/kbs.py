import subprocess
import os
import sys
from utils import run_command, set_environment_variables
from docker import remove_docker_container, build_docker_image, run_docker_container, verify_docker_container, get_build_args
import time
sys.path.insert(1, os.path.join(os.getcwd(), 'configuration'))
import configuration


def build_attestation_service():
    """Build Trustee Attestation Service Docker image."""
    trustee_dir = "trustee"
    dockerfile_path = "attestation-service/docker/as-grpc/Dockerfile"
    image_tag = "trustee-as:latest"
    
    build_args = get_build_args()
    
    return build_docker_image(trustee_dir, dockerfile_path, image_tag, build_args)


def create_as_config():
    """Create configuration file for Trustee Attestation Service."""
    config_dir = "trustee/config-data"
    os.makedirs(config_dir, exist_ok=True)
    
    config_content = """{
    "policy_engine": "opa",
    "rvps_config": {
        "type": "BuiltIn",
        "storage": {
            "type": "LocalFs",
            "file_path": "/opt/attestation-service/reference-values"
        }
    },
    "attestation_token_broker": {
        "type": "Ear",
        "duration_min": 5
    }
}"""
    
    config_path = os.path.join(config_dir, "as-config.json")
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    print(f"Created attestation service config at: {config_path}")
    return config_path


def start_attestation_service():
    """Start Trustee Attestation Service container."""
    trustee_dir = os.path.abspath("trustee")
    
    volumes = [
        f"{trustee_dir}/config-data/as-config.json:/opt/attestation-service/config.json:ro",
        f"{trustee_dir}/config-data/reference-values:/opt/attestation-service/reference-values",
        f"{trustee_dir}/attestation-service/docs/sgx_default_qcnl.conf:/etc/sgx_default_qcnl.conf:ro"
    ]
    
    env_vars = get_build_args()
    
    command_args = [
        "grpc-as",
        "--config-file", "/opt/attestation-service/config.json",
        "--socket", "0.0.0.0:3000"
    ]
    
    success = run_docker_container(
        container_name="trustee-as",
        image_tag="trustee-as:latest",
        network="trustee-net",
        environment_vars=env_vars,
        volumes=volumes,
        command_args=command_args
    )
    
    if success:
        # Verify deployment
        expected_patterns = [
            "Starting gRPC Attestation Service",
            "Listening on socket: 0.0.0.0:3000"
        ]
        return verify_docker_container("trustee-as", expected_patterns)
    
    return False


def modify_kbs_dockerfile():
    """Modify KBS Dockerfile to add Vault support."""
    dockerfile_path = "trustee/kbs/docker/coco-as-grpc/Dockerfile"
    
    # Read the file
    with open(dockerfile_path, 'r') as f:
        content = f.read()
    
    # Replace the make command
    modified_content = content.replace(
        'make AS_FEATURE=coco-as-grpc',
        'make background-check-kbs VAULT=true AS_FEATURE=coco-as-grpc'
    )
    
    # Write back
    with open(dockerfile_path, 'w') as f:
        f.write(modified_content)
    
    print("Modified KBS Dockerfile to add Vault support")


def build_kbs():
    """Build Trustee KBS Docker image."""
    trustee_dir = "trustee"
    dockerfile_path = "kbs/docker/coco-as-grpc/Dockerfile"
    image_tag = "trustee-kbs:latest"
    
    # Modify Dockerfile first
    modify_kbs_dockerfile()
    
    build_args = get_build_args()
    
    return build_docker_image(trustee_dir, dockerfile_path, image_tag, build_args)


def generate_kbs_certificates():
    """Generate self-signed certificate for KBS."""
    config_dir = "trustee/config-data"
    os.makedirs(config_dir, exist_ok=True)
    
    # Get system IP
    result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
    system_ip = result.stdout.strip().split()[0]
    
    # Create certificate configuration with prompt = no to avoid user interaction
    cert_conf_content = f"""[req]
default_bits = 3072
default_md = sha256
distinguished_name = req_distinguished_name
req_extensions = req_ext
x509_extensions = v3_ca
prompt = no

[req_distinguished_name]
countryName = US
stateOrProvinceName = CA
localityName = San Francisco
organizationName = Organization
organizationalUnitName = Development
commonName = localhost

[req_ext]
subjectAltName = @alt_names

[v3_ca]
subjectAltName = @alt_names

[alt_names]
IP.1 = {system_ip}
"""
    
    cert_conf_path = os.path.join(config_dir, "cert.conf")
    with open(cert_conf_path, 'w') as f:
        f.write(cert_conf_content)
    
    # Generate certificate
    cert_path = os.path.join(config_dir, "kbs.cert.pem")
    key_path = os.path.join(config_dir, "kbs.key.pem")
    
    subprocess.run([
        'openssl', 'req', '-x509', '-nodes', '-days', '365',
        '-newkey', 'rsa:3072',
        '-keyout', key_path,
        '-out', cert_path,
        '-config', cert_conf_path
    ], check=True)
    
    # Set permissions
    os.chmod(key_path, 0o600)
    os.chmod(cert_path, 0o644)
    
    print(f"Generated KBS certificate: {cert_path}")
    return system_ip, cert_path, key_path


def generate_kbs_admin_keys():
    """Generate asymmetric key pair for KBS admin access."""
    config_dir = "trustee/config-data"
    
    sk_path = os.path.join(config_dir, "sk_kbs_admin.pem")
    pk_path = os.path.join(config_dir, "pk_kbs_admin.pem")
    
    # Generate private key
    subprocess.run(['openssl', 'genpkey', '-algorithm', 'ed25519', '-out', sk_path])
    
    # Extract public key
    subprocess.run(['openssl', 'pkey', '-in', sk_path, '-pubout', '-out', pk_path])
    
    # Set permissions
    os.chmod(sk_path, 0o600)
    os.chmod(pk_path, 0o644)
    
    print(f"Generated KBS admin keys: {pk_path}")
    return sk_path, pk_path


def create_kbs_config(system_ip):
    """Create configuration file for Trustee KBS."""
    config_dir = "trustee/config-data"
    
    vault_token = os.environ.get('VAULT_ROOT_TOKEN')
    
    config_content = f"""[http_server]
sockets = ["0.0.0.0:8080"]
private_key = "/opt/kbs/certs/kbs.key.pem"
certificate = "/opt/kbs/certs/kbs.cert.pem"
insecure_http = false

[attestation_token]
insecure_key = true

[attestation_service]
type = "coco_as_grpc"
as_addr = "http://trustee-as:3000"
policy_engine = "opa"

[attestation_service.attestation_token_broker]
type = "Ear"
duration_min = 5

[attestation_service.rvps_config]
type = "BuiltIn"

[admin]
auth_public_key = "/opt/kbs/certs/pk_kbs_admin.pem"

[[plugins]]
name = "resource"
type = "Vault"
vault_url = "http://trustee-vault:8200"
token = "{vault_token}"
mount_path = "keybroker"
kv_version = 1
"""
    
    config_path = os.path.join(config_dir, "kbs-config.toml")
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    print(f"Created KBS config at: {config_path}")
    return config_path


def start_kbs(kbs_port=8080):
    """Start Trustee KBS container."""
    trustee_dir = os.path.abspath("trustee")
    
    volumes = [
        f"{trustee_dir}/config-data/kbs-config.toml:/opt/kbs/kbs-config.toml:ro",
        f"{trustee_dir}/config-data/kbs.cert.pem:/opt/kbs/certs/kbs.cert.pem:ro",
        f"{trustee_dir}/config-data/kbs.key.pem:/opt/kbs/certs/kbs.key.pem:ro",
        f"{trustee_dir}/config-data/pk_kbs_admin.pem:/opt/kbs/certs/pk_kbs_admin.pem:ro"
    ]
    
    env_vars = get_build_args()
    
    ports = [f"{kbs_port}:8080"]
    
    command_args = [
        "kbs",
        "--config-file", "/opt/kbs/kbs-config.toml"
    ]
    
    success = run_docker_container(
        container_name="trustee-kbs",
        image_tag="trustee-kbs:latest",
        network="trustee-net",
        environment_vars=env_vars,
        volumes=volumes,
        ports=ports,
        command_args=command_args
    )
    
    if success:
        # Verify deployment
        expected_patterns = [
            "Using config file /opt/kbs/kbs-config.toml",
            "Starting HTTPS server",
            "starting service"
        ]
        return verify_docker_container("trustee-kbs", expected_patterns, wait_time=10)
    
    return False


def update_kbs_env_file(kbs_port, kbs_url, kbs_cert_path, sk_kbs_admin):
    """Update the environment file with KBS configuration."""
    env_file_path = os.environ.get('SETUP_CONFIG_FILE')
    
    # Ensure the file exists
    if not os.path.exists(env_file_path):
        print(f"Error: Environment file not found at {env_file_path}")
        return
    
    # Update environment variables
    sed_commands = [
        (f'sed -i "/^export KBS_PORT=/c\\\\export KBS_PORT=\\"{kbs_port}\\"" "{env_file_path}"', True),
        (f'sed -i "/^export KBS_URL=/c\\\\export KBS_URL=\\"{kbs_url}\\"" "{env_file_path}"', True),
        (f'sed -i "/^export KBS_CERT_PATH=/c\\\\export KBS_CERT_PATH=\\"{kbs_cert_path}\\"" "{env_file_path}"', True),
        (f'sed -i "/^export SK_KBS_ADMIN=/c\\\\export SK_KBS_ADMIN=\\"{sk_kbs_admin}\\"" "{env_file_path}"', True),
    ]
    
    for cmd, shell in sed_commands:
        run_command(cmd, shell=shell)
    
    print(f"Updated environment file at {env_file_path}")


def setup_kbs_environment():
    """Set up the complete KBS environment with Attestation Service and KBS."""
    print("=== Setting up Trustee Attestation Service ===")
    
    # Build and start Attestation Service
    if not build_attestation_service():
        print("Failed to build Attestation Service")
        return False
    
    create_as_config()
    
    if not start_attestation_service():
        print("Failed to start Attestation Service")
        return False
    
    print("\n=== Setting up Trustee KBS ===")
    
    # Build KBS
    if not build_kbs():
        print("Failed to build KBS")
        return False
    
    # Generate certificates and keys
    system_ip, cert_path, key_path = generate_kbs_certificates()
    sk_admin, pk_admin = generate_kbs_admin_keys()
    
    # Set environment variables
    kbs_port = 8080
    kbs_url = f"https://{system_ip}:{kbs_port}"
    
    set_environment_variables(key="KBS_PORT", data=str(kbs_port))
    set_environment_variables(key="KBS_URL", data=kbs_url)
    set_environment_variables(key="KBS_CERT_PATH", data=os.path.abspath(cert_path))
    set_environment_variables(key="SK_KBS_ADMIN", data=os.path.abspath(sk_admin))
    
    # Create KBS config
    create_kbs_config(system_ip)
    
    # Start KBS
    if not start_kbs(kbs_port):
        print("Failed to start KBS")
        return False
    
    # Update environment file
    update_kbs_env_file(kbs_port, kbs_url, os.path.abspath(cert_path), os.path.abspath(sk_admin))
    
    print("\n=== KBS Environment Setup Complete ===")
    return True