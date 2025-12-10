repo_url="https://github.com/intel-innersource/applications.security.confidential-computing.tdx.tools.public.git"
branch='harshtpa/trustee-fde-direct-boot-updates'
folder_name="fde_source"
dir_name = "fde/full-disk-encryption"
repo_name ='fde'

canonical_tdx_dir = "canonical-tdx"

trustee_config_file = "setup_config.sh"
trustee_reference_value_dir = "trustee/config-data/reference-values"



image_directory =  "/fde_source/TDXSampleUseCases/full-disk-encryption/canonical-tdx/guest-tools/image"

os_version = "24.04"

ubuntu_kernel_version = "generic"
intel_kernel_version = "intel"

tdx_file_path  = "setup-tdx-config"

os_name_2404="PRETTY_NAME=\"Ubuntu 24.04.2 LTS\""
fde_check=" TYPE=\"crypto_LUKS\" PARTLABEL=\"rootfs\"" 

Error_TD_FDE_BOOT="Error: Failed to add new key to LUKS partition, returned with status: 2."
Error_r_negative="Warning: file is smaller than 512 bytes; the loop device may be useless or invisible for system tools."
Error_b_negative="Unable to set partition 16's name to 'boot'!"