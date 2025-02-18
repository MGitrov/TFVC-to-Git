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
    url = f"{organization}/_apis/projects/{project_name}?api-version=6.0-preview"

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
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching project ID: {e}")
        return None

def get_variable_groups(organization, project_name, authentication_header):
    '''
    This function fetches all variable groups in a project.
    '''
    url = f"{organization}/{project_name}/_apis/distributedtask/variablegroups?api-version=6.0-preview"

    print("##############################")
    print(f"[INFO] Fetching variable groups from '{project_name}' project in '{organization}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            variable_groups = response.json().get("value", [])
            print(f"Found {len(variable_groups)} variable group(s).")

            for vg in variable_groups:
                print(f"- Variable group id: {vg['id']} | Name: {vg['name']}")

            return variable_groups

        else:
            print(f"[ERROR] Failed to fetch variable groups from '{project_name}' project.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching variable groups: {e}")
        return None

def create_variable_group(organization, authentication_header, variable_group_payload, project_id, project_name):
    """
    Creates a variable group in the target Azure DevOps organization.
    """
    variable_group_payload["variableGroupProjectReferences"] = [
        {
            "name": variable_group_payload["name"],
            "projectReference": {
                "id": project_id,
                "name": project_name
            }
        }
    ]

    url = f"{organization}/_apis/distributedtask/variablegroups?api-version=6.0-preview"

    print("##############################")
    print(f"[INFO] Creating variable group '{variable_group_payload['name']}' in Azure DevOps organization '{organization}'...")
    print(f"[DEBUG] API URL: {url}")
    print(f"[DEBUG] Variable Group Payload: {json.dumps(variable_group_payload, indent=4)}")

    try:
        response = requests.post(url, headers=authentication_header, json=variable_group_payload)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200 or response.status_code == 201:
            print(f"[INFO] Variable group '{variable_group_payload['name']}' created successfully.")
            return response.json()

        else:
            print(f"[ERROR] Failed to create variable group '{variable_group_payload['name']}'.")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while creating the variable group: {e}")
        return None

def migrate_public_variable_groups(source_organization, source_project, target_organization, target_project, source_auth_header, target_auth_header):
    '''
    This function migrates public variable groups from the source project to the target project.
    '''
    print("##############################")
    print(f"[INFO] Migrating public variable groups from '{source_project}' to '{target_project}'...")

    variable_groups = get_variable_groups(source_organization, source_project, source_auth_header)

    if not variable_groups:
        print(f"[WARNING] No variable groups found in '{source_project}' project.")
        return

    target_project_id = get_project_id(target_organization, target_project, target_auth_header)
    if not target_project_id:
        print(f"[ERROR] Failed to fetch target project ID for '{target_project}'.")
        return

    for group in variable_groups:
        # Ensure the group has a valid name
        if not group.get("name"):
            print(f"[ERROR] Variable group is missing a 'name'. Skipping...")
            continue

        public_variables = {
            name: var for name, var in group["variables"].items() if not var.get("isSecret", False)
        }

        if public_variables:
            new_group = {
                "name": group["name"],
                "variables": public_variables,
                "type": group.get("type", "Vsts"),  # Default to "Vsts" type.
                "description": group.get("description", "")
            }

            created = create_variable_group(TARGET_ORGANIZATION, TARGET_AUTHENTICATION_HEADER, new_group, target_project_id, target_project)
            if not created:
                print(f"[WARNING] Variable group '{group['name']}' could not be created in '{target_project}'.")

        else:
            print(f"[INFO] Skipping variable group '{group['name']}' as it contains only secret variables.")

if __name__ == "__main__":
    migrate_public_variable_groups(SOURCE_ORGANIZATION, SOURCE_PROJECT, TARGET_ORGANIZATION, TARGET_PROJECT, SOURCE_AUTHENTICATION_HEADER, TARGET_AUTHENTICATION_HEADER)