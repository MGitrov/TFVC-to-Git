import subprocess
import json

source_collection = "https://dev.azure.com/Qognify"
target_collection = "https://dev.azure.com/maximpetrov2612"
source_path = "$/NiceVision"
#destination_path = "$/DestinationProject/NiceVision"
#local_source_path = "C:/Migration/Source"
#local_destination_path = "C:/Migration/Destination"

# There is a need to figure out what changesets are branch creation changeset as it requires a different handling.
branch_creation_changesets = {
    # VA branch.
    8143: {
        "source_path": "$/NiceVision",
        "target_path": "$/NiceVision/VA",
        "comment": "Creating VA branch"
    },
    # AppGroup/Trunk branch.
    23146: {
        "source_path": "$/NiceVision",
        "target_path": "$/NiceVision/AppGroup/Trunk",
        "comment": "Creating Trunk branch"
    },
    # Trunk branch from VA.
    33041: {
        "source_path": "$/NiceVision/VA",
        "target_path": "$/NiceVision/Trunk",
        "comment": "Creating Trunk branch"
    },
    # 12.1.27 branch (top level).
    44803: {
        "source_path": "$/NiceVision",
        "target_path": "$/NiceVision/12.1.27",
        "comment": "Creating 12.1.27 branch"
    },
    # Trunk-PI branch from 12.1.27.
    44855: {
        "source_path": "$/NiceVision/12.1.27",
        "target_path": "$/NiceVision/Trunk-PI",
        "comment": "Creating Trunk-PI branch"
    },
    # 12.1-Plugin branch from Trunk-PI.
    56743: {
        "source_path": "$/NiceVision/Trunk-PI",
        "target_path": "$/NiceVision/12.1-Plugin",
        "comment": "Creating 12.1-Plugin branch"
    }
}

def run_tf_command(command, capture_output=True):
    """Execute a TF command and return its output"""
    print(f"Executing: tf {command}")
    try:
        result = subprocess.run(f"tf {command}", shell=True, 
                              capture_output=capture_output, text=True, check=True)
        if capture_output:
            return result.stdout
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        if capture_output:
            print(f"Error output: {e.stderr}")
        return None

def parse_history_file(history_file):
    """
    This function parses the TFVC repository history file, extracting only changeset IDs.
    """
    print(f"Extracting changeset IDs from the '{history_file}' history file...")

    changeset_ids = set()
    
    with open(history_file, 'r', encoding='utf-16le') as f:
        line_count = 0
        
        for line in f:
            line_count += 1
            line = line.strip()

            if line.startswith("Changeset:"):
                try:
                    changeset_id = int(line.split("Changeset:")[1].strip().split()[0])
                    changeset_ids.add(changeset_id)

                except Exception as e:
                    print(f"[ERROR] Error parsing changeset ID from line {line}; error message: {e}")
    
    changeset_ids_list = sorted(list(changeset_ids))

    print(f"Processed {line_count} lines and found {len(changeset_ids_list)} unique changeset IDs")
    
    return changeset_ids_list

def save_changesets_to_file(changesets_id, filename="changesets.json"):
    """
    This function saves the changesets id list to a JSON file.
    """
    print(f"\nSaving {len(changesets_id)} changeset IDs to {filename}...")
    
    changesets = []

    for changeset_id in changesets_id:
        is_branch_creation = changeset_id in branch_creation_changesets # Checks whether the current processed changeset is a branch creation changeset.

        changesets.append({
            "changeset_id": changeset_id,
            "is_branch_creation": is_branch_creation
        })
    
    with open(filename, 'w') as f:
        json.dump(changesets, f, indent=2)

    print(f"[SUCCESS] Successfully created the '{filename}' file.")

def setup_workspaces():
    print("Setting up workspaces for migration...")

    # Checks whether there are existing workspaces for the source and target collection and if yes, they are deleted.
    # It helps us start with a clean state and avoid potential mapping conflicts.
    run_tf_command(f"workspace /delete source_workspace /collection:{source_collection}", capture_output=False)
    run_tf_command(f"workspace /delete target_workspace /collection:{target_collection}", capture_output=False)

if __name__ == "__main__":
    """
    In order to create the history file of the repository, we will execute the following command:
        'tf history $/tfsPath /recursive /noprompt /format:detailed /collection:organizationURL > history.txt'
    """
    changesets = parse_history_file(history_file="C:\\Users\\maxim\\history.txt")

    if changesets:
        save_changesets_to_file(changesets)
        setup_workspaces()