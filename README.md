- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started-seedling)
  - [Processes Migration](#one-processes-migration)
  - [Feeds Migration](#two-feeds-migration)
  - [Work Items (Boards, Backlogs, and Sprints), Iterations and Areas, and Teams Migration](#three-work-items-boards-backlogs-and-sprints-iterations-and-areas-and-teams-migration)
  - [Branches and Changesets Migration](#four-branches-and-changesets-migration)
  - [Pipelines Migration](#five-pipelines-migration)
  - [Test Artifacts (Shared Parameters, Shared Steps, Test Plans, Test Suites and Test Cases) Migration](#six-test-artifacts-shared-parameters-shared-steps-test-plans-test-suites-and-test-cases-migration)
  - [Shared Queries Migration](#seven-shared-queries-migration-must-be-migrated-prior-to-dashboards)
  - [Dashboards Migration](#eight-dashboards-migration)
  - [Assign Users To Teams](#nine-assign-users-to-teams)


# Introduction
A migration guide for migrating projects between Azure DevOps environments.

# Prerequisites
### **:one: [git-tfs](https://github.com/git-tfs/git-tfs) (and its related prerequisites)**
  git-tfs will be used to migrate the code from a TFVC-based repository to Git while preserving the changesets (version history).
  * **Installation:** [Instructions](https://github.com/git-tfs/git-tfs?tab=readme-ov-file#get-git-tfs).
  * **PAT (Personal Access Token):** Ensure you have generated a PAT with ```Code (Read)``` (at least) access for your user.

### **:two: [Azure DevOps Migration Tools](https://github.com/nkdAgility/azure-devops-migration-tools) (and its related prerequisites)**
  Azure DevOps Migration Tools will be used to migrate work items and their related information (boards, backlogs, and sprints), shared queries, iteration and area paths, and project's teams.
  * **Installation:** [Instructions](https://nkdagility.com/learn/azure-devops-migration-tools/setup/installation/).
  * **Permissions:** [Instructions](https://nkdagility.com/learn/azure-devops-migration-tools/setup/permissions/).

### **:three: Users Synchronization**
  All the users relevant for migration should be migrated to the relevant target Azure DevOps organization(s), along with their permissions.

### **:four: Branches and History To Migrate**
  Understand what branches you have to migrate, as it will affect the amount of history that has to be migrated so all the branches will be migrated properly. It will also affect the amount of time needed for the migration to be completed.

### **:five: Agent Pools Configuration**
  * **Self-hosted agents:** Ensure that all necessary software, tools, and dependencies are installed and configured identically to the source environment. This is particularly important for specialized build requirements, custom tools, or specific software versions that the build pipelines depend on. Any misalignment in agent pool configuration could lead to build failures or unexpected behavior after migration.

  * **Microsoft-hosted agents:** Verify that the target organization has the appropriate access level and quota to use these agents, as licensing and availability can affect the build pipeline execution capacity (parallel execution).

# Getting Started :seedling:
Once you have the prerequisites in place, follow these steps to perform the migration:
### :one: Processes Migration
A Process in Azure DevOps defines the way you manage and track work in your project. It is like a template that defines how work is managed in your project.

A Process determines work item types you can use (e.g., Epics, Features, User Stories, Bugs, Tasks), along with the fields (e.g., Title, Description, Priority) and workflow states (e.g., To Do, In Progress, Done) for those work items.

Every project in Azure DevOps is based on a process, which governs how work items behave. Because of that, the processes will be migrated first.

Processes migration will be handled manually as some work item types are locked in Azure DevOps, or the migration tools has partial support for such case. **Hence, to ensure a full migration, the processes will be configured manually in the target organization(s).**

**For a migration from Azure DevOps Server (on-premises):**

A process in an Azure DevOps Server is configured using an XML file, and it is not reside within the Azure DevOps Server. In such case, you will have to export the process' XML configuration file to figure out what adjustments (if any) are needed for the target environment's process.

Export the process' XML configuration file using the following ```witadmin``` command :link: [**READ BEFORE EXECUTING!**](https://learn.microsoft.com/en-us/azure/devops/reference/witadmin/witadmin-import-export-process-configuration?view=azure-devops):
``` bash
witadmin exportprocessconfig /collection:<collection_url> /p:<project_name> /f:"DirectoryPath\ProcessConfiguration.xml"
```
* Replace ```<collection_url>``` with your Azure DevOps Server collection URL.
* Replace ```<project_name>``` with your project's name within the collection.
* ```"DirectoryPath\ProcessConfiguration.xml"``` will export the XML file to your current working directory, can be modified as well.

### :two: Feeds Migration
![usedToolBadge](https://img.shields.io/badge/Tool-tfvc__to__git__artifacts.py-blue?style=social)

Artifacts Feeds provide secure and private package management for your organization. They store and distribute packages (e.g., NuGet, npm, Maven) that your projects depend on, enabling versioning, access control, and simplified dependency management. Feeds can host both private packages developed by your team and cached copies of public packages, ensuring reliable builds while maintaining control over which external dependencies are approved for use.

:warning: **Prior to the execution of the ```tfvc_to_git_artifacts.py``` script, make sure the feed itself, its views and upstream source(s) are created in the target organization.**

The ```tfvc_to_git_artifacts.py``` script handles the migration of feeds' packages, but only packages with source configured as 'This feed'. This is because packages with source configured as a public source are available through the public source, and Azure DevOps will reject its migration (unless the specific public source is not configured for the feed).

### :three: Work Items (Boards, Backlogs, and Sprints), Iterations and Areas, and Teams Migration

![usedToolBadge](https://img.shields.io/badge/Tool-Azure%20DevOps%20Migration%20Tools-blue?style=for-the-badge&labelColor=orange)

**Reverse Proxy:**

THIS SECTION IS RELEVANT FOR EVERY PART WE MIGRATE USING THE AZURE DEVOPS MIGRATION TOOLS.

The Azure DevOps Migration Tools have to use an HTTPS connection to the Azure DevOps Server. Usually, the Azure DevOps Server use the HTTP protocol which is not compatible with the requirement.

Hence, to use an HTTPS connection to your Azure DevOps Server, you can either install an SSL/TLS certificate, or use a reverse proxy.

![image](https://github.com/user-attachments/assets/dc86ffe0-237f-4ad6-858f-6ee22c035fe4)

Caddy can be used as a reverse proxy to switch the Azure DevOps Server from HTTP to HTTPS. Caddy automatically provisions SSL/TLS certificates for the provided domain using Let’s Encrypt.

:link: [**READ CADDY'S DOCUMENTATION**](https://caddyserver.com/docs/)

**If you have used the ```Caddyfile``` provided in the repository, the collection URL you will use in your JSON files is ```https://localhost:9000/tfs/<your_collection_name>```**.

From where the ```Caddyfile``` is located run the following command:
``` bash
caddy run --config .\Caddyfile
```
------------------------------

Work items are the building blocks for planning, tracking, and managing work in Azure DevOps. They help teams organize and monitor tasks, bugs, features, and requirements throughout the development lifecycle.

**Common Work Item Types:**
* **Epics:** A large piece of work that can be broken down into smaller pieces (e.g., Redesign the user experience for the website).
* **Features:** Features represent what needs to be done to achieve the goal defined by the Epic.
* **User Stories:** A small task or piece of functionality written from the perspective of the user.
* **Bugs:** A problem or error in the application that needs fixing.
* **Tasks:** A small piece of work needed to complete a User Story, Feature, or fix a Bug. Tasks are the actionable steps.

**Iterations and Areas:**
* **Iterations:** “When the work happens” (e.g., Sprint 1, Sprint 2).
* **Areas:** “Where the work belongs” (e.g., Team A, Feature B).

Work items (boards, backlogs, and sprints), iterations and areas, and teams migration will be handled using the provided ```work-items.json``` file in this repository. From your working directory run the following command:
``` bash
devopsmigration execute --config .\work-items.json
```
:warning: You may need to modify the ```work-items.json``` file to fit your specific needs - :link: [**DOCUMENTATION**](https://nkdagility.com/learn/azure-devops-migration-tools/).

**Cross-Project Links:**

![usedToolBadge](https://img.shields.io/badge/Tool-ado__migration__wi__cross__project__links.py-blue?style=social)

:warning: **Prior to the execution of the ```ado_migration_wi_cross_project_links.py``` script, make sure all the relevant work items already migrated to target organization.**

:warning: **Prior to the execution of the ```ado_migration_wi_cross_project_links.py``` script, make sure all the cross-referenced projects exist in target organization.**

:warning: **Prior to the execution of the ```ado_migration_wi_cross_project_links.py``` script, make sure all the relevant work item titles and types preserved during migration.**

When work items are migrated, links within the same project are preserved by "Azure DevOps Migration Tools", but cross-project links are lost. The ```ado_migration_wi_cross_project_links.py``` script recreates these cross-project links.

### :four: Branches and Changesets Migration
![usedToolBadge](https://img.shields.io/badge/Tool-git--tfs-blue?style=for-the-badge&labelColor=orange)

**4.1.** Start by cloning the TFVC-based repository to your local machine using the following commands:

(Optional but recommended) List all available TFVC branches using the following command:
  ``` bash
  git tfs list-remote-branches http://tfs-server:8080/tfs/<your_collection_name>
  ```
  * Replace ```http://tfs-server:8080/tfs/<your_collection_name>``` with your Azure DevOps' Server collection URL.

Depending on the branches that has to be migrated, we will set the ```branches``` flag in the command.

* Cloning a TFVC-based repository from Azure DevOps Server (on-premises):

  **4.1.1** Clone all branches and their related history using the following command:
  ``` bash
  git tfs clone --branches=all http://tfs-server:8080/tfs/<your_collection_name> $/Project/Main
  ```
  * Replace ```http://tfs-server:8080/tfs/<your_collection_name>``` with your Azure DevOps' Server collection URL.
  * Replace ```$/Project/Main``` with a path to one of your repository's branch. Basically, it will alow ```git-tfs``` to detect related branches, and make every branch in the TFVC repository a branch in the Git repository.
  * Using the ```--branches=all``` flag will cause ```git-tfs``` to clone the entire repository with all the branches and their related history (less recommended for complex branch scenarios).
  * After the clone completion, a new Git directory (new Git repository) will be created named by the cloned branch.

  **4.1.2** Clone a specified branch with its full history using the following command:
  ``` bash
  git tfs clone --branches=none http://tfs-server:8080/tfs/<your_collection_name> $/Project/Main
  ```
  * Replace ```http://tfs-server:8080/tfs/<your_collection_name>``` with your Azure DevOps' Server collection URL.
  * Replace ```$/Project/Main``` with a path to one of your repository's branch. Basically, it will alow ```git-tfs``` to detect related branches, and make every branch in the TFVC repository a branch in the Git repository.
  * Using the ```--branches=none``` flag will cause ```git-tfs``` to clone only the ```$/Project/Main``` branch with its full history, whereas other branches and their relationships (parent/child/merge metadata) are not initialized or fetched automatically.
  * In Git, branches are natvely independent so this type of clone is more recommended and has a better chance to succeed.
  * There might be cases that the whole history for the ```$/Project/Main``` branch will not be fetched initially. In such case you can run the ```git tfs fetch --all``` command to force ```git-tfs``` to recheck all the changesets for the branch and ensures no changes are missed.
  * After the clone completion, a Git new directory (new Git repository) will be created named by the cloned branch.
  
    **4.1.2.1** Initialize and fetch additional branches with their full history using the following command:
 
    :warning: By default, ```git-tfs``` tries to maintain the hierarchical relationships between TFVC branches. If the current branch you want to init and fetch was created as a child of some other branch, ```git-tfs``` considers the parent branch necessary to preserve the branch structure. **But**, pay attention to it as a manual intervention might be needed.
    ``` bash
    git tfs branch --init $/Project/Main
    ```
    * Replace ```$/Project/Main``` with a path to one of your repository's branch.
    * Repeat this command for every branch you need to be at the same Git repository.

  **4.1.3** (Optional) Verify that the cloning went well using the ```git tfs verify --all``` command.

* Cloning a TFVC-based repository from Azure DevOps Services (cloud environment):
  1. Navigate from within the command prompt or terminal to the directory where you want to create the local repository.
  2. Clone the TFVC repository with full history using the following command:
  ``` bash
  git tfs clone "https://{organization}.visualstudio.com/DefaultCollection" "$/Project/PathToTFVC" --branches=all --password {PAT}
  ```
  * Replace ```{organization}``` with your Azure DevOps organization name.
  * Replace ```$/Project/PathToTFVC``` with the TFVC repository path.
  * Replace ```{PAT}``` with your personal access token generated for your user in Azure DevOps.
------------------------------
**4.2.** Verify the local Git repository using the following commands:
* Navigate to the cloned directory:
 ``` bash
  cd PathToLocalGitRepo
  ```
* Ensure that all the branches from TFVC are present in the Git repository.
 ``` bash
  git branch
  ```
* Ensure that all the changesets from TFVC are present as commits in the Git repository.
 ``` bash
  git log
  ```
**4.3.** Add the Azure DevOps Git repository as a remote using the following command:
 ``` bash
git remote add origin https://dev.azure.com/<your_organization_name>/<your_project_name>/_git/<your_repository_name>
  ```
  * The URL also can be taken from the project's web portal in Azure DevOps.

**4.4.** Push the migrated history to Azure DevOps Git Repository using the following command:
 ``` bash
  git push --all origin
  ```
  * The ```--all``` flag ensures that all local branches are pushed to the remote repository.
  * In this sub-step, ensure you are able to authenticate via the CLI in order to ```push``` to the remote repository.

### :five: Pipelines Migration
![usedToolBadge](https://img.shields.io/badge/Tool-CodeWizard%20Script-blue?style=for-the-badge&labelColor=orange)

A Pipeline in Azure DevOps is a workflow automation tool that allows you to build, test, and deploy your code automatically.

**Types of Pipelines:**
* **Build Pipelines:** Focus on compiling code, running tests, and creating build artifacts.
  * There are two types of build pipelines:
    * **Classic Pipelines:** Stored as configuration data in Azure DevOps database, not as part of the codebase.
    * **YAML Pipelines:** Defined as code using a YAML file, part of the codebase.
* **Release Pipelines:** Focus on deploying build artifacts to environments, such as staging or production.
  * Example: Deploy a Docker image to a Kubernetes cluster.

**Task Groups (must be migrated prior to pipelines):**

![usedToolBadge](https://img.shields.io/badge/Tool-tfvc__to__git__pipelines__task__groups.py-blue?style=social)

A task group is a reusable collection of build/release tasks shared across multiple pipelines. Task groups are stored as organizational-level resources, not within project repositories.

Task groups must be migrated separately from pipelines, as dependent pipelines will break if task groups are not migrated before pipeline execution.

The ```tfvc_to_git_pipelines_task_groups.py``` script handles the migration of task groups and their nested task groups (if a task group is a task within another task group, the script will maintain this linkage).

**Variable Groups (must be migrated prior to pipelines):**

![usedToolBadge](https://img.shields.io/badge/Tool-tfvc__to__git__pipelines__variable__groups.py-blue?style=social)

A variable group is a centralized collection of variables shared across multiple pipelines.

Secret variables cannot be automatically migrated with standard tools as they store sensitive information (e.g., passwords, connection strings) as encrypted secrets, and hence they have to be recreated manually in the target environment.

The ```tfvc_to_git_pipelines_variable_groups.py``` script handles the migration of non-secret variables.

**5.1. Build Pipelines:**

  **5.1.1. Classic Build Pipelines:**
  
  :warning: **Prior to the execution of the ```tfvc_to_git_classic_pipelines.py``` or ```tfvc_to_tfvc_classic_pipelines.py``` script, make sure all the relevant service connections (per project) are reconfigured in the target organization.**
  
  :warning: **Prior to the execution of the ```tfvc_to_git_classic_pipelines.py``` or ```tfvc_to_tfvc_classic_pipelines.py``` script, make sure all the relevant secret files configured in the variable groups (per project) are reconfigured in the target organization.**

  **5.1.1.1. TFVC-based -> Git-based:**
  
  ![usedToolBadge](https://img.shields.io/badge/Tool-tfvc__to__git__classic__pipelines.py-blue?style=social)

  The ```tfvc_to_git_classic_pipelines.py``` script converts classic build pipelines that reference TFVC repositories to use Git repositories instead.

  **5.1.1.2. TFVC-based -> TFVC-based:**
  
  ![usedToolBadge](https://img.shields.io/badge/Tool-tfvc__to__tfvc__classic__pipelines.py-blue?style=social)

  The ```tfvc_to_tfvc_classic_pipelines.py``` script migrates classic build pipelines between TFVC repositories while maintaining the TFVC structure.

  **5.1.2. YAML Build Pipelines:**
  
  :construction: **UNDER CONSTRUCTION!**
  
------------------------------
**5.2. Release Pipelines:**

:construction: **UNDER CONSTRUCTION!**

### :six: Test Artifacts (Shared Parameters, Shared Steps, Test Plans, Test Suites and Test Cases) Migration
![usedToolBadge](https://img.shields.io/badge/Tool-Azure%20DevOps%20Migration%20Tools-blue?style=for-the-badge&labelColor=orange)

:construction: **UNDER CONSTRUCTION!**

:warning: **The user performing the test artifacts migration need the "Basic + Test Plans" access level in both the source Azure DevOps organization/collection and the destination Azure DevOps organization/collection.**


### :seven: Shared Queries Migration (must be migrated prior to dashboards)
![usedToolBadge](https://img.shields.io/badge/Tool-Azure%20DevOps%20Migration%20Tools-blue?style=for-the-badge&labelColor=orange)

:warning: **Migration only available for shared queries, not private queries.**

:warning: **Shared queries migration requires adjusting the ```EndpointType``` field, and hence this migration type will be handled in a separate JSON configuration file.**

Shared queries are pre-defined queries that allow teams to filter and view work items (e.g., tasks, bugs, user stories) based on specific criteria. These queries are shared across the team, making them a centralized and consistent way to track progress, identify issues, or prioritize work.

In the provided ```shared-queries.json``` file in this repository ensure that the ```SharedFolderName``` (under "Processors") aligns with your source project's shared queries' folder name in Azure DevOps.
  ![image](https://github.com/user-attachments/assets/d6baa748-cdb4-430e-a5e0-965e3f40e07e)

Shared queries migration will be handled using the provided ```shared-queries.json``` file in this repository. From your working directory run the following command:
``` bash
devopsmigration execute --config .\shared-queries.json
```
:warning: You may need to modify the ```shared-queries.json``` file to fit your specific needs - :link: [**DOCUMENTATION**](https://nkdagility.com/learn/azure-devops-migration-tools/).

### :eight: Dashboards Migration
![usedToolBadge](https://img.shields.io/badge/Tool-tfvc__to__git__dashboards.py-blue?style=social)

Dashboards are customizable, interactive panels that provide teams with a consolidated view of important project metrics, progress, and tools. Dashboards are associated with specific teams and can be tailored to display relevant widgets like sprint burndown charts, work item queries, team member details, and build pipeline summaries. They serve as a central hub for monitoring project health, team performance, and delivery timelines.

:warning: **Prior to the execution of the ```tfvc_to_git_dashboards.py``` script, make sure all the relevant third party extensions (including widgets) are reinstalled in the target organization.**

### :nine: Assign Users To Teams
![usedToolBadge](https://img.shields.io/badge/Tool-tfvc__to__git__user__to__team.py-blue?style=social)

:warning: **Prior to the execution of the ```tfvc_to_git_user_to_team.py``` script, make sure all the relevant users exist in the target organization.**

The ```tfvc_to_git_user_to_team.py``` script handles the assignment of users to their respective teams, preserving the same structure as the source environment. You will be prompted to confirm each user assignment found in the target environment, giving you full control over the migration process. Team administrator roles are also maintained.
