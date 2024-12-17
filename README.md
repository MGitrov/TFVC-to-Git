- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started-seedling)
  - [Code and Changesets Migration](#one-code-and-changesets-migration)
  - [Work Items Migration](#two-work-items-migration)
  - [Shared Queries Migration](#three-shared-queries-migration)

# Introduction
TFVC to Git migration guide repository.

# Prerequisites
### **:one: [git-tfs](https://github.com/git-tfs/git-tfs) (and its related prerequisites)**
  git-tfs will be used to migrate the code from a TFVC-based repository to Git while preserving the changesets (version history).
  * **Installation:** [Instructions](https://github.com/git-tfs/git-tfs?tab=readme-ov-file#get-git-tfs).

### **:two: [Azure DevOps Migration Tools](https://github.com/nkdAgility/azure-devops-migration-tools) (and its related prerequisites)**
  Azure DevOps Migration Tools will be used to migrate the work items and their related information.
  * **Installation:** [Instructions](https://nkdagility.com/learn/azure-devops-migration-tools/setup/installation/).

# Getting Started :seedling:
Once you have the prerequisites in place, follow these steps to perform the migration:
### :one: Code and Changesets Migration
**1.1.** Start by cloning the **TFVC-based** repository to your local machine using the following commands:
* Cloning a TFVC-based repository from Azure DevOps Server (on-premises):
```Add relevant guidelines later.```

* Cloning a TFVC-based repository from Azure DevOps Services (cloud environment):
  1. Navigate from within the command prompt or terminal to the directory where you want to create the local repository.
  2. Clone the TFVC repository with full history using the following command:
  ``` bash
  git tfs clone "https://{organization}.visualstudio.com/DefaultCollection" "$/Project/PathToTFVC" --branches=all --password {PAT}
  ```
  * Replace ```{organization}``` with your Azure DevOps organization name.
  * Replace ```$/Project/PathToTFVC``` with the TFVC repository path.
  * Replace ```{PAT}``` with your personal access token generated for your user in Azure DevOps. The required PAT scope for cloning is ```Code (Read)```.
 
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
  git remote add origin https://{organization}.visualstudio.com/{project}/_git/{repository}
  ```
  * Replace ```{organization}``` with your Azure DevOps organization name.
  * Replace ```{project}``` with the name of the target Git project in Azure DevOps.
  * Replace ```{repository}``` with the name of the target Git repository.

**1.4.** Push the migrated history to Azure DevOps Git Repository using the following command:
 ``` bash
  git push --all origin
  ```
  * The ```--all``` flag ensures that all local branches are pushed to the remote repository.

### :two: Work Items Migration
Before we proceed with the migration, let's first understand what work items are.

Work items are the building blocks for planning, tracking, and managing work in Azure DevOps. They help teams organize and monitor tasks, bugs, features, and requirements throughout the development lifecycle.

**Common Work Item Types:**
* **Epics:** A large piece of work that can be broken down into smaller pieces (e.g., Redesign the user experience for the website).
* **Features:** Features represent what needs to be done to achieve the goal defined by the Epic.
* **User Stories:** A small task or piece of functionality written from the perspective of the user.
* **Bugs:** A problem or error in the application that needs fixing.
* **Tasks:** A small piece of work needed to complete a User Story, Feature, or fix a Bug. Tasks are the actionable steps.

The Getting Started guide is described [here](https://nkdagility.com/learn/azure-devops-migration-tools/getstarted/).

**In the ```configuration.json``` file:**
* In Azure DevOps go to ```Organization Settings > Process > [Your Process] > Work Item Types > Epic (or another type)```.
  * Add a custom field of type ```Text (single line)```.
    ![image](https://github.com/user-attachments/assets/67e6a9d2-fdaa-4c1f-9ecf-aaa4277c251c)

  * Add the same custom field to the rest of the work items you would like to migrate **as an existing field**.
    ![image](https://github.com/user-attachments/assets/78bf3d31-6ffa-4f0d-95c5-577789b209d4)

  * Your custom field will now be available in all work item types where it has been added, and now you can adjust the ```ReflectedWorkItemIdField``` field both in ```Source``` and ```Target``` with the custom field value.
* Ensure that the ```ProcessorType``` (under "Processors") is set to ```TfsWorkItemMigrationProcessor```.
* Ensure that the ```Enabled``` field is set to ```True```.

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
* Ensure that the ```SharedFolderName``` (under "Processors") aligns with your shared queries' folder name in Azure DevOps.
  ![image](https://github.com/user-attachments/assets/d6baa748-cdb4-430e-a5e0-965e3f40e07e)
* Make sure to rename one of the configuration files if you are executing them from within the same directory.
