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
    
    #print("##############################")
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
                    #print(f"\n{batch_items}\n")
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
    print(f"\n[INFO] Fetching codebase objects from '{project_name}' in '{organization}'...")
    
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

    print(f"\n[INFO] Fetching TFVC changesets from '{project_name}' in '{organization}'...")
    
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

def get_git_repositories(organization, project_name, authentication_header):
    """
    This function fetches all Git repositories of a project.
    """
    api_version = "7.1"
    url = f"{organization}/{project_name}/_apis/git/repositories?api-version={api_version}"
    
    print(f"\n[INFO] Fetching Git repositories from '{project_name}' in '{organization}'...")
    
    try:
        response = requests.get(url, headers=authentication_header)
        #print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            repositories = response.json().get("value", [])
            print(f"[INFO] Found {len(repositories)} Git repositories.")
            
            if repositories:
                print("-" * 50)  # Visual separator
                for repo in repositories:
                    repo_name = repo.get("name", "Unknown Name")
                    repo_id = repo.get("id", "Unknown ID")
                    print(f"Name: {repo_name}")
                    print(f"ID: {repo_id}")
                    print("-" * 50)  # Visual separator
            
            return repositories
            
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch Git repositories.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR][ERROR] An error occurred while fetching Git repositories: {e}\033[0m")
        return []

def get_git_commits(organization, project_name, authentication_header, repository_id):
    """
    This function fetches all commits of a Git repository.
    """
    api_version = "7.1"
    url = f"{organization}/{project_name}/_apis/git/repositories/{repository_id}/commits?api-version={api_version}"

    print(f"\n[INFO] Fetching Git commits from repository id '{repository_id}'...")
    
    try:
        response = requests.get(url, headers=authentication_header)
        #print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
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

    print(f"\n[INFO] Fetching Git pull requests from repository id '{repository_id}'...")

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

    print(f"\n[INFO] Fetching Git branches from repository id '{repository_id}'...")
    
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

def map_objects(source_organization, source_project, source_authentication_header,
                              target_organization, target_project, target_authentication_header):
    """
    Builds comprehensive mapping between source and target objects.
    """
    mapping = {
        'work_items': {},
        'git_repositories': {},
        'git_commits': {},
        'git_branches': {},
        'git_pullrequests': {},
        'tfvc_changesets': {}
    }
    
    # Step 1: Maps work items by their title and type.
    work_items_mapping = map_work_items(
        source_organization, source_project, source_authentication_header,
        target_organization, target_project, target_authentication_header
    )

    mapping['work_items'] = work_items_mapping['work_items']
    
    # Step 2: Maps Git repositories by their name.
    source_repositories = get_git_repositories(source_organization, source_project, source_authentication_header)
    target_repositories = get_git_repositories(target_organization, target_project, target_authentication_header)
    
    for source_repository in source_repositories:
        source_id = source_repository.get('id')
        source_name = source_repository.get('name')
        
        for target_repository in target_repositories:
            if target_repository.get('name') == source_name:
                mapping['git_repositories'][source_id] = target_repository.get('id')
                break
    
    # Step 3: For each mapped repository, maps commits, branches, and pull requests.
    for source_repository_id, target_repository_id in mapping['git_repositories'].items():
        # Step 3.1: Maps Git commits by their hash value.
        source_commits = get_git_commits(source_organization, source_project, source_authentication_header, source_repository_id)
        target_commits = get_git_commits(target_organization, target_project, target_authentication_header, target_repository_id)
        
        for source_commit in source_commits:
            source_hash = source_commit.get('commitId')
            for target_commit in target_commits:
                target_hash = target_commit.get('commitId')
                if source_hash == target_hash:
                    mapping['git_commits'][source_hash] = target_hash
                    break
        
        # Step 3.2: Maps Git branches by their name.
        source_branches = get_git_branches(source_organization, source_project, source_authentication_header, source_repository_id)
        target_branches = get_git_branches(target_organization, target_project, target_authentication_header, target_repository_id)
        
        for source_branch in source_branches:
            source_name = source_branch.get('name', '').replace('refs/heads/', '')
            source_id = source_branch.get('objectId')
            
            for target_branch in target_branches:
                target_name = target_branch.get('name', '').replace('refs/heads/', '')
                target_id = target_branch.get('objectId')
                
                if source_name == target_name:
                    mapping['git_branches'][source_id] = target_id
                    break
        
        # Step 3.3: Maps Git pull requests by their title and associated work items.
        source_prs = get_git_pullrequests(source_organization, source_project, source_authentication_header, source_repository_id)
        target_prs = get_git_pullrequests(target_organization, target_project, target_authentication_header, target_repository_id)
        '''
        pr_mapping = map_pull_requests(source_prs, target_prs, mapping['work_items'])
        mapping['git_pullrequests'].update(pr_mapping)
        '''

    # Step 4: Maps TFVC changesets by their ID.
    tfvc_changesets_mapping = map_tfvc_changesets(
        source_organization, source_project, source_authentication_header,
        target_organization, target_project, target_authentication_header
    )

    mapping['tfvc_changesets'].update(tfvc_changesets_mapping)
    
    return mapping

def map_work_items(source_organization, source_project, source_authentication_header,
                          target_organization, target_project, target_authentication_header):
    """
    This function maps work items between source and target environments using title and type.
    """
    work_items_mapping = {'work_items': {}}
    
    print("[INFO] Mapping work items...")
    
    source_work_items = get_work_items(source_organization, source_project, source_authentication_header)
    target_work_items = get_work_items(target_organization, target_project, target_authentication_header)
    
    # Creates a lookup dictionary for faster matching.
    target_lookup = {}

    for work_item in target_work_items:
        item_id = work_item.get('id')
        item_title = work_item.get('fields', {}).get('System.Title', '')
        item_type = work_item.get('fields', {}).get('System.WorkItemType', '')
        
        # Creates a key of type + title as the mapping is done using title and type.
        composite_key = f"{item_type}|{item_title}"
        target_lookup[composite_key] = item_id
    
    matches = 0

    # Maps source work items to target work items.
    for work_item in source_work_items:
        source_id = work_item.get('id')
        item_title = work_item.get('fields', {}).get('System.Title', '')
        item_type = work_item.get('fields', {}).get('System.WorkItemType', '')
        
        composite_key = f"{item_type}|{item_title}"
        
        if composite_key in target_lookup:
            target_id = target_lookup[composite_key]
            work_items_mapping['work_items'][source_id] = target_id
            matches += 1
            print(f"[INFO] Mapped '{item_type}: {item_title}' ({source_id} → {target_id})")
    
    print(f"\n[INFO] Mapped {matches} out of {len(source_work_items)} work items.")
    
    return work_items_mapping

def map_pull_requests(source_prs, target_prs, work_item_mapping):
    """
    This function maps pull requests between source and target environments using title and associated work items.

    First Pass: Title-Based Matching
        For each source pull request:
            • The function extracts its id and title.
            • The function checks for target pull request(s) with exactly the same title.
            • There are three possible outcomes:
                1. No matches: The pull request cannot be mapped.
                2. One match: The pull request has a unique, reliable mapping.
                3. Multiple matches: The pull request has multiple potential mappings, requiring further investigation.

        If there is exactly one match by title, it is immediately mapped since it is likely correct.
        If there are multiple target pull requests with the same title, they are stored them "potential matches" for the second pass.

    Second Pass: Work Item-Based Matching
        For each ambiguous source pull request:
            • The function retrieves its associated work items.
            • The function checks for target pull request(s) with the same associated work items.
            • The function selects the target pull request with the most matching work items.

        If there is a clear winner with the highest match score, that mapping is created.
    """
    pr_mapping = {}
    
    # First pass: Maps by pull request's title.
    title_matches = {}

    for source_pr in source_prs:
        source_id = source_pr.get('pullRequestId')
        source_title = source_pr.get('title', '')
        
        matches = []

        for target_pr in target_prs:
            target_id = target_pr.get('pullRequestId')
            target_title = target_pr.get('title', '')
            
            if source_title == target_title:
                matches.append(target_id)
        
        # Checks for a unique match.
        if len(matches) == 1:
            pr_mapping[source_id] = matches[0]

        elif len(matches) > 1:
            title_matches[source_id] = matches
    
    # Second pass: Uses associated work items to resolve ambiguities.
    for source_id, potential_targets in title_matches.items():
        source_pr = next((pr for pr in source_prs if pr.get('pullRequestId') == source_id), None)

        if not source_pr:
            continue
        
        # Get associated work items for source PR
        source_work_items = get_work_items_for_pr(source_id)
        source_mapped_work_items = set()
        
        for work_item_id in source_work_items:
            if work_item_id in work_item_mapping:
                source_mapped_work_items.add(work_item_mapping[work_item_id])
        
        # Find best match among potential targets
        best_match = None
        best_match_score = 0
        
        for target_id in potential_targets:
            target_work_items = get_work_items_for_pr(target_id)
            match_score = len(source_mapped_work_items.intersection(target_work_items))
            
            if match_score > best_match_score:
                best_match = target_id
                best_match_score = match_score
        
        if best_match:
            pr_mapping[source_id] = best_match
    
    return pr_mapping

def map_tfvc_changesets(source_organization, source_project, source_authentication_header,
                               target_organization, target_project, target_authentication_header):
    """
    This function maps TFVC changesets between source and target environments by examining changeset's comment.
    """
    tfvc_changesets_mapping = {}
    multiple_mappings_count = 0
    
    print("[INFO] Mapping TFVC changesets...")
    
    source_changesets = get_tfvc_changesets(source_organization, source_project, source_authentication_header)
    target_changesets = get_tfvc_changesets(target_organization, target_project, target_authentication_header)
    
    # regex patterns to extract source changeset IDs from target comments.
    patterns = [
        r"Migrated from changeset no\. (\d+)",
        r"Migrated changeset no\. (\d+)"
    ]
    
    # Compiles the regex patterns for improved and efficient performance.
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    # Sorts the list of target changesets by their changeset ID to ensure they're processed in chronological order from oldest to newest.
    sorted_target_changesets = sorted(target_changesets, key=lambda cs: cs.get('changesetId', 0))
    
    for target_cs in sorted_target_changesets:
        target_id = target_cs.get('changesetId')
        target_comment = target_cs.get('comment', '')
        
        for pattern in compiled_patterns:
            match = pattern.search(target_comment)

            if match:
                source_id = int(match.group(1))
                
                # Because of a possible case(s) of multiple mappings, the function checks if the source ID is already mapped to a target ID.
                # If it is, it will map the source ID to the most recent target ID.
                if source_id in tfvc_changesets_mapping:
                    multiple_mappings_count += 1
                    print(f"[INFO] Source changeset {source_id} is currently mapped to target changeset {tfvc_changesets_mapping[source_id]}, "
                          f"but will be remapped to a more recent target changeset {target_id}.")
                
                tfvc_changesets_mapping[source_id] = target_id
                break
    
    total_source = len(source_changesets)
    total_mapped = len(tfvc_changesets_mapping)
    
    print(f"\n[INFO] Mapped {total_mapped} out of {total_source} TFVC changesets.")
    print(f"[INFO] {multiple_mappings_count} source TFVC changeset(s) had multiple target mappings (used most recent).")

    return tfvc_changesets_mapping

def link_work_items(target_organization, target_project, target_authentication_header, work_items_links, objects_mapping):
    """
    This function replicates links between work items and codebase objects from source environment to target environment.
    """
    print("\n" + "\033[1m=\033[0m" * 100)
    print("\033[1mSTARTING WORK ITEMS-CODEBASE OBJECTS LINKS RECREATION PROCESS\033[0m")
    print("\033[1m=\033[0m" * 100)
    
    results = {
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'details': {}
    }
    
    # Prepare mapping dictionaries
    work_item_id_map = {}

    if objects_mapping and 'work_items' in objects_mapping:
        work_item_id_map = objects_mapping['work_items']
    
    '''{
        '123': [
          {'type': 'git_commit', 'url': 'vstfs:///Git/Commit/...', 'name': 'Fixed in Commit'},
          {'type': 'tfvc_changeset', 'url': 'vstfs:///VersionControl/Changeset/42', 'name': 'Fixed in Changeset'}
        ],
        ...
      }'''

    # Process each work item and its codebase links
    for source_work_item_id, codebase_links in work_items_links.items():
        target_work_item_id = work_item_id_map.get(int(source_work_item_id)) # Translates the source work item ID to the target work item ID.
        
        if not target_work_item_id:
            print(f"[WARNING] No target ID mapping found for work item {source_work_item_id}. Skipping...")
            results['skipped'] += len(codebase_links)
            continue
        
        print(f"[INFO] Processing links for work item {source_work_item_id} → {target_work_item_id}")
        
        # Track results for this work item
        item_results = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'links': []
        }
        
        # Process each codebase link
        for link in codebase_links:
            print(f"\n{link}\n")
            print(f"\n{objects_mapping}\n")
            link_type = link.get('type')
            link_name = link.get('name')
            source_url = link.get('url')
            
            # Map the codebase reference to target system
            target_reference = create_target_reference_url(link, objects_mapping)
            
            if not target_reference:
                print(f"[WARNING] Could not map codebase reference for {link_type}. Skipping...")
                item_results['skipped'] += 1
                continue
            
            # Create the link in the target system
            success, message = create_link(
                target_organization, 
                target_project, 
                target_authentication_header, 
                target_work_item_id, 
                target_reference,
                link_name
            )
            
            # Track the result
            if success:
                item_results['success'] += 1
                print(f"[INFO] Successfully created {link_type} link for work item {target_work_item_id}")
            else:
                item_results['failed'] += 1
                print(f"[ERROR] Failed to create {link_type} link for work item {target_work_item_id}: {message}")
            
            # Record details
            item_results['links'].append({
                'type': link_type,
                'name': link_name,
                'source_url': source_url,
                'target_reference': target_reference,
                'success': success,
                'message': message
            })
        
        # Update overall results
        results['success'] += item_results['success']
        results['failed'] += item_results['failed']
        results['skipped'] += item_results['skipped']
        results['details'][target_work_item_id] = item_results
        
        # Log summary for this work item
        print(f"[INFO] Work item {target_work_item_id} link creation summary: "
              f"{item_results['success']} successful, "
              f"{item_results['failed']} failed, "
              f"{item_results['skipped']} skipped")
    
    # Log overall summary
    print(f"[INFO] Overall link creation summary: "
          f"{results['success']} successful, "
          f"{results['failed']} failed, "
          f"{results['skipped']} skipped")
    
    return results

def create_target_reference_url(link, id_mapping):
    """
    This function translates a source codebase object link into the corresponding reference URL in the target environment.
    """
    if not id_mapping:
        print(f"\033[1;38;5;214m[WARNING] No ID mapping provided for codebase objects.\033[0m")
        return None
    
    project_id = get_project_id(TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER)
    link_type = link.get('type')
    link_id = link.get('id')
    
    if link_type == 'git_commit':
        if 'git_commits' in id_mapping and link_id in id_mapping['git_commits']: # Checks the key (which is the source commit hash) in the mapping dict.
            target_commit = id_mapping['git_commits'][link_id]
            
            source_repo_id = link.get('repository_id')

            if not source_repo_id:
                print(f"\033[1;38;5;214m[WARNING] No repository ID found for Git commit '{link_id}'.\033[0m")
                return None
                
            target_repo_id = id_mapping.get('git_repositories', {}).get(source_repo_id) # Translates the source repository ID to the target repository ID.
            
            if target_repo_id and target_commit:
                return f"vstfs:///Git/Commit/{project_id}%2F{target_repo_id}%2F{target_commit}"
            
            else:
                print(f"\033[1;38;5;214m[WARNING] No target repository found for Git commit '{link_id}'.\033[0m")
                return None
            
        else:
            print(f"\033[1;38;5;214m[WARNING] No mapping found for Git commit '{link_id}'.\033[0m")
            return None
            
    elif link_type == 'git_pullrequest':
        if 'git_pullrequests' in id_mapping and link_id in id_mapping['git_pullrequests']:
            target_pr_id = id_mapping['git_pullrequests'][link_id]
            
            source_repo_id = link.get('repository_id')

            if not source_repo_id:
                print(f"\033[1;38;5;214m[WARNING] No repository ID found for Git pull request '{link_id}'.\033[0m")
                return None
                
            target_repo_id = id_mapping.get('git_repositories', {}).get(source_repo_id)
            
            if target_repo_id and target_pr_id:
                return f"vstfs:///Git/PullRequestId/{target_repo_id}%2F{target_pr_id}"
            
            else:
                print(f"\033[1;38;5;214m[WARNING] No target repository found for Git pull request '{link_id}'.\033[0m")
                return None
            
        else:
            print(f"\033[1;38;5;214m[WARNING] No mapping found for Git pull request '{link_id}'.\033[0m")
            return None
            
    elif link_type == 'git_branch':
        if 'git_branches' in id_mapping and link_id in id_mapping['git_branches']:
            target_branch = id_mapping['git_branches'][link_id]
            
            source_repo_id = link.get('repository_id')

            if not source_repo_id:
                print(f"\033[1;38;5;214m[WARNING] No repository ID found for Git branch '{link_id}'.\033[0m")
                return None
                
            target_repo_id = id_mapping.get('git_repositories', {}).get(source_repo_id)
            
            if target_repo_id and target_branch:
                return f"vstfs:///Git/Ref/{target_repo_id}%2FGB{target_branch}"
            
            else:
                print(f"\033[1;38;5;214m[WARNING] No target repository found for Git branch '{link_id}'.\033[0m")
                return None
            
        else:
            print(f"\033[1;38;5;214m[WARNING] No mapping found for Git branch '{link_id}'.\033[0m")
            return None

    elif link_type == 'tfvc_changeset':
        if 'tfvc_changesets' in id_mapping and int(link_id) in id_mapping['tfvc_changesets']:
            target_changeset_id = id_mapping['tfvc_changesets'][int(link_id)]
            return f"vstfs:///VersionControl/Changeset/{target_changeset_id}"
        
        else:
            print(f"\033[1;38;5;214m[WARNING] A TFVC changeset link type was detected, but no mapping found for source TFVC changeset {link_id}.\033[0m")
            return None

    else:
        print(f"\n\033[1;38;5;214m[WARNING] '{link_type}' is an unsupported link type.\033[0m")
        print(f"[INFO] Supported link types are:")
        print(f"    • Commits (for Git)")
        print(f"    • Pull Requests (for Git)")
        print(f"    • Branches (for Git)")
        print(f"    • Changesets (for TFVC)")
        return None

def create_link(organization, project_name, authentication_header, work_item_id, reference_url, link_name):
    """
    This function creates a link between a work item and a codebase object.
    
    Returns:
    • Tuple (success\fail, message)
    """
    api_version = "7.1"
    url = f"{organization}/{project_name}/_apis/wit/workitems/{work_item_id}?api-version={api_version}"
    
    payload = [
        {
            "op": "add",
            "path": "/relations/-", # Appends to the 'relations' array.
            "value": {
                "rel": "ArtifactLink",
                "url": reference_url,
                "attributes": {
                    "name": link_name
                }
            }
        }
    ]
    
    headers = {
        **authentication_header,
        "Content-Type": "application/json-patch+json" # A required content type for PATCH operations using Azure DevOps' REST API.
    }
    
    try:
        response = requests.patch(url, headers=headers, json=payload)
        
        if response.status_code in (200, 201):
            return True, "[SUCCESS] Link created successfully"
        
        else:
            return False, f"[ERROR] {response.status_code}: {response.text}"
            
    except requests.exceptions.RequestException as e:
        return False, f"[ERROR]: {str(e)}"

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
    os.system('cls' if os.name == 'nt' else 'clear')
    ascii_art = pyfiglet.figlet_format("by codewizard", font="ogre")
    print(ascii_art)

    #target_work_items = get_work_items(TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER)
    source_work_items = get_work_items(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    #get_tfvc_changesets(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    #get_git_commits(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, get_git_repo_id(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, "dmy_rpstry"))
    #get_git_pullrequests(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, get_git_repo_id(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, "dmy_rpstry"))
    #get_git_branches(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, get_git_repo_id(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, "Dumbo"))
    #codebase_objects = get_codebase_objects(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    work_items_refs = extract_work_item_references(source_work_items)

    mapping = map_objects(
        SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER,
        TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER
    )

    link_work_items(TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER, work_items_refs, mapping)

    # Source: 'vstfs:///Git/Commit/462c3573-8a19-42e7-9165-87e99091bcc9%2Fd085fadf-9718-4d8c-8d3c-da4573763f72%2Fe55922615c66c4ec4a853e67e1327eed37e93c2e'
    # Target: 'vstfs:///Git/Commit/681f7e98-32f1-4e9c-9ccd-db9ef45622ee%2Fe55922615c66c4ec4a853e67e1327eed37e93c2e'