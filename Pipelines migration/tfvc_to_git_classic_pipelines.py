import os
import base64
import requests
import json
from datetime import datetime, UTC
import re
from dotenv import load_dotenv

load_dotenv()

SOURCE_ORGANIZATION=os.getenv("SOURCE_ORGANIZATION")
SOURCE_PROJECT=os.getenv("SOURCE_PROJECT")
SOURCE_PAT = os.getenv("SOURCE_PAT")

GAU_TARGET_ORGANIZATION=os.getenv("GAU_TARGET_ORGANIZATION") # The target organization without the 'https://dev.azure.com/' part, only the name.
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

def get_pipelines(organization, project_name, authentication_header):
    """
    This function fetches the build pipelines of a project.
    """
    api_version = "6.0-preview"
    url = f"{organization}/{project_name}/_apis/pipelines?api-version={api_version}"

    print(f"[INFO] Fetching pipelines from '{project_name}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            pipelines = response.json().get("value", []) # Parses the JSON response and retrieves the list of pipelines from the value field.
            print(f"[INFO] There are {len(pipelines)} pipelines in '{organization}':")

            for pipeline in pipelines:
                print(f"• Pipeline id: {pipeline['id']} | Name: {pipeline['name']}")

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

    print("\n##############################")
    print(f"[INFO] Fetching the users of the '{organization}' organization...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            users = response.json().get("members", [])

            print(f"\nFound {len(users)} users in '{organization}' organization:")
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

    print("\n##############################")
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

def get_queues(organization, project_name, authentication_header):
    api_version = "6.0-preview"
    url = f"{organization}/{project_name}/_apis/distributedtask/queues?api-version={api_version}"

    print("\n##############################")
    print(f"[INFO] Fetching the queues of the '{project_name}' project...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            queues = response.json().get("value", [])
            #print(f"[INFO] There are {len(queues)} queues in '{project_name}' project.")

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

    print("\n##############################")
    print(f"[INFO] Fetching the available agent pool(s) for '{organization}'...")
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

def get_git_target_details():
    """
    This function prompts the user to provide information the target Git environment the build pipeline will be migrated to.
    """
    print("\n\033[1;33mPlease provide information about the Git repository containing the relevant codebase for the current migrated pipeline.\033[0m")
    
    print("\nAvailable Git repositories in the target project:")

    api_version = "6.0-preview"
    target_repositories = requests.get(
            f"{TARGET_ORGANIZATION}/{TARGET_PROJECT}/_apis/git/repositories?api-version={api_version}",
            headers=TARGET_AUTHENTICATION_HEADER
        ).json()["value"]
    
    for idx, repo in enumerate(target_repositories, 1):
        print(f"{idx} - {repo['name']}")
    
    repository_choice = input("\nSelect the repository number (select the repository containing the relevant codebase for the current migrated pipeline): ")
    selected_repository = target_repositories[int(repository_choice) - 1]

    print("\nAvailable branches in the selected repository:")

    branches = requests.get(
            f"{TARGET_ORGANIZATION}/{TARGET_PROJECT}/_apis/git/repositories/{selected_repository['id']}/refs?filter=heads/&api-version={api_version}",
            headers=TARGET_AUTHENTICATION_HEADER
        ).json()["value"]
    
    for idx, branch in enumerate(branches, 1):
        clean_branch_name = branch["name"].replace('refs/heads/', '')
        print(f"{idx} - {clean_branch_name}")
    
    branch_choice = input("\nSelect the branch number (select the branch containing the relevant codebase for the current migrated pipeline): ")
    selected_branch = branches[int(branch_choice) - 1]
    
    return {
        'repository': selected_repository,
        'branch': selected_branch
    }

def update_repository_section(pipeline_json_config, git_details):
    """
    This function adjusts the 'repository' section of a build pipeline based on user-provided information.
    """
    tfvc_path = pipeline_json_config['repository'].get('defaultBranch')
    print(f"\n\033[1mThe default TFVC branch of the '{pipeline_json_config['name']}' pipeline: {tfvc_path}\033[0m")
    
    # Get user input about Git target
    #git_details = get_git_target_details()
    clean_branch_name = git_details["branch"]["name"].replace('refs/heads/', '')
    # Update the repository configuration
    pipeline_json_config['repository'].update({
        'id': git_details["repository"]["id"],
        'type': "TfsGit",
        'name': git_details["repository"]["name"],
        'defaultBranch': f"refs/heads/{clean_branch_name}",
        'url': git_details["repository"]["url"]
    })

    pipeline_json_config.pop("rootFolder", None)
    
    print(f"\n[INFO] In the target environment, the '{pipeline_json_config['name']}' pipeline has been configured to monitor:")
    print(f"• Repository: {git_details["repository"]["name"]}")
    print(f"• Branch: {clean_branch_name}")
    
    return pipeline_json_config

def update_triggers_section(triggers_section, target_repository):
    """
    This function adjusts the 'triggers' section of a build pipeline.
    """
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
    """
    This function adjusts the 'queue' (and additional queue-related staff) section of a build pipeline.
    """
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
            raise Exception(f"\033[1;31mNo queue found for pool '{source_pool_name}' in '{TARGET_ORGANIZATION}'.\033[0m")

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

def get_task_groups(organization, project_name, authentication_header):
    """
    This function fetches all task groups from a project.
    """
    api_version = "6.0-preview"
    url = f"{organization}/{project_name}/_apis/distributedtask/taskgroups?api-version={api_version}"

    print("\n##############################")
    print(f"[INFO] Fetching task groups from '{project_name}' in '{organization}'...")
    
    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            task_groups = response.json().get("value", [])
            return task_groups
        
        else:
            print(f"\033[1;31m[ERROR] Failed to fetch task groups from '{project_name}' project.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching task groups: {e}\033[0m")
        return None

def handle_task_groups(pipeline_json_config):
    """
    This function adjusts task group references in a build pipeline to match the target environment.
    """
    target_task_groups = get_task_groups(TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER)

    for phase in pipeline_json_config.get("process", {}).get("phases", []):
        for step in phase.get("steps", []):
            if step.get("task", {}).get("definitionType") == "metaTask": # In Azure DevOps, when a task is another task group, its 'definitionType' field will be 'metaTask'.
                display_name = step.get("displayName")

                # Maps the source task group with its respective target task group.
                matching_task_group = None
                for task_group in target_task_groups:
                    if task_group["name"] in display_name:
                        matching_task_group = task_group
                        break

                if matching_task_group:
                    step["task"].update({"id": matching_task_group["id"], "definitionType": "metaTask"})

                else:
                    raise Exception(
                        f"\033[1;31mCould not find a matching task group for '{display_name}' in the target environment.\033[0m"
                        "\n[INFO] Please ensure all required task groups exist before migrating the pipeline."
                    )

    return pipeline_json_config

def get_variable_groups(organization, project_name, authentication_header):
    '''
    This function fetches all variable groups from a project.
    '''
    api_version = "6.0-preview"
    url = f"{organization}/{project_name}/_apis/distributedtask/variablegroups?api-version={api_version}"

    print("\n##############################")
    print(f"[INFO] Fetching variable groups from '{project_name}' project in '{organization}'...")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            variable_groups = response.json().get("value", [])
            return variable_groups

        else:
            print(f"\033[1;31m[ERROR] Failed to fetch variable groups from '{project_name}' project.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while fetching variable groups: {e}\033[0m")
        return None

def handle_variable_groups(pipeline_json_config):
    """
    This function adjusts variable group references in a build pipeline to match the target environment.
    """
    target_variable_groups = get_variable_groups(TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER)
    
    if "variableGroups" in pipeline_json_config:
        for variable_group in pipeline_json_config["variableGroups"]:
            variable_group_name = variable_group.get("name")
            
            # Maps the source variable group with its respective target variable group.
            matching_variable_group = None
            for target_variable_group in target_variable_groups:
                if target_variable_group["name"] == variable_group_name:
                    matching_variable_group = target_variable_group
                    break
            
            if matching_variable_group:
                variable_group["id"] = matching_variable_group["id"]

            else:
                raise Exception(
                    f"\033[1;31mCould not find a matching variable group for '{variable_group_name}' in the target environment.\033[0m"
                    "\n[INFO] Please ensure all required variable groups exist before migrating the pipeline."
                )
    
    return pipeline_json_config

def handle_service_connections(pipeline_json_config):
    source_service_connections = get_service_connections(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER)
    target_service_connections = get_service_connections(TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER)

    # Creates a mapping of service connection names to their ids in the target environment for more efficient lookup.
    target_connections_by_name = {tsc["name"]: tsc["id"] for tsc in target_service_connections}

    for phase in pipeline_json_config.get("process", {}).get("phases", []):
        for step in phase.get("steps", []):
            if step.get("inputs", {}).get("externalEndpoints"): # Checks if the current step has inputs and uses service connections.
                source_service_connection_id = step["inputs"]["externalEndpoints"]
                
                # Extracts the name of the source service connection.
                source_service_connection = next((ssc for ssc in source_service_connections if ssc["id"] == source_service_connection_id), None)
                
                if source_service_connection:
                    ssc_name = source_service_connection["name"]

                    if ssc_name in target_connections_by_name:
                        step["inputs"]["externalEndpoints"] = target_connections_by_name[ssc_name]

                    else:
                        raise Exception(
                            f"Service connection '{ssc_name}' not found in target environment.\n"
                            f"Available service connections:\n"
                            f"- " + "\n- ".join(target_connections_by_name.keys())
                        )
                else:
                    raise Exception(
                        f"Could not find source service connection with id: {source_service_connection_id}."
                    )

    return pipeline_json_config

def adjust_pipeline_config(pipeline_json_config, git_details):
    """
    This function adjusts the pipeline configuration file to use Git as the source.
    """
    # Adjusts the 'triggers' section.
    #triggers = pipeline_json_config.get('triggers', [])
    #adjusted_triggers_section = update_triggers_section(triggers, target_repository)

    #pipeline_json_config["triggers"] = adjusted_triggers_section

    # Adjusts the 'repository' section.
    pipeline_json_config = update_repository_section(pipeline_json_config, git_details)

    # Adjusts the 'properties' sub-section.
    properties = pipeline_json_config["repository"].get('properties', {})

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
    pipeline_json_config = update_queue_section(pipeline_json_config, available_pools_map, available_target_pools)
    
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
    pipeline_json_config["queueStatus"] = 0
    pipeline_json_config["revision"] = 1
    pipeline_json_config["createdDate"] = datetime.now(UTC).isoformat()

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
    
    # Adjusts task groups.
    pipeline_json_config = handle_task_groups(pipeline_json_config)

    # Adjusts variable groups.
    pipeline_json_config = handle_variable_groups(pipeline_json_config)

    # Adjusts service connections.
    pipeline_json_config = handle_service_connections(pipeline_json_config)

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
                raise ValueError("\033[1;31m[ERROR] No valid pipelines selected.\033[0m")
            
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

    print("\033[1m=\033[0m" * 100)
    print(f"[DEBUG] Source Organization: {source_organization}")
    print(f"[DEBUG] Target Organization: {target_organization}")
    print(f"[DEBUG] Source Project: {source_project}")
    print(f"[DEBUG] Target Project: {target_project}")
    print("\033[1m=\033[0m" * 100)

    print("\n[INFO] Starting pipeline migration process...\n")

    try:
        source_pipelines = get_pipelines(source_organization, source_project, source_headers)

    except Exception as e:
        print(f"\033[1;31m[ERROR] Failed to fetch pipelines from the source project: {e}\033[0m")
        return None

    if not source_pipelines:
        print(f"\033[1m[INFO] No pipelines found in the '{source_project}' project in the '{source_organization}' organization.\033[0m")
        return None

    print("\n\033[1m[INFO] Fetching pipelines completed.\033[0m")
    selected_pipeline_ids = select_pipelines_to_migrate(source_pipelines)

    for pipeline in source_pipelines:
        if pipeline["id"] in selected_pipeline_ids:
            try:
                print(f"\n##############################>-{pipeline['name']}<##############################")
                pipeline_id = pipeline["id"]
                pipeline_name = pipeline["name"]
                pipeline_config = get_pipeline_config(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, pipeline_id)

            except Exception as e:
                print(f"\033[1;31m[ERROR] Failed to fetch or process pipeline '{pipeline['name']}': {e}\033[0m")
                continue

            try:
                # Prompts the user to provide information about the target Git environment.
                git_details = get_git_target_details()

                adjusted_pipeline_config = adjust_pipeline_config(pipeline_config, git_details)
                create_pipeline(TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER, adjusted_pipeline_config)

            except Exception as e:
                print(f"\033[1;31m[ERROR] Failed during pipeline migration for '{pipeline_name}': {e}\033[0m")
                continue

if __name__ == "__main__":
    migrate_pipelines(SOURCE_ORGANIZATION, TARGET_ORGANIZATION, SOURCE_PROJECT, TARGET_PROJECT, SOURCE_AUTHENTICATION_HEADER, TARGET_AUTHENTICATION_HEADER)