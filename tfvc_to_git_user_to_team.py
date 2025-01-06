import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

SOURCE_ORGANIZATION="source_organization" # Configure source organization here as the URLs in this script aren't using the whole organization URL as specified in the ".env" file.
SOURCE_PROJECT=os.getenv("SOURCE_PROJECT")
SOURCE_PAT = os.getenv("SOURCE_PAT")

TARGET_ORGANIZATION="target_organization" # Configure target organization here as the URLs in this script aren't using the whole organization URL as specified in the ".env" file.
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
    if "localhost" in organization: # On-premises adjusted URL.
        url = f"{organization}/_apis/projects/{project_name}?api-version=6.0-preview"

    else: # Cloud adjusted URL.
        url = f"https://dev.azure.com/{organization}/_apis/projects/{project_name}?api-version=6.0-preview"

    print("##############################")
    print(f"[INFO] Fetching the id of '{project_name}' project from '{organization}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            project_id = response.json()["id"]
            print(f"Project: {project_name} | ID: {project_id}")

            return project_id
        
        else:
            print(f"[ERROR] Failed to fetch project id of '{project_name}' project.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching project id: {e}")
        return None

def get_teams(organization, project_id, authentication_header):
    '''
    This function fetches the teams of a project.
    '''
    if "localhost" in organization: # On-premises adjusted URL.
        url = f"{organization}/_apis/projects/{project_id}/teams?api-version=6.0-preview"

    else: # Cloud adjusted URL.
        url = f"https://dev.azure.com/{organization}/_apis/projects/{project_id}/teams?api-version=6.0-preview"
    
    print("##############################")
    print(f"[INFO] Fetching the teams of '{project_id}' project id from '{organization}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            teams = response.json()["value"]
            print(f"Found {len(teams)} teams:")

            for idx, team in enumerate(teams):
                print(f"{idx + 1}. Team: {team['name']} | id: {team['id']}")

        else:
            print(f"[ERROR] Failed to fetch the teams of '{project_id}' project id.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching teams: {e}")
        return None

    return teams

def get_team_members(organization, project_id, team_id, authentication_header):
    '''
    This function fetches the teams of a project.
    '''
    if "localhost" in organization: # On-premises adjusted URL.
        url = f"{organization}/_apis/projects/{project_id}/teams/{team_id}/members?api-version=6.0-preview"

    else: # Cloud adjusted URL.
        url = f"https://dev.azure.com/{organization}/_apis/projects/{project_id}/teams/{team_id}/members?api-version=6.0-preview"

    print("##############################")
    print(f"[INFO] Fetching the team members of team id '{team_id}' from project id '{project_id}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            members = response.json()["value"]
            print(f"Found {len(members)} team members:")

            for idx, team_member in enumerate(members):
                is_admin = team_member.get("isTeamAdmin", False)
                role = "Admin" if is_admin else "Member"
                print(f"{idx + 1}. Team Member: {team_member['identity']['uniqueName']} | ID: {team_member['identity']['id']} | Role: {role}")

        else:
            print(f"[ERROR] Failed to fetch the team members of '{team_id}' team id.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching team members: {e}")
        return None

    return members

def get_all_users(organization, authentication_header):
    '''
    This function fetches all users from the target environment.
    '''
    url = f"https://vsaex.dev.azure.com/{organization}/_apis/userentitlements?api-version=6.0-preview"

    print("##############################")
    print(f"[INFO] Fetching the users of the '{organization}' organization...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            users = response.json().get("members", [])

            print(f"Found {len(users)} users:")
            for idx, user in enumerate(users):
                print(f"{idx + 1}. {user['user']['displayName']} - {user['id']}")

        else:
            print(f"[ERROR] Failed to fetch the users of the '{organization}' organization.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching team members: {e}")
        return None

    return users

def add_user_to_team(organization, team_id, member_id, email, authentication_header):
    '''
    This function adds a user to a team.
    '''
    url = f"https://vsaex.dev.azure.com/{organization}/_apis/GroupEntitlements/{team_id}/members/{member_id}?api-version=6.0-preview"
    
    print("##############################")
    print(f"[INFO] Adding user '{email}' to team '{team_id}' team...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.put(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code in [200, 204]:
            print(f"[INFO] Successfully added user {email} to team {team_id}.")

        else:
            print(f"[ERROR] Failed to add user {email}.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while adding user: {e}")

def set_team_admin(organization, project_id, team_id, member_id, authentication_header):
    '''
    This function assigns a user as admin.
    '''
    url = f"https://dev.azure.com/{organization}/{project_id}/_api/_identity/AddTeamAdmins?api-version=6.0-preview"

    payload = {
        "teamId": team_id,
        "newUsersJson": "[]",
        "existingUsersJson": f"[\"{member_id}\"]"
    }

    try:
        response = requests.post(url, headers=authentication_header, json=payload)
        print(f"[INFO] Originally, user {member_id} was admin. Setting him up as an admin in the target team...")

        if response.status_code in [200, 204]:
            print(f"[INFO] Successfully set user {member_id} as admin in team {team_id}.")

        else:
            print(f"[ERROR] Failed to set user {member_id} as admin.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while setting team admin: {e}")

def assign_users_to_team(source_organization, target_organization, source_project, target_project, source_headers, target_headers):
    '''
    This function handles user migration from one team to another.
    '''
    print("##############################")
    print("[INFO] Starting user assignment process...")
    print(f"[DEBUG] Source Organization: {source_organization}")
    print(f"[DEBUG] Target Organization: {target_organization}")
    print(f"[DEBUG] Source Project: {source_project}")
    print(f"[DEBUG] Target Project: {target_project}")

    target_users = get_all_users(TARGET_ORGANIZATION, TARGET_AUTHENTICATION_HEADER)

    source_project_id = get_project_id(source_organization, source_project, source_headers)
    target_project_id = get_project_id(target_organization, target_project, target_headers)

    source_teams = get_teams(source_organization, source_project_id, source_headers)
    target_teams = get_teams(target_organization, target_project_id, target_headers)

    for idx, source_team in enumerate(source_teams):
        print(f"\nSource Team #{idx + 1}: {source_team['name']}")

        print("\nAvailable Target Teams:")
        for t_idx, target_team in enumerate(target_teams):
            print(f"{t_idx + 1} - {target_team['name']}")
        
        print(f"0 - Skip migrating team members from '{source_team['name']}'")

        try:
            target_team_idx = int(input("\nSelect by number the target team to migrate members to: ")) - 1

            if target_team_idx == 0-1:
                print(f"Skipping '{source_team['name']}' team, moving to the next team...")
                continue

            target_team = target_teams[target_team_idx]

            print(f"\nMigrating members from '{source_team['name']}' to '{target_team['name']}'...")

            team_members = get_team_members(source_organization, source_project_id, source_team["id"], source_headers)
            team_admins = [member for member in team_members if member.get("isTeamAdmin", False)]  # Extracts team admins.

            if not team_members:
                print(f"[ERROR] No team members has been found in source team '{source_team['name']}'. Skipping...")
                continue

            for team_member in team_members:
                team_member_display_name = team_member["identity"].get("displayName", "Unknown")


                # Validates that the current source team member exists in the target environment users.
                matching_user = next((user for user in target_users if user["user"]["displayName"] == team_member_display_name), None)

                if not matching_user:
                    print(f"[WARNING] No matching user found in the target environment for '{team_member_display_name}'. Skipping...")
                    continue

                target_user_id = matching_user["id"]

                accept = input(f"\nDo you want to add '{team_member_display_name}' to '{target_team['name']}'? (Yes/No/All): ").strip().lower()

                if accept == "yes":
                    add_user_to_team(target_organization, target_team["id"], target_user_id, team_member_display_name, target_headers)

                    if team_member_display_name in [admin["identity"]["displayName"] for admin in team_admins]:
                        set_team_admin(target_organization, target_project_id, target_team["id"], target_user_id, target_headers)

                elif accept == "all":
                    for remaining_team_member in team_members:
                        team_member_display_name = remaining_team_member["identity"].get("displayName", "Unknown")

                        matching_user = next((user for user in target_users if user["user"]["displayName"] == team_member_display_name), None)

                        if not matching_user:
                            print(f"[WARNING] No matching user found in the target environment for '{team_member_display_name}'. Skipping...")
                            continue

                        target_user_id = matching_user["id"]

                        add_user_to_team(target_organization, target_team["id"], target_user_id, team_member_display_name, target_headers)

                        if team_member_display_name in [admin["identity"]["displayName"] for admin in team_admins]:
                            set_team_admin(target_organization, target_project_id, target_team["id"], target_user_id, target_headers)
                    break

        except ValueError:
            print("[ERROR] Invalid selection. Please enter a valid number.")

        except IndexError:
            print("[ERROR] Selected team index is out of range.")

if __name__ == "__main__":
    assign_users_to_team(SOURCE_ORGANIZATION, TARGET_ORGANIZATION, SOURCE_PROJECT, TARGET_PROJECT, SOURCE_AUTHENTICATION_HEADER, TARGET_AUTHENTICATION_HEADER)
