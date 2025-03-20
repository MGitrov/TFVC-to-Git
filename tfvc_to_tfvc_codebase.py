import subprocess
import re
import os
import sys
import threading
import io
import shutil
import time
import datetime
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
• Parent (trunk) branches' first changeset - the 'parent_branch_creation_changesets' list has to be filled.
    The branch hierarchy can be viewed using either the 'git tfs list-remote-branches <collectionURL>' command, or Visual Studio.
    The parent branch is migrated as a regular changeset, and once migrated will be converted to a branch via Visual Studio.

• The first changeset of all other branches - the 'branch_creation_changesets' list has to be filled.
• An history file of the source TFVC repository.
    Command: tf history '<source_server_path (e.g., $/...)>' /recursive /noprompt /format:detailed /collection:<collectionURL> > history.txt
"""

source_collection = "https://dev.azure.com/maximpetrov2612"
target_collection = "https://dev.azure.com/maximpetrov1297"
source_server_path = "$/TFS-based test project"
target_server_path = "$/Magnolia"
local_source_path = "P:\Work\Migration\SourcePath"
local_target_path = "P:\Work\Migration\TargetPath"

# A list that holds the changeset IDs of parent (trunk) branch creation.
parent_branch_creation_changesets = [6]

# A list that holds the changeset IDs of non-parent (branch from other branches) branch creation.
branch_creation_changesets = [7, 11, 12]

def execute_tf_command(command, capture_output=True):
    """
    This function executes a 'TF' command with improved error handling for already-tracked files, and progress display for the 'tf get' command.
    """
    print(f"\033[1m[COMMAND EXECUTION] Executing the following command: tf {command}\033[0m")
    
    # Checks whether this is a 'get' command as it is handled differently.
    if ('get' in command and '/recursive' in command) or 'get /version' in command:
        return execute_tf_get_command(command)
    
    # Standard command execution for non-get commands.
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
                # For non-add commands, the message displayed as a warning message to indicate that there is a conflict in the pending changes that TFVC cannot automatically resolve.
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

def execute_tf_get_command(command):
    """
    This function executes the 'tf get' command with a progress indicator showing that the command is still running (helpful for large repositories).
    """
    print("\033[1m[INFO] Starting file retrieval (this may take some time for large repositories)...\033[0m")
    
    start_time = time.time()
    
    output = io.StringIO()
    error_output = io.StringIO()
    return_code = [0]  # A list to store the exit status - used by the thread function to communicate to the main thread.
    
    """
    A separate thread execution that executes the 'tf get' command.
    The threading approach is necessary because Python's standard 'subprocess.run()' function is blocking - it would stop all execution until the command completes, 
    preventing any progress updates.

    Using a separate thread, the main Python thread remains responsive, allowing us to update the progress display.
    """
    def run_command():
        try:
            process = subprocess.run(f"tf {command}", shell=True, capture_output=True, text=True, check=False)
            output.write(process.stdout)
            error_output.write(process.stderr)
            return_code[0] = process.returncode

        except Exception as e:
            error_output.write(f"Exception occurred: {str(e)}")
            return_code[0] = -1
    
    thread = threading.Thread(target=run_command)
    thread.start()
    
    spinners = ['⣾', '⣷', '⣯', '⣟', '⡿', '⢿', '⣻', '⣽']
    index = 0
    
    while thread.is_alive():
        elapsed = time.time() - start_time
        mins, secs = divmod(int(elapsed), 60)
        hours, mins = divmod(mins, 60)
        
        time_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
        print(f"\rRetrieving files {spinners[index]} [Elapsed: {time_str}]", end="", flush=True)
        
        index = (index + 1) % len(spinners) # Ensures the index wraps around to zero after reaching the end of the array, creating a continuous animation loop.
        time.sleep(0.1)  # Updates 10 times per second for smoother animation.
    
    elapsed_time = time.time() - start_time
    mins, secs = divmod(int(elapsed_time), 60)
    hours, mins = divmod(mins, 60)
    time_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
    
    print(f"\rOperation completed in {time_str} {'  ' * 10}.")
    
    if return_code[0] != 0:
        print(f"\n\033[1;31m[ERROR] The 'tf get' command failed with return code {return_code[0]}.\033[0m")
        error_text = error_output.getvalue()

        if error_text:
            print(f"\033[1;31m[ERROR] Output: {error_text}.\033[0m")
        return None
    
    return output.getvalue() # The '.getvalue()' method retrieves all the text that has been accumulated in the StringIO buffer and returns it as a single string. 
    # It is converting the in-memory text stream back into a regular Python string that can be used by the rest of the script.

def parse_history_file(history_file):
    """
    This function parses the TFVC repository history file, extracting only changeset IDs.
    """
    print(f"\033[1m[INFO] Extracting changeset IDs from the '{history_file}' history file...\033[0m")

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
                    print(f"\n\033[1;31m[ERROR] Error parsing changeset ID from line {line}; error message: {e}\033[0m")
    
    changeset_ids_list = sorted(list(changeset_ids))

    #print(f"\033[1m[INFO] Processed {line_count} lines and found {len(changeset_ids_list)} unique changeset IDs.\033[0m")
    
    return changeset_ids_list

def process_regular_changeset(changeset_id):
    """
    This function processes a regular (non-branch creation) changeset.

    • For each changeset, the function gets the specific changeset from the source repository and check it into the target repository.
    """
    print("\n" + "\033[1m-\033[0m" * 100)
    print(f"\033[1mPROCESSING REGULAR CHANGESET {changeset_id}\033[0m")
    print("\033[1m-\033[0m" * 100)
    
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
    print(f"\n\033[1m[INFO] Fetching the state of the changeset...\033[0m")

    os.chdir(local_source_path)
    print(f"Current working directory: {os.getcwd()}\n")

    get_result = execute_tf_command(
        f"get \"{source_server_path}\" /version:C{changeset_id} /recursive /force"
    )

    if not get_result:
        print(f"\033[1;31m[ERROR] Failed to fetch the state of the changeset.\033[0m")
        return False
    

    # Step 3: Copies files and directories from the source local path to the local target path.
    print(f"\n\033[1m[INFO] Copying all files to '{local_target_path}' (local target path)...\033[0m")
    copy_files_recursively(local_source_path, local_target_path)


    # Step 4: Stages all files for check-in.
    print("\n\033[1m[INFO] Staging all files for check-in...\033[0m")

    os.chdir(local_target_path)
    print(f"Current working directory: {os.getcwd()}\n")

    add_result = execute_tf_command("add * /recursive /noprompt")

    if not add_result:
        print("\033[1;38;5;214m[WARNING] Failed to add files.\033[0m")

    # Verifies files were successfully staged for check-in.
    final_status = execute_tf_command("status")

    if "There are no pending changes" in final_status:
        print("\n\033[1;38;5;214m[WARNING] No pending changes detected after adding files, please verify results.\033[0m")
        return False
    
    # Step 5: Checks-in the changeset.
    print(f"\n\033[1m[INFO] Checking in changeset with the following comment: '{new_comment}'\033[0m")

    checkin_result = execute_tf_command(
        f"checkin /comment:\"{new_comment}\" /noprompt /recursive"
    )
    
    if not checkin_result:
        print("\n\033[1;31m[ERROR] Failed to check-in the changeset.\033[0m")
        return False
    
    #print(f"\n\033[1;32m[SUCCESS] Successfully processed changeset no. {changeset_id}.\033[0m")
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

def add_file_safely(file_path): # DEPRECATED.
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

def is_file_tracked(file_path): # DEPRECATED.
    """
    Checks if a file already exists in TFVC using 'tf get'.
    """
    output = execute_tf_command(f'get "{file_path}" /preview')
    return "All files are up to date" in output or "Replacing" in output

def has_pending_changes(file_path): # DEPRECATED.
    """Checks if the file has pending changes using 'tf status'."""
    output = execute_tf_command(f'status "{file_path}" /format:detailed /noprompt')
    return "edit" in output.lower() or "add" in output.lower() # return true because of "candidate changes"

def was_file_deleted(file_path): # DEPRECATED.
    """Checks if a file was previously deleted using 'tf history'."""
    output = execute_tf_command(f'history "{file_path}" /noprompt')
    return "delete" in output.lower()

def save_migration_state(last_processed_changeset, branch_changeset, all_changesets):
    """
    Saves the current migration state to a local file when encountering a branch creation changeset.
    
    Args:
        last_processed_changeset: The ID of the last successfully processed changeset
        branch_changeset: The ID of the branch creation changeset that needs manual handling
        all_changesets: The complete list of changesets from the history file
    """
    # Get the script's directory to save the state files there
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create a timestamp for unique filenames
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Determine remaining changesets
    if all_changesets:
        current_index = all_changesets.index(branch_changeset) if branch_changeset in all_changesets else -1
        remaining_changesets = all_changesets[current_index+1:] if current_index >= 0 else []
    else:
        remaining_changesets = []
    
    # Create state data
    state_data = {
        "last_processed_changeset": last_processed_changeset,
        "branch_creation_changeset": branch_changeset,
        "timestamp": timestamp,
        "resume_from_changeset": branch_changeset + 1,  # Suggest resuming from the next changeset
        "source_collection": source_collection,
        "source_server_path": source_server_path,
        "target_server_path": target_server_path,
        "remaining_changesets": remaining_changesets  # Add the list of remaining changesets
    }
    
    # Save the state information to a JSON file
    state_file_path = os.path.join(script_dir, f"migration_state_{timestamp}.json")
    with open(state_file_path, "w") as state_file:
        json.dump(state_data, state_file, indent=4)
    
    # Also create a more user-friendly text file with instructions
    instructions_file_path = os.path.join(script_dir, f"migration_instructions_{timestamp}.txt")
    with open(instructions_file_path, "w") as instructions_file:
        instructions_file.write("=" * 80 + "\n")
        instructions_file.write(f"TFVC MIGRATION PAUSED - BRANCH CREATION DETECTED\n")
        instructions_file.write("=" * 80 + "\n\n")
        
        instructions_file.write(f"Migration paused at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        instructions_file.write("CURRENT STATE:\n")
        instructions_file.write(f"• Last successfully processed changeset: {last_processed_changeset}\n")
        instructions_file.write(f"• Branch creation changeset requiring manual handling: {branch_changeset}\n\n")
        
        instructions_file.write("MANUAL STEPS REQUIRED:\n")
        instructions_file.write("1. Create the branch in the target repository manually\n")
        instructions_file.write("2. Check in the branch creation\n")
        instructions_file.write("3. Verify the branch structure is correct\n\n")
        
        instructions_file.write("TO RESUME MIGRATION:\n")
        instructions_file.write(f"• Resume the script with changeset {branch_changeset + 1}\n")
        instructions_file.write(f"• Command: python tfvc_to_tfvc_codebase.py --start-changeset {branch_changeset + 1}\n\n")
        
        instructions_file.write("REPOSITORY DETAILS:\n")
        instructions_file.write(f"• Source collection: {source_collection}\n")
        instructions_file.write(f"• Source path: {source_server_path}\n")
        instructions_file.write(f"• Target path: {target_server_path}\n\n")
        
        # Add the remaining changesets section
        instructions_file.write("REMAINING CHANGESETS TO PROCESS:\n")
        if remaining_changesets:
            for i, changeset in enumerate(remaining_changesets, 1):
                instructions_file.write(f"• {i}. Changeset {changeset}\n")
        else:
            instructions_file.write("• No remaining changesets (branch creation was the last changeset)\n")
    
    print("\n" + "!" * 100)
    print(f"\033[1;33m[INFO] Migration state saved to: {state_file_path}\033[0m")
    print(f"\033[1;33m[INFO] Instructions for resuming migration saved to: {instructions_file_path}\033[0m")
    print("!" * 100 + "\n")

def handle_branch_creation_changeset(changeset_id, last_processed_changeset, all_changesets):
    """
    Handles a branch creation changeset by pausing the script and providing instructions.
    
    Args:
        changeset_id: The ID of the branch creation changeset
        last_processed_changeset: The ID of the last successfully processed changeset
        all_changesets: The complete list of changesets from the history file
    """
    print("\n" + "\033[1m=\033[0m" * 100)
    print(f"\033[1;33m[BRANCH CREATION DETECTED] Changeset {changeset_id} creates a new branch\033[0m")
    print("\033[1m=\033[0m" * 100)
    
    # Get branch details for user reference
    branch_details = execute_tf_command(
        f"changeset {changeset_id} /collection:{source_collection} /noprompt"
    )
    
    # Save current migration state with the list of remaining changesets
    save_migration_state(last_processed_changeset, changeset_id, all_changesets)
    
    print("\n\033[1;33m[MANUAL ACTION REQUIRED] This changeset creates a new branch and needs manual handling.\033[0m")
    print("\n\033[1;33mBranch creation details:\033[0m")
    print(branch_details)
    
    print("\n\033[1;33mPlease follow these steps:\033[0m")
    print("1. Create the branch in the target repository manually")
    print("2. Check in the branch creation")
    print("3. Verify the branch structure is correct")
    print(f"4. Resume the script with changeset {changeset_id + 1}")
    print(f"   Command: python tfvc_to_tfvc_codebase.py --start-changeset {changeset_id + 1}")
    
    # Exit the script with a special code indicating manual intervention is needed
    sys.exit(42)  # Using 42 as a special exit code to indicate manual steps needed

def process_repository_changesets(history_file):
    """
    This function migrates a TFVC-based repository from a source project to a target project.

    Returns:
        tuple: (success_count, failure_count, stopped_at_changeset)
    """
    print("\n" + "\033[1m=\033[0m" * 100)
    print(f"\033[1mSTARTING REPOSITORY MIGRATION\033[0m")
    print("\033[1m=\033[0m" * 100)
    
    # Fetches all changesets from repository's history file.
    start_time = time.time()
    all_changesets = [17, 18]#parse_history_file(history_file=history_file)
    parse_time = time.time() - start_time
    
    if not all_changesets:
        print("\033[1;31m[ERROR] Failed to get changesets from repository's history file.\033[0m")
        return 0, 0, None
    
    total_changesets = len(all_changesets)
    print(f"\nFound {total_changesets} changesets in repository's history file (took {parse_time:.2f} seconds).\033[0m")
    
    # Counters.
    success_count = 0
    failure_count = 0
    last_processed_changeset = None
    
    # Processes the changesets sequentially.
    for index, changeset_id in enumerate(all_changesets):
        # Calculate progress percentage
        progress = (index + 1) / total_changesets * 100
        
        # Checks whether this is an any branch creation changeset.
        if changeset_id in parent_branch_creation_changesets:
            print(f"\n\033[1;33m[BRANCH CREATION DETECTED] Changeset {changeset_id} is a parent (trunk) branch creation changeset.\033[0m")
            handle_branch_creation_changeset(changeset_id, last_processed_changeset, all_changesets)
            
            # The script will exit within the 'handle_branch_creation_changeset' function, but just in case.
            return success_count, failure_count, changeset_id
            
        if changeset_id in branch_creation_changesets:
            print(f"\n\033[1;33m[BRANCH CREATION DETECTED] Changeset {changeset_id} is a branch creation (non-parent) changeset.\033[0m")
            handle_branch_creation_changeset(changeset_id, last_processed_changeset, all_changesets)
            
            # The script will exit within the 'handle_branch_creation_changeset' function, but just in case.
            return success_count, failure_count, changeset_id
        
        changeset_start_time = time.time()
        
        try:
            result = process_regular_changeset(changeset_id)
            
            if result:
                success_count += 1
                last_processed_changeset = changeset_id
                changeset_time = time.time() - changeset_start_time
                print(f"\n\033[1;32m[SUCCESS] Successfully processed changeset no. {changeset_id} (took {changeset_time:.2f} seconds).\033[0m")

            else:
                failure_count += 1
                print(f"\n\033[1;31m[FAILURE] Failed to process changeset no. {changeset_id}.\033[0m")
                
            # Calculates estimated time remaining.
            elapsed_time = time.time() - start_time
            changesets_left = total_changesets - (index + 1)
            avg_time_per_changeset = elapsed_time / (index + 1)
            estimated_time_left = avg_time_per_changeset * changesets_left
            
            # Formats as 'hours:minutes:seconds'.
            hours, remainder = divmod(estimated_time_left, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            print(f"\n• Progress: {index+1}/{total_changesets} changesets processed ({progress:.1f}%)")
            print(f"• Status: {success_count} successful, {failure_count} failed")
            print(f"• Elapsed time: {elapsed_time:.2f} seconds")
            print(f"• Estimated time remaining: {int(hours)}h {int(minutes)}m {int(seconds)}s")
                
        except Exception as e:
            failure_count += 1
            print(f"\033[1;31m[ERROR] An error occurred while processing changeset no. {changeset_id}: {e}\033[0m")
            traceback.print_exc()
    
    total_time = time.time() - start_time
    print("\n" + "\033[1m=\033[0m" * 100)
    print("\033[1mMIGRATION SUMMARY\033[0m")
    print("\033[1m=\033[0m" * 100)
    print(f"• Total changesets: {total_changesets}")
    print(f"• Successful migration: {success_count}")
    print(f"• Failed migration: {failure_count}")
    print(f"• Total time: {total_time:.2f} seconds")
    
    return success_count, failure_count, None

if __name__ == "__main__":
    process_repository_changesets(history_file="C:\\Users\\maxim\\history.txt")