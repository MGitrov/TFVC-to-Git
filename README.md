- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started-seedling)
  - [Code and Changesets Migration](#one-code-and-changesets-migration)

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

### :two: Work Items Migration
Start by cloning the **TFVC-based** repository to your local machine using the following commands:
