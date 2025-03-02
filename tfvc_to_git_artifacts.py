import os
import base64
import requests
import json
from dotenv import load_dotenv
import subprocess
import twine

load_dotenv()

SOURCE_ORGANIZATION=os.getenv("SOURCE_ORGANIZATION")
SOURCE_PROJECT=os.getenv("SOURCE_PROJECT")
SOURCE_PAT = os.getenv("SOURCE_PAT")

TARGET_ORGANIZATION=os.getenv("TARGET_ORGANIZATION")
TARGET_PROJECT=os.getenv("TARGET_PROJECT")
TARGET_PAT = os.getenv("TARGET_PAT")

SOURCE_ORGANIZATION_FEEDS=os.getenv("SOURCE_ORGANIZATION_FEEDS")
TARGET_ORGANIZATION_FEEDS=os.getenv("TARGET_ORGANIZATION_FEEDS")

# Azure DevOps REST APIs require Basic Authentication, and since PAT is used here, the username is not required.
# Encoding ensures that special characters in the PAT (such as : or @) are safely transmitted without breaking the HTTP header's format.
SOURCE_AUTHENTICATION_HEADER = {
    "Authorization": f"Basic {base64.b64encode(f':{SOURCE_PAT}'.encode()).decode()}"
}
TARGET_AUTHENTICATION_HEADER = {
    "Authorization": f"Basic {base64.b64encode(f':{TARGET_PAT}'.encode()).decode()}"
}

def get_project_id(organization, project_name, authentication_header):
    '''
    This function fetches the id of a project.
    '''
    api_version = "6.0-preview"
    url = f"{organization}/_apis/projects/{project_name}?api-version={api_version}"

    print("##############################")
    print(f"[INFO] Fetching the ID of '{project_name}' project from '{organization}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            project_id = response.json()["id"]
            print(f"Project: {project_name} | ID: {project_id}")

            return project_id
        
        else:
            print(f"[ERROR] Failed to fetch project ID of '{project_name}' project.")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching project ID: {e}")
        return None

def get_feeds(organization, project_name, authentication_header):
    """
    This function fetches all feeds of a project.
    """
    api_version = "6.0-preview"
    url = f"https://feeds.dev.azure.com/{organization}/{project_name}/_apis/packaging/feeds?api-version={api_version}"

    print(f"[INFO] Fetching feeds from '{project_name}' in '{organization}'...")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            feeds = response.json().get("value", [])
            print(f"\nFound {len(feeds)} feed(s).")

            print("-" * 50)  # Visual separator for better readability.
            for feed in feeds:
                feed_name = feed.get("name", "Unknown Name")
                feed_id = feed.get("id", "Unknown ID")
                print(f"Name: {feed_name}")
                print(f"ID: {feed_id}")
                print("-" * 50)  # Visual separator between task groups for better readability.

            return feeds
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch feeds from '{project_name}' project.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")
            return []
        
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching feeds: {e}\033[0m")
        return []

def get_feed_config(organization, project_name, authentication_header, feed_id):
    """
    This function fetches the configuration of a feed.
    """
    api_version = "6.0-preview"
    url = f"https://feeds.dev.azure.com/{organization}/{project_name}/_apis/packaging/feeds/{feed_id}?api-version={api_version}"

    print(f"[INFO] Fetching the configuration of feed id {feed_id} from '{project_name}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            feed_config = response.json()
            print(f"[INFO] Successfully retrieved configuration for feed id {feed_id}.")
            print(f"\n[DEBUG] Raw Configuration:\n{json.dumps(feed_config, indent=4)}\n")  # Prettified JSON for better readability.

            return feed_config
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch feed configuration for feed id {feed_id}.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching feed configuration: {e}\033[0m")
        return None

def get_feed_packages(organization, project_name, authentication_header, feed_id):
    """
    This function fetches all packages from a feed.
    """
    api_version = "6.0-preview"
    url = f"https://feeds.dev.azure.com/{organization}/{project_name}/_apis/packaging/feeds/{feed_id}/packages?api-version={api_version}"
    
    print(f"[INFO] Fetching packages from feed id {feed_id}...")
    
    try:
        response = requests.get(url, headers=authentication_header)
        
        if response.status_code == 200:
            packages = response.json()["value"]
            print(f"\nFound {len(packages)} package(s).")

            print("-" * 50)  # Visual separator for better readability.
            for package in packages:
                package_name = package.get("name", "Unknown Name")
                package_id = package.get("id", "Unknown ID")
                print(f"Name: {package_name}")
                print(f"ID: {package_id}")
                print("-" * 50)  # Visual separator between task groups for better readability.

            return packages
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch packages for feed id {feed_id}.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
        
    except Exception as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching packages: {e}\033[0m")
        return None

def get_package_versions(organization, project_name, authentication_header, feed_id, package_id):
    """
    This function fetches all versions of a specific package.
    """
    api_version = "6.0-preview"
    url = f"https://feeds.dev.azure.com/{organization}/{project_name}/_apis/packaging/feeds/{feed_id}/packages/{package_id}/versions?api-version={api_version}"
    
    print(f"[INFO] Fetching versions for package id {package_id}...")
    
    try:
        response = requests.get(url, headers=authentication_header)
        
        if response.status_code == 200:
            versions = response.json()["value"]
            print(f"[INFO] Found {len(versions)} version(s).")
            
            print("-" * 50)
            for version in versions:
                version_id = version.get("id", "Unknown ID")
                version_number = version.get("normalizedVersion", "Unknown Version")
                is_latest = version.get("isLatest", False)
                print(f"Version: {version_number}" + (" (Latest)" if is_latest else ""))
                print(f"ID: {version_id}")
                print("-" * 50)
            
            return versions
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch package versions.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")
            return None
        
    except Exception as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching package versions: {e}\033[0m")
        return None

def download_package_version(organization, project_name, authentication_header, feed_id, package_name, package_version, version_id, protocol_type, download_directory):
    """
    This function downloads a specific package version.
    """
    package_details = get_package_details(organization, project_name, authentication_header, feed_id, package_id, version_id)

    # Checks if the package has files.
    if not package_details or 'files' not in package_details or not package_details['files']:
        print(f"\033[1;31m[ERROR] No files found for package '{package_name}' for version '{package_version}'.\033[0m")
        return []

    package_type = protocol_type.lower() # Ensures the 'package_type' is lowercase for case-insensitive comparison.

    os.makedirs(download_directory, exist_ok=True) # Creates a download directory if it does not exist.

    downloaded_files = []

    for file in package_details['files']:
        filename = file['name']
        download_url = None
        
        if package_type == "pypi":
            if filename:
                download_url = f"https://pkgs.dev.azure.com/{organization}/{project_name}/_apis/packaging/feeds/{feed_id}/pypi/packages/{package_name}/versions/{package_version}/{filename}/content"

        # Once there will be information about other package types, the logic will be adjusted.
        elif package_type == "nuget":
            pass

        download_path = os.path.join(download_directory, filename)
        
        print(f"[INFO] Downloading the '{filename}' file from the '{package_name}' package to '{download_path}'...")
    
        try:
            # The 'stream' parameter tells the requests library not to download the entire file into memory at once, but to keep the connection open and stream the data in chunks.
            response = requests.get(download_url, headers=authentication_header, stream=True) 

            if response.status_code == 200:
                with open(download_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192): # This approach prevents memory issues when downloading large files.
                        f.write(chunk)

                print(f"✅[INFO] Successfully downloaded the '{filename}' file from the '{package_name}' package to '{download_path}'.")
                downloaded_files.append(download_path)
            
            else:
                print(f"\033[1;31m❌[ERROR] Failed to download the '{filename}' file from the '{package_name}' package.\033[0m")
                print(f"[DEBUG] Request's Status Code: {response.status_code}")
                print(f"[DEBUG] Response: {response.text}")
            
        except Exception as e:
            print(f"\033[1;31m[ERROR] Exception while downloading package version: {str(e)}\033[0m")

    print(f"✅[INFO] Successfully downloaded the '{package_name}' package.")
    return downloaded_files

def get_package_details(organization, project_name, authentication_header, feed_id, package_id, version_id):
    """
    Get detailed information about a package version, including available file names.
    """
    api_version = "6.0-preview"
    url = f"https://feeds.dev.azure.com/{organization}/{project_name}/_apis/packaging/feeds/{feed_id}/packages/{package_id}/versions/{version_id}?api-version={api_version}"
    
    try:
        response = requests.get(url, headers=authentication_header)
        
        if response.status_code == 200:
            #print(f"\n{response.json()}\n")
            return response.json()
        else:
            print(f"\033[1;31m[ERROR] Failed to get package details. Status Code: {response.status_code}\033[0m")
            print(f"[DEBUG] Response: {response.text}")
            return None
    except Exception as e:
        print(f"\033[1;31m[ERROR] Exception while getting package details: {str(e)}\033[0m")
        return None

def upload_package(organization, project_name, target_pat, target_feed_id, package_paths, package_type="pypi"):
    """
    This function uploads a package to a feed.
    """
    if not package_paths:
        print(f"\033[1;31m[ERROR] No package files to upload.\033[0m")
        return False
        
    try:
        package_type = package_type.lower() # Ensures the 'package_type' is lowercase for case-insensitive comparison.
        
        if package_type == "pypi":
            """
            • 'twine' handles all the complexities of preparing and uploading Python packages, including proper metadata formatting, package validation, and file handling.
            • 'twine' verifies that the package is formatted correctly according to Python packaging standards.
            • 'twine' manages authentication with the package repository.
            • Using 'twine' is much simpler than implementing the equivalent functionality through the Azure DevOps' REST API, which would require understanding all 
            the PyPI package upload protocols.
            • For PyPI packages, Microsoft recommends using standard Python tools like 'twine' rather than their REST API directly.
            """
            upload_url = f"https://pkgs.dev.azure.com/{organization}/{project_name}/_packaging/{target_feed_id}/pypi/upload"
            
            # Create .pypirc file with credentials
            pypirc_path = os.path.join(os.path.expanduser("~"), ".pypirc")

            with open(pypirc_path, "w") as f:
                f.write(f"""[distutils]
index-servers = azure

[azure]
repository = {upload_url}
username = azure
password = {target_pat}
""")
            
            # Upload each package file using twine
            success = True
            for package_path in package_paths:
                print(f"[INFO] Uploading {os.path.basename(package_path)} to target feed...")
                result = subprocess.run(
                    ["twine", "upload", "--repository", "azure", package_path],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    print(f"✅[INFO] Successfully uploaded {os.path.basename(package_path)} to target feed")
                else:
                    print(f"\033[1;31m❌[ERROR] Failed to upload {os.path.basename(package_path)} to target feed\033[0m")
                    print(f"[DEBUG] STDOUT: {result.stdout}")
                    print(f"[DEBUG] STDERR: {result.stderr}")
                    success = False
            
            # Clean up .pypirc file
            if os.path.exists(pypirc_path):
                os.remove(pypirc_path)
            
            return success
        
        else:
            print(f"\033[1;31m❌[ERROR] Unsupported package type: {package_type}\033[0m")
            return False
            
    except Exception as e:
        print(f"\033[1;31m❌[ERROR] Exception while uploading package: {str(e)}\033[0m")
        return False

if __name__ == "__main__":
    source_feeds = get_feeds(SOURCE_ORGANIZATION_FEEDS, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    target_feeds = get_feeds(TARGET_ORGANIZATION_FEEDS, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER)

    for feed in source_feeds:
        feed_id = feed['id']
        feed_packages = get_feed_packages(SOURCE_ORGANIZATION_FEEDS, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, feed_id)

        for package in feed_packages:
            package_id = package['id']
            package_name = package['name']
            package_protocol_type = package['protocolType']
            package_versions = get_package_versions(SOURCE_ORGANIZATION_FEEDS, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, feed_id, package_id)

            for version in package_versions:
                version_id = version['id']
                version_number = version.get("normalizedVersion", "Unknown Version")
                downloaded_files = download_package_version(SOURCE_ORGANIZATION_FEEDS, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, feed_id, package_name, version_number, version_id, package_protocol_type, '/Users/pyruc/Desktop/TFVC-to-Git')
                
                for tf in target_feeds:
                    tf_id = tf['id']
                    upload_package(TARGET_ORGANIZATION_FEEDS, TARGET_PROJECT, TARGET_PAT, tf_id, downloaded_files, package_protocol_type)