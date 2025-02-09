import os
import base64
import requests
import json
import yaml
import re
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

def get_source_pipelines():
    """
    This function fetches the pipelines from the source project.
    """
    url = f"{SOURCE_ORGANIZATION}/{SOURCE_PROJECT}/_apis/pipelines?api-version=6.0-preview"

    print("##############################")
    print(f"[INFO] Fetching pipelines from '{SOURCE_PROJECT}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=SOURCE_AUTHENTICATION_HEADER)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            pipelines = response.json().get("value", []) # Parses the JSON response and retrieves the list of pipelines from the value field.
            print(f"[INFO] There are {len(pipelines)} pipelines in '{SOURCE_ORGANIZATION}'.")

            for pipeline in pipelines:
                print(f"- Pipeline id: {pipeline['id']} | Name: {pipeline['name']}")

            return pipelines
        
        else:
            print(f"[ERROR] Failed to fetch pipelines.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return []

    except requests.exceptions.RequestException as e: # Catches any exceptions that occur during the HTTP request (e.g., connection issues, timeouts).
        print(f"[ERROR] An error occurred while fetching the pipelines: {e}")
        return []
    
def get_pipeline_config(pipeline_id):
    """
    This function fetches the configuration of a pipeline.
    """
    url = f"{SOURCE_ORGANIZATION}/{SOURCE_PROJECT}/_apis/build/definitions/{pipeline_id}?api-version=6.0-preview"

    print(f"[INFO] Fetching the configuration of pipeline id {pipeline_id} from '{SOURCE_PROJECT}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=SOURCE_AUTHENTICATION_HEADER)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            pipeline_config = response.json()
            print(f"[INFO] Successfully retrieved configuration for pipeline id {pipeline_id}.")
            print(f"\n[DEBUG] Raw Configuration:\n{json.dumps(pipeline_config, indent=4)}\n")  # Prettified JSON for better readability.

            return pipeline_config
        
        else:
            print(f"[ERROR] Failed to fetch pipeline configuration for pipeline id {pipeline_id}.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching pipeline configuration: {e}")
        return None

def get_pipeline_yaml(organization, project, pipeline_id, authentication_header):
    """
    This function fetches the YAML content of a pipeline.
    """
    url = f"{organization}/{project}/_apis/build/definitions/{pipeline_id}/yaml?api-version=6.0-preview"

    print("##############################")
    print(f"[INFO] Fetching the configuration of pipeline id {pipeline_id} from '{SOURCE_PROJECT}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            pipeline_yaml = response.json()["yaml"] # Extracts the "yaml" field from the response.
            # The "yaml" field contains the actual pipeline definition written in YAML format.

            return yaml.safe_load(pipeline_yaml) # Converts the YAML string into a Python dictionary for further manipulation.
        
        else:
            print(f"[ERROR] Failed to fetch pipeline configuration for pipeline id {pipeline_id}.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching pipeline configuration: {e}")
        return None

def extract_branches_from_pipeline_yaml(exported_yaml_config):
    """
    This function extracts branch names from the 'trigger' section of the exported YAML file.
    """
    print("##############################")
    print("[INFO] Starting branch extraction from pipeline YAML configuration...")

    branches = []

    if "trigger" in exported_yaml_config and "paths" in exported_yaml_config["trigger"]:
        print("[INFO] Found 'trigger' section with 'paths'. Processing paths...")

        paths = (
            exported_yaml_config["trigger"]["paths"].get("include", []) +
            exported_yaml_config["trigger"]["paths"].get("exclude", [])
        )
        print(f"[DEBUG] Paths to process: {paths}")

        for path in paths:
            branch_match = re.match(r"^\$/[^/]+/([^/]+)/", path)

            if branch_match:
                branch_name = branch_match.group(1)
                branches.append(branch_name)

            else:
                print(f"[WARNING] No branch match found for path: {path}")

    else:
        print("[WARNING] 'trigger' section or 'paths' not found in pipeline YAML configuration.")

    unique_branches = list(set(branches))
    print(f"[INFO] Extracted unique branches: {unique_branches}")

    return unique_branches

def get_agent_pools(organization, authentication_header):
    """
    This function fetches the available agent pool(s) for an organization.
    """
    url = f"{organization}/_apis/distributedtask/pools?api-version=6.0-preview"

    print(f"\n[INFO] Fetching the available agent pool(s) for '{organization}'...")
    print(f"[DEBUG] API URL: {url}")

    response = requests.get(url, headers=authentication_header)
    print(f"[DEBUG] Request's Status Code: {response.status_code}")

    if response.status_code == 200:
        pools = response.json().get("value", [])
        filtered_pools = [pool for pool in pools if not pool.get("isLegacy", True)] # Ensures the user is only presented with relevant and supported agent pools.

        if not filtered_pools:
            print("[WARNING] No non-legacy agent pools available.")

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
                print("[ERROR] Invalid choice. Please select a valid option.")

        except ValueError:
            print("[ERROR] Invalid input. Please enter a number.")

def convert_to_yaml(pipeline_config, pipeline_yaml_config, target_repository, selected_target_branch):
    """
    This function converts a classic Azure DevOps pipeline configuration into a YAML string format compatible with YAML-based pipelines.
    """
    print("##############################")
    print("[INFO] Converting the classic pipeline logic into a YAML string logic...")

    """
    In the "pool" section there are two possible scenarios: 1. A Microsoft-hosted agent pool 2. A self-hosted agent pool.
    - If the current pipeline uses a Microsoft-hosted agent pool, then in the "pool" section will be specified the "vmImage" variable.
    - If the current pipeline uses a self-hosted agent pool, then in the "pool" section will be specified the "name" variable.
    """
    yaml_format_pipeline = {
        "trigger": [], # Defines the branches that will trigger the pipeline automatically.
        "pool": {}, # Specifies the agent pool that Azure DevOps will use to run the pipeline.
        "variables": {},
        "steps": [] # Holds a list of steps (tasks) to execute during the pipeline. This is initialized as an empty list and populated later.
    }

    # Configures the "trigger" section based on the pipeline configuration.
    # Uses the 'trigger' section from the exported YAML file.
    if "trigger" in pipeline_yaml_config:
        exported_trigger = pipeline_yaml_config["trigger"]

        # Initializes the Git-compatible trigger structure.
        git_trigger = {"branches": {"include": extract_branches_from_pipeline_yaml(pipeline_yaml_config)}, "paths": {"include": [], "exclude": []}}

        extracted_branch = None
        branches_set = set()

        # Adjusts paths to a Git-compatible format.
        if "paths" in exported_trigger:
            for path in exported_trigger["paths"].get("include", []):
                adjusted_path = re.sub(r"^\$\S+?/", "", path)  # Removes the '$/...' part.
                adjusted_path = re.sub(r"^[^/]+?/", "", adjusted_path)  # Removes the '/.../' part.
                git_trigger["paths"]["include"].append(adjusted_path)

            for path in exported_trigger["paths"].get("exclude", []):
                adjusted_path = re.sub(r"^\$\S+?/", "", path)  # Removes the '$/...' part.
                adjusted_path = re.sub(r"^[^/]+?/", "", adjusted_path)  # Removes the '/.../' part.
                git_trigger["paths"]["exclude"].append(adjusted_path)

        # Ensures the branch where the YAML file will be committed to is included.
        git_trigger["branches"]["include"].append(selected_target_branch)

        # Removes duplicates (if any).
        git_trigger["branches"]["include"] = list(set(git_trigger["branches"]["include"]))

        yaml_format_pipeline["trigger"] = git_trigger

    elif "options" in pipeline_config:
        branch_filters = []

        for option in pipeline_config["options"]:
            if option.get("enabled") and "inputs" in option:
                filters = option["inputs"].get("branchFilters", "[]")
                filters_list = json.loads(filters) # Converts the "filters" variable from a stringified JSON list to a Python list.

                # Extracts branch names, removing the "+refs/heads/" prefix.
                for branch_filter in filters_list:
                    if branch_filter.startswith("+refs/heads/"):
                        branch_filters.append(branch_filter.replace("+refs/heads/", ""))

                    # Filters start with "-refs/heads/" indicate branches that should not trigger the pipeline.
                    elif branch_filter.startswith("-refs/heads/"):
                        continue

        yaml_format_pipeline["trigger"] = branch_filters or [target_repository["defaultBranch"].replace("refs/heads/", "")]

    # Configures the "pool" section based on the available agent pools.
    pools = get_agent_pools(TARGET_ORGANIZATION, TARGET_AUTHENTICATION_HEADER)
    
    selected_pool = choose_agent_pool(pools)
    yaml_format_pipeline["pool"] = {"name": selected_pool["name"]}

    """
    Classic pipelines rely on "displayName" to describe each step. They don't include the exact task name and version required by YAML pipelines.
    The purpose of the mapping is to translate "displayName" (human-readable descriptions of tasks in the classic pipeline) into the correct task identifiers used in YAML pipelines.
    """
    task_name_mapping = {
        step.get("displayName", ""): step.get("task", "")
        for phase in pipeline_yaml_config.get("jobs", [])
        for step in phase.get("steps", [])
        if "task" in step
    }

    """
    There might be cases where the "variables" field within the pipeline's configuration file is empty but populated in the exported YAML file, and vice-versa.
    The script will check both configuration files and populate the new generated configuration file with the one that is populated, giving preference to the exported YAML if both
    are populated.
    """
    # Extracts the "variables" section from the exported YAML file.
    yaml_variables = pipeline_yaml_config.get("variables", [])
    exported_variables = {}

    # Processes the "variables" into the desired format.
    for variable in yaml_variables:
        if isinstance(variable, dict) and "name" in variable and "value" in variable:
            name_parts = variable["name"].split(".")[-1]  # Extracts only the last part of the variable name.
            exported_variables[name_parts] = variable["value"]

    # Extracts the "variables" section from the classic pipeline configuration
    config_variables = pipeline_config.get("variables", {})
    classic_variables = {}

    # Process variables if available in classic pipeline config
    if config_variables:
        for var_name, var_props in config_variables.items():
            if isinstance(var_props, dict) and "value" in var_props:
                classic_variables[var_name] = var_props["value"]

            else:
                classic_variables[var_name] = var_props

    # Preferes the exported YAML's "variables" section if both are populated, otherwise fallback.
    if exported_variables:
        yaml_format_pipeline["variables"] = exported_variables
        print("[INFO] Using variables from the exported YAML file.")

    elif classic_variables:
        yaml_format_pipeline["variables"] = classic_variables
        print("[INFO] Using variables from the classic pipeline configuration.")
        
    else:
        print("[WARNING] No variables found in either configuration.")
    
    #yaml_format_pipeline["variables"] = formatted_variables


    for phase in pipeline_config["process"]["phases"]: # Extracts all phases in the classic pipeline's process configuration.
        for step in phase["steps"]: # Extracts all steps within the current phase.
            if "task" in step: # Task handling.
                display_name = step["displayName"]

                # Uses the mapped task name if available. If not, the "displayName" field will be used.
                task_name = task_name_mapping.get(display_name, display_name)

                inputs = step.get("inputs", {})

                # Filters out unconfigured inputs.
                filtered_inputs = {k: v for k, v in inputs.items() if v not in [None, "", "false", "latest"]}

                if "script" in inputs:
                    yaml_format_step = {
                        "script": inputs["script"],
                        "displayName": display_name
                    }
                else:
                    yaml_format_step = {
                        "task": f"{task_name}",
                        "displayName": display_name,
                        "inputs": filtered_inputs
                    }

            elif "script" in step: # Inline script handling.
                yaml_format_step = {
                    "script": step["script"],
                    "displayName": step["displayName"]
                }
                if "continueOnError" in step:
                    yaml_format_step["continueOnError"] = step["continueOnError"]
                if "enabled" in step:
                    yaml_format_step["enabled"] = step["enabled"]

            else:
                raise ValueError(f"[ERROR] Unknown step type: {step}")

            yaml_format_pipeline["steps"].append(yaml_format_step)
            print(f"[DEBUG] Added step: {yaml_format_step}")

    yaml_string = yaml.dump(yaml_format_pipeline, sort_keys=False, default_flow_style=False)
    print("[DEBUG] Generated YAML format pipeline:\n", yaml_string)

    return yaml_string

def commit_yaml_to_target_repository(pipeline_name, yaml_pipeline_file, target_repository, selected_target_branch):
    """
    This function commits the generated YAML file to the target repository.
    """
    repository_id = target_repository["id"] # Used to identify the target repository in Azure DevOps' API.
    repository_name = target_repository["name"]
    yaml_file_name = f"azure-pipelines-{pipeline_name}.yml"
    url_commit = f"{TARGET_ORGANIZATION}/{TARGET_PROJECT}/_apis/git/repositories/{repository_id}/commits?api-version=6.0-preview"
    url_push = f"{TARGET_ORGANIZATION}/{TARGET_PROJECT}/_apis/git/repositories/{repository_id}/pushes?api-version=6.0-preview"

    print("##############################")
    print(f"[INFO] Committing YAML file '{yaml_file_name}' to repository '{repository_name}'...")

    # Fetches the latest commit id from the target repository.
    response = requests.get(url_commit, headers=TARGET_AUTHENTICATION_HEADER)
    print(f"[DEBUG] Request's Status Code: {response.status_code}")

    if response.status_code == 200:
        latest_commit = response.json()['value'][0]['commitId']
        print(f"[INFO] Latest commit id fetched: {latest_commit}")

    else:
        raise Exception(f"[ERROR] Failed to fetch the latest commit id | Request's Status Code: {response.status_code} | Response Body: {response.text}")

    #extracted_branches = extract_branches_from_pipeline_yaml(exported_yaml_config)

    # Validates the YAML file.
    yaml.safe_load(yaml_pipeline_file)

    # Commit payload.
    payload = {
        "refUpdates": [
            {
                "name": f"refs/heads/{selected_target_branch}", # Specifies which branch the YAML file will be committed to.
                "oldObjectid": latest_commit
            }
        ],
        "commits": [
            {
                "comment": f"Add {yaml_file_name} for pipeline migration",
                "changes": [
                    {
                        "changeType": "add",
                        "item": {
                            "path": f"/{yaml_file_name}"
                        },
                        "newContent": {
                            "content": yaml_pipeline_file,
                            "contentType": "rawtext"
                        }
                    }
                ]
            }
        ]
    }
    print("\n[DEBUG] Commit Payload:", json.dumps(payload, indent=4))

    response = requests.post(url_push, headers=TARGET_AUTHENTICATION_HEADER, json=payload)
    print(f"\n[DEBUG] Request's Status Code: {response.status_code}")

    if response.status_code == 201:
        print(f"[INFO] Successfully committed the YAML file to {target_repository['name']}.")
        return True
    
    else:
        print(f"[ERROR] Failed to commit the YAML file.")
        print(f"Request's Status Code: {response.status_code}")
        print(f"[DEBUG] Response Body: {response.text}")
        return False

def adjust_pipeline_config(pipeline_config, target_repositories): # DEPRECATED.
    """
    This function adjusts the pipeline configuration from a classic pipeline form (web editor) to YAML-based pipeline form.
    """
    print("##############################")
    print(f"[INFO] Adjusting configuration for pipeline '{pipeline_config.get('name')}'...")

    repository_name = "migrationTargetProject"  # The target repository where the YAML pipeline will be stored.

    target_repository = next((repository for repository in target_repositories if repository["name"] == repository_name), None) # Ensures that "repository_name" is valid and available in the target project.
    if not target_repository:
        raise ValueError(f"[ERROR] repository '{repository_name}' not found in '{TARGET_ORGANIZATION}'.")

    # Checks if "target_repository" contains the required "id" and "name" fields.
    if "id" not in target_repository or "name" not in target_repository:
        raise ValueError(f"[ERROR] Invalid repository structure:\n{json.dumps(target_repository, indent=4)}")

    yaml_file_location = "azure-pipelines.yml"

    return {
        "name": pipeline_config["name"],
        "configuration": {
            "path": yaml_file_location,
            "repository": {
                "id": target_repository["id"],
                "type": "azurerepositorysGit",  # Ensure 'azurerepositorysGit' is used
                "name": target_repository["name"]
            },
            "type": "yaml"
        }
    }

def create_target_pipeline(pipeline_config): # DEPRECATED.
    """
    This functionCreates a new pipeline in the target Azure DevOps project.
    """
    url = f"{TARGET_ORGANIZATION}/{TARGET_PROJECT}/_apis/pipelines?api-version=7.0"

    print("##############################")
    print(f"[INFO] Creating pipeline '{pipeline_config.get('name')}' in '{TARGET_PROJECT}'...")
    print(f"[DEBUG] API URL: {url}")
    print(f"[DEBUG] Final Payload:\n{json.dumps(pipeline_config, indent=4)}")

    try:
        response = requests.post(url, headers=TARGET_AUTHENTICATION_HEADER, json=pipeline_config)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 201:
            created_pipeline = response.json()
            print(f"[INFO] Successfully created pipeline: {created_pipeline.get('name')} with id: {created_pipeline.get('id')}")
            return created_pipeline
        
        else:
            print(f"[ERROR] Failed to create pipeline: {pipeline_config.get('name')}.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while creating the pipeline: {e}")
        return None

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
            print(f"[ERROR] Invalid selection: {e}")
            return select_pipelines_to_migrate(pipelines) # On invaild choice, the user will be prompted again.

def select_commit_branch(target_repository, yaml_branches):
    """
    This function fetches branches from the target repository and prompts the user to select one.
    """
    url = f"{TARGET_ORGANIZATION}/{TARGET_PROJECT}/_apis/git/repositories/{target_repository['id']}/refs?filter=heads/&api-version=6.0"
    response = requests.get(url, headers=TARGET_AUTHENTICATION_HEADER)

    if response.status_code != 200:
        raise Exception(f"[ERROR] Failed to fetch branches | Response Body: {response.text}")

    branches = response.json()["value"]
    branch_names = [branch["name"].replace("refs/heads/", "") for branch in branches]

    # Validates that the 'trigger' branches are exist in the target repository.
    if yaml_branches:
        print("\n[INFO] Validating branches from the exported YAML file...")

        missing_branches = [branch for branch in yaml_branches if branch not in branch_names]

        if missing_branches:
            print(f"\033[1;33m[WARNING] The following branches from the YAML file do not exist in the target repository: {missing_branches}\033[0m")
        else:
            print("[INFO] All branches from the YAML file exist in the target repository.")

    print(f"\n[INFO] Available Branches in the Target Repository ({target_repository['name']}):")
    for idx, branch_name in enumerate(branch_names, start=1):
        print(f"{idx} - {branch_name}")
        
    user_choice = input("\nSelect a branch by number: ").strip()

    if user_choice.isdigit():
        user_choice = int(user_choice)
        if 1 <= user_choice <= len(branch_names):
            return branch_names[user_choice - 1]
        else:
            raise ValueError("[ERROR] Invalid branch selection.")
    else:
        raise ValueError("[ERROR] Please select a valid number from the list.")

def migrate_pipelines(source_organization, target_organization, source_project, target_project, source_headers, target_headers):
    """
    This function migrates TFVC-based pipelines from a source project to a target project.
    """
    print("\n\033[1;33mEnsure the trigger branches are exist in your target environment before starting the migration.\033[0m")
    print("\033[1;33mEnsure you have configured agent pools in your target environment before starting the migration.\033[0m\n")
    print("[INFO] Starting pipeline migration process...")
    print(f"[DEBUG] Source Organization: {source_organization}")
    print(f"[DEBUG] Target Organization: {target_organization}")
    print(f"[DEBUG] Source Project: {source_project}")
    print(f"[DEBUG] Target Project: {target_project}")

    try:
        # Fetches target repositories.
        target_repositories = requests.get(
            f"{target_organization}/{target_project}/_apis/git/repositories?api-version=6.0-preview",
            headers=target_headers
        ).json()["value"]

    except Exception as e:
        print(f"[ERROR] Failed to fetch target repositories: {e}")
        return

    try:
        # Fetches pipelines from the source project.
        pipelines = get_source_pipelines()

    except Exception as e:
        print(f"[ERROR] Failed to fetch pipelines from the source project: {e}")
        return

    if pipelines:
        print("\n[INFO] Fetching pipelines completed.")
        selected_pipeline_ids = select_pipelines_to_migrate(pipelines)

        for pipeline in pipelines:
            if pipeline["id"] in selected_pipeline_ids:
                try:
                    print(f"##############################>-{pipeline['name']}-<##############################")
                    pipeline_id = pipeline["id"]
                    pipeline_name = pipeline["name"]
                    pipeline_config = get_pipeline_config(pipeline_id)

                    # Fetches the YAML format of the pipeline.
                    yaml_content = get_pipeline_yaml(
                        source_organization,
                        source_project,
                        pipeline_id,
                        source_headers
                    )

                except Exception as e:
                    print(f"[ERROR] Failed to fetch or process pipeline '{pipeline['name']}': {e}")
                    continue

                try:
                    # Prompts the user to choose which repository to commit to.
                    print("\n[INFO] Available Target Repositories:")
                    for idx, repository in enumerate(target_repositories, 1):
                        print(f"{idx} - {repository['name']} (id: {repository['id']})")
                    repository_selection = input("\nEnter the number of the target repository to commit the newly generated configuration file to (or press Enter for all): ").strip()

                    if repository_selection.isdigit():
                        repository_index = int(repository_selection) - 1
                        if 0 <= repository_index < len(target_repositories):
                            target_repositories = [target_repositories[repository_index]]
                        else:
                            print(f"[WARNING] Invalid repository selection. Proceeding with all repositories.")

                    print(f"[DEBUG] Target repositories list:\n{json.dumps(target_repositories, indent=4)}\n")

                except Exception as e:
                    print(f"[ERROR] Failed during repository selection: {e}")
                    continue

                # Migrates the pipeline(s) to the selected repositories.
                for repository in target_repositories:
                    yaml_branches = extract_branches_from_pipeline_yaml(yaml_content)
                    selected_target_branch = select_commit_branch(repository, yaml_branches)
                    
                    try:
                        if isinstance(repository, dict):  # Ensures repository is a dictionary
                            generated_yaml = convert_to_yaml(pipeline_config, yaml_content, repository, selected_target_branch)
                            success = commit_yaml_to_target_repository(pipeline_name, generated_yaml, repository, selected_target_branch)

                            if success:
                                print(f"\033[1;32m[SUCCESS] Pipeline '{pipeline_name}' migrated to repository '{repository['name']}'.\033[0m")

                            else:
                                print(f"\033[1;31m[ERROR] Failed to migrate pipeline '{pipeline_name}' to repository '{repository['name']}'.\033[0m")

                        else:
                            print(f"\033[1;31m[ERROR] Invalid repository object: {repository}\033[0m")

                    except Exception as e:
                        print(f"\033[1;31m[ERROR] An error occurred while migrating pipeline '{pipeline_name}' to repository '{repository['name']}': {e}\033[0m")
    else:
        print("[INFO] No pipelines found to migrate.")

if __name__ == "__main__":
    migrate_pipelines(SOURCE_ORGANIZATION, TARGET_ORGANIZATION, SOURCE_PROJECT, TARGET_PROJECT, SOURCE_AUTHENTICATION_HEADER, TARGET_AUTHENTICATION_HEADER)