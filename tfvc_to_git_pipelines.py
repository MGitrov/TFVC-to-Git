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

def list_source_pipelines():
    """
    This function lists the pipelines from the source project.
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
                print(f"  - Pipeline ID: {pipeline["id"]} | Name: {pipeline["name"]}")

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

    print("##############################")
    print(f"[INFO] Fetching the configuration of pipeline ID {pipeline_id} from '{SOURCE_PROJECT}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=SOURCE_AUTHENTICATION_HEADER)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")
        
        if response.status_code == 200:
            pipeline_config = response.json()
            print(f"[INFO] Successfully retrieved configuration for pipeline ID {pipeline_id}.")
            print(f"[DEBUG] Raw Configuration:\n{json.dumps(pipeline_config, indent=4)}")  # Prettified JSON for better readability.

            return pipeline_config
        
        else:
            print(f"[ERROR] Failed to fetch pipeline configuration for pipeline ID {pipeline_id}.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching pipeline configuration: {e}")
        return None

def fetch_pipeline_yaml(organization, project, pipeline_id, authentication_header):
    """
    This function fetches the YAML content of a pipeline.
    """
    url = f"{organization}/{project}/_apis/build/definitions/{pipeline_id}/yaml?api-version=6.0-preview"

    print("##############################")
    print(f"[INFO] Fetching the configuration of pipeline ID {pipeline_id} from '{SOURCE_PROJECT}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            pipeline_yaml = response.json()["yaml"] # Extracts the "yaml" field from the response.
            # The "yaml" field contains the actual pipeline definition written in YAML format.

            return yaml.safe_load(pipeline_yaml) # Converts the YAML string into a Python dictionary for further manipulation.
        
        else:
            print(f"[ERROR] Failed to fetch pipeline configuration for pipeline ID {pipeline_id}.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching pipeline configuration: {e}")
        return None

def fetch_agent_pools(organization, authentication_header):
    """
    This function fetches the list of the available agent pool(s) for an organization.
    """
    url = f"{organization}/_apis/distributedtask/pools?api-version=6.0-preview"

    print("##############################")
    print(f"[INFO] Fetching the available agent pool(s) for '{organization}'...")
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
    print("\n[INFO] Available Agent Pools:")
    for idx, pool in enumerate(pools):
        print(f"{idx + 1} - {pool["name"]} (ID: {pool["id"]}, Hosted: {pool.get("isHosted", False)})")

    while True:
        try:
            choice = int(input("\nEnter the number corresponding to your desired agent pool: ")) - 1
            if 0 <= choice < len(pools):
                return pools[choice]
            else:
                print("[ERROR] Invalid choice. Please select a valid option.")

        except ValueError:
            print("[ERROR] Invalid input. Please enter a number.")

def convert_to_yaml(pipeline_config, pipeline_yaml_config, target_repository):
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
    if "options" in pipeline_config:
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
    pools = fetch_agent_pools(TARGET_ORGANIZATION, TARGET_AUTHENTICATION_HEADER)
    
    selected_pool = choose_agent_pool(pools)
    yaml_format_pipeline["pool"] = {"name": selected_pool["name"]}

    """
    Classic pipelines rely on "displayName" to describe each step. They don’t include the exact task name and version required by YAML pipelines.
    The purpose of the mapping is to translate "displayName" (human-readable descriptions of tasks in the classic pipeline) into the correct task identifiers used in YAML pipelines.
    """
    task_name_mapping = {
        step.get("displayName", ""): step.get("task", "")
        for phase in pipeline_yaml_config.get("jobs", [])
        for step in phase.get("steps", [])
        if "task" in step
    }

    # Extracts the "variables" section from the exported YAML file.
    yaml_variables = pipeline_yaml_config.get("variables", [])
    formatted_variables = {}

    # Processes the "variables" into the desired format.
    for variable in yaml_variables:
        if isinstance(variable, dict) and "name" in variable and "value" in variable:
            name_parts = variable["name"].split(".")[-1]  # Extracts only the last part of the variable name.
            formatted_variables[name_parts] = variable["value"]
    
    yaml_format_pipeline["variables"] = formatted_variables


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

def commit_yaml_to_target_repository(pipeline_name, yaml_pipeline_file, target_repository):
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

    # Fetches the latest commit ID from the target repository.
    response = requests.get(url_commit, headers=TARGET_AUTHENTICATION_HEADER)
    print(f"[DEBUG] Request's Status Code: {response.status_code}")

    if response.status_code == 200:
        latest_commit = response.json()["value"][0]["commitId"]
        print(f"[INFO] Latest commit ID fetched: {latest_commit}")

    else:
        raise Exception(f"[ERROR] Failed to fetch the latest commit ID | Request's Status Code: {response.status_code} | Response Body: {response.text}")

    # Validates the YAML file.
    yaml.safe_load(yaml_pipeline_file)

    # Commit payload.
    payload = {
        "refUpdates": [
            {
                "name": f"refs/heads/{select_commit_branch(target_repository)}", # Specifies which branch the YAML file will be committed to.
                "oldObjectId": latest_commit
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
    print("[DEBUG] Commit Payload:", json.dumps(payload, indent=4))

    response = requests.post(url_push, headers=TARGET_AUTHENTICATION_HEADER, json=payload)
    print(f"[DEBUG] Request's Status Code: {response.status_code}")

    if response.status_code == 201:
        print(f"[INFO] Successfully committed the YAML file to {target_repository["name"]}.")
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

    target_repository = next((repo for repo in target_repositories if repo["name"] == repository_name), None) # Ensures that "repository_name" is valid and available in the target project.
    if not target_repository:
        raise ValueError(f"[ERROR] Repository '{repository_name}' not found in '{TARGET_ORGANIZATION}'.")

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
                "type": "azureReposGit",  # Ensure 'azureReposGit' is used
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
    print(f"[INFO] Creating pipeline '{pipeline_config.get("name")}' in '{TARGET_PROJECT}'...")
    print(f"[DEBUG] API URL: {url}")
    print(f"[DEBUG] Final Payload:\n{json.dumps(pipeline_config, indent=4)}")

    try:
        response = requests.post(url, headers=TARGET_AUTHENTICATION_HEADER, json=pipeline_config)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 201:
            created_pipeline = response.json()
            print(f"[INFO] Successfully created pipeline: {created_pipeline.get("name")} with ID: {created_pipeline.get("id")}")
            return created_pipeline
        
        else:
            print(f"[ERROR] Failed to create pipeline: {pipeline_config.get("name")}.")
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
    print("\nAvailable Pipelines for Migration:")
    for index, pipeline in enumerate(pipelines, 1):
        print(f"{index} - {pipeline["name"]} (ID: {pipeline["id"]})")

    print("\nOptions:")
    print("0 - Migrate all pipelines")
    print("Enter pipeline numbers separated by commas to select specific pipelines.")

    selection = input("\nYour choice: ").strip()

    # User chose to migrate all pipelines.
    if selection == "0":
        return [pipeline["id"] for pipeline in pipelines]
    
    # User chose to migrate specific pipelines.
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

def select_commit_branch(target_repository):
    """
    This function fetches branches from the target repository and prompts the user to select one.
    """
    url = f"{TARGET_ORGANIZATION}/{TARGET_PROJECT}/_apis/git/repositories/{target_repository["id"]}/refs?filter=heads/&api-version=6.0"
    response = requests.get(url, headers=TARGET_AUTHENTICATION_HEADER)

    if response.status_code != 200:
        raise Exception(f"[ERROR] Failed to fetch branches | Response Body: {response.text}")

    branches = response.json()["value"]
    branch_names = [branch["name"].replace("refs/heads/", "") for branch in branches]

    print(f"[INFO] Available branches in the target repository ({target_repository["name"]}):")
    for idx, branch_name in enumerate(branch_names, start=1):
        print(f"{idx} - {branch_name}")

    user_choice = input("Select a branch by number: ").strip()

    if user_choice.isdigit():
        user_choice = int(user_choice)
        if 1 <= user_choice <= len(branch_names):
            return branch_names[user_choice - 1]
        else:
            raise ValueError("[ERROR] Invalid branch selection.")
    else:
        raise ValueError("[ERROR] Please select a valid number from the list.")

if __name__ == "__main__":
    fetch_agent_pools(TARGET_ORGANIZATION, TARGET_AUTHENTICATION_HEADER)

    pass
    # Fetches the target repositories.
    target_repos = requests.get(
        f"{TARGET_ORGANIZATION}/{TARGET_PROJECT}/_apis/git/repositories?api-version=6.0",
        headers=TARGET_AUTHENTICATION_HEADER
    ).json()["value"]

    # Fetches pipelines from the source project
    pipelines = list_source_pipelines()

    if pipelines:
        print("\n[INFO] Fetching pipelines completed.")
        selected_pipeline_ids = select_pipelines_to_migrate(pipelines)

        for pipeline in pipelines:
            if pipeline["id"] in selected_pipeline_ids:
                print(f"##############################>-{pipeline['name']}-<##############################")
                pipeline_id = pipeline["id"]
                pipeline_name = pipeline["name"]
                pipeline_config = get_pipeline_config(pipeline_id)

                # Fetches the YAML format of the pipeline
                yaml_content = fetch_pipeline_yaml(
                    SOURCE_ORGANIZATION,
                    SOURCE_PROJECT,
                    pipeline_id,
                    SOURCE_AUTHENTICATION_HEADER
                )

                # Allow user to choose which repository to commit to
                print("\nAvailable Target Repositories:")
                for idx, repo in enumerate(target_repos, 1):
                    print(f"{idx} - {repo['name']} (ID: {repo['id']})")
                repo_selection = input("\nEnter the number of the target repository (or press Enter for all): ").strip()

                if repo_selection.isdigit():
                    repo_index = int(repo_selection) - 1
                    if 0 <= repo_index < len(target_repos):
                        target_repos = [target_repos[repo_index]]
                    else:
                        print(f"[WARNING] Invalid repository selection. Proceeding with all repositories.")

                print(f"[DEBUG] Target repositories list:\n{json.dumps(target_repos, indent=4)}")
                # Migrate pipeline to the selected repositories
                for repo in target_repos:
                    if isinstance(repo, dict):  # Ensure repo is a dictionary
                        generated_yaml = convert_to_yaml(pipeline_config, yaml_content, repo)
                        #print(f"[DEBUG] Current repository object: {repo}")
                        success = commit_yaml_to_target_repository(pipeline_name, generated_yaml, repo)
                        if success:
                            print(f"[SUCCESS] Pipeline '{pipeline_name}' migrated to repository '{repo['name']}'.")
                        else:
                            print(f"[ERROR] Failed to migrate pipeline '{pipeline_name}' to repository '{repo['name']}'.")
                    else:
                        print(f"[ERROR] Invalid repository object: {repo}")
