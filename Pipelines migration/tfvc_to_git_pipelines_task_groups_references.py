import os
import base64
import requests
import json
from dotenv import load_dotenv

load_dotenv()

SOURCE_ORGANIZATION=os.getenv("SOURCE_ORGANIZATION")
SOURCE_PROJECT=os.getenv("SOURCE_PROJECT")
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
    api_version = "6.0-preview"
    url = f"{organization}/_apis/projects/{project_name}?api-version={api_version}"

    print("\n##############################")
    print(f"[INFO] Fetching the id of '{project_name}' project from '{organization}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            project_id = response.json()["id"]
            print(f"\n• Project: {project_name} | ID: {project_id}")

            return project_id
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch project id of '{project_name}' project.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching project id: {e}\033[0m")
        return None

def get_task_groups(organization, project_name, authentication_header):
    """
    This function fetches all task groups from a project.
    """
    url = f"{organization}/{project_name}/_apis/distributedtask/taskgroups?api-version=6.0-preview"

    print(f"\n[INFO] Fetching task groups from '{project_name}' in '{organization}'...")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            task_groups = response.json().get("value", [])
            print(f"\nFound {len(task_groups)} task group(s) in the '{project_name}' project.")

            print("-" * 50)  # Visual separator for better readability.
            for task_group in task_groups:
                task_group_name = task_group.get("name", "Unknown Name")
                task_group_id = task_group.get("id", "Unknown ID")
                print(f"• Task Group Name: {task_group_name} | Task Group ID: {task_group_id}")
                print("-" * 50)  # Visual separator between task groups for better readability.

            return task_groups
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch task groups from '{project_name}' project.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")
            return []
        
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching task groups: {e}\033[0m")
        return []

def task_group_mapping():
    """
    This function maps task groups between the source and target environments.
    """
    source_task_groups = get_task_groups(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    target_task_groups = get_task_groups(TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER)
    
    # A lookup dictionary for target task groups by their name.
    target_task_groups_lookup = {tg['name']: tg['id'] for tg in target_task_groups}
    
    task_groups_mapping = {}

    for stg in source_task_groups:
        if stg['name'] in target_task_groups_lookup:
            task_groups_mapping[stg['id']] = target_task_groups_lookup[stg['name']]
    
    return task_groups_mapping, source_task_groups

def get_task_group_config(organization, project_name, authentication_header, task_group_id):
    """
    This function fetches the configuration of a task group.
    """
    api_version = "6.0-preview"
    url = f"{organization}/{project_name}/_apis/distributedtask/taskgroups/{task_group_id}?api-version={api_version}"

    print(f"[INFO] Fetching the configuration of task group id {task_group_id} from '{project_name}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            task_group_config = response.json()
            print(f"[INFO] Successfully retrieved configuration for pipeline id {task_group_id}.")
            print(f"\n[DEBUG] Raw Configuration:\n{json.dumps(task_group_config, indent=4)}\n")  # Prettified JSON for better readability.

            return task_group_config
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch pipeline configuration for pipeline id {task_group_id}.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching pipeline configuration: {e}\033[0m")
        return None

if __name__ == "__main__":
    task_group_mapping()