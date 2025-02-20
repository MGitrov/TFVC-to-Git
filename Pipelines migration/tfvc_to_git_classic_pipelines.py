import os
import base64
import requests
import json
import yaml
from datetime import datetime
import re
from dotenv import load_dotenv

load_dotenv()

SOURCE_ORGANIZATION=os.getenv("SOURCE_ORGANIZATION")
SOURCE_PROJECT=os.getenv("SOURCE_PROJECT")
SOURCE_PAT = os.getenv("SOURCE_PAT")

GAU_TARGET_ORGANIZATION="maximpetrov1297"
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

def get_projects(organization, authentication_header):
    """
    This function fetches the projects of an organization.
    """
    api_version = "6.0-preview"
    url = f"{organization}/_apis/projects?api-version={api_version}"

    print("##############################")
    print(f"[INFO] Fetching projects from '{organization}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            projects = response.json().get("value", [])
            print(f"[INFO] There are {len(projects)} projects in '{organization}'.")

            for project in projects:
                print(f"\n{project}\n")

            return projects
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch projects.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching the projects: {e}\033[0m")
        return []

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
            print(f"Project: {project_name} | ID: {project_id}")

            return project_id
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch project id of '{project_name}' project.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching project id: {e}\033[0m")
        return None

def get_pipelines(organization, project_name, authentication_header):
    """
    This function fetches the build pipelines of a project.
    """
    api_version = "6.0-preview"
    url = f"{organization}/{project_name}/_apis/pipelines?api-version={api_version}"

    print("##############################")
    print(f"[INFO] Fetching pipelines from '{project_name}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            pipelines = response.json().get("value", []) # Parses the JSON response and retrieves the list of pipelines from the value field.
            print(f"[INFO] There are {len(pipelines)} pipelines in '{organization}'.")

            for pipeline in pipelines:
                print(f"- Pipeline id: {pipeline['id']} | Name: {pipeline['name']}")

            return pipelines
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch pipelines.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return []

    except requests.exceptions.RequestException as e: # Catches any exceptions that occur during the HTTP request (e.g., connection issues, timeouts).
        print(f"\033[1;31m[ERROR] An error occurred while fetching the pipelines: {e}\033[0m")
        return []

def get_pipeline_config(organization, project_name, authentication_header, pipeline_id):
    """
    This function fetches the configuration of a pipeline.
    """
    api_version = "6.0-preview"
    url = f"{organization}/{project_name}/_apis/build/definitions/{pipeline_id}?api-version={api_version}"

    print(f"[INFO] Fetching the configuration of pipeline id {pipeline_id} from '{project_name}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            pipeline_config = response.json()
            print(f"[INFO] Successfully retrieved configuration for pipeline id {pipeline_id}.")
            print(f"\n[DEBUG] Raw Configuration:\n{json.dumps(pipeline_config, indent=4)}\n")  # Prettified JSON for better readability.

            return pipeline_config
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch pipeline configuration for pipeline id {pipeline_id}.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching pipeline configuration: {e}\033[0m")
        return None

def get_all_users(organization, authentication_header):
    '''
    This function fetches all users of an organization.
    '''
    api_version = "6.0-preview"
    url = f"https://vsaex.dev.azure.com/{organization}/_apis/userentitlements?api-version={api_version}"

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
            print(f"\033[1;31m[ERROR] Failed to fetch the users of the '{organization}' organization.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching team members: {e}\033[0m")
        return None

    return users

def get_service_connections(organization, project, authentication_header):
    """
    This function fetches the available service connections of a project.
    """
    api_version = "6.0-preview"
    url = f"{organization}/{project}/_apis/serviceendpoint/endpoints?api-version={api_version}"

    print("##############################")
    print(f"[INFO] Fetching the service connections of the '{organization}' organization...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            service_connections = response.json().get("value", [])

            print(f"Found {len(service_connections)} service connections:") # what will be printed if no service connections were found.
            for sc in service_connections:
                print(f"\n{sc}\n")

        else:
            print(f"\033[1;31m[ERROR] Failed to fetch the service connections of the '{organization}' organization.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching service connections: {e}\033[0m")
        return None

    return service_connections

def download_pipeline_configs(organization, project_name, authentication_header, pipeline_ids, output_directory): # DEPRECATED.
    """
    Downloads the JSON configuration of multiple pipelines and saves them to files.
    """
    for pipeline_id in pipeline_ids:
        try:
            url = f"{organization}/{project_name}/_apis/build/Definitions/{pipeline_id}?api-version=6.0"
            response = requests.get(url, headers=authentication_header)
            
            if response.status_code == 200:
                pipeline_config = response.json()
                file_name = f"{output_directory}/pipeline_{pipeline_id}.json"
                
                with open(file_name, "w") as json_file:
                    json.dump(pipeline_config, json_file, indent=4)
                
                print(f"[INFO] Successfully downloaded pipeline {pipeline_id} to {file_name}.")
            else:
                print(f"[ERROR] Failed to download pipeline {pipeline_id}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[ERROR] An error occurred while downloading pipeline {pipeline_id}: {str(e)}")

def get_queues(organization, project_name, authentication_header):
    api_version = "6.0-preview"
    url = f"{organization}/{project_name}/_apis/distributedtask/queues?api-version={api_version}"

    print("##############################")
    print(f"[INFO] Fetching the queues of the '{project_name}' project...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            queues = response.json().get("value", [])
            print(f"[INFO] There are {len(queues)} queues in '{project_name}' project.")

        else:
            print(f"\033[1;31m[ERROR] Failed to fetch the queues of the '{project_name}' project.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching queues: {e}\033[0m")
        return None

    return queues

def find_queue_for_pool(queues, pool_id):
    for queue in queues:
        if queue.get('pool', {}).get('id') == pool_id:
            return queue
        
    return None

def get_agent_pools(organization, authentication_header):
    """
    This function fetches the available agent pool(s) of an organization.
    """
    api_version = "6.0-preview"
    url = f"{organization}/_apis/distributedtask/pools?api-version={api_version}"

    print(f"\n[INFO] Fetching the available agent pool(s) for '{organization}'...")
    print(f"[DEBUG] API URL: {url}")

    response = requests.get(url, headers=authentication_header)
    print(f"[DEBUG] Request's Status Code: {response.status_code}")

    if response.status_code == 200:
        pools = response.json().get("value", [])
        filtered_pools = [pool for pool in pools if not pool.get("isLegacy", True)] # Ensures the user is only presented with relevant and supported agent pools.

        if not filtered_pools:
            print("\033[1;38;5;214m[WARNING] No non-legacy agent pools available.\033[0m")

        return filtered_pools
    
    else:
        raise Exception(f"Failed to fetch agent pools | Request's Status Code: {response.status_code} | Response Body: {response.text}")

def choose_agent_pool(pools):
    """
    This function prompts the user to select an agent pool from the list.
    """
    print("\n[INFO] Available Target Agent Pools:")
    for idx, pool in enumerate(pools):
        print(f"{idx + 1} - {pool['name']} (id: {pool['id']}, Hosted: {pool.get('isHosted', False)})")

    while True:
        try:
            choice = int(input("\nEnter the number corresponding to your desired agent pool: ")) - 1
            if 0 <= choice < len(pools):
                return pools[choice]
            
            else:
                print("\033[1;31m[ERROR] Invalid choice. Please select a valid option.\033[0m")

        except ValueError:
            print("\033[1;31m[ERROR] Invalid input. Please enter a number.\033[0m")

def update_triggers_section(triggers_section, target_repository):
    adjusted_triggers = []

    for trigger in triggers_section:
        if trigger.get("triggerType") == "gatedCheckIn": # Skips 'Gated check-in' triggers (triggerType 16 for TFVC) as it is a special type of trigger in TFVC.
            continue

        """
        • Branch Filters: Branch filters determine which branches in your repository will trigger the pipeline. They use a simple syntax starting with + (include) or - (exclude), 
            followed by the branch name.

        • Path Filters: Path filters add another layer of specificity by determining which file or folder changes within the matched branches should trigger the pipeline.
            They also use + and - prefixes.
        """
        adjusted_branch_filters = set() # Assigns branches based on the configured in the 'pathFilters' section.
        adjusted_path_filters = []

        for path in trigger.get("pathFilters", []):
            """
            The regex pattern matches TFVC path formats like "+$/ProjectName/BranchName/Path/To/Code".

            TFVC path pattern components:
            • ([+-]) -> Inclusion/exclusion marker.
            • \$/ -> TFVC root indicator.
            • ([^/]+) -> Project name.
            • ([^/]+) -> Branch name.
            • (/(.*))?-> Optional remaining path.
            """
            match = re.match(r"([+-])\$/([^/]+)/([^/]+)(/(.*))?", path)

            if match:
                inclusion = match.group(1)  # Catches the "+" or "-".
                branch_name = match.group(3)  # Catches the branch name.
                relative_path = match.group(5) or "*"  # Catches the remaining path that is relative to the branch.

                adjusted_branch_filters.add(f"+refs/heads/{branch_name}")

                adjusted_path_filters.append(f"{inclusion}{relative_path}/*" if relative_path != "*" else f"{inclusion}*")
            
            else:
                adjusted_path_filters.append(path)

        # Default to the target repository's default branch if no branch filters are identified
        if not adjusted_branch_filters:
            adjusted_branch_filters.add(f"refs/heads/{target_repository['defaultBranch'].split('/')[-1]}")

        adjusted_trigger = {
        "branchFilters": list(adjusted_branch_filters),
        "pathFilters": adjusted_path_filters,
        }

        additional_fields = ["triggerType", "batchChanges", "maxConcurrentBuildsPerBranch", "pollingInterval", "useWorkspaceMappings"]
        
        for field in additional_fields:
            if field in trigger:
                adjusted_trigger[field] = trigger[field]

        adjusted_triggers.append(adjusted_trigger)

    return adjusted_triggers

def update_queue_section(pipeline_json_config, available_pools_map, available_target_pools):
    available_queues = get_queues(TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER)
    queue_section = pipeline_json_config.get("queue", {})
    source_pool_name = queue_section.get("pool", {}).get("name", "")

    if source_pool_name in available_pools_map: # Checks whether the agent pool exists in the target environment.
        matched_pool = available_pools_map[source_pool_name]
        matched_queue = find_queue_for_pool(available_queues, matched_pool["id"])

        if matched_queue:
            queue_section["id"] = matched_queue["id"]
            queue_section["name"] = matched_queue["name"]
            queue_section["url"] = f"{TARGET_ORGANIZATION}/_apis/build/Queues/{matched_queue["id"]}"

            queue_section["pool"] = {
                "id": matched_pool["id"],
                "name": matched_pool["name"],
                "isHosted": matched_pool.get("isHosted", False)
            }

            queue_links = pipeline_json_config.get('queue', {}).get('_links', {})
    
            if 'self' in queue_links and 'href' in queue_links['self']:
                updated_href = f"{TARGET_ORGANIZATION}/_apis/build/Queues/{matched_queue["id"]}"
                queue_links['self']['href'] = updated_href
                pipeline_json_config['queue']['_links'] = queue_links

        else:
            raise Exception(f"No queue found for pool '{source_pool_name}' in '{TARGET_ORGANIZATION}'.")

    else:
        # Falls back to a default pool (e.g., "Azure Pipelines").
        default_pool = next((pool for pool in available_target_pools if pool["name"] == "Azure Pipelines"), None)

        if default_pool:
            print(f"[INFO] Defaulting to 'Azure Pipelines' agent pool.")
            matched_queue = find_queue_for_pool(available_queues, default_pool["id"])

            queue_section["id"] = matched_queue["id"]
            queue_section["name"] = matched_queue["name"]
            queue_section["url"] = f"{TARGET_ORGANIZATION}/_apis/build/Queues/{matched_queue["id"]}"

            queue_section["pool"] = {
                "id": default_pool["id"],
                "name": default_pool["name"],
                "isHosted": default_pool.get("isHosted", True)
            }

            queue_links = pipeline_json_config.get('queue', {}).get('_links', {})
    
            if 'self' in queue_links and 'href' in queue_links['self']:
                updated_href = f"{TARGET_ORGANIZATION}/_apis/build/Queues/{matched_queue["id"]}"
                queue_links['self']['href'] = updated_href
                pipeline_json_config['queue']['_links'] = queue_links

        else:
            raise Exception("No matching agent pool found, and 'Azure Pipelines' pool is not available.")
        
    return pipeline_json_config

def adjust_pipeline_config(target_projects, pipeline_json_config, target_repository): # REVIEW.
    """
    This function adjusts the pipeline configuration file to use Git as the source.
    """
    # Adjusts the 'triggers' section.
    #triggers = pipeline_json_config.get('triggers', [])
    #adjusted_triggers_section = update_triggers_section(triggers, target_repository)

    #pipeline_json_config["triggers"] = adjusted_triggers_section

    # Adjusts the 'repository' section.
    repository = pipeline_json_config["repository"]

    repository["id"] = target_repository["id"]
    repository["type"] = "TfsGit"
    repository["name"] = target_repository["name"]
    repository["url"] = target_repository["url"] #f"{TARGET_ORGANIZATION}/{TARGET_PROJECT}/_git/{target_repository['name']}"
    repository["defaultBranch"] = target_repository["defaultBranch"]

    repository.pop("rootFolder", None)

    # Adjusts the 'properties' sub-section.
    properties = repository.get('properties', {})

    git_specific_fields = { # Specific fields that are added once the source is changed to Git.
        "reportBuildStatus": "true",
        "fetchDepth": "1",
        "gitLfsSupport": "false",
        "skipSyncSource": "false",
        "checkoutNestedSubmodules": "false"
    }

    for key, value in git_specific_fields.items():
        if key not in properties or properties[key] != value:
            properties[key] = value

    properties.pop("tfvcMapping", None)
       
    # Adjusts the queue-related staff.
    available_target_pools = get_agent_pools(TARGET_ORGANIZATION, TARGET_AUTHENTICATION_HEADER)
    available_pools_map = {pool["name"]: pool for pool in available_target_pools}

    queue_section = update_queue_section(pipeline_json_config, available_pools_map, available_target_pools)

    pipeline_json_config = queue_section
    
    # Adjusts the 'authoredBy' section.
    authored_by = pipeline_json_config.get("authoredBy", {})
    source_display_name = authored_by.get("displayName", "Unknown")

    target_users = get_all_users(GAU_TARGET_ORGANIZATION, TARGET_AUTHENTICATION_HEADER)

    if not target_users:
        raise Exception(f"[ERROR] Unable to fetch users from {TARGET_ORGANIZATION}.")

    matching_user = next((user for user in target_users if user["user"]["displayName"] == source_display_name), None) # Matches the source user to a target user by 'displayName'.

    if not matching_user:
        raise Exception(f"[ERROR] No matching user found in the target environment for '{source_display_name}'.")

    pipeline_json_config["authoredBy"] = {
        "displayName": matching_user["user"]["displayName"],
        "url": matching_user["user"].get("_links", {}).get("self", {}).get("href"),
        "_links": {
            "avatar": {
                "href": matching_user["user"].get("_links", {}).get("avatar", {}).get("href")
            }
        },

        "id": matching_user["id"],
        "uniqueName": matching_user["user"]["principalName"],
        "imageUrl": matching_user["user"].get("_links", {}).get("avatar", {}).get("href"),
        "descriptor": matching_user["user"].get("descriptor")
    }

    # Adjusts the metadata.
    target_project_id = get_project_id(TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER)

    pipeline_json_config["id"] = 0 # A place holder. Azure DevOps will assign a new id once the pipeline will be created.
    pipeline_json_config["url"] = f"{TARGET_ORGANIZATION}/{target_project_id}/_apis/build/Definitions/0?revision=1"
    pipeline_json_config["uri"] = "vstfs:///Build/Definition/0"
    pipeline_json_config["path"] = "\\"  # Pipeline's location in the folder structure.
    pipeline_json_config["type"] = 2
    pipeline_json_config["queueStatus"] = 0
    pipeline_json_config["revision"] = 1
    pipeline_json_config["createdDate"] = datetime.utcnow().isoformat()  # Current timestamp in ISO 8601 format

    # Adjusts the 'project' section.
    pipeline_json_config["project"] = {
        "id": target_project_id,
        "name": TARGET_PROJECT,
        "url": f"{TARGET_ORGANIZATION}/_apis/projects/{target_project_id}"
    }

    # Adjusts the '_links' section.
    target_pipeline_id = 0
    links = pipeline_json_config.get('_links', {})

    links['self'] = {
        "href": f"{TARGET_ORGANIZATION}/{target_project_id}/_apis/build/Definitions/{target_pipeline_id}?revision=1"
    }
    links['web'] = {
        "href": f"{TARGET_ORGANIZATION}/{target_project_id}/_build/definition?definitionId={target_pipeline_id}"
    }
    links['editor'] = {
        "href": f"{TARGET_ORGANIZATION}/{target_project_id}/_build/designer?id={target_pipeline_id}&_a=edit-build-definition"
    }
    links['badge'] = {
        "href": f"{TARGET_ORGANIZATION}/{target_project_id}/_apis/build/status/{target_pipeline_id}"
    }
    
    # Adjusts service connections.
    source_service_connections = get_service_connections(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    target_service_connections = get_service_connections(TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER)
    service_connection_ids = set()

    process = pipeline_json_config.get("process")

    if not process:
        print("[WARNING] 'process' section is missing in the pipeline configuration.")

    elif not isinstance(process, dict):
        print("[ERROR] 'process' is not a dictionary. Check the pipeline configuration.")

    else:
        phases = process.get("phases", [])
        if not isinstance(phases, list):
            print("[ERROR] 'phases' in 'process' is not a list. Check the pipeline configuration.")
        else:
            for phase in phases:
                if not isinstance(phase, dict):
                    print("[WARNING] Skipping invalid phase that is not a dictionary.")
                    continue
                steps = phase.get("steps", [])
                if not isinstance(steps, list):
                    print("[WARNING] 'steps' in a phase is not a list. Skipping.")
                    continue
                for step in steps:
                    if not isinstance(step, dict):
                        print("[WARNING] Skipping invalid step that is not a dictionary.")
                        continue
                    # Validate 'inputs' in 'step'
                    inputs = step.get("inputs")
                    if not inputs:
                        print("[INFO] No 'inputs' section in this step.")
                    elif not isinstance(inputs, dict):
                        print("[ERROR] 'inputs' is not a dictionary. Skipping step.")
                    else:
                        external_endpoints = inputs.get("externalEndpoints")
                        if external_endpoints:
                            service_connection_ids.add(external_endpoints)
                            print(f"[INFO] Found 'externalEndpoints': {external_endpoints}")
                        else:
                            print("[INFO] 'externalEndpoints' is not present in 'inputs'.")

    def map_service_connection(source_id, source_connections, target_connections):
        source_connection = next((conn for conn in source_connections if conn.get("id") == source_id), None)

        for target_connection in target_connections:
            if source_connection.get("name") == target_connection.get("name"):
                return target_connection["id"]

        print(f"[WARNING] No matching service connection found for source ID: {source_id}. Skipping...")
        return None

    mapped_service_connections = {}
    for source_id in service_connection_ids:
        mapped_service_connections[source_id] = map_service_connection(
            source_id,
            source_service_connections,
            target_service_connections
    )
    print(f"\n{mapped_service_connections}\n")
    for phase in pipeline_json_config.get("process", {}).get("phases", []):
        for step in phase.get("steps", []):
            if "inputs" in step and "externalEndpoints" in step["inputs"]:
                source_id = step["inputs"]["externalEndpoints"]
                if source_id in mapped_service_connections:
                    step["inputs"]["externalEndpoints"] = mapped_service_connections[source_id]

    print(f"\n[DEBUG] Adjusted Configuration:\n{json.dumps(pipeline_json_config, indent=4)}\n")
    print("[INFO] Pipeline updated successfully.")
    return pipeline_json_config

def select_pipelines_to_migrate(pipelines):
    """
    This function prompts the user to select which pipelines to migrate.
    """
    print("\nAvailable Source Pipelines for Migration:")
    for index, pipeline in enumerate(pipelines, 1):
        print(f"{index} - {pipeline['name']} (id: {pipeline['id']})")

    print("\nOr:")
    print("0 - Migrate all pipelines (It is recommended to migrate the pipelines one by one for better controllability of the process)")
    print("\nEnter pipeline numbers separated by commas to select specific pipelines.")

    selection = input("\nYour choice: ").strip()

    # Migrate all pipelines.
    if selection == "0":
        return [pipeline["id"] for pipeline in pipelines]
    
    # Migrate specific pipelines.
    else:
        try:
            selected_indices = [int(x.strip()) - 1 for x in selection.split(",")]
            selected_pipelines = [
                pipelines[index]["id"] for index in selected_indices if 0 <= index < len(pipelines)
            ]

            if not selected_pipelines:
                raise ValueError("No valid pipelines selected.")
            return selected_pipelines
        
        except (ValueError, IndexError) as e:
            print(f"\033[1;31m[ERROR] Invalid selection: {e}\033[0m")
            return select_pipelines_to_migrate(pipelines) # On invaild choice, the user will be prompted again.

def create_pipeline(organization, project, authentication_header, pipeline_config):
    """
    This function creates a classic build pipeline.
    """
    api_version = "6.0-preview"
    url = f"{organization}/{project}/_apis/build/definitions?api-version={api_version}"

    response = requests.post(url, headers=authentication_header, json=pipeline_config)

    if response.status_code == 200 or response.status_code == 201:
        print(f"\033[1;32m[SUCCESS] Successfully created the '{pipeline_config['name']}' pipeline.\033[0m")
        return response.json()
    
    else:
        print(f"\033[1;31m[ERROR] Failed to create the '{pipeline_config['name']}' pipeline.\033[0m")
        print(f"[DEBUG] Request's Status Code: {response.status_code}")
        print(f"[DEBUG] Response Body: {response.text}")
        return None

def migrate_pipelines(source_organization, target_organization, source_project, target_project, source_headers, target_headers):
    """
    This function migrates TFVC-based pipelines from a source project to a target project.
    """
    print("\n\033[1;33mEnsure the trigger branches exist in your target environment before starting the migration.\033[0m")
    print("\033[1;33mEnsure you have configured agent pools in your target environment before starting the migration.\033[0m\n")
    print("[INFO] Starting pipeline migration process...")
    print(f"[DEBUG] Source Organization: {source_organization}")
    print(f"[DEBUG] Target Organization: {target_organization}")
    print(f"[DEBUG] Source Project: {source_project}")
    print(f"[DEBUG] Target Project: {target_project}")

    # Get Target Project ID
    #target_project_id = get_project_id(target_organization, target_project, target_headers)

    # Fetch Available Queues (Agent Pools) in Target Project
    """
    queues_url = f"{target_organization}/{target_project}/_apis/distributedtask/queues?api-version=6.0-preview"
    response = requests.get(queues_url, headers=target_headers)

    
    if response.status_code == 200:
        queues = response.json().get("value", [])
        filtered_target_queues = [queue for queue in queues if not queue["pool"].get("isLegacy", False)]
        print("\nFiltered Queues (Non-Legacy):\n")
        print(filtered_target_queues)
    else:
        print(f"[ERROR] Failed to fetch queues: {response.status_code} - {response.text}")
        return
    """

    # Fetch Target Repositories
    try:
        target_repositories = requests.get(
            f"{target_organization}/{target_project}/_apis/git/repositories?api-version=6.0-preview",
            headers=target_headers
        ).json()["value"]
    except Exception as e:
        print(f"[ERROR] Failed to fetch target repositories: {e}")
        return

    # Fetch Target Projects & Service Connections
    target_projects = get_projects(target_organization, target_headers)
    target_service_connections = get_service_connections(target_organization, target_project, target_headers)

    # Fetch Source Pipelines
    try:
        pipelines = get_pipelines(source_organization, source_project, source_headers)
    except Exception as e:
        print(f"[ERROR] Failed to fetch pipelines from the source project: {e}")
        return

    if not pipelines:
        print("[INFO] No pipelines found to migrate.")
        return

    print("\n[INFO] Fetching pipelines completed.")
    selected_pipeline_ids = select_pipelines_to_migrate(pipelines)

    for pipeline in pipelines:
        if pipeline["id"] in selected_pipeline_ids:
            try:
                print(f"##############################>-{pipeline['name']}<##############################")
                pipeline_id = pipeline["id"]
                pipeline_name = pipeline["name"]
                pipeline_config = get_pipeline_config(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, pipeline_id)

            except Exception as e:
                print(f"[ERROR] Failed to fetch or process pipeline '{pipeline['name']}': {e}")
                continue

            try:
                # Prompt the user to select the target repository
                print("\n[INFO] Available Target Repositories:")
                for idx, repository in enumerate(target_repositories, 1):
                    print(f"{idx} - {repository['name']} (id: {repository['id']})")
                repository_selection = input("\nEnter the number of the target repository to commit the configuration file to (or press Enter to skip): ").strip()

                if repository_selection.isdigit():
                    repository_index = int(repository_selection) - 1
                    if 0 <= repository_index < len(target_repositories):
                        target_repository = target_repositories[repository_index]
                    else:
                        print(f"[WARNING] Invalid repository selection. Skipping pipeline '{pipeline_name}'.")
                        continue
                else:
                    print(f"[WARNING] No valid repository selected. Skipping pipeline '{pipeline_name}'.")
                    continue

                # Update pipeline configuration to use Git
                adjusted_pipeline_config = adjust_pipeline_config(target_projects, pipeline_config, target_repository)
                create_pipeline(TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER, adjusted_pipeline_config)

            except Exception as e:
                print(f"[ERROR] Failed during pipeline migration for '{pipeline_name}': {e}")
                continue

if __name__ == "__main__":
    migrate_pipelines(SOURCE_ORGANIZATION, TARGET_ORGANIZATION, SOURCE_PROJECT, TARGET_PROJECT, SOURCE_AUTHENTICATION_HEADER, TARGET_AUTHENTICATION_HEADER)