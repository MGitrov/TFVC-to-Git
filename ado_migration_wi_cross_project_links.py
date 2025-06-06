import os
import requests
import base64
import re

from dotenv import load_dotenv



import pyfiglet


load_dotenv()

SOURCE_ORGANIZATION=os.getenv("SOURCE_ORGANIZATION")
SOURCE_PROJECT= os.getenv("SOURCE_PROJECT")
SOURCE_PAT = os.getenv("SOURCE_PAT")

TARGET_ORGANIZATION=os.getenv("TARGET_ORGANIZATION")
TARGET_PROJECT=os.getenv("TARGET_PROJECT")
TARGET_PAT = os.getenv("TARGET_PAT")

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
    api_version = "7.1"
    url = f"{organization}/_apis/projects/{project_name}?api-version={api_version}"

    #print("##############################")
    #print(f"[INFO] Fetching the ID of '{project_name}' project from '{organization}'...")
    #print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        #print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            project_id = response.json()["id"]
            #print(f"Project: {project_name} | ID: {project_id}")

            return project_id
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch project ID of '{project_name}' project.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching project ID: {e}\033[0m")
        return None

def get_work_items(organization, project_name, authentication_header, work_item_ids=None):
    """
    This function fetches all work items of a project.
    """
    api_version = "7.1"
    
    print(f"\n[INFO] Fetching work items from '{project_name}' in '{organization}'...")
    
    try:
        if work_item_ids is not None:
            if len(work_item_ids) == 0:
                print(f"[INFO] No work item IDs provided, returning empty list.")
                return []
            
            work_items = []
            batch_size = 200  # Azure DevOps' API limit.
            
            for i in range(0, len(work_item_ids), batch_size):
                batch_ids = work_item_ids[i:i+batch_size]
                ids_parameters = ",".join(map(str, batch_ids)) # Converts the list of IDs to a comma-separated string.

                # The '$expand=all' parameter requests all related information for each work item.
                url = f"{organization}/{project_name}/_apis/wit/workitems?ids={ids_parameters}&api-version={api_version}&$expand=all"
                
                response = requests.get(url, headers=authentication_header)
                #print(f"[DEBUG] Request's Status Code: {response.status_code}")

                if response.status_code == 200:
                    batch_items = response.json().get("value", [])
                    work_items.extend(batch_items)
                    #print(f"[INFO] Retrieved {len(batch_items)} work items in batch.")

                else:
                    print(f"\033[1;31m[ERROR] Failed to fetch work items batch from '{project_name}' project.\033[0m")
                    print(f"[DEBUG] Request's Status Code: {response.status_code}")
                    print(f"[DEBUG] Response Body: {response.text}")
            
            print(f"[INFO] Successfully retrieved {len(work_items)} work items.")
            return work_items
            
        else:
            wiql_url = f"{organization}/{project_name}/_apis/wit/wiql?api-version={api_version}"
            wiql_query = {
                "query": "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project AND [System.WorkItemType] NOT IN ('Test Case', 'Test Suite', 'Test Plan','Shared Steps','Shared Parameter','Feedback Request','Feedback Response', 'Code Review Request', 'Code Review Response') ORDER BY [System.Id]"
            } # Queries only for basic work items in the project.
            
            wiql_response = requests.post(wiql_url, headers=authentication_header, json=wiql_query)
            #print(f"[DEBUG] Request's Status Code: {wiql_response.status_code}")
            
            if wiql_response.status_code == 200:
                work_item_references = wiql_response.json().get("workItems", [])
                all_work_item_ids = [item["id"] for item in work_item_references]
                
                print(f"[INFO] Found {len(all_work_item_ids)} work item IDs.")
                
                # Calls the function recursively to fetch all work items in batches.
                return get_work_items(organization, project_name, authentication_header, work_item_ids=all_work_item_ids)
            else:
                print(f"\033[1;31m[ERROR] Failed to query work item IDs from '{project_name}' project.\033[0m")
                print(f"[DEBUG] Request's Status Code: {wiql_response.status_code}")
                print(f"[DEBUG] Response Body: {wiql_response.text}")
                return []
    
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching work items: {e}\033[0m")
        return []

def get_work_item_by_id(organization, authentication_header, work_item_id): # REVIEW.
    """
    Fetches a single work item by ID from any project in the organization.
    """
    api_version = "7.1"
    url = f"{organization}/_apis/wit/workitems/{work_item_id}?api-version={api_version}&$expand=all"
    
    try:
        response = requests.get(url, headers=authentication_header)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
            
    except requests.exceptions.RequestException as e:
        return None

def get_project_by_id(organization, authentication_header, project_id): # REVIEW.
    """
    Fetches project information by project ID/GUID.
    """
    api_version = "7.1"
    url = f"{organization}/_apis/projects/{project_id}?api-version={api_version}"
    
    try:
        response = requests.get(url, headers=authentication_header)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
            
    except requests.exceptions.RequestException as e:
        return None

def normalize_string(text): # REVIEW.
    """
    Normalizes a string by removing extra whitespace, hidden characters, emojis, and special characters.
    """
    if not text:
        return ""
    
    # Convert to string if not already
    text = str(text)
    
    # Replace smart quotes and similar characters with regular ones
    text = text.replace('"', '"')  # Left double quotation mark
    text = text.replace('"', '"')  # Right double quotation mark
    text = text.replace(''', "'")  # Left single quotation mark
    text = text.replace(''', "'")  # Right single quotation mark
    text = text.replace('–', '-')  # En dash
    text = text.replace('—', '-')  # Em dash
    text = text.replace('…', '...')  # Horizontal ellipsis
    
    # Replace common problematic whitespace characters
    text = text.replace('\u00A0', ' ')  # Non-breaking space
    text = text.replace('\u2000', ' ')  # En quad
    text = text.replace('\u2001', ' ')  # Em quad
    text = text.replace('\u2002', ' ')  # En space
    text = text.replace('\u2003', ' ')  # Em space
    text = text.replace('\u2004', ' ')  # Three-per-em space
    text = text.replace('\u2005', ' ')  # Four-per-em space
    text = text.replace('\u2006', ' ')  # Six-per-em space
    text = text.replace('\u2007', ' ')  # Figure space
    text = text.replace('\u2008', ' ')  # Punctuation space
    text = text.replace('\u2009', ' ')  # Thin space
    text = text.replace('\u200A', ' ')  # Hair space
    text = text.replace('\u202F', ' ')  # Narrow no-break space
    text = text.replace('\u205F', ' ')  # Medium mathematical space
    text = text.replace('\u3000', ' ')  # Ideographic space
    
    # Remove zero-width characters
    text = text.replace('\u200B', '')  # Zero-width space
    text = text.replace('\u200C', '')  # Zero-width non-joiner
    text = text.replace('\u200D', '')  # Zero-width joiner
    text = text.replace('\uFEFF', '')  # Zero-width no-break space
    
    # Remove emojis and other symbols
    # This regex removes most emojis and symbols while keeping basic punctuation
    #import re
    
    # Remove emojis (most common ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251" 
        "\U0001f926-\U0001f937"  # additional faces
        "\U00010000-\U0010ffff"  # supplementary planes
        "\u2640-\u2642"          # gender symbols
        "\u2600-\u2B55"          # misc symbols
        "\u200d"                 # zero width joiner
        "\u23cf"                 # eject symbol
        "\u23e9"                 # fast forward
        "\u231a"                 # watch
        "\ufe0f"                 # variation selector
        "\u3030"                 # wavy dash
        "]+", 
        flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)
    
    # Remove specific problematic characters found in your data
    text = text.replace('👀', '')   # Eyes emoji
    text = text.replace('🕒', '')   # Clock emoji  
    text = text.replace('🤔', '')   # Thinking emoji
    
    # Normalize whitespace: strip and replace multiple spaces with single space
    text = ' '.join(text.split())
    
    return text

def extract_project_guid_from_url(url): # REVIEW.
    """
    Extracts project GUID from Azure DevOps work item URL.
    Expected format: http://server/tfs/DefaultCollection/[PROJECT_GUID]/_apis/wit/workItems/[ID]
    """
    # Pattern to match project GUID in the URL
    pattern = r'/tfs/DefaultCollection/([0-9a-f-]{36})/_apis/wit/workItems'
    match = re.search(pattern, url, re.IGNORECASE)
    
    if match:
        return match.group(1)
    return None

def extract_cross_project_work_item_relations(organization, project_name, authentication_header):
    """
    This function extracts all cross-project work item relationships from a project.
    
    Returns:
    Dictionary mapping source work item IDs to their cross-project relationships:
    {
        '123': [
            {
                'relation_type': 'System.LinkTypes.Related',
                'target_work_item_id': '456',
                'target_project': 'OtherProject',
                'target_project_guid': 'abc123-...',
                'url': 'http://server/tfs/DefaultCollection/abc123/_apis/wit/workItems/456',
                'attributes': {...}
            }
        ]
    }
    """
    print("##############################")
    print("[INFO] Extracting cross-project work item relationships...")
    
    work_items = get_work_items(organization, project_name, authentication_header)
    
    # Extracts current project ID for comparison.
    current_project_id = get_project_id(organization, project_name, authentication_header)
    
    cross_project_relations = {}
    
    # Statistics
    total_work_items = len(work_items)
    total_work_items_with_cross_project_links = 0
    total_cross_project_links = 0
    relation_types_count = {}
    # Statistics

    external_projects = {}
    
    # Caches project IDs to avoid repeated API calls.
    project_id_cache = {}
    
    for work_item in work_items:
        work_item_id = work_item.get('id')
        
        work_item_relations = work_item.get('relations', [])
        
        if not work_item_relations:
            continue
        
        work_item_cross_project_links = []
        
        for relation in work_item_relations:
            relation_type = relation.get('rel', '')
            relation_url = relation.get('url', '')
            relation_attributes = relation.get('attributes', {})
            
            # 'ArtifactLink' relations specifically targeting links between work items and codebase objects.
            if relation_type == 'ArtifactLink':
                continue
            
            # Checks whether this is a link between work items.
            work_item_match = re.search(r'/workitems/(\d+)', relation_url, re.IGNORECASE)

            if work_item_match:
                linked_work_item_id = work_item_match.group(1)
                
                # Extracts the project ID from the relation URL (e.g., what project the linked work item is located in).
                project_id = extract_project_guid_from_url(relation_url)
                
                # Checks whether this is a cross-project link.
                if project_id and project_id != current_project_id:
                    # Searches the cache dictionary to avoid making multiple API calls for the same project ID.
                    if project_id not in project_id_cache:
                        project_info = get_project_by_id(organization, authentication_header, project_id)

                        if project_info:
                            project_id_cache[project_id] = project_info.get('name', 'Unknown')

                        else:
                            project_id_cache[project_id] = 'Unknown'
                    
                    linked_project_name = project_id_cache[project_id]
                    external_projects[project_id] = linked_project_name
                    
                    # Get target work item (within the source organization) details.
                    target_work_item = get_work_item_by_id(organization, authentication_header, linked_work_item_id)
                    target_work_item_type = 'Unknown'
                    target_work_item_title = 'Untitled'
                    
                    if target_work_item:
                        target_work_item_type = target_work_item.get('fields', {}).get('System.WorkItemType', 'Unknown')
                        target_work_item_title = target_work_item.get('fields', {}).get('System.Title', 'Untitled')
                    
                    relation_info = {
                        'relation_type': relation_type,
                        'target_work_item_id': int(linked_work_item_id),
                        'target_project': linked_project_name,
                        'target_project_guid': project_id,
                        'url': relation_url,
                        'attributes': relation_attributes,
                        'target_work_item_type': target_work_item_type,
                        'target_work_item_title': target_work_item_title
                    }
                    
                    # Statistics
                    work_item_cross_project_links.append(relation_info)
                    total_cross_project_links += 1
                    relation_types_count[relation_type] = relation_types_count.get(relation_type, 0) + 1
                    # Statistics
        
        if work_item_cross_project_links:
            # Assigns the current work item with its cross-project links.
            cross_project_relations[work_item_id] = work_item_cross_project_links
            total_work_items_with_cross_project_links += 1
    
    print(f"\n• Total work items processed: {total_work_items}")
    print(f"• Work items with cross-project links: {total_work_items_with_cross_project_links} ({(total_work_items_with_cross_project_links/total_work_items*100):.2f}% of total work items)")
    print(f"• Total cross-project links found: {total_cross_project_links}")
    
    print(f"\nExternal projects referenced:")
    for project_id, project_name in external_projects.items():
        print(f"• {project_name} (GUID: {project_id})")
    
    print(f"\nBreakdown by relation type:")
    print("-"*35)
    for relation_type, count in relation_types_count.items():
        print(f"• {relation_type}: {count} ({(count/total_cross_project_links*100):.2f}% of total cross-project links)")
    
    return cross_project_relations

def map_cross_project_work_items(source_organization, source_authentication_header,
                                target_organization, target_authentication_header,
                                cross_project_relations):
    """
    This function creates mappings between work items in external projects from the source environment to their corresponding work 
    items in the target environment.
    
    Returns:
    Dictionary with mappings for each external project:
    {
        'ExternalProject1': {
            source_work_item_id: target_work_item_id,
            ...
        },
        'ExternalProject2': {
            ...
        }
    }
    """
    print("##############################")
    print("[INFO] Mapping cross-project work items...")
    
    # Encompasses all external projects and work items there is a need to map.
    external_projects_work_items = {}
    
    # Traverses through the "cross_project_relations" dictionary, and groups work item IDs by their external project names (within the source organization).
    for source_work_item_id, relations in cross_project_relations.items():
        for relation in relations:
            target_project = relation['target_project']
            target_work_item_id = relation['target_work_item_id']
            
            if target_project not in external_projects_work_items:
                external_projects_work_items[target_project] = set()
            
            external_projects_work_items[target_project].add(target_work_item_id)
    
    mapping_results = {}
    
    for external_project, work_item_ids in external_projects_work_items.items():
        print(f"\n[INFO] Mapping work items for external project '{external_project}'...")
        
        # Fetches work items from source external project.
        source_external_work_items = get_work_items(
            source_organization, 
            external_project, 
            source_authentication_header,
            work_item_ids=list(work_item_ids) # Only the work items that are referenced in cross-project links are fetched.
        )
        
        # Fetches work items from target external project (assuming same project name).
        target_external_work_items = get_work_items(
            target_organization,
            external_project,  # Assuming same project name in the target environment.
            target_authentication_header
        )
        
        # Creates mapping based on work item title and type.
        target_lookup = {}

        for work_item in target_external_work_items:
            work_item_id = work_item.get('id')
            raw_title = work_item.get('fields', {}).get('System.Title', '')
            raw_type = work_item.get('fields', {}).get('System.WorkItemType', '')

            # Normalizes the title and type for reliant comparison.
            normalized_title = normalize_string(raw_title)
            normalized_type = normalize_string(raw_type)
            
            key = f"{normalized_type}|{normalized_title}"
            target_lookup[key] = work_item_id
        
        project_mapping = {}
        matches = 0
        unmapped_items = []
        
        for source_work_item in source_external_work_items:
            source_work_item_id = source_work_item.get('id')
            raw_title = source_work_item.get('fields', {}).get('System.Title', '')
            raw_type = source_work_item.get('fields', {}).get('System.WorkItemType', '')

            normalized_title = normalize_string(raw_title)
            normalized_type = normalize_string(raw_type)
            
            key = f"{normalized_type}|{normalized_title}"
            
            if key in target_lookup:
                target_id = target_lookup[key]
                project_mapping[source_work_item_id] = target_id
                matches += 1
                print(f"[INFO] Mapped '{raw_type}: {raw_title}' ({source_work_item_id} → {target_id}) in project '{external_project}'")
        
            else:
                unmapped_items.append({
                    'id': source_work_item_id,
                    'type': raw_type,
                    'title': raw_title,
                    'key': key
                })

        mapping_results[external_project] = project_mapping
        print(f"[INFO] Mapped {matches} out of {len(source_external_work_items)} work items in project '{external_project}'.")

        if unmapped_items:
            print(f"\n\033[1;38;5;214m[WARNING] {len(unmapped_items)} work items could not be mapped in project '{external_project}':\033[0m")
            #print("-" * 80)
            
            # Groups unmapped work items by type for better visualization.
            unmapped_by_type = {}

            for item in unmapped_items:
                item_type = item['type']

                if item_type not in unmapped_by_type:
                    unmapped_by_type[item_type] = []

                unmapped_by_type[item_type].append(item)
            
            # Prints unmapped work items grouped by type.
            for work_item_type, items in unmapped_by_type.items():
                print(f"\n  {work_item_type} ({len(items)} unmapped):")

                for item in items[:10]:  # Displays first 10 work items of each type to avoid overwhelming the output.
                    print(f"    ID {item['id']}: '{item['title']}'")
                
                if len(items) > 10:
                    print(f"    ... and {len(items) - 10} more {work_item_type} items.")
            
            print("-" * 80)

        else:
            print(f"\n\033[1;32m[SUCCESS] All work items in project '{external_project}' were successfully mapped!\033[0m")
    
    return mapping_results

def map_source_project_work_items(source_organization, source_project, source_authentication_header,
                                 target_organization, target_project, target_authentication_header):
    """
    This function creates mappings between source work items from the source environment to their corresponding work items in the 
    target environment.
    """
    print(f"\n[INFO] Mapping work items from source project '{source_project}' to target project '{target_project}'...")
    
    source_work_items = get_work_items(source_organization, source_project, source_authentication_header)
    target_work_items = get_work_items(target_organization, target_project, target_authentication_header)
    
    # Creates mapping based on work item title and type.
    target_lookup = {}

    for target_work_item in target_work_items:
        target_work_item_id = target_work_item.get('id')
        raw_title = target_work_item.get('fields', {}).get('System.Title', '')
        raw_type = target_work_item.get('fields', {}).get('System.WorkItemType', '')

        # Normalizes the title and type for reliant comparison.
        normalized_title = normalize_string(raw_title)
        normalized_type = normalize_string(raw_type)
        
        key = f"{normalized_type}|{normalized_title}"
        target_lookup[key] = target_work_item_id
    
    source_project_mapping = {}
    matches = 0
    unmapped_items = []
    
    for source_work_item in source_work_items:
        source_work_item_id = source_work_item.get('id')
        raw_title = source_work_item.get('fields', {}).get('System.Title', '')
        raw_type = source_work_item.get('fields', {}).get('System.WorkItemType', '')

        normalized_title = normalize_string(raw_title)
        normalized_type = normalize_string(raw_type)
        
        key = f"{normalized_type}|{normalized_title}"
        
        if key in target_lookup:
            target_id = target_lookup[key]
            source_project_mapping[source_work_item_id] = target_id
            matches += 1
            print(f"[INFO] Mapped '{raw_type}: {raw_title}' ({source_work_item_id} → {target_id}) in project '{source_project}'")

        else:
            unmapped_items.append({
                    'id': source_work_item_id,
                    'type': raw_type,
                    'title': raw_title,
                    'key': key
                })
    
    print(f"[INFO] Mapped {matches} out of {len(source_work_items)} work items in project '{source_project}'")

    if unmapped_items:
            print(f"\n\033[1;38;5;214m[WARNING] {len(unmapped_items)} work items could not be mapped in project '{source_project}':\033[0m")
            #print("-" * 80)
            
            # Groups unmapped work items by type for better visualization.
            unmapped_by_type = {}

            for item in unmapped_items:
                item_type = item['type']

                if item_type not in unmapped_by_type:
                    unmapped_by_type[item_type] = []

                unmapped_by_type[item_type].append(item)
            
            # Prints unmapped work items grouped by type.
            for work_item_type, items in unmapped_by_type.items():
                print(f"\n  {work_item_type} ({len(items)} unmapped):")

                for item in items[:10]:  # Displays first 10 work items of each type to avoid overwhelming the output.
                    print(f"    ID {item['id']}: '{item['title']}'")
                
                if len(items) > 10:
                    print(f"    ... and {len(items) - 10} more {work_item_type} items.")
            
            print("-" * 80)

    else:
            print(f"\n\033[1;32m[SUCCESS] All work items in project '{source_project}' were successfully mapped!\033[0m")

    return source_project_mapping

def add_reference_update_comment(organization, authentication_header, work_item_id, old_id, new_id):
    """
    This function adds a new comment to a work item that documents which work item ID references were updated during the 
    recreation of cross-project links.
    """
    api_version = "7.1"
    url = f"{organization}/_apis/wit/workitems/{work_item_id}?api-version={api_version}"
    
    comment_text = f"Cross-project link migration: This work item is now referencing work item #{new_id} instead of {old_id}."
    
    payload = [
        {
            "op": "add", # Operation type for adding new content to Azure DevOps.
            "path": "/fields/System.History", # The way how Azure DevOps API accepts new comments.
            "value": comment_text
        }
    ]
    
    headers = {
        **authentication_header,
        "Content-Type": "application/json-patch+json"
    }
    
    try:
        response = requests.patch(url, headers=headers, json=payload)
        
        if response.status_code in (200, 201):
            return True, f"Added comment documenting reference change: {old_id} → {new_id}"
        
        else:
            return False, f"Failed to add comment: {response.status_code} - {response.text}"
            
    except Exception as e:
        return False, f"Error adding comment: {str(e)}"

def create_work_item_link(organization, authentication_header, source_work_item_id, target_work_item_id, relation_type):
    """
    This function creates a one-way formal relationship link between two work items in the target environment.
    Azure DevOps automatically handles creating the reverse relationship.
    """
    api_version = "7.1"
    
    # Checks whether the link already exists in the target environment.
    link_check_url = f"{organization}/_apis/wit/workitems/{source_work_item_id}?api-version={api_version}&$expand=relations"
    
    try:
        check_response = requests.get(link_check_url, headers=authentication_header)
        
        if check_response.status_code == 200:
            work_item = check_response.json()
            relations = work_item.get('relations', [])
            
            target_url = f"{organization}/_apis/wit/workItems/{target_work_item_id}"

            for relation in relations:
                if (relation.get('rel') == relation_type and 
                    relation.get('url') == target_url):
                    return False, "Link already exists"
                
        else:
            print(f"\033[1;38;5;214m[WARNING] Could not check existing links: {check_response.status_code}\033[0m")

    except Exception as e:
        print(f"\033[1;31m[ERROR] Error checking existing links: {str(e)}\033[0m")
    
    # Creates the link if there is no link already exists in the target environment.
    url = f"{organization}/_apis/wit/workitems/{source_work_item_id}?api-version={api_version}"
    
    payload = [
        {
            "op": "add", # Operation type for adding new content to Azure DevOps.
            "path": "/relations/-", # "-" means "append to end".
            "value": { # The new relation object to add.
                "rel": relation_type,
                "url": f"{organization}/_apis/wit/workItems/{target_work_item_id}"
            }
        }
    ]
    
    headers = {
        **authentication_header,
        "Content-Type": "application/json-patch+json"
    }
    
    try:
        response = requests.patch(url, headers=headers, json=payload)
        
        if response.status_code in (200, 201):
            return True, "Link created successfully"
        else:
            return False, f"Failed to create link: {response.status_code} - {response.text}"
            
    except requests.exceptions.RequestException as e:
        return False, f"Error creating link: {str(e)}"

def recreate_cross_project_links():
    """
    This function recreates cross-project links between work items in an organization.
    """
    os.system('cls' if os.name == 'nt' else 'clear')
    ascii_art = pyfiglet.figlet_format("by codewizard", font="ogre")
    print(ascii_art)

    print("\n" + "\033[1m=\033[0m" * 100)
    print("\033[1mSTARTING CROSS-PROJECT WORK ITEM LINKS RECREATION PROCESS\033[0m")
    print("\033[1m=\033[0m" * 100)

    results = {
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'comment_updates': 0,
        'comment_failures': 0,
        'details': {}
    }

    # Step 1: Extracts cross-project relations from the source environment.
    cross_project_relations = extract_cross_project_work_item_relations(
        SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER
    )
    
    if not cross_project_relations:
        print(f"\n[INFO] No cross-project work item relationships found in '{SOURCE_PROJECT}' in '{SOURCE_ORGANIZATION}'.")
        return results
    
    # Step 2: Maps work items of the source project between both environments.
    source_project_mapping = map_source_project_work_items(
        SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER,
        TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER
    )
    
    # Step 3: Maps work items of the external projects between both environments.
    external_projects_mapping = map_cross_project_work_items(
        SOURCE_ORGANIZATION, SOURCE_AUTHENTICATION_HEADER,
        TARGET_ORGANIZATION, TARGET_AUTHENTICATION_HEADER,
        cross_project_relations
    )
    
    # Step 4: Recreates the links in the target environment.
    print("\n" + "\033[1m-\033[0m" * 50)
    print("[INFO] Starting cross-project link recreation...")
    
    # Processes each source work item that has cross-project relationships.
    for source_work_item_id, relations in cross_project_relations.items():
        '''
        {
            '11523': [  # source_work_item_id
                {
                    'target_work_item_id': 11168,
                    'target_project': 'System Requirements', 
                    'relation_type': 'System.LinkTypes.Related'
                }
            ]
        }
        '''
        # Gets the equivalent source work item ID in the target environment.
        # 11523 → 4577 in the target environment.
        target_source_work_item_id = source_project_mapping.get(int(source_work_item_id))
        
        if not target_source_work_item_id:
            print(f"\033[1;38;5;214m[WARNING] No mapping found in the target environment for source work item {source_work_item_id}. Skipping...\033[0m")
            results['skipped'] += len(relations)
            continue
        
        print(f"\n[INFO] Processing work item {source_work_item_id} → {target_source_work_item_id}...")
        
        # Processes each cross-project relationship for the current work item.
        for relation in relations:
            source_target_work_item_id = relation['target_work_item_id'] # The external work item being linked to in the source environment.
            target_project = relation['target_project']
            relation_type = relation['relation_type']
            
            if target_project in external_projects_mapping:
                # Gets the equivalent target work item ID in the target environment.
                # 11168 → 1380 in the target environment.
                target_target_work_item_id = external_projects_mapping[target_project].get(source_target_work_item_id)
                
                if target_target_work_item_id:
                    # Creates the formal relationship (Azure DevOps automatically handles creating the reverse relationship).
                    success, message = create_work_item_link(
                        TARGET_ORGANIZATION,
                        TARGET_AUTHENTICATION_HEADER,
                        target_source_work_item_id,
                        target_target_work_item_id,
                        relation_type
                    )
                    
                    if message == "Link already exists":
                        results['skipped'] += 1
                        print(f"\033[1;33m[INFO] Link already exists: {target_source_work_item_id} ↔ {target_target_work_item_id} ({relation_type})\033[0m")
                    
                    elif success:
                        results['success'] += 1
                        print(f"\033[1;32m[SUCCESS] Created bidirectional link: {target_source_work_item_id} ↔ {target_target_work_item_id} ({relation_type})\033[0m")
                        
                        # Adds a reference comment only to the source work item in the target environment.
                        comment_success, comment_message = add_reference_update_comment(
                            TARGET_ORGANIZATION,
                            TARGET_AUTHENTICATION_HEADER,
                            target_source_work_item_id,
                            source_target_work_item_id,
                            target_target_work_item_id
                        )
                        
                        if comment_success:
                            results['comment_updates'] += 1
                            print(f"\033[1;36m[INFO] '{comment_message}' for work item {target_source_work_item_id}.\033[0m")

                        else:
                            results['comment_failures'] += 1
                            print(f"\033[1;31m[WARNING] Failed to add comment to work item {target_source_work_item_id}: '{comment_message}'\033[0m")
                            
                    else:
                        results['failed'] += 1
                        print(f"\033[1;31m[ERROR] Failed to create link: {target_source_work_item_id} → {target_target_work_item_id} ({relation_type}): {message}\033[0m")
                        
                else:
                    print(f"\033[1;38;5;214m[WARNING] No target mapping found for external work item {source_target_work_item_id} in project '{target_project}' in the target environment. Skipping...\033[0m")
                    results['skipped'] += 1
                    
            else:
                print(f"\033[1;38;5;214m[WARNING] No mapping found for external project '{target_project}' in the target environment. Skipping...\033[0m")
                results['skipped'] += 1
    
    print("\n" + "\033[1m=\033[0m" * 100)
    print("\033[1mCROSS-PROJECT LINK RECREATION SUMMARY\033[0m")
    print("\033[1m=\033[0m" * 100)
    
    print(f"• Total links successfully created: {results['success']}")
    print(f"• Total links failed to be created: {results['failed']}")
    print(f"• Total links skipped: {results['skipped']}")
    print(f"• Reference comments added: {results['comment_updates']}")
    print(f"• Comment failures: {results['comment_failures']}")
    
    return results

if __name__ == "__main__":
    recreate_cross_project_links()