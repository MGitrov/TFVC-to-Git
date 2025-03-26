import os
import json
import base64
import requests
import hashlib
from dotenv import load_dotenv
import tqdm
import csv
import re
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
        #print(f"[DEBUG] Request's Status Code: {response.status_code}")

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
        #print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
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
        #print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
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
        #print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
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
            # Writes missing items.
            for path in missing_items:
                writer.writerow([
                    "MISSING FROM TARGET", 
                    path,
                    source_dictionary[path].get('size', 'N/A')
                ])
            
            # Writes extra items.
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

def sample_content(source_organization, source_project_name, source_header, source_tfvc_path, 
                  target_organization, target_project_name, target_header, target_tfvc_path, 
                  results_folder, sample_size=50):
    """
    The function compares the actual content of files of a source and target TFVC repositories. 
    
    Rather than comparing every single file (which could be very time-consuming for large repositories), 
    the function uses statistical sampling to check a representative subset of files.
    """
    print(f"[INFO] Sampling content of {sample_size} files...")
    
    source_tfvc_items = get_items(source_organization, source_project_name, source_tfvc_path, source_header)

    if not source_tfvc_items:
        return {"success": False, "error": "Failed to retrieve source items"}
    
    total_items = len(source_tfvc_items.get('value', []))
    print(f"[DEBUG] Total TFVC items fetched from source: {total_items}")
    
    # Filters for files only (not folders).
    files = [item for item in source_tfvc_items.get('value', []) if 'path' in item and '.' in item['path'].split('/')[-1]]

    print(f"[DEBUG] Files identified: {len(files)}")

    # If files are not found, the function tries to understand the structure.
    if not files:
        print("\n\033[1;38;5;214m[WARNING] No files found; Examining response structure...\033[0m")
        
        if source_tfvc_items.get('value') and len(source_tfvc_items.get('value')) > 0:
            first_item = source_tfvc_items.get('value')[0]
            print(f"[DEBUG] First item properties: {list(first_item.keys())}")
            print(f"[DEBUG] First item sample: {json.dumps(first_item, indent=2)[:500]}\n")
        
        return {"success": False, "error": "No files found in source path"}
    
    sample_size = min(sample_size, len(files))
    files_sample = random.sample(files, sample_size) if len(files) > sample_size else files
    
    print(f"[DEBUG] Files to compare: {len(files_sample)}")
    
    results = []
    error_count = 0
    
    for file in tqdm.tqdm(files_sample, desc="Comparing files"):
        try:
            source_file_path = file['path']
            target_file_path = source_file_path.replace(source_tfvc_path, target_tfvc_path)
            print("\n")
            print(f"[DEBUG] Comparing: '{source_file_path}' → '{target_file_path}'")
            
            source_file_content = get_item_content(source_organization, source_project_name, source_file_path, source_header)

            if source_file_content is None:
                error_count += 1
                results.append({
                    "path": source_file_path,
                    "match": False,
                    "error": "Failed to retrieve source content"
                })
                continue
                
            target_file_content = get_item_content(target_organization, target_project_name, target_file_path, target_header)

            if target_file_content is None:
                error_count += 1
                results.append({
                    "path": source_file_path,
                    "match": False,
                    "error": "Failed to retrieve target content"
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
            
            match = source_file_hash == target_file_hash
            
            results.append({
                "path": source_file_path,
                "match": match,
                "source_hash": source_file_hash,
                "target_hash": target_file_hash
            })

        except Exception as e:
            print(f"\033[1;31m[ERROR] An error occurred while comparing file '{file.get('path', 'unknown')}': {e}\033[0m")
            error_count += 1
            results.append({
                "path": file.get('path', 'unknown'),
                "match": False,
                "error": str(e)
            })
    
    print(f"\n[INFO] Comparison complete:")
    print(f"• Files compared: {len(results)}")
    print(f"• Errors encountered: {error_count}")
    
    # Outputs the results to a CSV file.
    try:
        with open(f"{results_folder}/content_comparison.csv", "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Path", "Match", "Source Hash", "Target Hash", "Error"])
            
            for result in results:
                writer.writerow([
                    result["path"], 
                    result["match"], 
                    result.get("source_hash", "N/A"), 
                    result.get("target_hash", "N/A"),
                    result.get("error", "")
                ])

        print(f"\n[INFO] Results written to '{results_folder}/content_comparison.csv'.")

    except Exception as e:
        print(f"\n\033[1;31m[ERROR] An error occurred while writing to '{results_folder}/content_comparison.csv': {e}\033[0m")
    
    match_count = sum(1 for result in results if result["match"])
    
    return {
        "success": True,
        "sample_size": len(results),
        "match_count": match_count,
        "match_percentage": (match_count / len(results)) * 100 if results else 0,
        "error_count": error_count
    }

def compare_changesets(source_organization, source_project_name, source_header, 
                  target_organization, target_project_name, target_header, 
                  results_folder, sample_size=50):
    """
    This function compares recent changesets between a source and target TFVC repositories.
    """
    print(f"[INFO] Comparing recent {sample_size} changesets...")
    
    source_changesets = get_changesets(source_organization, source_project_name, source_header, sample_size)
    target_changesets = get_changesets(target_organization, target_project_name, target_header, sample_size)
    
    if not source_changesets or not target_changesets:
        return {"success": False, "error": "Failed to retrieve changesets"}
    
    source_cs = source_changesets.get('value', [])
    target_cs = target_changesets.get('value', [])
    
    # Counts how many changesets were found in each repository.
    source_changesets_count = len(source_cs)
    target_changesets_count = len(target_cs)
    
    # Creates a lookup dictionary of source changesets by ID and comment.
    source_changesets_dictionary = {str(cs.get('changesetId')): {
        'comment': cs.get('comment', ''),
        'author': cs.get('author', {}).get('displayName', ''),
        'date': cs.get('createdDate', '')
    } for cs in source_cs}
    
    matched_ids = []  # Stores source changeset numbers that were found in the target.
    migrated_changesets = []  # Stores target changeset numbers that reference source changesets.
    match_details = [] # Stores detailed information about each match.

    for target_changeset in target_cs:
        target_changeset_comment = target_changeset.get('comment', '')
        target_changeset_id = target_changeset.get('changesetId', 'N/A')
        
        # Tries different regex patterns.
        # Pattern 1: "Migrated from changeset no. {changeset_id}: {original_comment}"
        pattern1 = re.match(r"Migrated from changeset no\. (\d+): (.*)", target_changeset_comment)

        # Pattern 2: "Migrated changeset no. {changeset_id} - recreated the 'branch' branch"
        pattern2 = re.match(r"Migrated changeset no\. (\d+).*", target_changeset_comment)
        
        extracted_id = None
        extracted_comment = None
        match_type = None
        
        if pattern1:
            extracted_id = pattern1.group(1)
            extracted_comment = pattern1.group(2)
            match_type = "full" # A 'full' match occurs when both the source changeset ID and comment are found in the target changeset comment.

        elif pattern2:
            extracted_id = pattern2.group(1)
            match_type = "id_only" # An 'id_only' match occurs when only the source changeset ID is found in the target changeset comment.
        
        if extracted_id:
            migrated_changesets.append(target_changeset_id)
            
            # Checks whether this ID is among the source changesets.
            if extracted_id in source_changesets_dictionary:
                matched_ids.append(extracted_id)
                
                # Prepare match details for CSV
                source_comment = source_changesets_dictionary[extracted_id]['comment']
                comment_match = False
                
                if match_type == "full" and extracted_comment:
                    # Checks whether the extracted comment is contained in the source comment (allowing for truncation).
                    if source_comment.startswith(extracted_comment) or extracted_comment in source_comment:
                        comment_match = True
                
                match_details.append({
                    "source_id": extracted_id,
                    "target_id": target_changeset_id,
                    "match_type": match_type,
                    "source_comment": source_comment,
                    "target_comment": target_changeset_comment,
                    "extracted_comment": extracted_comment if extracted_comment else "N/A",
                    "comment_match": comment_match
                })
    
    # Counts unique source changesets that were matched.
    unique_matched_ids = set(matched_ids)
    
    # Outputs the results to a CSV file.
    with open(f"{results_folder}/changeset_comparison.csv", "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Source ID", "Target ID", "Match Type", "Source Comment", "Target Comment", "Extracted Comment", "Comment Match"])
        
        # Writes all matches found.
        for match in match_details:
            writer.writerow([
                match["source_id"],
                match["target_id"],
                match["match_type"],
                match["source_comment"],
                match["target_comment"],
                match["extracted_comment"],
                match["comment_match"]
            ])
        
        # Writes any source changesets that were not matched.
        for source_id, source_data in source_changesets_dictionary.items():
            if source_id not in matched_ids:
                writer.writerow([
                    source_id,
                    "NOT FOUND",
                    "no_match",
                    source_data["comment"],
                    "N/A",
                    "N/A",
                    "False"
                ])
    
    # Calculates match percentages.
    id_match_percentage = (len(unique_matched_ids) / source_changesets_count) * 100 if source_changesets_count > 0 else 0
    
    # Count full matches (ID + comment match)
    full_matches = sum(1 for match in match_details if match["comment_match"])
    full_match_percentage = (full_matches / source_changesets_count) * 100 if source_changesets_count > 0 else 0
    
    return {
        "success": True,
        "source_count": source_changesets_count,
        "target_count": target_changesets_count,
        "matched_source_ids": len(unique_matched_ids),
        "migrated_target_changesets": len(migrated_changesets),
        "full_matches": full_matches,
        "id_match_percentage": id_match_percentage,
        "full_match_percentage": full_match_percentage,
        "unmatched_source_ids": [id for id in source_changesets_dictionary.keys() if id not in unique_matched_ids]
    }

if __name__ == "__main__":
    ascii_art = pyfiglet.figlet_format("by codewizard", font="ogre")
    print(ascii_art)
    #get_items(SOURCE_ORGANIZATION, SOURCE_PROJECT,"$/TFS-based test project", SOURCE_AUTHENTICATION_HEADER)
    #get_item_content(SOURCE_ORGANIZATION, SOURCE_PROJECT,"$/TFS-based test project/branchWithin/tulip/tlp.md", SOURCE_AUTHENTICATION_HEADER)
    #get_labels(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    #get_changesets(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    #compare_structure(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, "$/TFS-based test project", TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER, "$/Magnolia", "/Users/pyruc/Desktop/TFVC-to-Git")
    #sample_content(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, "$/TFS-based test project", TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER, "$/Magnolia", "/Users/pyruc/Desktop/TFVC-to-Git", 30)
    compare_changesets(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER, "/Users/pyruc/Desktop/TFVC-to-Git", 30)