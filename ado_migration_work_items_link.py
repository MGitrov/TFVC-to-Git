import os
import requests
import base64


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
    
    # If repository_info is not provided, discover repositories
    if not repository_info:
        # Check if project has TFVC
        tfvc_url = f"{organization}/{project_name}/_apis/tfvc/changesets?$top=1&api-version={api_version}"
        try:
            tfvc_response = requests.get(tfvc_url, headers=authentication_header)
            has_tfvc = tfvc_response.status_code == 200 and len(tfvc_response.json().get("value", [])) > 0
        except:
            has_tfvc = False
        
        # Get Git repositories
        git_repos = []
        git_url = f"{organization}/{project_name}/_apis/git/repositories?api-version={api_version}"
        try:
            git_response = requests.get(git_url, headers=authentication_header)
            if git_response.status_code == 200:
                git_repos = git_response.json().get("value", [])
        except:
            git_repos = []
        
        # Process TFVC if present
        if has_tfvc:
            print(f"[INFO] Detected TFVC in project. Fetching TFVC objects...")
            result['tfvc']['changesets'] = get_tfvc_changesets(organization, project_name, authentication_header, from_date, to_date)
        
        # Process Git repositories
        for repo in git_repos:
            repo_id = repo.get("id")
            repo_name = repo.get("name", repo_id)
            print(f"[INFO] Processing Git repository: {repo_name} (ID: {repo_id})")
            
            # Fetch Git objects
            result['git']['commits'].extend(get_git_commits(organization, project_name, authentication_header, repo_id, from_date, to_date))
            result['git']['pullrequests'].extend(get_git_pullrequests(organization, project_name, authentication_header, repo_id))
            result['git']['branches'].extend(get_git_branches(organization, project_name, authentication_header, repo_id))
    
    else:
        repository_type = repository_info.get('type', '').lower()
        repository_id = repository_info.get('id')
        
        if repository_type == 'tfvc':
            print(f"[INFO] Fetching TFVC codebase objects...")
            result['tfvc']['changesets'] = get_tfvc_changesets(organization, project_name, authentication_header)
        
        elif repository_type == 'git' and repository_id:
            print(f"[INFO] Fetching Git codebase objects for repository id '{repository_id}'...")
            result['git']['commits'] = get_git_commits(organization, project_name, authentication_header, repository_id)
            result['git']['pullrequests'] = get_git_pullrequests(organization, project_name, authentication_header, repo_id)
            result['git']['branches'] = get_git_branches(organization, project_name, authentication_header, repo_id)
        
        else:
            print(f"[ERROR] Invalid repository_info provided. Must include 'type' ('tfvc' or 'git') and 'id' for Git repositories.")
    
    # Count totals for logging
    git_total = len(result['git']['commits']) + len(result['git']['pullrequests']) + len(result['git']['branches'])
    tfvc_total = len(result['tfvc']['changesets'])
    
    print(f"[INFO] Retrieved a total of {git_total + tfvc_total} codebase objects:")
    print(f"  - Git: {git_total} objects ({len(result['git']['commits'])} commits, {len(result['git']['pullrequests'])} PRs, {len(result['git']['branches'])} branches)")
    print(f"  - TFVC: {tfvc_total} changesets")
    
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

def get_git_repo_id(organization, project, authentication_header, repository_name):
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

    #get_work_items(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    #get_tfvc_changesets(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    #get_git_commits(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, get_git_repo_id(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, "dmy_rpstry"))
    #get_git_pullrequests(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, get_git_repo_id(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, "dmy_rpstry"))
    get_git_branches(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, get_git_repo_id(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, "Dumbo"))