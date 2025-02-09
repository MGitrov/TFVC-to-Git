- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started-seedling)
  - [Processes Migration](#one-processes-migration)
  - [Work Items (Boards, Backlogs, and Sprints), Iterations and Areas, and Teams Migration](#two-work-items-boards-backlogs-and-sprints-iterations-and-areas-and-teams-migration)
  - [Branches and Changesets Migration](#three-branches-and-changesets-migration)
  - [Shared Queries Migration](#four-shared-queries-migration)
  - [Dashboards Migration](#five-dashboards-migration)
  - [Assign Users To Teams](#six-assign-users-to-teams)
  - [Pipelines Migration](#seven-pipelines-migration)


# Introduction
A migration guide from a TFVC-based project to a Git-based project.

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
witadmin exportprocessconfig /collection:CollectionURL /p:ProjectName /f:"DirectoryPath\ProcessConfiguration.xml"
```
* Replace ```CollectionURL``` with your Azure DevOps Server collection URL.
* Replace ```ProjectName``` with your project's name within the collection.
* ```"DirectoryPath\ProcessConfiguration.xml"``` will export the XML file to your current working directory, can be modified as well.

### :two: Work Items (Boards, Backlogs, and Sprints), Iterations and Areas, and Teams Migration
:purple_circle: Will be migrated using Azure DevOps Migration Tools.

:hourglass_flowing_sand: A migration of 2,400~ work items took nearly two hours.

**Reverse Proxy:**

THIS SECTION IS RELEVANT FOR EVERY PART WE MIGRATE USING THE AZURE DEVOPS MIGRATION TOOLS.

The Azure DevOps Migration Tools have to use an HTTPS connection to the Azure DevOps Server. Usually, the Azure DevOps Server use the HTTP protocol which is not compatible with the requirement.

Hence, to use an HTTPS connection to your Azure DevOps Server, you can either install an SSL/TLS certificate, or use a reverse proxy.

![image](https://github.com/user-attachments/assets/dc86ffe0-237f-4ad6-858f-6ee22c035fe4)

We can use Caddy as a reverse proxy to switch the Azure DevOps Server from HTTP to HTTPS. Caddy automatically provisions SSL/TLS certificates for the provided domain using Let’s Encrypt.

:link: [**READ CADDY'S DOCUMENTATION**](https://caddyserver.com/docs/)

If you have used the ```Caddyfile``` provided in the repository, the collection URL you will use in the JSON files is ```https://localhost:9000/tfs/YourCollectionName```.

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

### :three: Branches and Changesets Migration
:purple_circle: Will be migrated using git-tfs.

**1.1.** Start by cloning the **TFVC-based** repository to your local machine using the following commands:

Depending on the branches that has to be migrated, we will set the ```branches``` flag in the command.

* Cloning a TFVC-based repository from Azure DevOps Server (on-premises):

  **1.1.1** Clone all branches and their related history using the following command:
  ``` bash
  git tfs clone --branches=all http://tfs-server:8080/tfs/Collection $/Project/Main
  ```
  * Replace ```http://tfs-server:8080/tfs/Collection``` with your Azure DevOps' Server collection URL.
  * Replace ```$/Project/Main``` with a path to one of your repository's branch. Basically, it will alow ```git-tfs``` to detect related branches, and make every branch in the TFVC repository a branch in the Git repository.
  * Using the ```--branches=all``` flag will cause ```git-tfs``` to clone the entire repository with all the branches and their related history (less recommended for complex branch scenarios).
  * After the clone completion, a new Git directory (new Git repository) will be created named by the cloned branch.

  **1.1.2** Clone a specified branch with its full history using the following command:
  ``` bash
  git tfs clone --branches=none http://tfs-server:8080/tfs/Collection $/Project/Main
  ```
  * Replace ```http://tfs-server:8080/tfs/Collection``` with your Azure DevOps' Server collection URL.
  * Replace ```$/Project/Main``` with a path to one of your repository's branch. Basically, it will alow ```git-tfs``` to detect related branches, and make every branch in the TFVC repository a branch in the Git repository.
  * Using the ```--branches=none``` flag will cause ```git-tfs``` to clone only the ```$/Project/Main``` branch with its full history, whereas other branches and their relationships (parent/child/merge metadata) are not initialized or fetched automatically.
  * In Git, branches are natvely independent so this type of clone is more recommended and has a better chance to succeed.
  * There might be cases that the whole history for the ```$/Project/Main``` branch will not be fetched initially. In such case you can run the ```git tfs fetch --all``` command to force ```git-tfs``` to recheck all the changesets for the branch and ensures no changes are missed.
  * After the clone completion, a Git new directory (new Git repository) will be created named by the cloned branch.
  
    **1.1.2.1** Initialize and fetch additional branches with their full history using the following command:
 
    :warning: By default, ```git-tfs``` tries to maintain the hierarchical relationships between TFS branches. If the current branch you want to init and fetch was created as a child of some other branch, ```git-tfs``` considers the parent branch necessary to preserve the branch structure. **But**, pay attention to it as a manual intervention might be needed.
    ``` bash
    git tfs branch --init $/Project/Main
    ```
    * Replace ```$/Project/Main``` with a path to one of your repository's branch.
    * Repeat this command for every branch you need to be at the same Git repository.

  **1.1.3** (Optional) Verify that the cloning went well using the ```git tfs verify --all``` command.

* Cloning a TFVC-based repository from Azure DevOps Services (cloud environment):
  1. Navigate from within the command prompt or terminal to the directory where you want to create the local repository.
  2. Clone the TFVC repository with full history using the following command:
  ``` bash
  git tfs clone "https://{organization}.visualstudio.com/DefaultCollection" "$/Project/PathToTFVC" --branches=all --password {PAT}
  ```
  * Replace ```{organization}``` with your Azure DevOps organization name.
  * Replace ```$/Project/PathToTFVC``` with the TFVC repository path.
  * Replace ```{PAT}``` with your personal access token generated for your user in Azure DevOps.
 
**1.2.** Verify the local Git repository using the following commands:
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
**1.3.** Add the Azure DevOps Git repository as a remote using the following command:
 ``` bash
git remote add origin https://dev.azure.com/YourOrganizationName/YourProjectName/_git/YourRepositoryName
  ```
  * The URL also can be taken from the project's web portal in Azure DevOps.

**1.4.** Push the migrated history to Azure DevOps Git Repository using the following command:
 ``` bash
  git push --all origin
  ```
  * The ```--all``` flag ensures that all local branches are pushed to the remote repository.
  * In this sub-step, ensure you are able to authenticate via the CLI in order to ```push``` to the remote repository.

### :four: Shared Queries Migration
:purple_circle: Will be migrated using Azure DevOps Migration Tools.

:warning: **Migration only available for shared queries.**

:warning: **Shared queries migration requires adjusting the ```EndpointType``` field, and hence this migration type will be handled in a separate JSON configuration file.**

Shared queries are pre-defined queries that allow teams to filter and view work items (e.g., tasks, bugs, user stories) based on specific criteria. These queries are shared across the team, making them a centralized and consistent way to track progress, identify issues, or prioritize work.

In the provided ```shared-queries.json``` file in this repository ensure that the ```SharedFolderName``` (under "Processors") aligns with your shared queries' folder name in Azure DevOps (source project).
  ![image](https://github.com/user-attachments/assets/d6baa748-cdb4-430e-a5e0-965e3f40e07e)

Shared queries migration will be handled using the provided ```shared-queries.json``` file in this repository. From your working directory run the following command:
``` bash
devopsmigration execute --config .\shared-queries.json
```
:warning: You may need to modify the ```shared-queries.json``` file to fit your specific needs - :link: [**DOCUMENTATION**](https://nkdagility.com/learn/azure-devops-migration-tools/).

### :five: Dashboards Migration
:purple_circle: Will be migrated using CodeWizard's script.

Dashboards are customizable, interactive panels that provide teams with a consolidated view of important project metrics, progress, and tools. Dashboards are associated with specific teams and can be tailored to display relevant widgets like sprint burndown charts, work item queries, team member details, and build pipeline summaries. They serve as a central hub for monitoring project health, team performance, and delivery timelines.

### :six: Assign Users To Teams
:purple_circle: Will be implemented using CodeWizard's script.

### :seven: Pipelines Migration
Before we proceed with the migration, let's first understand what pipeline is.

A Pipeline in Azure DevOps is a workflow automation tool that allows you to build, test, and deploy your code automatically.

**Types of Pipelines:**
* **Build Pipelines:** Focus on compiling code, running tests, and creating build artifacts.
  * Example: Compile a Java application and package it into a ```.jar``` file.
* **Release Pipelines:** Focus on deploying build artifacts to environments, such as staging or production.
  * Example: Deploy a Docker image to a Kubernetes cluster.
* **Multi-Stage Pipelines:** Combine both build and release processes into a single YAML-defined pipeline.
  * Example: Build, test, and deploy a web application in one cohesive workflow.

 
