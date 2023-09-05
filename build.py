import os
import re
import yaml
import subprocess
import time
import secrets  # Python built-in CSPRNG module
from colorama import init, Fore, Style
import threading

# Initialize Colorama for terminal color formatting
init(autoreset=True)

# Load settings from settings.yaml
with open('settings.yaml', 'r') as settings_file:
    settings = yaml.safe_load(settings_file)

# Define the GPG key name and link prefixes from the settings
KEY_NAME = settings.get("key_name", "my_gpg_key")
SCRIPT_LOCATION_PREFIX = settings.get("script_location_prefix", "https://example.com/scripts/")
SIGNATURE_LOCATION_PREFIX = settings.get("signature_location_prefix", "https://example.com/signatures/")
FORCE_OVERWRITE = settings.get("force_overwrite", False)  # Set to True to force key overwrite

# Define the regex pattern to match the fields
field_patterns = {
    "Author": r'# Author:\s*(.+)',
    "Title": r'# Title:\s*(.+)',
    "Version": r'# Version:\s*(.+)',
    "Verified": r'# Verified:\s*(.+)',
    "Description": r'# Description:\s*(.+)',
}

# Get the current time in 12-hour format with seconds
def get_current_time():
    return time.strftime("%I:%M:%S %p")

# Generate a random passphrase for GPG
def generate_random_passphrase():
    return secrets.token_hex(16)

# Create a lock for GPG operations
gpg_lock = threading.Lock()

# Initialize a dictionary to store the extracted information
all_scripts_data = []

# Create output folders if they don't exist
if not os.path.exists("gpg_signatures"):
    os.mkdir("gpg_signatures")

if not os.path.exists("scripts"):
    os.mkdir("scripts")

# List all script files in the "scripts" folder
script_files = os.listdir("scripts")

# Loop through script files
for script_file in script_files:
    script_path = os.path.join("scripts", script_file)
    signature_path = os.path.join("gpg_signatures", f"{script_file}.asc")

    # Generate a unique passphrase for each script
    passphrase = generate_random_passphrase()

    # Acquire the GPG lock to ensure sequential GPG operations
    with gpg_lock:
        # Generate a GPG key pair (if not already done or if force overwrite is True)
        key_exists = os.path.exists(f"gpg_signatures/{KEY_NAME}.asc")
        if not key_exists or (key_exists and FORCE_OVERWRITE):
            try:
                subprocess.check_output(["gpg", "--gen-key", "--batch", "--yes", "--passphrase", passphrase, f"--quick-gen-key", KEY_NAME], universal_newlines=True)
                print(f"[{Fore.GREEN}{get_current_time()}{Style.RESET_ALL}] GPG key pair generated successfully for {script_file}.")
            except subprocess.CalledProcessError as e:
                print(f"[{Fore.RED}{get_current_time()}{Style.RESET_ALL}] Error generating GPG key pair for {script_file}:", e)

        # Sign the script with the generated GPG key
        try:
            subprocess.check_output(["gpg", "--sign", "--local-user", KEY_NAME, "--yes", "--passphrase", passphrase, "-o", signature_path, script_path], universal_newlines=True)
            print(f"[{Fore.GREEN}{get_current_time()}{Style.RESET_ALL}] {script_file} signed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"[{Fore.RED}{get_current_time()}{Style.RESET_ALL}] Error signing {script_file} with GPG:", e)
            continue

    # Initialize a dictionary to store the extracted information for this script
    extracted_data = {}

    # Read the script file
    with open(script_path, 'r') as file:
        for line in file:
            for field_name, pattern in field_patterns.items():
                match = re.match(pattern, line)
                if match:
                    extracted_data[field_name] = match.group(1)

    # Add the script and signature locations to the extracted data
    extracted_data["script_location"] = f"{SCRIPT_LOCATION_PREFIX}{script_file}"
    extracted_data["signature_location"] = f"{SIGNATURE_LOCATION_PREFIX}{script_file}.asc"

    # Add the generated passphrase to the extracted data
    extracted_data["passphrase"] = passphrase

    # Append the extracted data to the list
    all_scripts_data.append(extracted_data)

# Create a YAML dictionary with script information numbered as 1, 2, 3, ...
yaml_data = {str(i + 1): script_data for i, script_data in enumerate(all_scripts_data)}

# Output the YAML data to resources.yml
with open('resources.yml', 'w') as yaml_file:
    yaml.dump(yaml_data, yaml_file, default_flow_style=False)

print(f"[{Fore.GREEN}{get_current_time()}{Style.RESET_ALL}] Data has been saved to resources.yml.")
