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

    print("\n##############################")
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

def get_teams(organization, project_id, authentication_header):
    '''
    This function fetches the teams of a project.
    '''
    url = f"{organization}/_apis/projects/{project_id}/teams?api-version=6.0-preview"
    
    print("\n##############################")
    print(f"[INFO] Fetching the teams of '{project_id}' project id from '{organization}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            teams = response.json()["value"]
            print(f"Found {len(teams)} teams:")

            for idx, team in enumerate(teams):
                print(f"{idx + 1}. {team['name']}")

        else:
            print(f"[ERROR] Failed to fetch the teams of '{project_id}' project id.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching teams: {e}")
        return None

    return teams

def get_dashboards(organization, project_name, team_name, authentication_header):
    '''
    This function fetches the dashboards that are assigned to the team.
    '''
    url = f"{organization}/{project_name}/{team_name}/_apis/dashboard/dashboards?api-version=6.0-preview"

    print("\n##############################")
    print(f"[INFO] Fetching the dashboards of the '{team_name}' team from '{project_name}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            dashboards = response.json()["value"]
            print(f"Found {len(dashboards)} dashboards for team '{team_name}'.")

            for idx, dashboard in enumerate(dashboards):
                print(f"{idx + 1}. Dashboard: {dashboard['name']} | ID: {dashboard['id']}")

            return dashboards
        
        else:
            print(f"[ERROR] Failed to fetch the dashboards of the '{team_name}' team.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching dashboards: {e}")
        return None

def get_widgets(organization, project_name, team_name, dashboard_id, authentication_header):
    '''
    This function fetches the widgets of a dashboard.
    '''
    url = f"{organization}/{project_name}/{team_name}/_apis/dashboard/dashboards/{dashboard_id}/widgets?api-version=6.0-preview"
    
    print("\n##############################")
    print(f"[INFO] Fetching the widgets of the '{dashboard_id}' dashboard id from '{project_name}'...")
    print(f"[DEBUG] API URL: {url}")
    
    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            widgets = response.json()["value"]
            print(f"Found {len(widgets)} widgets for dashboard id {dashboard_id}.")

            for idx, widget in enumerate(widgets):
                print(f"\n{idx + 1}. Widget: {widget['name']} | ID: {widget['id']}")
                print(f"{widget}")

            return widgets
        
        else:
            print(f"[ERROR] Failed to fetch the widgets of dashboard id {dashboard_id}.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching widgets: {e}")
        return None

def map_teams(source_teams, target_teams):
    '''
    This function maps the teams from the source environment to the teams in the target environment.

    Team mapping is needed because dashboards are often created within the context of a specific team, and when migrating dashboards, 
    it's crucial to assign them to the correct corresponding team in the target environment.
    '''
    print("\n##############################")
    print("[INFO] Mapping source teams to target teams...")
    team_mapping = {}
    target_team_names = {team["name"]: team["id"] for team in target_teams}

    for source_team in source_teams:
        source_team_name = source_team["name"]
        target_team_id = target_team_names.get(source_team_name) # Gets the target's team ID using the source's team name.

        if target_team_id: # Managed to find a corresponding team.
            team_mapping[source_team["id"]] = target_team_id
            print(f"Mapped Source Team: '{source_team_name}' -> Target Team ID: {target_team_id}")

        else:
            print(f"\033[1;33m[WARNING] No matching target team for source Team '{source_team_name}'!\033[0m")

    print(f"[DEBUG] {len(team_mapping)} teams mapped successfully.")
    return team_mapping

def extract_shared_queries(folder):
    '''
    This function extracts all shared queries from a hierarchical folder structure.
    '''
    shared_queries = []

    if "children" in folder and folder["children"]: # Checks whether the current folder has a children key and whether it contains any sub-items.
        # The children key holds a list of subfolders or queries in the current folder.

        for child in folder["children"]: # Iterates through each child element (either a subfolder or a query) in the children list.
            if child.get("isFolder", False):
                shared_queries.extend(extract_shared_queries(child)) # If the current child element is a folder, the function calls itself recursively to process this subfolder.

            else: # If the current child element is not a folder (i.e., it is a query), the function extracts the query’s details and appends a dictionary to the 'shared_queries' list.
                shared_queries.append({
                    "id": child["id"],
                    "name": child["name"],
                    "path": child["path"],
                    "url": child["url"]
                })

    return shared_queries

def get_shared_queries(organization, project_name, authentication_header):
    '''
    This function fetches all shared queries in a project.
    '''
    url = f"{organization}/{project_name}/_apis/wit/queries?$depth=2&api-version=6.0"
    
    print("\n##############################")
    print(f"[INFO] Fetching shared queries for project '{project_name}' from '{organization}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()["value"]

            # Extracts the 'Shared Queries' folder as only this type of queries were migrated.
            shared_queries_folder = next(
                (item for item in data if item["name"] == "Shared Queries" and item.get("isFolder", False)),
                None
            )

            if not shared_queries_folder:
                print("[WARNING] No 'Shared Queries' folder found.")
                return []

            # Extracts all queries under the "Shared Queries" folder.
            shared_queries = extract_shared_queries(shared_queries_folder)
            print(f"Found {len(shared_queries)} shared queries.")
            
            for idx, query in enumerate(shared_queries):
                print(f"{idx + 1}. Query ID: {query['id']} | Name: {query['name']} | Path: {query['path']}")
            
            return shared_queries
        
        else:
            print(f"[ERROR] Failed to fetch shared queries for project '{project_name}'.")
            print(f"[DEBUG] Response Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching shared queries: {e}")
        return []

def map_queries(source_queries, target_queries):
    '''
    This function maps shared queries from the source environment to the target environment.

    Query mapping is needed because dashboards are often contain widgets that display data based on specific queries 
    (e.g., Query Results, Chart widgets). These widgets reference queries by their IDs, not by names or paths, so even if queries in 
    the source and target environments have the same name or path, their IDs will be different.
    '''
    print("\n##############################")
    print("[INFO] Mapping shared queries between source and target environments...")

    # Creates a dictionary for quick lookup of target queries by their path.
    target_paths = {query["path"]: query["id"] for query in target_queries}

    query_mapping = {}

    print("[INFO] Processing source queries for mapping...")
    try:
        for source_query in source_queries:
            source_path = source_query["path"]
            target_query_id = target_paths.get(source_path) # Gets the target's query ID using the source's query path.

            if target_query_id: # Managed to find a corresponding query.
                query_mapping[source_query["id"]] = target_query_id
                print(f"[INFO] Mapped: Source Query '{source_query['name']}' | ({source_path}) "
                      f"-> Target Query ID: {target_query_id}")
                
            else:
                print(f"[WARNING] No matching target query for source query '{source_query['name']}' | ({source_path})")

        print("\n[INFO] Final Query Mapping:")
        for source_id, target_id in query_mapping.items():
            print(f"Source Query ID: {source_id} -> Target Query ID: {target_id}")

        print(f"\n{len(query_mapping)} queries mapped successfully.")
        return query_mapping

    except Exception as e:
        print(f"[ERROR] An error occurred during query mapping: {e}")
        return {}

def create_dashboard(organization, project_name, team_name, dashboard_payload, authentication_header):
    '''
    This function creates a dashboard in a specific team within a project.
    '''
    url = f"{organization}/{project_name}/{team_name}/_apis/dashboard/dashboards?api-version=6.0-preview"

    print("\n##############################")
    print(f"[INFO] Creating dashboard '{dashboard_payload['name']}' for team '{team_name}' in project '{project_name}'...")
    print(f"[DEBUG] API URL: {url}")
    print(f"[DEBUG] Dashboard Payload: {dashboard_payload}")

    try:
        response = requests.post(url, headers=authentication_header, json=dashboard_payload)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200 or response.status_code == 201: # 201 status code indicates that the request was successfully 
            # processed, and a new resource was created. 
            print(f"\033[1;32m[INFO] Dashboard '{dashboard_payload['name']}' created successfully.\033[0m")
            return response.json()
        
        else:
            print(f"\033[1;31m[ERROR] Failed to create dashboard '{dashboard_payload['name']}' for team '{team_name}'.\033[0m")
            print(f"[DEBUG] Response Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while creating the dashboard: {e}")
        return None

def create_widget(organization, project_name, team_name, dashboard_id, widget, authentication_header):
    '''
    This function adds a widget to a dashboard.
    '''
    url = f"{organization}/{project_name}/{team_name}/_apis/dashboard/dashboards/{dashboard_id}/widgets?api-version=6.0-preview"

    print("\n##############################")
    print(f"[INFO] Adding widget '{widget['name']}' to dashboard ID '{dashboard_id}' for team '{team_name}' in project '{project_name}'...")
    print(f"[DEBUG] API URL: {url}")

    widget_payload = widget.copy() # We are about to modify the payload, and we don't want these changes to affect the original 
    # widget object, which might be used elsewhere in the code.

    widget_payload.pop("id", None) # When creating a new widget in Azure DevOps, the API doesn't allow an id to be included in 
    # the payload. The id field is only generated by the system after the widget is created successfully.
    print(f"[DEBUG] Widget Payload for '{widget['name']}':\n{json.dumps(widget_payload, indent=4)}")

    try:
        response = requests.post(url, headers=authentication_header, json=widget_payload)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200 or response.status_code == 201:
            print(f"\033[1;32m[INFO] Widget '{widget['name']}' added successfully to dashboard ID '{dashboard_id}'.\033[0m")
            return response.json()
        
        else:
            print(f"\033[1;31m[ERROR] Failed to add widget '{widget['name']}' to dashboard ID '{dashboard_id}'.\033[0m")
            print(f"[DEBUG] Response Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while adding the widget: {e}")
        return None

def migrate_dashboards(source_organization, target_organization, source_project, target_project, source_headers, target_headers, query_mapping):
    '''
    This function migrates dashboards and their widgets from a source project to a target project.
    '''
    print("\n##############################")
    print("[INFO] Starting dashboard migration process...")
    print(f"[DEBUG] Source Organization: {source_organization}")
    print(f"[DEBUG] Target Organization: {target_organization}")
    print(f"[DEBUG] Source Project: {source_project}")
    print(f"[DEBUG] Target Project: {target_project}")

    try:
        # Fetches project IDs.
        print("[INFO] Fetching project IDs...")
        source_project_id = get_project_id(source_organization, source_project, source_headers)
        target_project_id = get_project_id(target_organization, target_project, target_headers)

        # Fetches teams from source and target projects.
        print("[INFO] Fetching teams from source and target projects...")
        source_teams = get_teams(source_organization, source_project_id, source_headers)
        target_teams = get_teams(target_organization, target_project_id, target_headers)

        # Maps source teams to target teams.
        print("[INFO] Mapping source teams to target teams...")
        team_mapping = map_teams(source_teams, target_teams)

        for source_team in source_teams:
            source_team_name = source_team["name"]
            source_team_id = source_team["id"]

            # Finds the corresponding target team
            target_team_id = team_mapping.get(source_team_id)

            if not target_team_id:
                print(f"\033[1;33m[WARNING] Skipping team '{source_team_name}': No matching team found in target.\033[0m")
                continue

            print(f"[INFO] Starting migration for team '{source_team_name}'...")

            # Fetches dashboards for the current source team.
            print(f"[INFO] Fetching dashboards for team '{source_team_name}'...")
            source_dashboards = get_dashboards(source_organization, source_project, source_team_name, source_headers)
            target_dashboards = get_dashboards(target_organization, target_project, source_team_name, target_headers)

            target_dashboard_names = {dashboard["name"]: dashboard for dashboard in target_dashboards}

            for source_dashboard in source_dashboards:
                print(f"[INFO] Preparing to migrate dashboard '{source_dashboard['name']}'...")

                # Checks if a dashboard with the same name exists in the target project.
                if source_dashboard["name"] in target_dashboard_names:
                    print(f"\033[1;33m[WARNING] A dashboard with the name '{source_dashboard['name']}' already exists in the target project.\033[0m")
                    user_input = input(
                        f"Do you want to append the team name to the dashboard '{source_dashboard['name']}' "
                        f"({source_dashboard['name']}-{source_team_name})? (yes/no): "
                    ).strip().lower()
                    
                    if user_input != "yes":
                        print(f"[INFO] Skipping migration of dashboard '{source_dashboard['name']}' as all dashboards within a team must have unique names.")
                        continue
                    
                    source_dashboard["name"] = f"{source_dashboard['name']}-{source_team_name}"

                print(f"[INFO] Migrating dashboard '{source_dashboard['name']}'...")

                print(f"[INFO] Fetching widgets for dashboard '{source_dashboard['name']}'...")
                widgets = get_widgets(source_organization, source_project, source_team_name, source_dashboard["id"], source_headers)

                # Updates widget settings with mapped query IDs and paths.
                updated_widgets = []

                for widget in widgets:
                    print(f"\n[DEBUG] Processing widget '{widget['name']}'...")

                    if widget.get("settings") is None:
                        print(f"[INFO] Widget '{widget['name']}' does not have settings, adding to dashboard as-is.")
                        updated_widgets.append(widget)
                        continue

                    widget_settings = json.loads(widget["settings"])

                    # Updates widget's associated query ID.
                    source_query_id = None

                    if "queryId" in widget_settings:
                        source_query_id = widget_settings["queryId"]

                    elif "groupKey" in widget_settings:
                        source_query_id = widget_settings["groupKey"]

                    if source_query_id:
                        target_query_id = query_mapping.get(source_query_id)

                        if target_query_id:
                            if "queryId" in widget_settings:
                                widget_settings["queryId"] = target_query_id
                                print(f"[INFO] Updated widget '{widget['name']}' queryId: {source_query_id} -> {target_query_id}")

                            if "groupKey" in widget_settings:
                                widget_settings["groupKey"] = target_query_id
                                print(f"[INFO] Updated widget '{widget['name']}' groupKey: {source_query_id} -> {target_query_id}")
                        else:
                            print(f"\033[1;33m[WARNING] No target query found for source query ID {source_query_id}.\033[0m")

                    # Handles the "transformOptions" field if present.
                    if "transformOptions" in widget_settings:
                        if "filter" in widget_settings["transformOptions"]:
                            widget_settings["transformOptions"]["filter"] = query_mapping.get(source_query_id, widget_settings["transformOptions"]["filter"])
                            print(f"[INFO] Updated 'transformOptions' -> 'filter' for widget '{widget['name']}'.")

                    # Handles "path" and "artifactId" fields.
                    if "path" in widget_settings and "lastArtifactName" in widget_settings:
                        print(f"[INFO] Updating widget path for '{widget['name']}' from {widget_settings['path']}...")
                        widget_settings["path"] = widget_settings["path"].replace(source_project, target_project)
                        widget_settings["lastArtifactName"] = widget_settings["lastArtifactName"].replace(source_project, target_project)

                    # Transforms the updated settings back to the serialized form.
                    widget["settings"] = json.dumps(widget_settings)
                    updated_widgets.append(widget)

                print(f"[INFO] Creating dashboard '{source_dashboard['name']}' in target project...")
                target_dashboard_payload = {
                    "name": source_dashboard["name"],
                    "description": source_dashboard.get("description", ""),
                    "refreshInterval": source_dashboard.get("refreshInterval", 5),
                    "position": source_dashboard.get("position", 0)
                }
                target_dashboard = create_dashboard(target_organization, target_project, source_team_name, target_dashboard_payload, target_headers)

                if not target_dashboard:
                    print(f"[ERROR] Failed to create dashboard '{source_dashboard['name']}' in target project.")
                    continue

                target_dashboard_id = target_dashboard["id"]

                print(f"[INFO] Adding widgets to the dashboard '{source_dashboard['name']}'...")
                for widget in updated_widgets:
                    create_widget(target_organization, target_project, source_team_name, target_dashboard_id, widget, target_headers)

            print(f"[INFO] Completed migration for team '{source_team_name}'.")

        print("\n\033[1;32m[INFO] Dashboard migration process complete.\033[0m")

    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during migration: {e}")

if __name__ == "__main__":
    source_shared_queries = get_shared_queries(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    target_shared_queries = get_shared_queries(TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER)
    mapped_queries = map_queries(source_shared_queries, target_shared_queries)

    migrate_dashboards(SOURCE_ORGANIZATION, TARGET_ORGANIZATION, SOURCE_PROJECT, TARGET_PROJECT, SOURCE_AUTHENTICATION_HEADER, 
                       TARGET_AUTHENTICATION_HEADER, mapped_queries)
