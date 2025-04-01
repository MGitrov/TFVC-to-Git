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

def get_work_items(organization, project_name, authentication_header, work_item_ids=None):
    """
    This function fetches all work items of a project.
    """
    api_version = "7.1"
    
    #print("##############################")
    print(f"[INFO] Fetching work items from '{project_name}' in '{organization}'...")
    
    try:
        if work_item_ids:
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
                    print(f"[INFO] Retrieved {len(batch_items)} work items in batch.")

                else:
                    print(f"\033[1;31m[ERROR] Failed to fetch work items batch from '{project_name}' project.\033[0m")
                    print(f"[DEBUG] Request's Status Code: {response.status_code}")
                    print(f"[DEBUG] Response Body: {response.text}")
            
            print(f"[INFO] Successfully retrieved {len(work_items)} work items.")
            return work_items
            
        else:
            wiql_url = f"{organization}/{project_name}/_apis/wit/wiql?api-version={api_version}"
            wiql_query = {
                "query": "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project AND [System.WorkItemType] NOT IN ('Test Case', 'Test Suite', 'Test Plan','Shared Steps','Shared Parameter','Feedback Request') ORDER BY [System.Id]"
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

def get_codebase_objects(organization, project_name, authentication_header, repository_info=None):
    """
    This function fetches all codebase objects of a repository.
    
    Codebase objects handled by this function are:
    • Changesets (for TFVC).
    • Commits (for Git).
    • Pull Requests (for Git).
    • Branches (for Git).

    Returns:
    • Dictionary with categories of codebase objects:
        {
            'git': {
                'commits': [...],
                'pull_requests': [...],
                'branches': [...]
            },
            'tfvc': {
                'changesets': [...]
            }
        }
    """
    api_version = "7.1"
    
    print("##############################")
    print(f"[INFO] Fetching all codebase objects from '{project_name}' in '{organization}'...")
    
    # Initializes return structure.
    result = {
        'git': {
            'commits': [],
            'pull_requests': [],
            'branches': []
        },
        'tfvc': {
            'changesets': []
        }
    }
    
    if not repository_info:
        # Checks whether the project contains at least one TFVC-based repository by fetching the latest changeset.
        tfvc_url = f"{organization}/{project_name}/_apis/tfvc/changesets?$top=1&api-version={api_version}"

        try:
            tfvc_response = requests.get(tfvc_url, headers=authentication_header)
            has_tfvc = tfvc_response.status_code == 200 and len(tfvc_response.json().get("value", [])) > 0

        except:
            has_tfvc = False
        
        # Checks for Git repositories.
        git_repos = []
        git_url = f"{organization}/{project_name}/_apis/git/repositories?api-version={api_version}"

        try:
            git_response = requests.get(git_url, headers=authentication_header)

            if git_response.status_code == 200:
                git_repos = git_response.json().get("value", [])

        except:
            git_repos = []
        
        # Has TFVC repositories.
        if has_tfvc:
            print(f"[INFO] A TFVC-based repository was detected, fetching TFVC codebase objects...")
            result['tfvc']['changesets'] = get_tfvc_changesets(organization, project_name, authentication_header)
        
        # Has Git repositories.
        for repo in git_repos:
            repository_id = repo.get("id")
            repository_name = repo.get("name", repository_id)

            print(f"[INFO] Fetching Git codebase objects for repository '{repository_name}' (id: '{repository_id}')...")
            
            result['git']['commits'].extend(get_git_commits(organization, project_name, authentication_header, repository_id))
            result['git']['pull_requests'].extend(get_git_pullrequests(organization, project_name, authentication_header, repository_id))
            result['git']['branches'].extend(get_git_branches(organization, project_name, authentication_header, repository_id))
    
    else:
        repository_type = repository_info.get('type', '').lower()
        repository_id = repository_info.get('id')
        
        if repository_type == 'tfvc':
            print(f"[INFO] Fetching TFVC codebase objects...")
            result['tfvc']['changesets'] = get_tfvc_changesets(organization, project_name, authentication_header)
        
        elif repository_type == 'git' and repository_id:
            print(f"[INFO] Fetching Git codebase objects for repository id '{repository_id}'...")
            result['git']['commits'] = get_git_commits(organization, project_name, authentication_header, repository_id)
            result['git']['pull_requests'] = get_git_pullrequests(organization, project_name, authentication_header, repository_id)
            result['git']['branches'] = get_git_branches(organization, project_name, authentication_header, repository_id)
        
        else:
            print(f"\033[1;31m[ERROR] Invalid repository details; must include 'type' ('tfvc' or 'git') field and 'id' field for Git repositories.\033[0m")
            return None
    
    total_git_objects = len(result['git']['commits']) + len(result['git']['pull_requests']) + len(result['git']['branches'])
    total_tfvc_objects = len(result['tfvc']['changesets'])
    
    print(f"[INFO] Retrieved a total of {total_git_objects + total_tfvc_objects} codebase objects:")
    print(f"  • Git: {len(result['git']['commits'])} commit(s), {len(result['git']['pull_requests'])} pull request(s), {len(result['git']['branches'])} branch(es)")
    print(f"  • TFVC: {total_tfvc_objects} changesets")
    
    return result

def get_tfvc_changesets(organization, project_name, authentication_header):
    """
    This function fetches all changesets of a TFVC repository.
    """
    api_version = "7.1"
    url = f"{organization}/{project_name}/_apis/tfvc/changesets?api-version={api_version}"
    
    try:
        response = requests.get(url, headers=authentication_header)
        #print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            changesets = response.json().get("value", [])
            print(f"[INFO] Found {len(changesets)} TFVC changeset(s).")
            
            # Appends source control type for reference.
            for changeset in changesets:
                changeset["sourceControlType"] = "TFVC"
            
            return changesets
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch TFVC changesets.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching TFVC changesets: {e}\033[0m")
        return []

def get_git_commits(organization, project_name, authentication_header, repository_id):
    """
    This function fetches all commits of a Git repository.
    """
    api_version = "7.1"
    url = f"{organization}/{project_name}/_apis/git/repositories/{repository_id}/commits?api-version={api_version}"
    
    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            commits = response.json().get("value", [])
            print(f"[INFO] Found {len(commits)} Git commit(s) in repository id '{repository_id}'.")
            
            # Appends repository and source control info for reference.
            for commit in commits:
                commit["repositoryId"] = repository_id
                commit["sourceControlType"] = "Git"
            
            return commits
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch Git commits.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching Git commits: {e}\033[0m")
        return []

def get_git_pullrequests(organization, project_name, authentication_header, repository_id):
    """
    This function fetches all pull requests of a Git repository.
    """
    api_version = "7.1"
    url = f"{organization}/{project_name}/_apis/git/repositories/{repository_id}/pullrequests?api-version={api_version}&searchCriteria.status=all"

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            pull_requests = response.json().get("value", [])
            print(f"[INFO] Found {len(pull_requests)} Git pull request(s) in repository id '{repository_id}'.")
            
            # Appends repository and source control info for reference.
            for pr in pull_requests:
                pr["repositoryId"] = repository_id
                pr["sourceControlType"] = "Git"
            
            return pull_requests
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch Git pull requests.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching Git pull requests: {e}\033[0m")
        return []

def get_git_branches(organization, project_name, authentication_header, repository_id):
    """
    This function fetches all branches of a Git repository.
    """
    api_version = "7.1"
    url = f"{organization}/{project_name}/_apis/git/repositories/{repository_id}/refs?api-version={api_version}"
    
    try:
        response = requests.get(url, headers=authentication_header)
        #print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            refs = response.json().get("value", [])
            branches = [ref for ref in refs if ref.get("name", "").startswith("refs/heads/")] # Filters the list to include only branch references, 
            # excluding other types of references like tags (which would start with "refs/tags/") or other reference types.
            print(f"[INFO] Found {len(branches)} Git branch(es) in repository id '{repository_id}'.")
            
            # Appends repository and source control info for reference.
            for branch in branches:
                branch["repositoryId"] = repository_id
                branch["sourceControlType"] = "Git"
                branch["branchName"] = branch.get("name", "").replace("refs/heads/", "") # Extracts branch name without the "refs/heads/" prefix for easier reference.
            
            return branches
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch Git branches.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching Git branches: {e}\033[0m")
        return []

def extract_work_item_references(work_items):
    """
    This function extracts all links between work items and codebase objects.
    
    Codebase objects handled by this function are:
    • Changesets (for TFVC).
    • Commits (for Git).
    • Pull Requests (for Git).
    • Branches (for Git).
    
    Returns:
    • Dictionary mapping work item IDs to linked codebase objects:
      {
        '123': [
          {'type': 'git_commit', 'url': 'vstfs:///Git/Commit/...', 'name': 'Fixed in Commit'},
          {'type': 'tfvc_changeset', 'url': 'vstfs:///VersionControl/Changeset/42', 'name': 'Fixed in Changeset'}
        ],
        ...
      }
    """
    print("##############################")
    print("[INFO] Extracting links between work items and codebase objects...")
    
    # Mapping dictionary.
    work_item_to_codebase = {}
    
    # URL patterns for identifying codebase object types.
    patterns = {
        'git_commit': r'vstfs:///Git/Commit/',
        'git_pullrequest': r'vstfs:///Git/PullRequestId/',
        'git_branch': r'vstfs:///Git/Ref/',
        'tfvc_changeset': r'vstfs:///VersionControl/Changeset/'
    }

    total_work_items = len(work_items)
    total_work_items_with_links = 0
    total_links = 0

    link_types_count = {key: 0 for key in patterns.keys()}
    link_names_count = {}
    
    for work_item in work_items:
        work_item_id = work_item.get('id')

        if not work_item_id:
            continue
        
        # Fetches work item type and title for enhanced logging.
        work_item_type = work_item.get('fields', {}).get('System.WorkItemType', 'Unknown')
        work_item_title = work_item.get('fields', {}).get('System.Title', 'Untitled')

        # The links between work items and codebase objects are stored in the work item's 'relations' array.
        relations = work_item.get('relations', [])
        
        # Filters for 'ArtifactLink' relations. By filtering for 'ArtifactLink' relations, it is specifically targeting the links between work items and codebase objects. 
        # Without filtering, other types of links (like parent-child relationships between work items) would be processed which are not relevant.
        artifact_links = [rel for rel in relations if rel.get('rel') == 'ArtifactLink']
        
        if not artifact_links:
            continue
        
        # Creates an entry for the current processed work item.
        work_item_to_codebase[work_item_id] = []
        work_item_link_count = 0
        
        for link in artifact_links:
            link_url = link.get('url', '')
            link_attributes = link.get('attributes', {})
            link_name = link_attributes.get('name', '')
            
            # Skips if not a codebase object link.
            if not link_name or not any(re.search(pattern, link_url) for pattern in patterns.values()):
                continue
            
            codebase_type = None

            # Checks the link URL against the predefined patterns to determine the type of codebase object.
            for type_key, pattern in patterns.items():
                if re.search(pattern, link_url):
                    codebase_type = type_key
                    break
            
            if codebase_type:
                id_match = None

                if codebase_type == 'tfvc_changeset':
                    id_match = re.search(r'vstfs:///VersionControl/Changeset/(\d+)', link_url) # Extracts changeset id.

                elif codebase_type == 'git_pullrequest':
                    id_match = re.search(r'vstfs:///Git/PullRequestId/.*?%2F(\d+)', link_url) # Extracts pull request id.

                elif codebase_type == 'git_commit':
                    id_match = re.search(r'([0-9a-f]{40})$', link_url) # Extracts the commit hash.

                elif codebase_type == 'git_branch':
                    id_match = re.search(r'GB(.+)$', link_url) # Extracts the branch name after the "GB" prefix.
                
                # Creates link object with all available metadata.
                link_object = {
                    'type': codebase_type,
                    'url': link_url,
                    'name': link_name,
                    'created_date': link_attributes.get('resourceCreatedDate'),
                    'modified_date': link_attributes.get('resourceModifiedDate'),
                    'authorized_date': link_attributes.get('authorizedDate'),
                    'link_id': link_attributes.get('id')
                }
                
                if id_match:
                    link_object['id'] = id_match.group(1)
                
                repository_match = re.search(r'%2F([0-9a-f-]+)%2F', link_url)

                if repository_match:
                    link_object['repository_id'] = repository_match.group(1)
                
                # Assigns the link to the current processed work item.
                work_item_to_codebase[work_item_id].append(link_object)
                
                total_links += 1
                work_item_link_count += 1
                link_types_count[codebase_type] += 1
                link_names_count[link_name] = link_names_count.get(link_name, 0) + 1
                
                print(f"\n[INFO] Work item {work_item_id} ({work_item_type}: {work_item_title}) → Link: {link_name}")
        
        if work_item_link_count > 0:
            total_work_items_with_links += 1
            print(f"[INFO] Found {work_item_link_count} link(s) to codebase objects for work item {work_item_id}")
    
    # Removes work items with no links to codebase objects.
    work_item_to_codebase = {k: v for k, v in work_item_to_codebase.items() if v}
    
    print(f"\n• Total work items processed: {total_work_items}")
    print(f"• Work items with links to codebase objects: {total_work_items_with_links} ({(total_work_items_with_links/total_work_items*100):.2f}% of total work items)")
    print(f"• Total links to codebase objects found: {total_links}")
    
    print("\nBreakdown by codebase object type:")
    print("-"*30)
    for link_type, count in link_types_count.items():
        if count > 0:
            print(f"  {link_type}: {count} ({(count/total_links*100):.2f}% of total codebase objects)")
    
    return work_item_to_codebase

def get_git_repo_id(organization, project, authentication_header, repository_name): # HELPER.
    """
    Retrieves the repository ID of a Git repository in Azure DevOps.

    :param organization: Azure DevOps organization name
    :param project: Azure DevOps project name
    :param repository: Name of the Git repository
    :param pat: Personal Access Token (PAT) for authentication
    :return: Repository ID (string) if found, otherwise None
    """
    url = f"{organization}/{project}/_apis/git/repositories/{repository_name}?api-version=7.1-preview.1"
    
    # Use Basic Authentication with PAT (username is empty)
    response = requests.get(url, headers=authentication_header)
    
    if response.status_code == 200:
        repo_data = response.json()
        return repo_data.get("id")
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    ascii_art = pyfiglet.figlet_format("by codewizard", font="ogre")
    print(ascii_art)

    work_items = get_work_items(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    #get_tfvc_changesets(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    #get_git_commits(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, get_git_repo_id(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, "dmy_rpstry"))
    #get_git_pullrequests(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, get_git_repo_id(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, "dmy_rpstry"))
    #get_git_branches(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, get_git_repo_id(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, "Dumbo"))
    #codebase_objects = get_codebase_objects(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    extract_work_item_references(work_items)