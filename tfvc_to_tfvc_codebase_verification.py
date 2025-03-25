import os
import shutil
import base64
import requests
import hashlib
from dotenv import load_dotenv
import tqdm
import csv
import random
import pyfiglet

load_dotenv()

SOURCE_ORGANIZATION=os.getenv("SOURCE_ORGANIZATION")
SOURCE_PROJECT="TFS-based test project"
SOURCE_PAT = os.getenv("SOURCE_PAT")

TARGET_ORGANIZATION=os.getenv("TARGET_ORGANIZATION")
TARGET_PROJECT="Magnolia"
TARGET_PAT = os.getenv("TARGET_PAT")

# Azure DevOps REST APIs require Basic Authentication, and since PAT is used here, the username is not required.
# Encoding ensures that special characters in the PAT (such as : or @) are safely transmitted without breaking the HTTP header's format.
SOURCE_AUTHENTICATION_HEADER = {
    "Authorization": f"Basic {base64.b64encode(f':{SOURCE_PAT}'.encode()).decode()}"
}
TARGET_AUTHENTICATION_HEADER = {
    "Authorization": f"Basic {base64.b64encode(f':{TARGET_PAT}'.encode()).decode()}"
}

def get_items(organization, project_name, tfvc_path, authentication_header, recursion="Full"):
    """
    This function fetches all TFVC items of a TFVC path in a project.
    """
    url = f"{organization}/{project_name}/_apis/tfvc/items"
    
    params = {
        "api-version": "7.1"
    }
    
    # When recursion is "None", the function uses the 'path' parameter in the API request, which retrieves just that specific item.
    if recursion == "None":
        params["path"] = tfvc_path

    # When recursion is "OneLevel" or "Full", the function uses 'scopePath' as the path parameter and adds a 'recursionLevel' parameter to specify how deep to go.
    else:
        params["scopePath"] = tfvc_path
        params["recursionLevel"] = recursion
    
    headers = {
        "Accept": "application/json"
    }
    headers.update(authentication_header)
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            return response.json()
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch TFVC items from '{tfvc_path}' path.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching TFVC items: {e}\033[0m")
        return None
    
def get_item_content(organization, project_name, tfvc_path, authentication_header):
    """
    This function fetches the content of a TFVC item.
    """
    url = f"{organization}/{project_name}/_apis/tfvc/items"
    
    params = {
        "path": tfvc_path,
        "api-version": "7.1"
    }
    
    headers = {
        "Accept": "application/octet-stream"
    }
    headers.update(authentication_header)
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            return response.content
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch content for '{tfvc_path}'.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching item content: {e}\033[0m")
        return None

def get_labels(organization, project_name, authentication_header):
    """
    This function fetches all labels of a TFVC repository.
    """
    url = f"{organization}/{project_name}/_apis/tfvc/labels"
    
    params = {
        "api-version": "7.1"
    }
    
    headers = {
        "Accept": "application/json"
    }
    headers.update(authentication_header)
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            #print(f"\n{response.json()}\n")
            return response.json()
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch TFVC labels.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching labels: {e}\033[0m")
        return None

def get_changesets(organization, project_name, authentication_header, top=100):
    """
    This function fetches recent changesets of a TFVC repository.
    """
    url = f"{organization}/{project_name}/_apis/tfvc/changesets"
    
    params = {
        "api-version": "7.1",
        "$top": top  # Get the most recent changesets
    }
    
    headers = {
        "Accept": "application/json"
    }
    headers.update(authentication_header)
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch changesets.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching changesets: {e}\033[0m")
        return None

def compare_structure(source_organization, source_project_name, source_header, source_tfvc_path, target_organization, target_project_name, 
                     target_header, target_tfvc_path, results_folder):
    """
    This function compares the structure of a source and target TFVC repositories.
    """
    print(f"[INFO] Comparing repository structures...")
    
    source_tfvc_items = get_items(source_organization, source_project_name, source_tfvc_path, source_header)
    target_tfvc_items = get_items(target_organization, target_project_name, target_tfvc_path, target_header)
    
    if not source_tfvc_items or not target_tfvc_items:
        return {"success": False, "error": "Failed to retrieve repository structure"}
    
    # Creates a lookup dictionaries by TFVC path.
    source_dictionary = {item['path']: item for item in source_tfvc_items.get('value', [])}

    # Normalizes the target paths by replacing the target root path with the source root path. This creates a consistent basis for comparison.
    target_dictionary = {item['path'].replace(target_tfvc_path, source_tfvc_path): item 
                  for item in target_tfvc_items.get('value', [])}
    
    source_counter = len(source_dictionary)
    target_counter = len(target_dictionary)
    
    # Finds missing and/or extra items between the repositories.
    source_paths = set(source_dictionary.keys())
    target_paths = set(target_dictionary.keys())
    
    # These items exist in the source TFVC repository but are not found in the target repository. These are files/folders that should have been migrated but were not.
    missing_items = source_paths - target_paths

    # These exist in the target TFVC repository but are not found in the source repository. These are files/folders that appeared in the target repository without corresponding items in the source.
    extra_items = target_paths - source_paths
    
    # Outputs the results to a CSV file.
    with open(f"{results_folder}/structure_comparison.csv", "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Status", "TFVC Path", "Size (bytes)"])
        
        if not missing_items and not extra_items:
            writer.writerow(["INFO", f"'{source_tfvc_path}' and '{target_tfvc_path}' are identical", f"All {source_counter} items match"])

        else:
            # Write missing items.
            for path in missing_items:
                writer.writerow([
                    "MISSING FROM TARGET", 
                    path,
                    source_dictionary[path].get('size', 'N/A')
                ])
            
            # Write extra items.
            for path in extra_items:
                # Formats back the target path to its original form.
                actual_target_path = path.replace(source_tfvc_path, target_tfvc_path)
                writer.writerow([
                    "EXTRA IN TARGET", 
                    actual_target_path,
                    target_dictionary[path].get('size', 'N/A')
                ])
    
    return {
        "success": True,
        "source_count": source_counter,
        "target_count": target_counter,
        "missing_count": len(missing_items),
        "extra_count": len(extra_items),
        "matching_count": len(source_paths.intersection(target_paths))
    }

def sample_content(source_organization, source_project_name, source_header, source_tfvc_path, target_organization, target_project_name, 
                     target_header, target_tfvc_path, results_folder, sample_size=50):
    """
    The function compares the actual content of files of a source and target TFVC repositories. 
    
    Rather than comparing every single file (which could be very time-consuming for large repositories), 
    the function uses statistical sampling to check a representative subset of files.
    """
    print(f"[INFO] Sampling content of {sample_size} files...")
    
    source_tfvc_items = get_items(source_organization, source_project_name, source_tfvc_path, source_header)

    if not source_tfvc_items:
        return {"success": False, "error": "Failed to retrieve source items"}
    
    # Filters for files only (not folders).
    files = [item for item in source_tfvc_items.get('value', []) if item.get('isFolder') is False]
    
    # Takes a sample of files.
    sample_size = min(sample_size, len(files))
    files_sample = random.sample(files, sample_size) if len(files) > sample_size else files
    
    results = []
    
    for file in tqdm.tqdm(files_sample, desc="Comparing files"):
        source_file_path = file['path']
        target_file_path = source_file_path.replace(source_tfvc_path, target_tfvc_path)
        
        source_file_content = get_item_content(source_organization, source_project_name, source_file_path, source_header)
        target_file_content = get_item_content(target_organization, target_project_name, target_file_path, target_header)
        
        if source_file_content is None or target_file_content is None:
            results.append({
                "path": source_file_path,
                "match": False,
                "error": "Failed to retrieve content"
            })
            continue
        
        """
        Uses SHA-256 hash to compare the content of the files.

        • The same file will always produce the same hash.
        • Different files will almost always produce different hashes.
        • Even a small change in the file will produce a completely different hash.
        """
        source_file_hash = hashlib.sha256(source_file_content).hexdigest()
        target_file_hash = hashlib.sha256(target_file_content).hexdigest()
        
        results.append({
            "path": source_file_path,
            "match": source_file_hash == target_file_hash,
            "source_hash": source_file_hash,
            "target_hash": target_file_hash
        })
    
    # Write results to CSV
    with open(f"{results_folder}/content_comparison.csv", "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Path", "Match", "Source Hash", "Target Hash"])
        
        for result in results:
            writer.writerow([
                result["path"], 
                result["match"], 
                result.get("source_hash", "N/A"), 
                result.get("target_hash", "N/A")
            ])
    
    match_count = sum(1 for result in results if result["match"])
    
    return {
        "success": True,
        "sample_size": len(results),
        "match_count": match_count,
        "match_percentage": (match_count / len(results)) * 100 if results else 0
    }

if __name__ == "__main__":
    #get_items(SOURCE_ORGANIZATION, SOURCE_PROJECT,"$/TFS-based test project", SOURCE_AUTHENTICATION_HEADER)
    #get_item_content(SOURCE_ORGANIZATION, SOURCE_PROJECT,"$/TFS-based test project/branchWithin/tulip/tlp.md", SOURCE_AUTHENTICATION_HEADER)
    #get_labels(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    #get_changesets(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    #compare_structure(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, "$/TFS-based test project", TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER, "$/Magnolia", "/Users/pyruc/Desktop/TFVC-to-Git")
    sample_content(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, "$/TFS-based test project", TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER, "$/Magnolia", "/Users/pyruc/Desktop/TFVC-to-Git", 300)