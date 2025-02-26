from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
import os
from azure.devops.v7_1.git.models import GitVersionDescriptor


def main():
    personal_access_token = os.getenv("PAT")
    project = os.getenv("PROJECT")
    organization_url = os.getenv("ORGANIZATION_URL")
    update = False
    # Create a connection to the org
    credentials = BasicAuthentication("", personal_access_token)
    connection = Connection(base_url=organization_url, creds=credentials)
    git_client = connection.clients.get_git_client()

    for repo in git_client.get_repositories(project=project):
        if update == False:
            print(repo.name)
            continue
        try:
            response = git_client.get_item(
                project=project,
                repository_id=repo.id,
                path="pom.xml",
                include_content=True,
                version_descriptor=GitVersionDescriptor(
                    version_type="branch", version="pom-patrol"
                ),
            )
        except Exception as e:
            print(e)
            response = git_client.get_item(
                project=project,
                repository_id=repo.id,
                path="pom.xml",
                include_content=True,
                version_descriptor=GitVersionDescriptor(
                    version_type="branch",
                    version=str(repo.default_branch).replace("refs/heads/", ""),
                ),
            )

        with open("pom.xml", "w") as f:
            f.write(response.content)
        os.system(
            "mvn versions:use-latest-versions \
                -DallowMajorUpdates=false \
                -DallowMinorUpdates=true \
                -DallowIncrementalUpdates=true \
                -DexcludesSnapshots=true"
        )
        updated_pom = ""
        with open("pom.xml", "r") as f:
            updated_pom = f.read()
        try:
            git_client.create_push(
                push={
                    "refUpdates": [
                        {
                            "name": "refs/heads/pom-patrol",
                            "oldObjectId": response.commit_id,
                        }
                    ],
                    "commits": [
                        {
                            "comment": "Pom Patrol - Update dependencies",
                            "changes": [
                                {
                                    "changeType": "edit",
                                    "item": {"path": "pom.xml"},
                                    "newContent": {
                                        "content": updated_pom,
                                        "contentType": "rawtext",
                                    },
                                }
                            ],
                        }
                    ],
                },
                repository_id=repo.id,
                project=project,
            )
        except Exception as e:
            print(e)
            continue

        try:
            git_client.create_pull_request(
                git_pull_request_to_create={
                    "sourceRefName": "refs/heads/pom-patrol",
                    "targetRefName": repo.default_branch,
                    "title": "Pom Patrol - Update dependencies",
                    "description": "This PR was created by Pom Patrol",
                },
                project=project,
                repository_id=repo.id,
            )
        except Exception as e:
            print(e)


if __name__ == "__main__":
    main()
