import os
import shutil
import base64
import requests
import json
from dotenv import load_dotenv
import subprocess
import re
import time
import pyfiglet
import twine

load_dotenv()

SOURCE_ORGANIZATION=os.getenv("SOURCE_ORGANIZATION")
SOURCE_PROJECT="Cayuga"#os.getenv("SOURCE_PROJECT")
SOURCE_PAT = "FfyolvVvPsdp7r4JQB9jdY1RxZX1cablwAuCdMh9MJSHGGbMgRyoJQQJ99BCACAAAAA67SVyAAASAZDOv4Mx"#os.getenv("SOURCE_PAT")

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

def download_package_version(organization, project_name, authentication_header, feed_id, package_id, package_name, package_version, version_id, protocol_type, download_directory):
    """
    This function downloads a specific package version.
    """
    package_details = get_package_details(organization, project_name, authentication_header, feed_id, package_id, version_id)

    package_type = protocol_type.lower() # Ensures the 'package_type' is lowercase for case-insensitive comparison.

    os.makedirs(download_directory, exist_ok=True) # Creates a download directory if it does not exist.

    downloaded_files = []

    # NuGet packages requires special handling as they are downloaded using the 'nuget' CLI tool.
    if package_type == "nuget":
        # Creates the 'NuGet.config' file to be used by 'nuget'.
        nuget_config_path = os.path.join(os.path.expanduser("~"), "NuGet.Config")
        feed_url = f"https://pkgs.dev.azure.com/{organization}/{project_name}/_packaging/{feed_id}/nuget/v3/index.json"
        
        with open(nuget_config_path, "w") as f:
            f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <add key="AzureDevOps" value="{feed_url}" />
  </packageSources>
  <packageSourceCredentials>
    <AzureDevOps>
      <add key="Username" value="az" />
      <add key="ClearTextPassword" value="{SOURCE_PAT}" />
    </AzureDevOps>
  </packageSourceCredentials>
</configuration>""")
        
        try:
            # Executes the downloading command using CLI.
            cmd = [
                "nuget", "install", 
                package_name, 
                "-Version", package_version,
                "-Source", "AzureDevOps",
                "-OutputDirectory", download_directory,
                "-ConfigFile", nuget_config_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                package_directory = os.path.join(download_directory, package_name)
                
                # Finds the '.nupkg' files of each package version.
                # When uploading to a NuGet repository (including Azure DevOps Artifacts), the 'nuget push' command specifically requires a '.nupkg' file as input.
                for root, directories, files in os.walk(package_directory if os.path.exists(package_directory) else download_directory):
                    for file in files:
                        if file.endswith(".nupkg"):
                            nupkg_path = os.path.join(root, file)
                            downloaded_files.append(nupkg_path)
                            print(f"[INFO] Successfully downloaded the '{file}' file to '{nupkg_path}'.")
                
                if downloaded_files:
                    print(f"[INFO] Successfully downloaded the '{package_name}' package in version {package_version}.")

                else:
                    print(f"\033[1;38;5;214m[WARNING] NuGet package downloaded but the '.nupkg' file not found.\033[0m")

            else:
                print(f"\033[1;31m[ERROR] Failed to download NuGet package '{package_name}'.\033[0m")
                print(f"[DEBUG] STDOUT: {result.stdout}")
                print(f"[DEBUG] STDERR: {result.stderr}")
                
        except Exception as e:
            print(f"\033[1;31m[ERROR] An error occurred while downloading NuGet package: {e}\033[0m")
        
        # Cleans up the 'NuGet.config' file created earlier.
        if os.path.exists(nuget_config_path):
            os.remove(nuget_config_path)
        
        return downloaded_files

    # Checks if the package has files.
    if not package_details or 'files' not in package_details or not package_details['files']:
        print(f"\033[1;31m[ERROR] No files found for package '{package_name}' in version '{package_version}'.\033[0m")
        return []

    for file in package_details['files']:
        filename = file['name']
        download_path = os.path.join(download_directory, filename)
        download_url = None
        
        if package_type == "pypi":
            if filename:
                download_url = f"https://pkgs.dev.azure.com/{organization}/{project_name}/_apis/packaging/feeds/{feed_id}/pypi/packages/{package_name}/versions/{package_version}/{filename}/content"

        elif package_type == "maven":
            # For Maven, the package name is typically in format 'groupId:artifactId'.
            if ':' in package_name:
                group_id, artifact_id = package_name.split(':')
                #group_id_path = group_id.replace('.', '/') # Replace dots with forward slashes in group id as per Maven convention.
                download_url = f"https://pkgs.dev.azure.com/{organization}/{project_name}/_apis/packaging/feeds/{feed_id}/maven/{group_id}/{artifact_id}/{package_version}/{filename}/content"
                
            else:
                print(f"\033[1;31m[ERROR] Invalid Maven package name format for '{package_name}'. Expected format: 'groupId:artifactId'.\033[0m")
                continue
        
        print(f"[INFO] Downloading the '{filename}' file from the '{package_name}' package to '{download_path}'...")
    
        try:
            # The 'stream' parameter tells the requests library not to download the entire file into memory at once, but to keep the connection open and stream the data in chunks.
            response = requests.get(download_url, headers=authentication_header, stream=True) 

            if response.status_code == 200:
                with open(download_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192): # This approach prevents memory issues when downloading large files.
                        f.write(chunk)

                print(f"[INFO] Successfully downloaded the '{filename}' file from the '{package_name} ({package_version})' package to '{download_path}'.")
                downloaded_files.append(download_path)
            
            else:
                print(f"\033[1;31m[ERROR] Failed to download the '{filename}' file from the '{package_name} ({package_version})' package.\033[0m")
                print(f"[DEBUG] Request's Status Code: {response.status_code}")
                print(f"[DEBUG] Response: {response.text}")
            
        except Exception as e:
            print(f"\033[1;31m[ERROR] An error occurred while downloading package version: {e}\033[0m")

    print(f"[INFO] Successfully downloaded the '{package_name}' package in version {package_version}.")
    return downloaded_files

def get_package_details(organization, project_name, authentication_header, feed_id, package_id, version_id):
    """
    This function fetches the configuration of a package.
    """
    api_version = "6.0-preview"
    url = f"https://feeds.dev.azure.com/{organization}/{project_name}/_apis/packaging/feeds/{feed_id}/packages/{package_id}/versions/{version_id}?api-version={api_version}"
    
    try:
        response = requests.get(url, headers=authentication_header)
        
        if response.status_code == 200:
            return response.json()
        
        else:
            print(f"\033[1;31m[ERROR] Failed to get package details.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")
            return None
        
    except Exception as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching package details: {e}\033[0m")
        return None

def upload_package(organization, project_name, target_pat, target_feed_id, package_paths, package_type, package_name):
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
            
            # Creates the '.pypirc' file to be used by 'twine'.
            pypirc_path = os.path.join(os.path.expanduser("~"), ".pypirc")

            with open(pypirc_path, "w") as f:
                f.write(f"""[distutils]
index-servers = azure

[azure]
repository = {upload_url}
username = azure
password = {target_pat}
""")
            
            success = True

            for package_path in package_paths:
                print(f"[INFO] Uploading {os.path.basename(package_path)} to target feed...")

                # Executes the uploading command using CLI.
                result = subprocess.run(
                    ["twine", "upload", "--repository", "azure", package_path],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    print(f"\033[1;32m[SUCCESS] Successfully uploaded {os.path.basename(package_path)} to target feed.\033[0m")

                else:
                    print(f"\033[1;31m[ERROR] Failed to upload {os.path.basename(package_path)} to target feed.\033[0m")
                    print(f"[DEBUG] STDOUT: {result.stdout}")
                    print(f"[DEBUG] STDERR: {result.stderr}")
                    success = False
            
            # Cleans up the '.pypirc' file created earlier.
            if os.path.exists(pypirc_path):
                os.remove(pypirc_path)
            
            return success
        
        # Once there will be information about other package types, the logic will be adjusted.
        elif package_type == "maven":
            """
            For Maven packages, the 'mvn deploy' command is used to upload the package.
            """
            # Creates the 'settings.xml' file to be used by 'mvn'.
            maven_settings_path = os.path.join(os.path.expanduser("~"), ".m2", "settings.xml")
            os.makedirs(os.path.dirname(maven_settings_path), exist_ok=True)
            
            with open(maven_settings_path, "w") as f:
                f.write(f"""<settings>
    <servers>
        <server>
            <id>azure-feed</id>
            <username>azure</username>
            <password>{target_pat}</password>
        </server>
    </servers>
</settings>""")
            
            success = True
    
            if ':' in package_name:
                group_id, artifact_id = package_name.split(':')

            else:
                print(f"\033[1;31m[ERROR] Invalid Maven package name format for '{package_name}'. Expected format: 'groupId:artifactId'.\033[0m")
                return False
            
            # Identifies the JAR and POM files needed for Maven deployment.
            main_jar_file = None
            sources_jar_file = None
            javadoc_jar_file = None
            pom_file = None
            
            for package_path in package_paths:
                file_name = os.path.basename(package_path)
                
                # Skips checksum files.
                if file_name.endswith('.sha256') or file_name.endswith('.sha512'):
                    continue
                    
                # Identifies different types of files.
                if file_name.endswith('.pom'):
                    pom_file = package_path

                elif file_name.endswith('-sources.jar'):
                    sources_jar_file = package_path

                elif file_name.endswith('-javadoc.jar'):
                    javadoc_jar_file = package_path

                elif file_name.endswith('.jar'):
                    main_jar_file = package_path

            # Prioritizes the JAR file if available, otherwise uses the available alternatives.
            jar_file = main_jar_file or sources_jar_file or javadoc_jar_file

            if not jar_file or not pom_file:
                print(f"\033[1;31m[ERROR] Both JAR and POM files are required for Maven package upload.\033[0m")
                return False
            
            # Extracts the package version using a multi-layered approach.
            if main_jar_file:
                file_name = os.path.basename(main_jar_file)

            elif sources_jar_file:
                file_name = os.path.basename(sources_jar_file)
                file_name = file_name.replace("-sources.jar", ".jar")

            else:
                file_name = os.path.basename(pom_file)

            # First attempt: Tries to extract the package version from filename using regex.
            version_pattern = re.compile(f"{artifact_id}-(.*)\\.jar")
            match = version_pattern.match(file_name)

            if match:
                version = match.group(1)

            else:
                # Second attempt: Tries to extract the package version using a more generic pattern (any numbers with dots).
                generic_pattern = re.compile(r"(\d+(\.\d+)+)")
                match = generic_pattern.search(file_name)
                
                if match:
                    version = match.group(1)

                else:
                    # Third attempt: Tries to extract the package version from POM file content.
                    try:
                        with open(pom_file, 'r') as f:
                            pom_content = f.read()
                            version_in_pom = re.search(r"<version>(.*?)</version>", pom_content)

                            if version_in_pom:
                                version = version_in_pom.group(1)

                            else:
                                # Last attempt: falls back to a default version if all other methods fail.
                                print(f"\033[1;38;5;214m[WARNING] Could not determine the package version from filenames, using default version '1.0'.\033[0m")
                                version = "1.0"

                    except Exception as e:
                        print(f"\033[1;38;5;214m[WARNING] Error reading the POM file: {e}. Using default version '1.0'.\033[0m")
                        version = "1.0"

            print(f"[INFO] Detected version: {version}")
            print(f"[INFO] Uploading the '{package_name}' package in version {version} to target feed...")
            
            upload_url = f"https://pkgs.dev.azure.com/{organization}/{project_name}/_packaging/{target_feed_id}/maven/v1"
            
            # Uploads the main JAR (compiled code) file.
            if main_jar_file:
                print(f"[INFO] Uploading the main JAR file for '{package_name}' package in version {version} to target feed...")

                main_cmd = [
                    "mvn", "deploy:deploy-file",
                    "-DgroupId=" + group_id,
                    "-DartifactId=" + artifact_id,
                    "-Dversion=" + version,
                    "-Dpackaging=jar",
                    "-Dfile=" + main_jar_file,
                    "-DpomFile=" + pom_file,
                    "-DrepositoryId=azure-feed",
                    "-Durl=" + upload_url,
                    "-s", maven_settings_path
                ]
                
                result = subprocess.run(
                    main_cmd,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    print(f"\033[1;32m[SUCCESS] Successfully uploaded the main JAR file for '{package_name}' package in version {version} to target feed.\033[0m")

                else:
                    print(f"\033[1;31m[ERROR] Failed to upload the main JAR file for '{package_name}' package in version {version} to target feed.\033[0m")
                    print(f"[DEBUG] STDOUT: {result.stdout}")
                    print(f"[DEBUG] STDERR: {result.stderr}")
                    success = False

            # Uploads the sources JAR (source code) file if available.
            if sources_jar_file and success:
                time.sleep(2)
                print(f"[INFO] Uploading the sources JAR file for '{package_name}' package in version {version} to target feed...")

                sources_cmd = [
                    "mvn", "deploy:deploy-file",
                    "-DgroupId=" + group_id,
                    "-DartifactId=" + artifact_id,
                    "-Dversion=" + version,
                    "-Dpackaging=jar",
                    "-Dfile=" + sources_jar_file,
                    "-Dclassifier=sources",
                    "-DrepositoryId=azure-feed",
                    "-Durl=" + upload_url,
                    "-s", maven_settings_path
                ]
                
                if not main_jar_file:
                    sources_cmd.append("-DpomFile=" + pom_file)
                
                result = subprocess.run(sources_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"\033[1;32m[SUCCESS] Successfully uploaded the sources JAR file for '{package_name}' package in version {version} to target feed.\033[0m")

                else:
                    print(f"\033[1;38;5;214m[WARNING] Failed to upload the sources JAR file for '{package_name}' package in version {version} to target feed.\033[0m")
                    print(f"[DEBUG] STDOUT: {result.stdout}")
                    print(f"[DEBUG] STDERR: {result.stderr}")

            # Uploads the javadoc JAR (documentation) file if available.
            if javadoc_jar_file and success:
                time.sleep(2)
                print(f"[INFO] Uploading the javadoc JAR file for '{package_name}' package in version {version} to target feed...")

                javadoc_cmd = [
                    "mvn", "deploy:deploy-file",
                    "-DgroupId=" + group_id,
                    "-DartifactId=" + artifact_id,
                    "-Dversion=" + version,
                    "-Dpackaging=jar",
                    "-Dfile=" + javadoc_jar_file,
                    "-Dclassifier=javadoc",
                    "-DrepositoryId=azure-feed",
                    "-Durl=" + upload_url,
                    "-s", maven_settings_path
                ]
                
                if not main_jar_file:
                    sources_cmd.append("-DpomFile=" + pom_file)

                result = subprocess.run(javadoc_cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"\033[1;32m[SUCCESS] Successfully uploaded the javadoc JAR file for '{package_name}' package in version {version} to target feed.\033[0m")

                else:
                    print(f"\033[1;38;5;214m[WARNING] Failed to upload the sources JAR file for '{package_name}' package in version {version} to target feed.\033[0m")
                    print(f"[DEBUG] STDOUT: {result.stdout}")
                    print(f"[DEBUG] STDERR: {result.stderr}")
            
            # Cleans up the 'settings.xml' file created earlier.
            if os.path.exists(maven_settings_path):
                os.remove(maven_settings_path)
            
            if success:
                print(f"\033[1;32m[SUCCESS] Successfully uploaded the '{package_name}' package in version {version} to target feed.\033[0m")

            else:
                print(f"\033[1;31m[ERROR] Failed to upload the '{package_name}' package in version {version} to target feed.\033[0m")
                print(f"\033[1m[INFO] The failure might occur because the main JAR file is already exists in the target feed.\033[0m\n")
                print(f"[DEBUG] STDOUT: {result.stdout}")
                print(f"[DEBUG] STDERR: {result.stderr}")

            return success

        elif package_type == "nuget":
            """
            For NuGet packages, the 'nuget push' command is used to upload the package.
            """
            upload_url = f"https://pkgs.dev.azure.com/{organization}/{project_name}/_packaging/{target_feed_id}/nuget/v3/index.json"

            # Creates the 'NuGet.Config' file to be used by 'nuget'.
            nuget_config_path = os.path.join(os.path.expanduser("~"), "NuGet.Config")
            
            with open(nuget_config_path, "w") as f:
                f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <add key="TargetFeed" value="{upload_url}" />
  </packageSources>
  <packageSourceCredentials>
    <TargetFeed>
      <add key="Username" value="az" />
      <add key="ClearTextPassword" value="{target_pat}" />
    </TargetFeed>
  </packageSourceCredentials>
</configuration>""")

            success = True

            for package_path in package_paths:
                if package_path.endswith('.nupkg'):
                    print(f"[INFO] Uploading '{os.path.basename(package_path)}' to target feed...")

                    # Executes the uploading command using CLI.
                    cmd = [
                        "nuget", "push",
                        package_path,
                        "-src", "TargetFeed",
                        "-SkipDuplicate",
                    ]

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=180
                    )
                    
                    if result.returncode == 0:
                        print(f"\033[1;32m[SUCCESS] Successfully uploaded '{os.path.basename(package_path)}' to target feed.\033[0m")

                    else:
                        print(f"\033[1;31m[ERROR] Failed to upload '{os.path.basename(package_path)}' to target feed.\033[0m")
                        print(f"[DEBUG] STDOUT: {result.stdout}")
                        print(f"[DEBUG] STDERR: {result.stderr}")
                        success = False
                
            # Cleans up the 'NuGet.config' file created earlier.
            if os.path.exists(nuget_config_path):
                os.remove(nuget_config_path)
            
            return success

        else:
            print(f"\033[1;31m[ERROR] Unsupported package type: '{package_type}'.\033[0m")
            return False
            
    except Exception as e:
        print(f"\033[1;31m[ERROR] An error occurred while uploading package '{package_name}': {e}\033[0m")
        return False

def migrate_packages(source_organization, source_project, source_headers, target_organization, target_project, target_headers):
    """
    This function migrates packages from a source feed to a target feed.

    • Only packages with source configured as 'This feed' can be migrated.
    """
    ascii_art = pyfiglet.figlet_format("by codewizard", font="ogre")
    print(ascii_art)

    print("\n" + "\033[1m=\033[0m" * 100)
    print("\033[1mSTARTING FEEDS MIGRATION PROCESS\033[0m")
    print("\033[1m=\033[0m" * 100)

    source_feeds = get_feeds(source_organization, source_project, source_headers)

    if not source_feeds:
        print(f"\033[1;31m[ERROR] No feeds found in the '{source_project}' project in the '{source_organization}' organization; migration aborted\033[0m")
        return

    print("\n\033[1;38;5;38mAvailable Source Feeds:\033[0m")
    for i, feed in enumerate(source_feeds, 1):
        print(f"{i} - {feed.get('name', 'Unknown')}")
    
    while True:
        try:
            source_feed_index = int(input("\n[USER INPUT] Enter source feed number: ")) - 1

            if 0 <= source_feed_index < len(source_feeds):
                source_feed = source_feeds[source_feed_index]
                print(f"Selected source feed: {source_feed.get('name')}")
                break

            else:
                print(f"Please enter a number between 1 and {len(source_feeds)}.")

        except ValueError:
            print(f"Please enter a number between 1 and {len(source_feeds)}.")
    
    source_feed_packages = get_feed_packages(source_organization, source_project, source_headers, source_feed.get('id'))
    
    if not source_feed_packages:
        print("\033[1;31m[ERROR] No packages found in the selected source feed; migration aborted\033[0m")
        return
    
    print("\n\033[1;38;5;38mAvailable Packages for Migration:\033[0m")
    for i, package in enumerate(source_feed_packages, 1):
        print(f"{i} - {package.get('name', 'Unknown')} (type: {package.get('protocolType', 'Unknown')})")
    
    selected_packages = []
    print("\n0 - Migrate all packages.")
 
    while True:
        try:
            package_selection = input("\n[USER INPUT] Enter package numbers separated by commas to select specific packages: ").strip()
            
            if package_selection == '0':
                selected_packages = source_feed_packages
                break

            else:
                try:
                    selection_indices = [int(idx.strip()) - 1 for idx in package_selection.split(',')]
                    selected_packages = [source_feed_packages[idx] for idx in selection_indices
                                        if 0 <= idx < len(source_feed_packages)]
                    
                    if not selected_packages:
                        print(f"Please enter a number(s) between 1 and {len(source_feed_packages)}, or 0 to migrate all packages.")
                        continue
                    
                    break

                except ValueError:
                    print(f"Please enter a number(s) between 1 and {len(source_feed_packages)}, or 0 to migrate all packages.")
                    continue
                
        except ValueError:
            print(f"Please enter a number(s) between 1 and {len(source_feed_packages)}, or 0 to migrate all packages.")
    
    print(f"\nSelected {len(selected_packages)} package(s) for migration.")

    target_feeds = get_feeds(target_organization, target_project, target_headers)

    if not target_feeds:
        print(f"\033[1;31m[ERROR] No feeds found in the '{target_project}' project in the '{target_organization}' organization; migration aborted\033[0m")
        return

    print("\n\033[1;38;5;38mAvailable Target Feeds:\033[0m")
    for i, feed in enumerate(target_feeds, 1):
        print(f"{i} - {feed.get('name', 'Unknown')}")
    
    while True:
        try:
            target_feed_index = int(input("\n[USER INPUT] Enter target feed number: ")) - 1

            if 0 <= source_feed_index < len(target_feeds):
                target_feed = target_feeds[target_feed_index]
                print(f"Selected target feed: {target_feed.get('name')}")
                break

            else:
                print(f"Please enter a number between 1 and {len(target_feeds)}.")

        except ValueError:
            print(f"Please enter a number between 1 and {len(target_feeds)}.")

    migrate_all_versions = input("\n[USER INPUT] Migrate all versions of each package? (y/n - default: y): ").lower()
    migrate_all_versions = migrate_all_versions != 'n'  # Defaults to True if not explicitly 'n'.
    
    print("\n" + "\033[1m=\033[0m" * 100)
    print("\033[1mMIGRATION SUMMARY\n\033[0m")
    print(f"• Source environment: {source_organization}/{source_project} | Feed: {source_feed.get('name')}")
    print(f"• Target environment: {target_organization}/{target_project} | Feed: {target_feed.get('name')}")
    print(f"• Packages to migrate: {len(selected_packages)}")
    print("\033[1m=\033[0m" * 100)
    
    confirmation = input("\n[USER INPUT] Proceed with the migration? (y/n): ").lower()

    if confirmation != 'y':
        print("Migration aborted by user.")
        return
    
    # Creates local temporary directory for package download.
    temp_dir = os.path.join(os.getcwd(), "downloaded_packages")
    #os.makedirs(temp_dir, exist_ok=True) # Creates a download directory if it does not exist.

    # Migration counter for summary.
    successful_migrations = 0
    total_versions = 0
    
    for package in selected_packages:
        package_name = package.get('name')
        package_id = package.get('id')
        package_protocol_type = package.get('protocolType')
        
        print(f"\n{'=' * 100}")
        print(f"Migrating package '{package_name}' (type: {package_protocol_type})...")
        
        package_versions = get_package_versions(
            source_organization,
            source_project,
            source_headers,
            source_feed.get('id'),
            package_id
        )
        
        if not package_versions:
            print(f"\033[1;31m[ERROR] No versions found for package '{package_name}'; moving to the next package\033[0m")
            continue
            
        # Determines which versions to migrate.
        versions_to_migrate = package_versions

        if not migrate_all_versions:
            latest_version = None

            for version in package_versions:
                if version.get("isLatest", False):
                    latest_version = version
                    break
            
            if not latest_version and package_versions:
                latest_version = package_versions[0]
                
            if not latest_version:
                print(f"\033[1;31m[ERROR] Could not determine latest version for package '{package_name}'.\033[0m")
                continue
                
            versions_to_migrate = [latest_version]
        
        print(f"Migrating {len(versions_to_migrate)} version(s) of package '{package_name}'...")
        total_versions += len(versions_to_migrate)
        
        for version in versions_to_migrate:
            version_str = version.get("normalizedVersion", version.get("version"))
            version_id = version.get("id")
            
            print(f"\n{'-' * 50}")
            print(f"Processing version '{version_str}'...")
            
            package_directory = os.path.join(temp_dir, package_name, version_str)
            #os.makedirs(pkg_dir, exist_ok=True)
            
            print(f"Downloading the '{package_name}' package in version '{version_str}'...")

            downloaded_files = download_package_version(
                source_organization, 
                source_project, 
                source_headers,
                source_feed.get('id'),
                package_id, 
                package_name, 
                version_str,
                version_id, 
                package_protocol_type, 
                package_directory
            )
            
            if not downloaded_files:
                print(f"\033[1;31m[ERROR] Failed to download version '{version_str}' of the '{package_name}' package; moving to the next version\033[0m")
                continue
        
            print(f"Uploading the '{package_name}' package to target feed...")
            
            upload_success = upload_package(
                target_organization, 
                target_project, 
                TARGET_PAT,
                target_feed.get('id'), 
                downloaded_files, 
                package_protocol_type, 
                package_name
            )
        
        if upload_success:
            successful_migrations += 1
            print(f"\n\033[1;32m[SUCCESS] Package '{package_name}' has been successfully migrated.\033[0m")

        else:
            print(f"\n\033[1;31m[ERROR] Failed to migrate package '{package_name}' to target feed.\033[0m")
    
    print("\nCleaning up temporary files and directories...")
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print("\n" + "\033[1m=\033[0m" * 100)
    print(f"\033[1mMIGRATION COMPLETED!\n\033[0m")
    print(f"Successfully migrated {successful_migrations} out of {len(selected_packages)} package(s).")
    print("\033[1m=\033[0m" * 100)

if __name__ == "__main__":
    migrate_packages('Qognify', SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, TARGET_ORGANIZATION_FEEDS, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER)