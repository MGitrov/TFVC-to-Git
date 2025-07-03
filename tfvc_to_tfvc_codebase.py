import subprocess
import re
import os
import threading
import io
import shutil
import time
import datetime
import json
import traceback
import pyfiglet

"""
CLARIFICATIONS:
• Workspace creation ('tf workspace /new') is handled manually.
    Command: tf workspace /new /collection:<collectionURL> /comment:"<comment>" <workspace_name>
    Workspace creation verification: tf workspaces (optional - /collection:<collectionURL>)

• Mapping server path to local path ('tf workfold /map') is handled manually.
    Command: tf workfold /map '<source_server_path (e.g., $/...)>' '<local_source_path>' /collection:<collection_url> /workspace:<workspace_name>

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
    Command: tf history '<source_server_path (e.g., $/...)>' /recursive /noprompt /format:detailed /collection:<collection_url> > history.txt
"""

source_collection = "http://192.168.1.15:8080/tfs/DefaultCollection"
target_collection = "https://dev.azure.com/NetlineDevOPS"
source_server_path = "$/SoftwareDev"
target_server_path = "$/SoftwareDev"
local_source_path = r"P:\Src"
local_target_path = r"P:\Trgt"

# A list that holds the changeset IDs of parent (trunk) branch creation.
parent_branch_creation_changesets = [
    323,   # $/SoftwareDev/Dev
    934,   # $/SoftwareDev/Prod/Challange_13 
    3245   # $/SoftwareDev/SQA
]

# A list that holds the changeset IDs of non-parent (branch from other branches) branch creation.
branch_creation_changesets = [
    # Branches from $/SoftwareDev/Dev
    344,   # Challange_14
    680,   # MCOPhase1, Tradeco, Unity12_2017 (same changeset)
    5914,  # Dev-branch-1398
    5448,  # Dev-branch-4414
    5640,  # Dev-branch-5545
    5430,  # Dev-branch-5644
    5554,  # Dev-branch-Miniz_Build_5824
    5745,  # Dev-branch-Zara-4
    6822,  # Dev-Savannah
    3908,  # Dev-SuperSpeedo
    4635,  # Dev-UCS
    5696,  # EMS.JNM
    6908,  # Production
    1763,  # Prod/Geodome
    686,   # Prod/MCOPhase2
    1454,  # Prod/Nutella2018
    1002,  # Prod/PriliDemo
    1195,  # Prod/Ringo
    1207,  # Prod/Tania
    1773,  # Prod/Unity05_2019
    1392,  # Prod/Unity12_2018
    6937,  # Dev-Knife8
    
    # Sub-branches (branches from branches)
    1149,  # Challange_14-Jango2
    1191,  # Challange_14-Lavaza3
    1724,  # Challange_14-Lavaza3-Marinade
    6888,  # Dev-LiteSavannah
    6950,  # Dev-Water5
    5623,  # Dev-UCS-branch-5249
    5944,  # EMS.JNM-Kalamari
    1205,  # MCOPhase2-DTMF
    2211,  # Esperanto
    2213,  # Esperanto1
    4418,  # NCC
    4729,  # NCC-DB
    3704,  # Nutella_Phase_2
    1795,  # Nutella2018-1661CS
    2526,  # Nutella2018-branchWithoutDepartments
    1534,  # Nutella2018-Idra
    3542,  # Nutella2018-onecodebasetest
    1124,  # Challange_13-Jango3
    1196   # Challange_13-Lavaza3[Obsolete]
]

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
            # Handles other types of errors normally.
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

    return changeset_ids_list

def get_changeset_operations(changeset_details):
    """
    This function parses the raw text output from the 'tf changeset' command to extract individual file operations (add, edit, delete, etc) that were performed in the changeset.

    Returns: List of tuples [(operation, file_path), ...]
    For example: [('add', '$/Project/NewFile.cs'), ('edit', '$/Project/ExistingFile.cs')]
    """
    file_operations = []
    
    try:
        lines = changeset_details.split('\n') # Splits the raw 'tf changeset' command output into individual lines.
        in_changes_section = False # Tracks when we are inside the file operations section.
        
        for line in lines:
            line = line.strip()
            
            # Finds the start of file operations section.
            if 'Changes:' in line or 'Items:' in line:
                in_changes_section = True
                continue
            
            # Finds the end of file operations section.
            if in_changes_section and (line.startswith('Comment:') or line.startswith('Check-in Notes:')):
                break
                
            # Parses individual file operations.
            if in_changes_section and line:
                # Usually, the format will be as follows: "operation $/path/to/file".
                
                parts = line.split()

                if len(parts) >= 2:
                    operation = parts[0].lower().strip()
                    file_path = ' '.join(parts[1:]).strip()  # Join in case path has spaces
                    
                    # Removes TFS' version notation (e.g., ;X2, ;C123) from file paths.
                    if ';' in file_path:
                        file_path = file_path.split(';')[0]
                    
                    # Processes only standard operations.
                    if operation in ['add', 'edit', 'delete', 'rename', 'branch', 'merge']:
                        file_operations.append((operation, file_path))
                        
    except Exception as e:
        print(f"\n\033[1;31m[ERROR] Failed to parse changeset operations: {e}\033[0m")
        print(f"\033[1;38;5;214m[WARNING] Falling back to bulk processing...\033[0m")
        return []
    
    return file_operations

def analyze_changeset(changeset_details, changeset_id):
    """
    This function parses changeset details and provides insights about file count, types, potential issues, etc.
    """
    try:
        print(f"\n\033[1m[INFO] Analyzing changeset no. {changeset_id}...\033[0m")

        # Extracts the file operations from the changeset details.
        operations = get_changeset_operations(changeset_details)
        
        # Categorizes all file operations by type.
        total_files = len(operations)
        add_operations = len([op for op, path in operations if op == 'add'])
        edit_operations = len([op for op, path in operations if op == 'edit'])
        delete_operations = len([op for op, path in operations if op == 'delete'])
        other_operations = total_files - add_operations - edit_operations - delete_operations
        
        file_extensions = {}
        large_paths = []
        
        for operation, file_path in operations:
            # Long paths (>200 characters) might cause Windows/TFS issues.
            if len(file_path) > 200:
                large_paths.append(file_path)
            
            # Extracts and cleans file extensions by removing non-alphanumeric characters.
            if '.' in file_path:
                extension = file_path.split('.')[-1].lower()
                extension = ''.join(c for c in extension if c.isalnum())

                # Only valid extensions are counted.
                if extension:
                    file_extensions[extension] = file_extensions.get(extension, 0) + 1
        
        # Displays comprehensive analysis.
        print(f"\n" + "\033[1m*\033[0m" * 80)
        print(f"\n\033[1m[ANALYSIS] Changeset {changeset_id} Summary:\033[0m")
        print(f"  • Total operations: {total_files}")
        print(f"  • Add operations: {add_operations}")
        print(f"  • Edit operations: {edit_operations}")
        print(f"  • Delete operations: {delete_operations}")
        print(f"  • Other operations: {other_operations}")
        print(f"\033[1m*\n\033[0m" * 80)
        
        if file_extensions:
            print(f"  • File types:")
            # Shows top 10 most common file types.
            sorted_extensions = sorted(file_extensions.items(), key=lambda x: x[1], reverse=True)[:10]

            for extension, count in sorted_extensions:
                print(f"    - .{extension}: {count} files")
        
        if large_paths:
            print(f"  • \033[1;38;5;214m[WARNING] Found {len(large_paths)} files with very long paths (>200 characters) for changeset no. {changeset_id} (3 examples):\033[0m")
            # Shows first 3 examples (truncated to 100 characters)
            for path in large_paths[:3]:
                print(f"    - {path[:100]}...")
        
        if operations:
            print(f"  • Example operations:")
            # Shows first 5 operations as examples.
            for i, (op, path) in enumerate(operations[:5]):
                short_path = path.split('/')[-1] if '/' in path else path  # Displays just the filename (not full path) for readability.
                print(f"    - {op}: '{short_path}'")

            if len(operations) > 5:
                print(f"    - ... and {len(operations) - 5} more.")
        
        # Risk assessment.
        risk_factors = []

        # Large changesets will cause longer processing time.
        if total_files > 1000:
            risk_factors.append(f"\033[1;38;5;214mLarge changeset ({total_files} files)")

        # Many adds might cause potential conflicts with existing files.
        if add_operations > 500:
            risk_factors.append(f"\033[1;38;5;214mMany new files ({add_operations} adds)")

        # Long paths might cause issues because of Windows/TFS path limit.
        if len(large_paths) > 0:
            risk_factors.append(f"\033[1;38;5;214mLong file paths ({len(large_paths)} files)")
        
        if risk_factors:
            print(f"  • \033[1;38;5;214m[WARNING] Potential risks for changeset no. {changeset_id}: {', '.join(risk_factors)}\033[0m")

        else:
            print(f"  • \033[1m[INFO] No obvious risk factors detected for changeset no. {changeset_id}.\033[0m")
        
        return operations
            
    except Exception as e:
        print(f"\033[1;31m[ERROR] Failed to analyze changeset no. {changeset_id}: {e}\033[0m")
        print(f"\033[1m[INFO] Proceeding with the migration regardless...\033[0m")
        return []

def undo_pending_changes():
    """
    This function undos any pending changes that might interfere with the migration.
    """
    try:
        print(f"\n\033[1m[INFO] Checking for any existing pending changes...\033[0m")
        
        status_result = execute_tf_command("status", capture_output=True)
        
        # TFS returns "There are no pending changes" when workspace is clean.
        if status_result and "There are no pending changes" not in status_result:
            print(f"\033[1;38;5;214m[WARNING] Found existing pending changes:\033[0m")
            print(status_result[:500] + "..." if len(status_result) > 500 else status_result)
            
            # Once any pending changes are found, they are undone.
            print(f"\033[1m[INFO] Undoing all pending changes...\033[0m")
            undo_result = execute_tf_command("undo * /recursive /noprompt")
            
            if undo_result:
                print(f"\033[1;32m[SUCCESS] Successfully undo all pending changes!\033[0m")

            else:
                print(f"\033[1;38;5;214m[WARNING] Failed to undo some pending changes.\033[0m")

        else:
            print(f"\033[1m[INFO] No pending changes found.\033[0m")
        
        return True
        
    except Exception as e:
        print(f"\033[1;31m[ERROR] Failed to undo pending changes: {e}\033[0m")
        return False

def process_changeset_operations(operations):
    """
    This function processes each file operation from a changeset individually, rather than using the bulk "copy everything + add everything" approach. In other words, this function checks what operation (e.g. add, edit) has been performed upon each file in the changeset. Reduces unnecessary conflicts and improves performance.
    """
    try:
        print(f"\n\033[1m[INFO] Processing {len(operations)} individual operations...\033[0m")
        
        actual_files_added = 0    # Files that were successfully added to TFS.
        already_tracked_files = 0 # Files that were already tracked (not added again).
        skipped_directories = 0   # Directories that were skipped.
        edit_count = 0            # Files that were successfully edited.
        other_count = 0           # Other operations (delete, etc).
        failed_operations = 0     # Operations that failed.
        
        # Iterates through each operation from the changeset one by one.
        for index, (operation, file_path) in enumerate(operations):
            if index < 3:  # Displays detailed information for the first 3 operations to help with debugging.
                print(f"\n\033[1;36m[DEBUG] Operation {index+1}: {operation} {file_path}\033[0m")

            else:
                print(f"\n\033[1m[INFO] Operation {index+1}/{len(operations)}: {operation} {file_path.split('/')[-1]}\033[0m")
            
            target_local_file_path = convert_server_path_to_target_local(file_path)
            source_local_file_path = convert_server_path_to_source_local(file_path)
            
            if index < 3: # Displays path conversion for first 3 operations to help with debugging.
                print(f"\033[1;36m[DEBUG] Server path: {file_path}\033[0m")
                print(f"\033[1;36m[DEBUG] Source local file path: {source_local_file_path}\033[0m")
                print(f"\033[1;36m[DEBUG] Target local file path: {target_local_file_path}\033[0m")
            
            if operation == 'add':
                status, success = copy_and_add_file(source_local_file_path, target_local_file_path)
                
                if status == 'success':
                    actual_files_added += 1
                elif status == 'skipped':
                    skipped_directories += 1
                elif status == 'already_tracked':
                    already_tracked_files += 1
                elif status == 'failed':
                    failed_operations += 1
                    
            elif operation == 'edit':
                if checkout_and_update_file(source_local_file_path, target_local_file_path):
                    edit_count += 1

                else:
                    failed_operations += 1
                    
            elif operation == 'delete':
                if delete_file(file_path):
                    other_count += 1

                else:
                    failed_operations += 1
            else:
                print(f"\033[1;38;5;214m[WARNING] Skipping unsupported operation: {operation} '{file_path}'...\033[0m")
                other_count += 1
        
        print(f"\n" + "\033[1m*\033[0m" * 80)
        print(f"\033[1;33m[PROCESSING COMPLETED] Processing Summary:\033[0m")
        print(f"  • New files actually added to TFVC: {actual_files_added}")
        print(f"  • Files already tracked (not added): {already_tracked_files}")
        print(f"  • Directories skipped: {skipped_directories}")
        print(f"  • Edit operations: {edit_count}")
        print(f"  • Other operations: {other_count}")
        print(f"  • Failed operations: {failed_operations}")
        print(f"\n\033[1m[INFO] Azure DevOps should show: {actual_files_added + edit_count + other_count} file changes.\033[0m")
        print(f"\033[1m*\033[0m" * 80)
        
        return True
        
    except Exception as e:
        print(f"\033[1;31m[ERROR] Failed to process individual operations: {e}\033[0m")
        return False

def convert_server_path_to_target_local(server_path):
    """
    This function converts TFS server paths (e.g. $/Project/File.cs) into local file system paths (e.g. P:\Work\Migration\TargetTestPath\Project\File.cs) for the target workspace.
    """
    try:
        # Verifies this is a valid TFS server path.
        if server_path.startswith('$/'):
            # Extracts path relative to the source server path.
            # For example:
            # server_path: "$/SoftwareDev/Source/Common/Licensing/File.cs"
            # source_server_path: "$/SoftwareDev/Source"
            # relative_path: "Common/Licensing/File.cs"
            
            if server_path.startswith(source_server_path):
                relative_path = server_path[len(source_server_path):].lstrip('/')

            else:
                # Removes just the "$/" prefix if the server path does not start with "source_server_path".
                relative_path = server_path[2:].lstrip('/')
            
            # Converts forward slashes to operation system's appropriate separators.
            relative_path = relative_path.replace('/', os.sep)
            
            # Builds final path.
            # For example:
            # local_target_path: "P:\Work\Migration\TargetTestPath"
            # relative_path: "Common\Licensing\File.cs"
            # Final path: "P:\Work\Migration\TargetTestPath\Common\Licensing\File.cs"
            return os.path.join(local_target_path, relative_path)
        
        else:
            return server_path
        
    except Exception as e:
        print(f"\n\033[1;31m[ERROR] Path conversion failed for '{server_path}': {e}\033[0m")
        return server_path

def convert_server_path_to_source_local(server_path):
    """
    This function converts TFS server paths (e.g. $/Project/File.cs) into local file system paths (e.g. P:\Work\Migration\TargetTestPath\Project\File.cs) for the source workspace.
    """
    try:
        # Verifies this is a valid TFS server path.
        if server_path.startswith('$/'):
            if server_path.startswith(source_server_path):
                relative_path = server_path[len(source_server_path):].lstrip('/')

            else:
                relative_path = server_path[2:].lstrip('/')
            
            relative_path = relative_path.replace('/', os.sep)
            
            # Builds final path.
            # For example:
            # local_source_path: "P:\Work\Migration\SourceTestPath"
            # relative_path: "Common\Licensing\File.cs"
            # Final path: "P:\Work\Migration\SourceTestPath\Common\Licensing\File.cs"
            return os.path.join(local_source_path, relative_path)
        
        else:
            return server_path
        
    except Exception as e:
        print(f"\n\033[1;31m[ERROR] Path conversion failed for '{server_path}': {e}\033[0m")
        return server_path

def copy_and_add_file(source_file, target_file):
    """
    This function copies file from the source workspace to the target workspace, and adds it to TFVC.
    """
    try:
        # Checks whether the source path is a directory (not a file), as TFVC creates them automatically when files are added.
        if os.path.isdir(source_file):
            print(f"\033[1m[INFO] Skipping directory (will be created automatically by TFVC): '{os.path.basename(source_file)}'\033[0m")
            return ('skipped', True)
        
        # Checks whether the source file exists before trying to copy it.
        if not os.path.exists(source_file):
            print(f"\033[1;38;5;214m[WARNING] Source file not found: '{source_file}'\033[0m")
            return ('failed', False)
        
        # Ensures target directory exists.
        target_dir = os.path.dirname(target_file)
        os.makedirs(target_dir, exist_ok=True) # 'exist_ok=True' means "do not error if directories already exist".
        
        # Copies the file.
        shutil.copy2(source_file, target_file)
        print(f"\033[1;32m[SUCCESS] Successfully copied '{os.path.basename(source_file)}'!\033[0m")
        
        # Checks for Windows path length limitations (260 characters). Long paths can cause issues in Windows/TFS environments.
        if len(target_file) > 260:
            print(f"\033[1;38;5;214m[WARNING] Path length ({len(target_file)} characters) can cause issues: '{target_file}'\033[0m")
        
        # Verifies once again copied file existence before adding to TFVC.
        if not os.path.exists(target_file):
            print(f"\n\033[1;31m[ERROR] File not found after copy: '{target_file}'\033[0m")
            return ('failed', False)
        
        # Additional diagnostics in order to catch any failures.
        print(f"\n" + "\033[1m*\033[0m" * 80)
        print(f"\033[1;36m[DEBUG] About to add file: '{target_file}'\033[0m")
        print(f"\033[1;36m[DEBUG] File exists in target workspace: {os.path.exists(target_file)}\033[0m")
        print(f"\033[1;36m[DEBUG] Current working directory: {os.getcwd()}\033[0m")
        print(f"\033[1;36m[DEBUG] Path length: {len(target_file)} characters\033[0m")
        print(f"\033[1m*\n\033[0m" * 80)
        
        # Adds the file to TFVC with special handling for files starting with ".".
        filename = os.path.basename(target_file)

        # Files starting with "." can be problematic for TFVC.
        if filename.startswith('.'):
            print(f"\033[1m[INFO] Handling file with leading dot: '{filename}'\033[0m")
            
            # Method 1: Uses "/recursive" flag.
            result = execute_tf_command(f'add "{target_file}" /recursive /noprompt')
            
            # Method 2: Adds the file from its parent directory.
            if not result:
                print(f"\033[1m[INFO] First method failed, trying alternative approach for '{filename}'...\033[0m")
                current_dir = os.getcwd()

                try:
                    os.chdir(target_dir)
                    result = execute_tf_command(f'add "{filename}" /noprompt')
                    
                finally:
                    os.chdir(current_dir)
            
            # Skips file if both methods fail.
            if not result:
                print(f"\033[1;38;5;214m[WARNING] TFVC cannot handle file '{filename}'; skipping to continue migration...\033[0m")
                return ('skipped', True)  # Treat as skipped rather than failed
            
        else:
            # Uses directory-based approach as workaround for workspace issues for all other files.
            print(f"\033[1m[INFO] Using directory-based add...\033[0m")
            current_dir = os.getcwd()

            try:
                os.chdir(target_dir)
                print(f"\033[1;36m[DEBUG] Changed directory to: '{os.getcwd()}'\033[0m")
                result = execute_tf_command(f'add "{filename}" /noprompt')

            finally:
                os.chdir(current_dir)
            
            # If directory-based approach fails, falls back to original full path approach.
            if not result:
                print(f"\033[1m[INFO] Directory-based add failed, trying original full path approach...\033[0m")
                result = execute_tf_command(f'add "{target_file}" /noprompt')

        # Verifies that the file was added to TFVC.
        if result:
            print(f"\033[1;36m[DEBUG] Current working directory during 'tf add' command execution: '{os.getcwd()}'\033[0m")
            
            print(f"\033[1;36m[DEBUG] Verifying '{filename}' was added to TFVC...\033[0m")
            status_check = execute_tf_command(f'status "{target_file}"', capture_output=True)
            
            if status_check and target_file in status_check and "add" in status_check.lower():
                print(f"\033[1;32m[SUCCESS] '{filename}' is pending for check-in!\033[0m")

                if isinstance(result, dict) and result.get('status') == 'already_tracked':
                    print(f"\033[1m[INFO] '{filename}' is already tracked by TFVC.\033[0m")
                    return ('already_tracked', True)
                
                else:
                    return ('success', True)
                
            else:
                print(f"\033[1;38;5;214m[WARNING] '{filename}' was not staged.\033[0m")
                print(f"\033[1m[INFO] Attempting directory-based add for '{filename}'...\033[0m")
                
                current_dir = os.getcwd()

                try:
                    os.chdir(target_dir)
                    print(f"\033[1;36m[DEBUG] Changed directory to: '{os.getcwd()}'\033[0m")
                    retry_result = execute_tf_command(f'add "{filename}" /noprompt')
                    
                    if retry_result:
                        retry_status = execute_tf_command(f'status "{filename}"', capture_output=True)

                        if retry_status and "add" in retry_status.lower():
                            print(f"\033[1;32m[SUCCESS] Successfully staged '{filename}' using directory-based approach!\033[0m")
                            return ('success', True)
                    
                    print(f"\033[1;38;5;214m[WARNING] Directory-based add also failed for '{filename}'.\033[0m")
                    return ('already_tracked', True)
                    
                finally:
                    os.chdir(current_dir)

        else:
            print(f"\n\033[1;31m[ERROR] Failed to add '{target_file}' to TFVC.\033[0m")
            return ('failed', False)
            
    except Exception as e:
        print(f"\n\033[1;31m[ERROR] Failed to copy and add '{source_file}': {e}\033[0m")
        return ('failed', False)
    
def checkout_and_update_file(source_file, target_file):
    """
    This function handles edit operations - when a file already exists in TFVC and needs to be updated with a new version.
    """
    try:
        # Checks out the file for editing.
        checkout_result = execute_tf_command(f'checkout "{target_file}" /noprompt')
        
        if checkout_result:
            # Overwrites the existing file with the updated version from the source changeset.
            if os.path.exists(source_file):
                shutil.copy2(source_file, target_file)
                return True
            
            else:
                print(f"\033[1;38;5;214m[WARNING] Source file not found: '{source_file}'\033[0m")
                return False
            
        else:
            print(f"\033[1;38;5;214m[WARNING] Failed to checkout '{target_file}'.\033[0m")
            return False
            
    except Exception as e:
        print(f"\n\033[1;31m[ERROR] Failed to checkout and update '{target_file}': {e}\033[0m")
        return False
    
def delete_file(server_path):
    """
    This function handles delete operations - when a file that existed in previous changesets needs to be removed from TFVC as part of the current changeset migration.
    """
    try:
        # Converts server path to local path because TFVC commands work on local workspace files.
        local_file = convert_server_path_to_target_local(server_path)
        
        # Marks file for deletion for the next check-in.
        result = execute_tf_command(f'delete "{local_file}" /noprompt')
        return bool(result)
        
    except Exception as e:
        print(f"\n\033[1;31m[ERROR] Failed to delete '{server_path}': {e}\033[0m")
        return False

def filter_redundant_deletes(operations):
    """
    This function filters out unnecessary 'delete' operations when a parent directory is already being deleted.
    """
    delete_operations = [(op, path) for op, path in operations if op == 'delete']
    non_delete_operations = [(op, path) for op, path in operations if op != 'delete']
    
    # If there are no delete operations, there is nothing to filter out.
    if not delete_operations:
        return operations
    
    # Sorts 'delete' operations by path length.
    delete_operations.sort(key=lambda x: len(x[1]))
    
    filtered_deletes = []
    deleted_parent_directories = set()
    
    # Checks whether the path is under any already-deleted parent directory.
    for operation, path in delete_operations:
        is_redundant = False
        
        for deleted_parent in deleted_parent_directories:
            if path.startswith(deleted_parent + '/') or path == deleted_parent:
                is_redundant = True
                print(f"\033[1m[INFO] Skipping redundant 'delete' operation: '{path}' (parent '{deleted_parent}' already being deleted).\033[0m")
                break
        
        if not is_redundant:
            filtered_deletes.append((operation, path))
            deleted_parent_directories.add(path)
    
    # Combines filtered 'delete' with non-delete operations.
    optimized_operations = non_delete_operations + filtered_deletes
    
    print(f"\n\033[1m[INFO] Reduced {len(delete_operations)} delete operations to {len(filtered_deletes)} (saved {len(delete_operations) - len(filtered_deletes)} redundant operations)\033[0m")
    
    return optimized_operations

def process_regular_changeset(changeset_id):
   """
   This function processes a regular (non-branch creation) changeset.

   • For each changeset, the function gets the specific changeset from the source repository and check it into the target repository.
   """
   print("\n" + "\033[1m-\033[0m" * 100)
   print(f"\033[1mPROCESSING REGULAR CHANGESET {changeset_id}\033[0m")
   print("\033[1m-\033[0m" * 100)

   # Step 1: Fetches the information about the current processed changeset to use later in check-in.
   print(f"\n\033[1m[INFO] Fetching changeset details...\033[0m")
   changeset_details = execute_tf_command(
       f"changeset {changeset_id} /collection:{source_collection} /noprompt"
   )

   # Analyzes changeset details and provides insights about file count, types, potential issues, etc.
   operations = analyze_changeset(changeset_details, changeset_id)

   # Extracts changeset's comment and user details.
   comment_match = re.search(r"Comment:\s*(.*?)(?:\r?\n\r?\n|\r?\n$|$)", changeset_details, re.DOTALL)
   user_match = re.search(r"User:\s*(.*?)(?:\r?\n)", changeset_details)

   MAX_COMMENT_LENGTH = 2048

   # Builds the new comment for the check-in.
   if comment_match:
       original_comment = comment_match.group(1).strip()

        # Cleans comment to prevent TFS command line issues.
       original_comment = original_comment.replace('\n', ' ').replace('\r', '')
       original_comment = ' '.join(original_comment.split()) # Removes extra spaces.
       original_comment = original_comment.replace('"', "'") # Replaces double quotes with single quotes.

   else:
       original_comment = ""
   
   if user_match:
       original_user = user_match.group(1).strip()

       if original_comment:
           new_comment = f"#{changeset_id}: {original_comment} ({original_user})"
           base_part = f"#{changeset_id}: "
           user_part = f" ({original_user})"
           available_space = MAX_COMMENT_LENGTH - len(base_part) - len(user_part)

           if len(original_comment) > available_space:
               truncated_comment = original_comment[:available_space-15] + "...[truncated]"
               new_comment = f"{base_part}{truncated_comment}{user_part}"

           else:
               new_comment = f"{base_part}{original_comment}{user_part}"
               
       else:
           new_comment = f"#{changeset_id}: ({original_user})"

   else:
       if original_comment:
           base_part = f"#{changeset_id}: "
           available_space = MAX_COMMENT_LENGTH - len(base_part)

           if len(original_comment) > available_space:
               truncated_comment = original_comment[:available_space-15] + "...[truncated]"
               new_comment = f"{base_part}{truncated_comment}"

           else:
               new_comment = f"{base_part}{original_comment}"

       else:
           new_comment = f"#{changeset_id}"

   # Step 2: Downloads the exact state of files as they were in the current processed changeset.
   print(f"\n\033[1m[INFO] Fetching the state of the changeset...\033[0m")
   print(f"\033[1m[PROGRESS] Starting file download from changeset no. {changeset_id}...\033[0m")

   os.chdir(local_source_path)
   print(f"Current working directory: {os.getcwd()}\n")

   get_result = execute_tf_command(
       f"get \"{source_server_path}\" /version:C{changeset_id} /recursive"
   )

   if not get_result:
       print(f"\n\033[1;31m[ERROR] Failed to fetch the state of changeset no. {changeset_id}.\033[0m")
       return False
   
   print(f"\033[1;32m[SUCCESS] Successfully downloaded the state of changeset no. {changeset_id}!\033[0m")

   # Steps 3 & 4: Processes files based on operations.
   print(f"\n\033[1m[INFO] Processing changeset operations...\033[0m")
   
   os.chdir(local_target_path)
   print(f"Current working directory: {os.getcwd()}\n")
   
   if operations:
       # Uses targeted approach - only changed files are processed.
       print(f"\n\033[1m[PROGRESS] Using targeted processing for {len(operations)} operations...\033[0m")
       
       # Cleans up any existing pending changes first.
       undo_pending_changes()
       
       success = process_changeset_operations(operations)

       if not success:
           print(f"\n\033[1;31m[ERROR] Failed to process changeset's no. {changeset_id} operations, falling back to bulk processing.\033[0m")
           operations = []
   
   if not operations:
       # Falls back to original bulk processing approach.
       print(f"\n\033[1m[PROGRESS] Using bulk processing approach...\033[0m")

       print(f"\n\033[1m[INFO] Cleaning target workspace directory (preserving .tf metadata)...\033[0m")
       print(f"\033[1m[PROGRESS] Starting clean operation...\033[0m")
       clean_target_workspace_content()
       
       # Step 3: Copies files and directories from the source local path to the local target path.
       print(f"\n\033[1m[INFO] Copying ALL files to '{local_target_path}' (local target path)...\033[0m")
       print(f"\033[1m[PROGRESS] Starting file copy operation...\033[0m")
       copy_files_recursively(local_source_path, local_target_path)
       print(f"\033[1;32m[SUCCESS] Successfully copied ALL files to '{local_target_path}' (local target path)!\033[0m")

       # Step 4: Stages all files for check-in.
       #print("\n\033[1m[INFO] Staging all files for check-in...\033[0m")
       #print(f"\033[1m[PROGRESS] Starting add operation...\033[0m")

       # Step 4: Reconciles workspace to detect all changes.
       print("\n\033[1m[INFO] Reconciling workspace changes...\033[0m")
       print(f"\033[1m[PROGRESS] Starting reconcile operation...\033[0m")

       # Universal operation detection.
       reconcile_result = execute_tf_command("reconcile /promote")
       #add_result = execute_tf_command("add * /recursive /noprompt")

       if reconcile_result:
        print(f"\033[1;32m[SUCCESS] Successfully reconciled workspace changes!\033[0m")

       else:
        print("\033[1;38;5;214m[WARNING] Reconcile operation failed, falling back to add operation...\033[0m")
        add_result = execute_tf_command("add * /recursive /noprompt")

        if add_result:
            print(f"\033[1m[PROGRESS] Add operation completed.\033[0m")
        
        print("\n\033[1m[INFO] Resolving any conflicts...\033[0m")
        print(f"\033[1m[PROGRESS] Starting conflict resolution (KeepYours)...\033[0m")

        resolve_result = execute_tf_command("resolve /auto:KeepYours /recursive")

        if resolve_result:
            print(f"\033[1;32m[SUCCESS] Successfully resolved conflicts!\033[0m")

        else:
            print("\033[1;38;5;214m[WARNING] No conflicts to resolve or resolve command failed.\033[0m")

       #if not add_result:
           #print("\033[1;38;5;214m[WARNING] Failed to add files.\033[0m")

       #else:
           #print(f"\033[1m[PROGRESS] Add operation completed.\033[0m")

       # Step 4.5: Resolves any conflicts that may have been triggered by the 'add' operation.
       #print("\n\033[1m[INFO] Resolving any conflicts...\033[0m")
       #print(f"\033[1m[PROGRESS] Starting conflict resolution (KeepYours)...\033[0m")

       #resolve_result = execute_tf_command("resolve /auto:KeepYours /recursive")

       #if not resolve_result:
           #print("\033[1;38;5;214m[WARNING] No conflicts to resolve or resolve command failed.\033[0m")

       #else:
           #print(f"\033[1;32m[SUCCESS] Successfully resolved conflicts!\033[0m")

   # Verifies files were successfully staged for check-in.
   final_status = execute_tf_command("status")

   if "There are no pending changes" in final_status:
       print("\n\033[1;38;5;214m[WARNING] No pending changes detected after adding files, please verify results.\033[0m")
       return False

   # Step 5: Checks-in the changeset with retry logic for conflicts.
   print(f"\n\033[1m[INFO] Checking in changeset with the following comment: '{new_comment}'\033[0m")
   print(f"\033[1m[PROGRESS] Starting check-in process...\033[0m")

   max_retries = 3
   retry_count = 0
   
   while retry_count <= max_retries:
       print(f"\n\033[1m[PROGRESS] Check-in attempt {retry_count + 1}/{max_retries + 1}...\033[0m")
       
       checkin_result = execute_tf_command(
           f"checkin /comment:\"{new_comment}\" /noprompt /recursive /force /noautoresolve",
           capture_output=False
       )
       
       if checkin_result:
           #print(f"\n\033[1;32m[SUCCESS] Successfully processed changeset no. {changeset_id}.\033[0m")
           return True
       
       print(f"\n\033[1;38;5;214m[WARNING] Check-in attempt {retry_count + 1} failed.\033[0m")
       
       if retry_count < max_retries:
           print(f"\n\033[1m[INFO] Resolving conflicts and retrying check-in... (attempt {retry_count + 2}/{max_retries + 1})\033[0m")
           print(f"\033[1m[PROGRESS] Starting retry conflict resolution...\033[0m")
           
           resolve_retry_result = execute_tf_command("resolve /auto:KeepYours /recursive")
           
           if not resolve_retry_result:
               print("\033[1;38;5;214m[WARNING] No conflicts to resolve or resolve command failed during retry.\033[0m")

           else:
               print(f"\033[1;32m[SUCCESS] Successfully resolved conflicts!\033[0m")
           
           retry_count += 1

       else:
           # Max retries reached.
           print(f"\n\033[1;31m[ERROR] Failed to check-in the changeset no. {changeset_id} after {max_retries + 1} attempts.\033[0m")
           return False
   
   print(f"\n\033[1;31m[ERROR] Failed to check-in the changeset.\033[0m")
   return False

def copy_files_recursively(source_local_directory, target_local_directory):
    """
    This function copies files from the source workspace (where files are downloaded from the source TFVC server) to the target workspace 
    (where they will be added to the target TFVC server).
    """
    for item in os.listdir(source_local_directory):
        # Extracts the name of each file, and builds full paths for source and destination directories.
        source_item = os.path.join(source_local_directory, item)
        destination_item = os.path.join(target_local_directory, item)
        
        # Skips the ".tf" directory as it contains each workspace TFS metadata, and copying it would corrupt the target workspace.
        if item == '.tf':
            continue
            
        # If the source item is a directory, a respective target directory should exist in the target workspace.
        if os.path.isdir(source_item):
            os.makedirs(destination_item, exist_ok=True) # 'exist_ok=True' means "do not error if directories already exist".
            copy_files_recursively(source_item, destination_item) # Recursive call.

        # The source item is a file.
        else:
            shutil.copy2(source_item, destination_item)

def clean_target_workspace_content():
    """
    This function removes all content from the target workspace directory while preserving the ".tf" (or "$tf") folder (TFS metadata). 
    Creates a "clean slate" so that after copying from source workspace directory, the target workspace directory contains exactly and only what should exist in the current changeset.
    """
    items_removed = 0
    
    for item in os.listdir(local_target_path):
        # Skips the ".tf" directory as it contains the workspace TFS metadata.
        if item == '.tf':
            continue

        item_path = os.path.join(local_target_path, item)

        try:
            # Removes directories.
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
                print(f"\033[1;33m[CLEANUP] Removed directory: '{item}'\033[0m")
                items_removed += 1

            # Removes files.
            else:
                os.remove(item_path)
                print(f"\033[1;33m[CLEANUP] Removed file: '{item}'\033[0m")
                items_removed += 1

        except Exception as e:
            print(f"\n\033[1;38;5;214m[WARNING] Could not delete '{item}': {e}\033[0m")
    
    if items_removed > 0:
        print(f"\n\033[1;32m[SUCCESS] Successfully cleaned {items_removed} items from the target workspace!\033[0m")

    else:
        print(f"\n\033[1m[INFO] Target workspace was already clean.\033[0m")

def save_migration_state(last_processed_changeset, branch_changeset, all_changesets):
    """
    This function captures the migration state to a local file when encountering a branch creation changeset.
    
    It is needed so the user will be able to continue the migration process smoothly after the branch creation changeset was handled manually.
    """
    # Gets the script's directory to save the state files there.
    script_directory = os.path.dirname(os.path.abspath(__file__))
    
    # Creates a timestamp for unique state filenames.
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Determines remaining changesets, so it can be displayed to the user.
    if all_changesets:
        current_index = all_changesets.index(branch_changeset) if branch_changeset in all_changesets else -1
        remaining_changesets = all_changesets[current_index+1:] if current_index >= 0 else []

    else:
        remaining_changesets = []
    
    state_data = {
        "Last processed changeset": last_processed_changeset,
        "Branch creation changeset": branch_changeset,
        "Timestamp": timestamp,
        "Resume from changeset no.": branch_changeset + 1,
        "Source collection (or organization)": source_collection,
        "Source server path": source_server_path,
        "Target collection (or organization)": target_collection,
        "Target server path": target_server_path,
        "Remaining changesets": remaining_changesets
    }
    
    state_file_path = os.path.join(script_directory, f"migration_state_{timestamp}.json")

    with open(state_file_path, "w") as state_file:
        json.dump(state_data, state_file, indent=4)
    
    # Creates a more user-friendly text file with instructions for resuming migration.
    instructions_file_path = os.path.join(script_directory, f"migration_instructions_{timestamp}.txt")

    with open(instructions_file_path, "w") as instructions_file:
        instructions_file.write("=" * 100 + "\n")  # Added newline
        instructions_file.write(f"TFVC MIGRATION PAUSED - BRANCH CREATION DETECTED\n")
        instructions_file.write("=" * 100 + "\n")
        
        instructions_file.write(f"Migration paused at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        instructions_file.write("CURRENT STATE:\n")
        instructions_file.write(f"• Last successfully processed changeset: {last_processed_changeset}\n")
        instructions_file.write(f"• Branch creation changeset requiring manual handling: {branch_changeset}\n\n")
        
        instructions_file.write("MANUAL STEPS REQUIRED (PARENT BRANCH):\n")
        instructions_file.write(f"1. From your local source path ('{local_source_path}'), execute 'tf get \"{source_server_path}\" /version:C{branch_changeset} /recursive'.\n")
        instructions_file.write(f"2. Once fetched, copy all the fetched content from the '{local_source_path}' directory to the '{local_target_path}' directory.\n")
        instructions_file.write(f"3. From your local target path ('{local_target_path}'), execute 'tf add * /recursive' (adjust accordingly).\n")
        instructions_file.write("4. Execute 'tf checkin /comment:<your_comment_here> /noprompt /recursive /force /noautoresolve'.\n")
        instructions_file.write("5. From Visual Studio, convert the parent folder to a branch.\n\n")
        
        instructions_file.write("MANUAL STEPS REQUIRED (NON-PARENT BRANCH):\n")
        instructions_file.write(f"1. From your local target path ('{local_target_path}'), execute 'tf branch '<parent_branch_target_server_path (e.g., $/...)>' '<new_branch_target_server_path (e.g., $/...)>''.\n")
        instructions_file.write("2. Execute 'tf checkin /comment:<your_comment_here> /noprompt /recursive /force /noautoresolve'.\n\n")
        
        instructions_file.write("MANUAL STEPS REQUIRED (NESTED BRANCH - BRANCH WITHIN A FOLDER):\n")
        instructions_file.write(f"1. In your local target path ('{local_target_path}'), create the folder (either using the 'mkdir' command or UI) in which the branch resides.\n")
        instructions_file.write("2. Execute 'tf add * /recursive' (adjust accordingly).\n")
        instructions_file.write("3. Execute 'tf checkin /comment:<your_comment_here> /noprompt /recursive /force /noautoresolve'.\n")
        instructions_file.write("4. Follow the 'non-parent branch' steps.\n\n")
        
        instructions_file.write("TO RESUME MIGRATION:\n")
        instructions_file.write(f"• Resume the script with changeset no. {branch_changeset + 1}.\n")
        instructions_file.write(f"• Assign the 'Remaining changesets' list to the 'all_changesets' variable in the 'process_repository_changesets' function.\n\n")
        
        instructions_file.write("REPOSITORY DETAILS:\n")
        instructions_file.write(f"• Source collection (or organization): {source_collection}\n")
        instructions_file.write(f"• Source server path: {source_server_path}\n")
        instructions_file.write(f"• Target collection (or organization): {target_collection}\n")
        instructions_file.write(f"• Target server path: {target_server_path}\n\n")
        
        instructions_file.write("REMAINING CHANGESETS TO PROCESS:\n")
        if remaining_changesets:
            instructions_file.write(f"• Remaining changesets: {remaining_changesets}\n")

        else:
            instructions_file.write("• No remaining changesets (branch creation was the last changeset).\n")
    
    print("\n" + "\033[1m=\033[0m" * 100)
    print(f"\033[1;33m[INFO] Migration state saved to: {state_file_path}\033[0m")
    print(f"\033[1;33m[INFO] Instructions for resuming migration saved to: {instructions_file_path}\033[0m")
    print("\033[1m=\033[0m" * 100)

def process_repository_changesets(history_file):
    """
    This function migrates a TFVC-based repository from a source project to a target project.

    Returns:
        tuple: (success_count, failure_count, stopped_at_changeset)
    """
    os.system('cls' if os.name == 'nt' else 'clear')
    ascii_art = pyfiglet.figlet_format("by codewizard", font="ogre")
    print(ascii_art)

    print("\n" + "\033[1m=\033[0m" * 100)
    print(f"\033[1mSTARTING REPOSITORY MIGRATION\033[0m")
    print("\033[1m=\033[0m" * 100)
    
    # Fetches all changesets from repository's history file.
    start_time = time.time()
    all_changesets = parse_history_file(history_file=history_file)
    
    parse_time = time.time() - start_time
    
    if not all_changesets:
        print("\n\033[1;31m[ERROR] Failed to get changesets from repository's history file.\033[0m")
        return 0, 0, None
    
    total_changesets = len(all_changesets)
    print(f"\n\033[1m[INFO] Found {total_changesets} changesets in repository's history file (took {parse_time:.2f} seconds).\033[0m")
    
    # Counters.
    success_count = 0
    failure_count = 0
    last_processed_changeset = None
    
    # Processes the changesets sequentially.
    for index, changeset_id in enumerate(all_changesets):
        progress = (index + 1) / total_changesets * 100 # Calculates progress percentage.
        
        # Checks whether this is an any branch creation changeset.
        if changeset_id in parent_branch_creation_changesets:
            print(f"\n\033[1;33m[BRANCH CREATION DETECTED] Changeset no. {changeset_id} is a parent (trunk) branch creation changeset.\033[0m")
            save_migration_state(last_processed_changeset, changeset_id, all_changesets)
            
            # The script will exit within the 'handle_branch_creation_changeset' function, but just in case.
            return success_count, failure_count, changeset_id
            
        if changeset_id in branch_creation_changesets:
            print(f"\n\033[1;33m[BRANCH CREATION DETECTED] Changeset no. {changeset_id} is a branch creation (non-parent) changeset.\033[0m")
            save_migration_state(last_processed_changeset, changeset_id, all_changesets)
            
            # The script will exit within the 'handle_branch_creation_changeset' function, but just in case.
            return success_count, failure_count, changeset_id
        
        changeset_start_time = time.time()
        
        try:
            result = process_regular_changeset(changeset_id)
            
            if result:
                success_count += 1
                last_processed_changeset = changeset_id
                changeset_time = time.time() - changeset_start_time
                print(f"\n\033[1;32m[SUCCESS] Successfully processed changeset no. {changeset_id} (took {changeset_time:.2f} seconds)!\033[0m")

            else:
                failure_count += 1
                print(f"\n\033[1;31m[ERROR] Failed to process changeset no. {changeset_id}.\033[0m")
                
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
            traceback.print_exc() # A detailed output of the exception.
    
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
    process_repository_changesets(history_file="P:\\Work\\history.txt")