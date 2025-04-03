import os
import requests
import base64
import json

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
        print(f"\033[1;31m[ERROR] An error occurred while fetching Git repositories: {e}\033[0m")
        return []
    
def get_git_pull_requests(organization, project_name, authentication_header, repository_id):
    """
    This function fetches all pull requests of a Git repository.
    """
    api_version = "7.1"
    url = f"{organization}/{project_name}/_apis/git/repositories/{repository_id}/pullrequests?api-version={api_version}&searchCriteria.status=all"

    print(f"\n[INFO] Fetching Git pull requests from repository ID '{repository_id}'...")

    try:
        response = requests.get(url, headers=authentication_header)
        #print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
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

def get_pull_request_details(organization, project_name, repository_id, pull_request_id, authentication_header):
    """
    This function fetches detailed information about a pull request.
    """
    api_version = "7.1"
    url = f"{organization}/{project_name}/_apis/git/repositories/{repository_id}/pullrequests/{pull_request_id}?api-version={api_version}"
    
    print(f"\n[INFO] Fetching details for pull request ID '{pull_request_id}'...")
    
    try:
        response = requests.get(url, headers=authentication_header)
        
        if response.status_code == 200:
            pr_details = response.json()
            print(f"[INFO] Successfully retrieved details for pull request {pull_request_id}: {pr_details.get('title', 'No Title')}.")
            print(f"\n[DEBUG] Raw Configuration:\n{json.dumps(pr_details, indent=4)}\n")  # Prettified JSON for better readability.
            return pr_details
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch pull request details for pull request ID {pull_request_id}.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching pull request details: {e}\033[0m")
        return None

def get_pull_request_threads(organization, project_name, repository_id, pull_request_id, authentication_header):
    """
    This function fetches all comment threads of a pull request.
    """
    api_version = "7.1"
    url = f"{organization}/{project_name}/_apis/git/repositories/{repository_id}/pullrequests/{pull_request_id}/threads?api-version={api_version}"
    
    print(f"\n[INFO] Fetching comment threads for pull request {pull_request_id}...")
    
    try:
        response = requests.get(url, headers=authentication_header)
        
        if response.status_code == 200:
            comment_threads = response.json().get("value", [])
            print(f"[INFO] Found {len(comment_threads)} comment thread(s) for pull request ID {pull_request_id}.")
            return comment_threads
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch comment threads for pull request ID {pull_request_id}.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching pull request comment threads: {e}\033[0m")
        return None

def get_pull_request_commits(organization, project_name, repository_id, pull_request_id, authentication_header):
    """
    This function fetches all commits of a pull request.
    """
    api_version = "7.1"
    url = f"{organization}/{project_name}/_apis/git/repositories/{repository_id}/pullrequests/{pull_request_id}/commits?api-version={api_version}"
    
    print(f"\n[INFO] Fetching commits for pull request {pull_request_id}...")
    
    try:
        response = requests.get(url, headers=authentication_header)
        
        if response.status_code == 200:
            commits = response.json().get("value", [])
            print(f"[INFO] Found {len(commits)} commit(s) for pull request ID {pull_request_id}.")
            return commits
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch pull request commits for pull request ID {pull_request_id}.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching pull request commits: {e}\033[0m")
        return None

def get_pull_request_iterations(organization, project_name, repository_id, pull_request_id, authentication_header):
    """
    This function fetches all iterations (updates) of a pull request.
    """
    api_version = "7.1"
    url = f"{organization}/{project_name}/_apis/git/repositories/{repository_id}/pullrequests/{pull_request_id}/iterations?api-version={api_version}"
    
    print(f"\n[INFO] Fetching iterations for pull request {pull_request_id}...")
    
    try:
        response = requests.get(url, headers=authentication_header)
        
        if response.status_code == 200:
            iterations = response.json().get("value", [])
            print(f"[INFO] Found {len(iterations)} iteration(s) for pull request ID {pull_request_id}.")
            return iterations
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch pull request iterations for pull request ID {pull_request_id}.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching pull request iterations: {e}\033[0m")
        return None
    
def get_pull_request_changes(organization, project_name, repository_id, pull_request_id, pull_request_iterations, authentication_header):
    """
    This function fetches all file changes of all pull request iterations.
    """
    # A dictionary to store the latest change for each file path.
    latest_changes_by_path = {}

    # Sort iterations by their ID to process them chronologically.
    sorted_iterations = sorted(pull_request_iterations, key=lambda x: x.get("id", 0))

    for iteration in sorted_iterations:
        iteration_id = iteration.get("id", 0)
        iteration_changes = get_pull_request_iteration_changes(organization, project_name, repository_id, pull_request_id, iteration_id, authentication_header)
        
        # Updates the latest change for each file path.
        for change in iteration_changes:
            file_path = change.get("item", {}).get("path", "")

            if file_path:
                latest_changes_by_path[file_path] = change

    all_changes = list(latest_changes_by_path.values())
    return all_changes

def get_pull_request_iteration_changes(organization, project_name, repository_id, pull_request_id, iteration_id, authentication_header):
    """
    This function fetches all file changes of a pull request iteration.
    """
    api_version = "7.1"
    url = f"{organization}/{project_name}/_apis/git/repositories/{repository_id}/pullrequests/{pull_request_id}/iterations/{iteration_id}/changes?api-version={api_version}"
    
    print(f"\n[INFO] Fetching changes for pull request {pull_request_id}, iteration {iteration_id}...")
    
    try:
        response = requests.get(url, headers=authentication_header)
        
        if response.status_code == 200:
            changes = response.json().get("changes", [])
            #print(f"\n{changes}\n")
            print(f"[INFO] Found {len(changes)} file change(s) for pull request ID {pull_request_id}, iteration ID {iteration_id}.")
            return changes
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch file changes for pull request ID {pull_request_id}, iteration ID {iteration_id}.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching pull request iteration changes: {e}\033[0m")
        return None

def get_git_repo_id(organization, project, repository, authentication_header): # TEMP FUNCTION.
    """
    Retrieves the repository ID of a Git repository in Azure DevOps.

    :param organization: Azure DevOps organization name
    :param project: Azure DevOps project name
    :param repository: Name of the Git repository
    :param pat: Personal Access Token (PAT) for authentication
    :return: Repository ID (string) if found, otherwise None
    """
    url = f"{organization}/{project}/_apis/git/repositories/{repository}?api-version=7.1-preview.1"
    
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

    source_repository_id = get_git_repo_id(SOURCE_ORGANIZATION, SOURCE_PROJECT, "dmy_rpstry", SOURCE_AUTHENTICATION_HEADER)
    source_pull_requests = get_git_pull_requests(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, source_repository_id)

    for pull_request in source_pull_requests:
        #print(f"\n{pull_request}\n")
        pr_id = pull_request.get('pullRequestId')
        #get_pull_request_details(SOURCE_ORGANIZATION, SOURCE_PROJECT, source_repository_id, pr_id, SOURCE_AUTHENTICATION_HEADER)
        #get_pull_request_threads(SOURCE_ORGANIZATION, SOURCE_PROJECT, source_repository_id, pr_id, SOURCE_AUTHENTICATION_HEADER)
        #get_pull_request_commits(SOURCE_ORGANIZATION, SOURCE_PROJECT, source_repository_id, pr_id, SOURCE_AUTHENTICATION_HEADER)
        pr_iterations = get_pull_request_iterations(SOURCE_ORGANIZATION, SOURCE_PROJECT, source_repository_id, pr_id, SOURCE_AUTHENTICATION_HEADER)
        get_pull_request_changes(SOURCE_ORGANIZATION, SOURCE_PROJECT, source_repository_id, pr_id, pr_iterations, SOURCE_AUTHENTICATION_HEADER)