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

def get_task_groups(organization, project_name, authentication_header):
    """
    This function fetches all task groups from a project.
    """
    api_version = "6.0-preview"
    url = f"{organization}/{project_name}/_apis/distributedtask/taskgroups?api-version={api_version}"

    print(f"[INFO] Fetching task groups from '{project_name}' in '{organization}'...")

    try:
        response = requests.get(url, headers=authentication_header)
        print(f"[DEBUG] Request's Status Code: {response.status_code}")

        if response.status_code == 200:
            task_groups = response.json().get("value", [])
            print(f"\nFound {len(task_groups)} task group(s).")

            print("-" * 50)  # Visual separator for better readability.
            for task_group in task_groups:
                task_group_name = task_group.get("name", "Unknown Name")
                task_group_id = task_group.get("id", "Unknown ID")
                print(f"Name: {task_group_name}")
                print(f"ID: {task_group_id}")
                print("-" * 50)  # Visual separator between task groups for better readability.

            return task_groups
        
        else:
            print(f"[ERROR] Failed to fetch task groups from '{project_name}' project.")
            print(f"Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")
            return []
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] An error occurred while fetching task groups: {e}")
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

def clean_task_configuration(task):
    """
    This function ensures that irrelevant or incompatible fields are removed from the task’s configuration to ensure compatibility with target organization.
    """
    fields_to_remove = ['id', 'timeoutInMinutes']

    for field in fields_to_remove:
        task.pop(field, None)

def process_task_inputs(task):
    """
    This function ensures that any organization-specific dependencies are identified.
    """
    inputs = task.get('inputs', {})

    for input_name, input_value in inputs.items():
        if isinstance(input_value, str): # Only strings contain variable references.
            if '$(Build.' in input_value:
                print(f"\033[1;38;5;214m[WARNING] Build variable found in task '{task.get('displayName')}': {input_value}\033[0m")
            
            if 'ConnectedServiceName' in input_name and input_value != '':
                print(f"\033[1;38;5;214m[WARNING] Service connection reference found in task '{task.get('displayName')}': {input_value}\033[0m")

def prepare_migration_payload(task_group_data, id_mapping):
    """
    This function prepares task group data before migration by:
    • Creating a copy of the task group data to prevent modifying the original.
    • Removing organization-specific metadata that should not be migrated.
    • Processing each task within the task group to clean and adjust configurations.
    """
    migration_data = task_group_data.copy()

    fields_to_remove = ['createdBy', 'createdOn', 'modifiedBy', 'modifiedOn', 'id']
    for field in fields_to_remove:
        migration_data.pop(field, None)
    
    for task in migration_data.get('tasks', []):
        clean_task_configuration(task)
        process_task_inputs(task)

        # Checks if we have mapping data available and the current task is a reference to another task group.
        if task_group_mapping and task.get('task', {}).get('definitionType') == 'metaTask':
            source_referenced_tg_id = task.get('task', {}).get('id') # The id of the referenced task group in the source environment.
            
            # Checks if there is a mapping for this task group id.
            if source_referenced_tg_id in id_mapping:
                target_referenced_tg_id = id_mapping[source_referenced_tg_id]
                
                print(f"\033[1;36m[INFO] Updating task group reference from {source_referenced_tg_id} to {target_referenced_tg_id}.\033[0m")
                
                # Updates the task group reference with the target environment id.
                task['task']['id'] = target_referenced_tg_id
                
                # The 'inputs.taskGroup' property contains additional configuration for how the referenced task group should be used, so we have to make sure this
                # section is adjusted as well.
                if 'inputs' in task and 'taskGroup' in task['inputs']:
                    try:
                        # The "task['inputs']['taskGroup']" value is a JSON string, not a Python object, so we have to convert that string into a 
                        # Python dictionary so we can manipulate it.
                        task_group_input = json.loads(task['inputs']['taskGroup'])

                        if 'id' in task_group_input:
                            task_group_input['id'] = target_referenced_tg_id
                            task['inputs']['taskGroup'] = json.dumps(task_group_input) # Converts the Python object back to a JSON string because that is the format Azure DevOps expects.

                    except json.JSONDecodeError:
                        print(f"\033[1;33m[WARNING] Could not parse 'taskGroup' input for task in {task_group_data.get('name', 'unknown')}.\033[0m")

            else:
                print(f"\033[1;33m[WARNING] No target mapping found for referenced task group ID: {source_referenced_tg_id}.\033[0m")
    
    return migration_data

def create_task_group(organization, project_name, task_group_data, authentication_header):
    """
    This function creates a task group in the target organization based on the source task group data.
    """
    api_version = "6.0-preview"
    url = f"{organization}/{project_name}/_apis/distributedtask/taskgroups?api-version={api_version}"
    
    print(f"[INFO] Creating task group in target project '{project_name}'...")
    print(f"[DEBUG] API URL: {url}\n")
    
    try:
        response = requests.post(url, headers=authentication_header, json=task_group_data)
        print(f"[DEBUG] Request's Status Code: {response.status_code}\n")
        
        if response.status_code in [200, 201]:
            print(f"\033[1;32m[SUCCESS] Task group created successfully.\033[0m")
            return response.json()
        
        else:
            print(f"\033[1;31m[ERROR] Failed to create task group.\033[0m")
            print(f"[DEBUG] Request's Status Code: {response.status_code}")
            print(f"[DEBUG] Response: {response.text}")
            return {}
            
    except requests.exceptions.RequestException as e:
        print(f"\033[1;31m[ERROR] An error occurred while creating task group: {e}\033[0m")
        return {}

def manage_task_group_mapping(organization, project_name, authentication_header):
    """
    This function creates and manages a mapping between source and target task group IDs.
    
    This function ensures:
    • We can track which task groups have been migrated.
    • We know the source-target mapping when updating pipeline references.
    """
    mapping_data = {
        'source_task_groups': [],
        'id_mapping': {},
        'name_mapping': {}
    }
    
    try:
        source_task_groups = get_task_groups(organization, project_name, authentication_header)
        mapping_data['source_task_groups'] = source_task_groups
        
        # Creates an initial mapping based on the task group name.
        for task_group in source_task_groups:
            task_group_name = task_group.get('name')
            mapping_data['name_mapping'][task_group_name] = {
                'source_id': task_group.get('id'),
                'target_id': None,
                'migration_status': 'pending'
            }
        
        return mapping_data
        
    except Exception as e:
        print(f"\033[1;31m[ERROR] Failed to create task groups mapping: {e}\033[0m")
        return None

def identify_task_group_dependencies(task_group):
    """
    This function analyzes a task group and determines if it depends on other task groups within its steps.
    """
    dependencies = set()
    
    for task in task_group.get('tasks', []):
        # In Azure DevOps, when a task is another task group, its 'definitionType' field will be 'metaTask'.
        if task.get('task', {}).get('definitionType') == 'metaTask':
            dependency_id = task.get('task', {}).get('id') # The id of the nested task group.

            if dependency_id: # Ensures the id is not 'None' or empty.
                dependencies.add(dependency_id)
    
    return list(dependencies)

def plan_migration_order(dependency_graph):
    """
    This function determines the correct order in which task groups should be migrated from the source environment to the target environment, ensuring 
    that dependencies between task groups are properly handled.
    
    For example:
    If task group A contains task group B as one of its steps, then task group B is a dependency of task group A.
    If task group A depends on task group B, task group B must be migrated first.
    """
    # Create the migration order using topological sort
    migration_order = []
    processed = set()
    being_processed = set()
    
    def process_task_group(task_group_id):
        """
        This function is a helper function that implements depth-first search (DFS) to create a proper migration order based on the dependencies.
        """
        # Checks for circular dependencies to avoid infinite loops.
        if task_group_id in being_processed:
            raise ValueError(f"Circular dependency detected involving task group {task_group_id}.")
        
        # Skips if the task group already being processed.
        if task_group_id in processed:
            return
            
        being_processed.add(task_group_id)
        
        # Recursively processes all dependencies to ensure that all dependent task groups are migrated first.
        for dependency_id in dependency_graph[task_group_id]:
            if dependency_id not in processed:
                process_task_group(dependency_id)
        
        migration_order.append(task_group_id)
        processed.add(task_group_id)
        being_processed.remove(task_group_id)
    
    # Processes the task groups.
    for task_group_id in dependency_graph:
        if task_group_id not in processed:
            process_task_group(task_group_id)
    
    return migration_order

def update_task_group_mapping(mapping_data, source_task_group_id, target_task_group_id, status='completed'):
    """
    This function updates the mapping data structure after a task group has been migrated. It ensures that the source task group ID is properly mapped to its 
    new target task group ID, and updates the migration status accordingly.
    """
    mapping_data['id_mapping'][source_task_group_id] = target_task_group_id
    
    for task_group_info in mapping_data['name_mapping'].values():
        if task_group_info['source_id'] == source_task_group_id:
            task_group_info['target_id'] = target_task_group_id
            task_group_info['migration_status'] = status
            break

def migrate_task_groups(source_organization, source_project, source_authentication_header, target_organization, target_project, target_authentication_header):
    """
    This function ensures that all task groups are migrated in the correct order while maintaining a mapping system to track the migration process.
    """
    print("\n" + "\033[1m=\033[0m" * 100)
    print("\033[1mSTARTING TASK GROUP MIGRATION PROCESS\033[0m")
    print("\033[1m=\033[0m" * 100)

    id_mapping = {}
    source_task_groups = get_task_groups(source_organization, source_project, source_authentication_header)

    # A structure that maps task group IDs to their data.
    task_group_lookup = {tg['id']: tg for tg in source_task_groups}

    dependency_graph = {}
    for task_group in source_task_groups:
        task_group_id = task_group['id']
        dependencies = identify_task_group_dependencies(task_group)
        dependency_graph[task_group_id] = dependencies

    migration_order = plan_migration_order(dependency_graph)

    print("\n\033[1;38;5;38mPlanned Migration Order:\033[0m")
    for index, task_group_id in enumerate(migration_order, 1):
        task_group = task_group_lookup[task_group_id]
        dependencies = dependency_graph[task_group_id]
        
        if dependencies:
            dependency_names = [task_group_lookup[dep_id]['name'] for dep_id in dependencies]
            print(f"{index} - {task_group['name']} (depends on: '{', '.join(dependency_names)}')")

        else:
            print(f"{index} - {task_group['name']} (no dependencies)")

    # Migration counter for summary.
    successful = 0
    failed = 0

    # Migrates each task group in the determined order.
    for task_group_id in migration_order:
        source_task_group = task_group_lookup[task_group_id]
        
        print("\n" + "=" * 100)
        print(f"\033[1;38;5;38mMigrating task group {source_task_group['name']}...\033[0m")
        print("" + "=" * 100)
        
        try:
            cleaned_data = prepare_migration_payload(source_task_group, id_mapping)
            
            # Creates the task group in the target environment.
            new_task_group = create_task_group(
                target_organization,
                target_project,
                cleaned_data,
                target_authentication_header
            )
            
            if new_task_group:
                # Updates the mapping dictionary with the new id.
                id_mapping[task_group_id] = new_task_group['id']
                
                successful += 1
                print(f"\033[1;32m[SUCCESS] Task group migrated successfully.\033[0m")
                print(f"[INFO] Source environment task group id: {task_group_id}")
                print(f"[INFO] Target environment task group id: {new_task_group['id']}")
                
            else:
                failed += 1
                print(f"\033[1;31m[ERROR] Failed to create task group '{source_task_group['name']}' in '{target_organization}'.\033[0m")
        
        except Exception as e:
            failed += 1
            print(f"\033[1;31m[ERROR] An error occurred while migrating task group '{source_task_group['name']}': {e}\033[0m")
    
    # Print migration summary
    print("\n" + "\033[1m=\033[0m" * 100)
    print("\033[1mMIGRATION SUMMARY\033[0m")
    print("\033[1m=\033[0m" * 100)
    
    print(f"• Total task groups processed: {len(migration_order)}")
    print(f"• Successful migration: {successful}")
    print(f"• Failed migrations: {failed}")
    
    return id_mapping

if __name__ == "__main__":
    migrate_task_groups(SOURCE_ORGANIZATION, SOURCE_PROJECT, SOURCE_AUTHENTICATION_HEADER, TARGET_ORGANIZATION, TARGET_PROJECT, TARGET_AUTHENTICATION_HEADER)