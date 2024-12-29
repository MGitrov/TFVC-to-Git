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
    url = f"{SOURCE_ORGANIZATION}/{SOURCE_PROJECT}/_apis/pipelines?api-version=6.0"

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
    
def get_pipeline_details(pipeline_id): # DEPRECATED.
    """
    This function fetches detailed information about a specific pipeline from the source project.
    """
    url = f"{SOURCE_ORGANIZATION}/{SOURCE_PROJECT}/_apis/pipelines/{pipeline_id}?api-version=7.0"

    print("##############################")
    print(f"[INFO] Fetching details for pipeline ID {pipeline_id} from '{SOURCE_PROJECT}'...")
    print(f"[DEBUG] API URL: {url}")

    try:
        response = requests.get(url, headers=SOURCE_AUTHENTICATION_HEADER)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            pipeline_details = response.json()
            print(f"[INFO] Successfully retrieved details for pipeline ID {pipeline_id}.")
            print(f"[DEBUG] Pipeline Name: {pipeline_details.get('name')} | Repository: {pipeline_details.get('repository', {}).get('name')}")
            
            return pipeline_details
        
        else:
            print(f"[ERROR] Failed to fetch details for pipeline ID {pipeline_id}.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response Body: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching the pipeline details: {e}")
        return None
    
def get_pipeline_config(pipeline_id):
    """
    This function fetches the configuration of a pipeline.
    """
    url = f"{SOURCE_ORGANIZATION}/{SOURCE_PROJECT}/_apis/build/definitions/{pipeline_id}?api-version=6.0"

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
    url = f"{organization}/{project}/_apis/build/definitions/{pipeline_id}/yaml?api-version=6.0"

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

def print_readable_yaml(dict_pipeline_yaml): # DEPRECATED.
    """
    This function parses and prints the YAML configuration in a readable format.
    """
    try:
        readable_yaml = yaml.dump(dict_pipeline_yaml, default_flow_style=False, sort_keys=False)
        print("[INFO] Readable YAML Configuration:\n")
        print(readable_yaml)

    except Exception as e:
        print(f"[ERROR] An error occurred while parsing the YAML content: {e}")

def modify_pipeline_yaml(pipeline_yaml, target_repository_name, target_branch="main"): # DEPRECATED.
    """
    This function modifies a pipeline YAML configuration, represented as a Python dictionary, to make it compatible with 
    a target repository and branch.
    """
    # Ensures the input configuration file is a dictionary.
    if not isinstance(pipeline_yaml, dict):
        raise TypeError("Expected 'pipeline_yaml' to be a dictionary.")

    """
    The "resources.repositories" section defines external repositories used by the pipeline, specifying their names (name) and 
    branches (ref).

    When migrating pipelines, the original repository names and branches are often specific to the source environment. 
    These need to be updated to reflect the target environment.
    """
    if "resources" in pipeline_yaml and "repositories" in pipeline_yaml["resources"]:
        for repository in pipeline_yaml["resources"]["repositories"]:
            if target_repository_name:
                repository["name"] = target_repository_name
            if target_branch:
                repository["ref"] = f"refs/heads/{target_branch}"

    """
    The trigger section defines the branch or branches that automatically trigger the pipeline when changes are pushed.

    When migrating pipelines, the source pipeline might use main, but in the target environment, 
    the branch name might be different. The trigger must align with the new branch to ensure proper automation.
    """
    if "trigger" in pipeline_yaml:
        if target_branch:
            pipeline_yaml["trigger"] = [target_branch]

    """
    Variables define reusable configuration parameters for pipelines.
    """
    if "variables" in pipeline_yaml:
        for variable in pipeline_yaml["variables"]:
            if isinstance(variable, dict) and "name" in variable:
                if variable["name"] == "BuildParameters.wrapperScript":
                    variable["value"] = "./gradlew"
                elif variable["name"] == "BuildParameters.tasks":
                    variable["value"] = "build"

    # Additional adjustments can be added here...

    return pipeline_yaml

def extract_version(version_spec): # DEPRECATED.
    """
    Extracts the major version number from a versionSpec string.
    Args:
        version_spec (str): The version specification, e.g., "2.*" or "3.1".
    Returns:
        str: Extracted major version, or the original versionSpec if no match.
    """
    if version_spec:
        match = re.match(r"(\d+)", version_spec)
        return match.group(1) if match else version_spec
    return None

def convert_to_yaml(pipeline_config, pipeline_yaml_config, target_repository):
    """
    This function converts a classic Azure DevOps pipeline configuration into a YAML string format compatible with YAML-based pipelines.
    """
    print("##############################")
    print("[INFO] Converting the classic pipeline logic into a YAML string logic...")

    yaml_format_pipeline = {
        "trigger": [target_repository["defaultBranch"].replace("refs/heads/", "")], # Defines the branches that will trigger the pipeline automatically (ADJUSTABLE BY THE USER).
        "pool": pipeline_config.get("pool", {"vmImage": "ubuntu-latest"}), # Specifies the agent pool that Azure DevOps will use to run the pipeline.
        "variables": {},
        "steps": [] # Holds a list of steps (tasks) to execute during the pipeline. This is initialized as an empty list and populated later.
    }

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

    if "variables" in pipeline_config:
        yaml_format_pipeline["variables"] = {}

        # Checks if "variables" are in a dictionary format.
        if isinstance(pipeline_config["variables"], dict):
            for variable_name, variable_value in pipeline_config["variables"].items():
                if isinstance(variable_value, dict) and "value" in variable_value:
                    # Extracts the value from nested dictionary.
                    yaml_format_pipeline["variables"][variable_name] = variable_value["value"]

                else:
                    yaml_format_pipeline["variables"][variable_name] = variable_value

            """
        Checks if "variables" are in a list (array) format.

        "variables": [
              {"name": "python.version", "value": "3.8"},
              {"name": "system.debug", "value": "true"}
          ]
            """
        elif isinstance(pipeline_config["variables"], list):
            for variable in pipeline_config["variables"]:
                if isinstance(variable, dict) and "name" in variable:
                    yaml_format_pipeline["variables"][variable["name"]] = variable.get("value", "")


    for phase in pipeline_config["process"]["phases"]: # Extracts all phases in the classic pipeline's process configuration.
        for step in phase["steps"]: # Extracts all steps within the current phase.
            if "task" in step: # Task handling.
                display_name = step["displayName"]
                #version = step["task"].get("versionSpec")
                #task_version = extract_version(version)

                # Uses the mapped task name if available. If not, the "displayName" field will be used.
                task_name = task_name_mapping.get(display_name, display_name)

                if "script" in step.get("inputs", {}):
                    yaml_format_step = {
                        "script": step["inputs"]["script"],
                        "displayName": display_name
                    }
                else:
                    yaml_format_step = {
                        "task": f"{task_name}",
                        "displayName": display_name,
                        "inputs": step.get("inputs", {})
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

def commit_yaml_to_target_repository(pipeline_name, yaml_pipeline_file, target_repository, branch="main"):
    """
    This function commits the generated YAML file to the target repository.
    """
    repository_id = target_repository["id"] # Used to identify the target repository in Azure DevOps' API.
    repository_name = target_repository["name"]
    yaml_file_name = f"azure-pipelines-{pipeline_name}.yml"
    url_commit = f"{TARGET_ORGANIZATION}/{TARGET_PROJECT}/_apis/git/repositories/{repository_id}/commits?api-version=6.0"
    url_push = f"{TARGET_ORGANIZATION}/{TARGET_PROJECT}/_apis/git/repositories/{repository_id}/pushes?api-version=6.0"

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
                "name": f"refs/heads/{branch}", # Specifies which branch the YAML file will be committed to.
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

def adjust_pipeline_config(pipeline_config, target_repositories):
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

def create_target_pipeline(pipeline_config):

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

if __name__ == "__main__":
    # Fetches the target repositories
    target_repos = requests.get(
        f"{TARGET_ORGANIZATION}/{TARGET_PROJECT}/_apis/git/repositories?api-version=7.0",
        headers=TARGET_AUTHENTICATION_HEADER
    ).json()["value"]

    #print(f"[DEBUG] Target Repositories:\n{json.dumps(target_repos, indent=4)}")

    print("\nAvailable Repositories:")
    for repo in target_repos:
        print(f"- {repo['name']} (ID: {repo['id']})")

    desired_repo_name = input("\nEnter the name of the repository where the YAML file should be committed: ").strip()

    # Find the specified repository
    selected_repo = next((repo for repo in target_repos if repo["name"] == desired_repo_name), None)

    if not selected_repo:
        print(f"[ERROR] Repository '{desired_repo_name}' not found. Exiting...")
        exit(1)

    print(f"[INFO] Selected repository: {selected_repo['name']}")

    # Fetches the source pipelines
    pipelines = list_source_pipelines()

    if pipelines:
        for pipeline in pipelines:
            print(f"##############################>- {pipeline['name']} -<##############################")
            pipeline_id = pipeline["id"]
            pipeline_name = pipeline["name"]

            # Fetches the classic pipeline configuration
            pipeline_config = get_pipeline_config(pipeline_id)

            # Fetches the YAML format of the pipeline from the source system
            yaml_content = fetch_pipeline_yaml(
                SOURCE_ORGANIZATION,
                SOURCE_PROJECT,
                pipeline_id,
                SOURCE_AUTHENTICATION_HEADER
            )

            for repo in target_repos:
                # Converts the classic pipeline configuration to YAML
                generated_yaml = convert_to_yaml(pipeline_config, yaml_content, repo)

                # Commits the generated YAML to the target repository
                success = commit_yaml_to_target_repository(pipeline_name, generated_yaml, selected_repo)
                
                if success:
                    print(f"[INFO] Successfully committed pipeline '{pipeline_name}' to repository '{repo['name']}'.")
                else:
                    print(f"[ERROR] Failed to commit pipeline '{pipeline_name}' to repository '{repo['name']}'.")