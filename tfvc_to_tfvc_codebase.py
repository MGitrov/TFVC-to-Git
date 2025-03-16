import subprocess
import json

"""
CLARIFICATIONS:
• Workspace creation ('tf workspace /new') is handled manually.
    Command: tf workspace /new /collection:<collectionURL> /comment:"<comment>" <workspace_name>
    Workspace creation verification: tf workspaces (optional - /collection:<collectionURL>)

• Mapping server path to local path ('tf workfold /map') is handled manually.
    Command: tf workfold /map '<source_server_path (e.g., $/...)>' '<local_source_path>' /collection:<collectionURL> /workspace:<workspace_name>

• This script is automating regular changesets migration.
• Branch creation changesets ("unregular" changesets) are handled manually.
• The 'tf branch' command does not completely creates a branch. To convert a folder to a proper TFVC branch, Visual Studio is needed.
    (Only the parent branch has to be converted via Visual Studio, as all its descendants will be automatically created as branches
    once the 'tf branch' command is executed).

PREREQUISITES:
• Parent (trunk) branches' first changeset.
    The branch hierarchy can be viewed using either the 'git tfs list-remote-branches <collectionURL>' command, or Visual Studio.

• The first changeset of all other branches.
• An history file of the source TFVC repository.
    Command: tf history '<source_server_path (e.g., $/...)>' /recursive /noprompt /format:detailed /collection:<collectionURL> > history.txt
"""

source_collection = "https://dev.azure.com/maximpetrov2612"
target_collection = "https://dev.azure.com/maximpetrov1297"
source_path = "$/TFS-based test project"
target_path = "$/Magnolia"
local_source_path = "P:\Work\Migration\SourcePath"
local_target_path = "P:\Work\Migration\TargetPath"

# There is a need to figure out what changesets are branch creation changeset as it requires a different handling.
branch_creation_changesets = {
    # 'Folder_1-branch' branch.
    7: {
        "source_path": "$/NiceVision",
        "target_path": "$/NiceVision/VA",
        "comment": "Creating VA branch"
    },
    # 'Exodus' branch.
    11: {
        "source_path": "$/NiceVision",
        "target_path": "$/NiceVision/AppGroup/Trunk",
        "comment": "Creating Trunk branch"
    }
}

def execute_tf_command(command, capture_output=True):
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

    print(f"\n\033[1;32m[SUCCESS] Successfully created the '{filename}' file.\033[0m")

def process_regular_changeset(changeset_id):
    """
    This function processes a regular (non-branch creation) changeset.

    • For each changeset, the function gets the specific changeset from the source repository and check it into the target repository.
    """
    print(f"Processing regular changeset {changeset_id}...")
    
    # Step 1: Get detailed information about this changeset
    # This gives us the comment, user, and a list of changes (adds, edits, deletes, etc.)
    changeset_details = run_tf_command(
        f"changeset {changeset_id} /collection:{source_collection} /noprompt"
    )
    
    # Extract the comment for use in our check-in
    comment_match = re.search(r"Comment: (.*?)(?:\r?\n)(?:\r?\n|$)", changeset_details, re.DOTALL)
    if comment_match:
        original_comment = comment_match.group(1).strip()
        # Prepend a note that this is a migrated changeset
        comment = f"Migrated from changeset {changeset_id}: {original_comment}"
    else:
        comment = f"Migrated from changeset {changeset_id}"
    
    # Step 2: Clean the destination directory to start fresh
    # This ensures we're mirroring exactly what was in this changeset
    if os.path.exists(local_destination_path):
        print(f"Cleaning destination directory: {local_destination_path}")
        # Keep the hidden .tf folder to maintain workspace information
        for item in os.listdir(local_destination_path):
            full_path = os.path.join(local_destination_path, item)
            if item != '.tf' and os.path.isdir(full_path):
                shutil.rmtree(full_path)
            elif item != '.tf':
                os.remove(full_path)
    else:
        os.makedirs(local_destination_path, exist_ok=True)
    
    # Step 3: Get this specific version from the source repository
    # This downloads the exact state of files as they were in this changeset
    print(f"Getting source code for changeset {changeset_id}...")
    run_tf_command(
        f"workspace /workspace:SourceMigrationWorkspace /collection:{source_collection}"
    )
    # cd to source local path
    get_result = run_tf_command(
        f"get {source_path} /version:C{changeset_id} /recursive /force /noprompt"
    )
    if not get_result:
        print(f"Error getting source code for changeset {changeset_id}")
        return False
    
    # Step 4: Copy files from source to destination
    # This transfers the files to our destination workspace
    print("Copying files to destination workspace...")
    copy_files_recursively(local_source_path, local_destination_path)
    
    # Step 5: Add all files to TFVC in the destination
    # This stages the files for check-in
    print("Adding files to destination TFVC...")
    run_tf_command(
        f"workspace /workspace:DestinationMigrationWorkspace /collection:{destination_collection}"
    )
    
    # Change to the destination directory
    original_dir = os.getcwd()
    os.chdir(local_destination_path)
    
    # Add all files to version control
    add_result = run_tf_command("add * /recursive /noprompt")
    if not add_result:
        print("Error adding files to destination")
        os.chdir(original_dir)
        return False
    
    # Step 6: Check in the changes
    # This commits the changeset to the destination repository
    print(f"Checking in changeset to destination with comment: {comment}")
    checkin_result = run_tf_command(
        f"checkin /comment:\"{comment}\" /noprompt /recursive"
    )
    
    # Return to the original directory
    os.chdir(original_dir)
    
    if not checkin_result:
        print("Error checking in files to destination")
        return False
    
    print(f"Successfully processed changeset {changeset_id}")
    return True

if __name__ == "__main__":
    changesets = parse_history_file(history_file="C:\\Users\\maxim\\history.txt")

    if changesets:
        save_changesets_to_file(changesets)