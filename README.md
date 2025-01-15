- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started-seedling)
  - [Processes Migration](#one-processes-migration)
  - [Work Items (Boards, Backlogs, and Sprints), Iterations and Areas, and Teams Migration](#two-work-items-boards-backlogs-and-sprints-iterations-and-areas-and-teams-migration)
  - [Branches and Changesets Migration](#three-branches-and-changesets-migration)
  - [Work Items Migration](#two-work-items-migration)
  - [Shared Queries Migration](#three-shared-queries-migration)


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

The Azure DevOps Migration Tools have to use an HTTPS connection to the Azure DevOps Server. Usually, the Azure DevOps Server use the HTTP protocol which is not compatible with the requirement.

Hence, to use an HTTPS connection to your Azure DevOps Server, you can either install an SSL/TLS certificate, or use a reverse proxy.

![image](https://github.com/user-attachments/assets/dc86ffe0-237f-4ad6-858f-6ee22c035fe4)

We can use Caddy as a reverse proxy to switch the Azure DevOps Server from HTTP to HTTPS. Caddy automatically provisions SSL/TLS certificates for the provided domain using Let’s Encrypt.

:link: [**CONFIGURE REVERSE PROXY USING CADDY**](https://caddyserver.com/docs/quick-starts/reverse-proxy)

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
:warning: You may need to modify the ```work-items.json``` file to fit your specific needs - [**DOCUMENTATION**](https://nkdagility.com/learn/azure-devops-migration-tools/).

### :three: Branches and Changesets Migration
**1.1.** Start by cloning the **TFVC-based** repository to your local machine using the following commands:
* Cloning a TFVC-based repository from Azure DevOps Server (on-premises):
  1. Navigate from within the command prompt or terminal to the directory where you want to create the local repository.
  2. Clone the TFVC repository with full history using the following command:
  ``` bash
  git tfs clone --branches=all https://tfs-server:8080/tfs/Collection $/Project/Main .
  ```
  * Replace ```https://tfs-server:8080/tfs/Collection``` with your Azure DevOps' Server collection URL.
  * Replace ```$/Project/Main``` with a path to one of your repository's branch. Basically, it will alow ```git-tfs``` to detect related branches, and make every branch in the TFVC repository a branch in the Git repository.
  
  3. (Optional) Verify that the cloning went well using the ```git tfs verify --all``` command.

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
  git remote add origin https://{organization}@dev.azure.com/{organization}/{project}/_git/{repository}
  ```
  * Replace ```{organization}``` with your Azure DevOps organization name.
  * Replace ```{project}``` with the name of the target Git project in Azure DevOps.
  * Replace ```{repository}``` with the name of the target Git repository.
  * The URL also can be taken from the project's web portal in Azure DevOps.

**1.4.** Push the migrated history to Azure DevOps Git Repository using the following command:
 ``` bash
  git push --all origin
  ```
  * The ```--all``` flag ensures that all local branches are pushed to the remote repository.
  * In this sub-step, ensure you are able to authenticate via the CLI in order to ```push``` to the remote repository.

### :three: Shared Queries Migration
:warning: **Migration only available for shared queries.**

:warning: **Shared queries migration requires adjusting the ```EndpointType``` field, and hence this migration type will be handled in a separate ```configuration.json``` file.**

Before we proceed with the migration, let's first understand what shared queries are.

Shared queries are pre-defined queries that allow teams to filter and view work items (e.g., tasks, bugs, user stories) based on specific criteria. These queries are shared across the team, making them a centralized and consistent way to track progress, identify issues, or prioritize work.

**In the ```configuration.json``` file:**
 ``` json
{
  "Serilog": {
    "MinimumLevel": "Information"
  },
  "MigrationTools": {
    "Version": "16.0",
    "Endpoints": {
      "Source": {
        "EndpointType": "TfsEndpoint",
        "Collection": "https://dev.azure.com/nkdagility-preview/",
        "Project": "migrationSource1",
        "Authentication": {
          "AuthenticationMode": "AccessToken",
          "AccessToken": "jkashdjksahsjkfghsjkdaghvisdhuisvhladvnb"
        }
      },
      "Target": {
        "EndpointType": "TfsEndpoint",
        "Collection": "https://dev.azure.com/nkdagility-preview/",
        "Project": "migrationTest5",

        "Authentication": {
          "AuthenticationMode": "AccessToken",
          "AccessToken": "lkasjioryislaniuhfhklasnhfklahlvlsdvnls"
        },
        "ReflectedWorkItemIdField": "Custom.ReflectedWorkItemId"
      }
    },
    "CommonTools": {},
    "Processors": [
      {
        "ProcessorType": "TfsSharedQueryProcessorOptions",
        "Enabled": true,
        "PrefixProjectToNodes": false,
        "SharedFolderName": "Shared Queries",
        "SourceToTargetFieldMappings": null,
        "SourceName": "Source",
        "TargetName": "Target"
      }
    ]
  }
}
  ```
* Replace ```Collection``` (both in ```Source``` and ```Target```) with your Azure DevOps organization name.
* Replace ```Project``` (both in ```Source``` and ```Target```) with the respective project names.
* Replace ```AccessToken``` (both in ```Source``` and ```Target```) with the PAT you have generated for your user.
  * You may also set the ```AuthenticationMode``` (both in ```Source``` and ```Target```) field to ```Prompt``` (both in ```Source``` and ```Target```).
* Ensure that the ```SharedFolderName``` (under "Processors") aligns with your shared queries' folder name in Azure DevOps (source proj).
  ![image](https://github.com/user-attachments/assets/d6baa748-cdb4-430e-a5e0-965e3f40e07e)
* Make sure to rename one of the configuration files if you are executing them from within the same directory.

### :five: Pipelines Migration
Before we proceed with the migration, let's first understand what pipeline is.

A Pipeline in Azure DevOps is a workflow automation tool that allows you to build, test, and deploy your code automatically.

**Types of Pipelines:**
* **Build Pipelines:** Focus on compiling code, running tests, and creating build artifacts.
  * Example: Compile a Java application and package it into a ```.jar``` file.
* **Release Pipelines:** Focus on deploying build artifacts to environments, such as staging or production.
  * Example: Deploy a Docker image to a Kubernetes cluster.
* **Multi-Stage Pipelines:** Combine both build and release processes into a single YAML-defined pipeline.
  * Example: Build, test, and deploy a web application in one cohesive workflow.

 
