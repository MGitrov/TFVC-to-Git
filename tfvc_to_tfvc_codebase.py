import subprocess
import re
import os
import shutil
import time
import json
import traceback

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
    The parent branch is migrated as a regular changeset, and once migrated will be converted to a branch via Visual Studio.

• The first changeset of all other branches.
• An history file of the source TFVC repository.
    Command: tf history '<source_server_path (e.g., $/...)>' /recursive /noprompt /format:detailed /collection:<collectionURL> > history.txt
"""

source_collection = "https://dev.azure.com/maximpetrov2612"
target_collection = "https://dev.azure.com/maximpetrov1297"
source_server_path = "$/TFS-based test project"
local_source_path = "P:\Work\Migration\SourcePath"
local_target_path = "P:\Work\Migration\TargetPath"

parent_branch_creation_changesets = [6]
branch_creation_changesets = [7, 11, 12]

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
    },
    # 'tulip' branch.
    12: {
        "source_path": "$/NiceVision",
        "target_path": "$/NiceVision/AppGroup/Trunk",
        "comment": "Creating Trunk branch"
    }
}

def execute_tf_command(command, capture_output=True):
    """
    This function executes a 'TF' command with improved error handling for already-tracked files.
    """
    print(f"Executing the following command: tf {command}")
    
    try:
        result = subprocess.run(f"tf {command}", shell=True,
                               capture_output=capture_output, text=True, check=True)
        
        if capture_output:
            return result.stdout
        return True
        
    except subprocess.CalledProcessError as e:
        # Checks whether this is an "already has pending changes" error.
        if e.stderr and "already has pending changes" in e.stderr:
            file_match = re.search(r'\$/(.*?) already has pending changes', e.stderr)

            if file_match:
                file_path = file_match.group(1)
                print(f"\n\033[1;33m[INFO] File '${file_path}' is already tracked by TFVC and was not added in this changeset.\033[0m")

            else:
                print(f"\n\033[1;33m[INFO] Some files are already tracked by TFVC and were not added in this changeset.\033[0m")
            
            # If this is an 'add' command, this is treated as a warning, not an error, and the script continues.
            if "add " in command or "add*" in command:
                print("\033[1;33m[INFO] This is an expected behavior in TFVC when migrating sequential changesets and will not affect the process.\033[0m")
                
                if capture_output:
                    return {"status": "already_tracked", "message": e.stderr}
                return True
            
            else:
                # For non-add commands, still show the error but in warning color
                print(f"\n\033[1;38;5;214m[WARNING] Command returned non-zero exit status: {e}\033[0m")

                if capture_output:
                    print(f"\033[1;38;5;214m[WARNING] Output: {e.stderr}\033[0m\n")
                return None
        else:
            # Handle other types of errors normally
            print(f"\n\033[1;31m[ERROR] An error occurred while executing the 'tf' command: {e}\033[0m")
            
            if capture_output:
                print(f"\033[1;31m[ERROR] Output: {e.stderr}\033[0m\n")
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

def process_regular_changeset(changeset_id):
    """
    This function processes a regular (non-branch creation) changeset.

    • For each changeset, the function gets the specific changeset from the source repository and check it into the target repository.
    """
    print("\n" + "\033[1m=\033[0m" * 100)
    print(f"\033[1mPROCESSING REGULAR CHANGESET {changeset_id}\033[0m")
    print("\033[1m=\033[0m" * 100)
    
    # Step 1: Fetches the information about the current processed changeset to use later in check-in.
    changeset_details = execute_tf_command(
        f"changeset {changeset_id} /collection:{source_collection} /noprompt"
    )
    
    comment_match = re.search(r"Comment:\s*(.*?)(?:\r?\n\r?\n|\r?\n$|$)", changeset_details, re.DOTALL) # Extracts the comment for use in the changeset's check-in.

    if comment_match:
        original_comment = comment_match.group(1).strip()
        new_comment = f"Migrated from changeset no. {changeset_id}: {original_comment}" # Prepends a note that this is a migrated changeset.

    else:
        new_comment = f"Migrated from changeset no. {changeset_id}"

    # Step 2: Downloads the exact state of files as they were in the current processed changeset.
    print(f"\nFetching the state of the changeset...")

    os.chdir(local_source_path)
    print(f"\nCurrent working directory: {os.getcwd()}\n")

    get_result = execute_tf_command(
        f"get \"{source_server_path}\" /version:C{changeset_id} /recursive /force"
    )

    if not get_result:
        print(f"\033[1;31m[ERROR] Failed to fetch the state of the changeset.\033[0m")
        return False
    

    # Step 3: Copies files and directories from the source local path to the local target path.
    print(f"\nCopying all files to '{local_target_path}' (local target path)...")
    copy_files_recursively(local_source_path, local_target_path)


    # Step 4: Stages all files for check-in
    print("\nStaging all files for check-in...")

    os.chdir(local_target_path)
    print(f"Current working directory: {os.getcwd()}\n")

    # Force workspace reconciliation to ensure accurate status
    #print("Reconciling workspace to ensure accurate status...")
    #execute_tf_command("workfold /reconcile")

    # Use a single batch add command, which is more reliable for this scenario
    print("Adding all files...")
    add_result = execute_tf_command("add * /recursive /noprompt")

    if not add_result:
        print("\033[1;33m[WARNING] Failed to add files.\033[0m")
        # Try using pendadd as an alternative
        #execute_tf_command("pendadd /recursive /noprompt")

    # Verify files were successfully staged
    final_status = execute_tf_command("status")
    if "There are no pending changes" in final_status:
        print("\033[1;33m[WARNING] No pending changes detected after adding files. Verify results.\033[0m")
        return False
    
    # Step 5: Checks-in the changeset.
    print(f"\nChecking in changeset with the following comment: '{new_comment}'")

    checkin_result = execute_tf_command(
        f"checkin /comment:\"{new_comment}\" /noprompt /recursive"
    )
    
    if not checkin_result:
        print("\033[1;31m[ERROR] Failed to check-in the changeset.\033[0m")
        return False
    
    print(f"\n\033[1;32m[SUCCESS] Successfully processed changeset no. {changeset_id}.\033[0m")
    return True

def copy_files_recursively(source_local_directory, target_local_directory):
    """
    Copy all files from source directory to destination directory, recursively.
    This utility function helps transfer files between workspaces.
    """
    for item in os.listdir(source_local_directory):
        source_item = os.path.join(source_local_directory, item)
        dest_item = os.path.join(target_local_directory, item)
        
        # Skip the .tf directory which contains workspace information
        if item == '.tf':
            continue
            
        if os.path.isdir(source_item):
            # Create the directory if it doesn't exist
            os.makedirs(dest_item, exist_ok=True)
            # Recursively copy contents
            copy_files_recursively(source_item, dest_item)
        else:
            # Copy the file
            shutil.copy2(source_item, dest_item)

def add_file_safely(file_path):
    """Attempts to add a file to TFVC safely, handling edge cases."""
    
    # Step 1: Undo pending changes if any exist
    if has_pending_changes(file_path):
        print(f"🔄 Undoing pending changes for: {file_path}")
        execute_tf_command(f'undo "{file_path}"')

    # Step 2: Check if the file was deleted before
    if was_file_deleted(file_path):
        print(f"🛠️ File was previously deleted, undeleting: {file_path}")
        execute_tf_command(f'undelete "{file_path}"')
        return

    # Step 3: Check if the file is already in TFVC
    if is_file_tracked(file_path):
        print(f"⚠️ File already exists in TFVC, skipping add: {file_path}")
        return

    # Step 4: If it's truly a new file, add it
    print(f"✅ Adding new file: {file_path}")
    execute_tf_command(f'add "{file_path}"')

def is_file_tracked(file_path):
    """
    Checks if a file already exists in TFVC using 'tf get'.
    """
    output = execute_tf_command(f'get "{file_path}" /preview')
    return "All files are up to date" in output or "Replacing" in output

def has_pending_changes(file_path):
    """Checks if the file has pending changes using 'tf status'."""
    output = execute_tf_command(f'status "{file_path}" /format:detailed /noprompt')
    return "edit" in output.lower() or "add" in output.lower() # return true because of "candidate changes"

def was_file_deleted(file_path):
    """Checks if a file was previously deleted using 'tf history'."""
    output = execute_tf_command(f'history "{file_path}" /noprompt')
    return "delete" in output.lower()

def process_repository_changesets():
    """
    Main logic function that processes all changesets in the repository.
    
    This function:
    1. Gets all changesets from the history file
    2. Processes them in chronological order
    3. Stops when a branch creation changeset is encountered
    4. Provides detailed progress information
    
    Returns:
        tuple: (success_count, failure_count, stopped_at_changeset)
    """
    print("\n" + "=" * 100)
    print("STARTING REPOSITORY MIGRATION")
    print("=" * 100)
    
    # Get all changesets from history file
    print("\nParsing history file to extract all changesets...")
    start_time = time.time()
    all_changesets = [8, 10, 11, 12]#parse_history_file(history_file="C:\\Users\\maxim\\history.txt")
    parse_time = time.time() - start_time
    
    if not all_changesets:
        print("\033[1;31m[ERROR] Failed to get changesets from history file.\033[0m")
        return 0, 0, None
    
    total_changesets = len(all_changesets)
    print(f"\033[1;32m[SUCCESS] Found {total_changesets} changesets in history file (took {parse_time:.2f} seconds).\033[0m")
    
    # Initialize counters
    success_count = 0
    failure_count = 0
    
    # Process each changeset in order
    for index, changeset_id in enumerate(all_changesets):
        # Calculate progress percentage
        progress = (index + 1) / total_changesets * 100
        
        # Display progress header
        print("\n" + "-" * 100)
        print(f"\033[1mPROCESSING CHANGESET {index+1}/{total_changesets} ({progress:.1f}%): ID {changeset_id}\033[0m")
        print("-" * 100)
        
        # Check if this is a branch creation changeset
        if changeset_id in parent_branch_creation_changesets:
            print(f"\033[1;33m[STOPPING] Changeset {changeset_id} is a parent branch creation changeset.\033[0m")
            print(f"\033[1;33mMigration process stopped at changeset {changeset_id}. Please handle this branch creation manually.\033[0m")
            return success_count, failure_count, changeset_id
            
        if changeset_id in branch_creation_changesets:
            print(f"\033[1;33m[STOPPING] Changeset {changeset_id} is a branch creation changeset.\033[0m")
            print(f"\033[1;33mMigration process stopped at changeset {changeset_id}. Please handle this branch creation manually.\033[0m")
            return success_count, failure_count, changeset_id
        
        # Process regular changeset
        changeset_start_time = time.time()
        print(f"Starting to process changeset {changeset_id}...")
        
        try:
            result = process_regular_changeset(changeset_id)
            
            if result:
                success_count += 1
                changeset_time = time.time() - changeset_start_time
                print(f"\033[1;32m[SUCCESS] Processed changeset {changeset_id} successfully (took {changeset_time:.2f} seconds).\033[0m")
            else:
                failure_count += 1
                print(f"\033[1;31m[FAILURE] Failed to process changeset {changeset_id}.\033[0m")
                
            # Calculate estimated time remaining
            elapsed_time = time.time() - start_time
            changesets_left = total_changesets - (index + 1)
            avg_time_per_changeset = elapsed_time / (index + 1)
            estimated_time_left = avg_time_per_changeset * changesets_left
            
            # Format as hours:minutes:seconds
            hours, remainder = divmod(estimated_time_left, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            print(f"\nProgress: {index+1}/{total_changesets} changesets processed ({progress:.1f}%)")
            print(f"Status: {success_count} successful, {failure_count} failed")
            print(f"Elapsed time: {elapsed_time:.2f} seconds")
            print(f"Estimated time remaining: {int(hours)}h {int(minutes)}m {int(seconds)}s")
            
            """             # Optional: Save progress to a file so we can resume later if needed
            with open("migration_progress.json", "w") as f:
                json.dump({
                    "last_processed_index": index,
                    "last_processed_changeset": changeset_id,
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "timestamp": time.time()
                }, f, indent=2) """
                
        except Exception as e:
            failure_count += 1
            print(f"\033[1;31m[ERROR] Exception while processing changeset {changeset_id}: {str(e)}\033[0m")
            traceback.print_exc()
    
    # Final summary - only reached if we process all changesets
    total_time = time.time() - start_time
    print("\n" + "=" * 100)
    print("MIGRATION SUMMARY")
    print("=" * 100)
    print(f"Total changesets: {total_changesets}")
    print(f"Successfully processed: {success_count}")
    print(f"Failed: {failure_count}")
    print(f"Total time: {total_time:.2f} seconds")
    
    # Calculate success rate
    if total_changesets > 0:
        success_rate = (success_count / total_changesets) * 100
        print(f"Success rate: {success_rate:.2f}%")
    
    return success_count, failure_count, None

if __name__ == "__main__":
    process_repository_changesets()