from abc import ABC, abstractmethod
from dataclasses import dataclass

import tempfile
import os, traceback
import json
import uuid
import datetime
from gitbugactions.util import delete_repo_clone, clone_repo, checkout_commit
from gitbugactions.actions.actions import (
    GitHubActions,
    ActCacheDirManager,
    ActCheckCodeFailureStrategy,
)
from gitbugactions.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MinimalRepository:
    full_name: str
    clone_url: str
    stargazers_count: int
    language: str
    size: str
    pull_number: int


@dataclass
class PullRequest:
    repo: MinimalRepository
    pull_number: int
    base_commit: str


class PullRequestStrategy(ABC):
    def __init__(self, data_path: str):
        self.data_path = data_path

    @abstractmethod
    def handle_pr(self, pr: PullRequest):
        pass


class HandlePullRequestsStrategy(PullRequestStrategy):
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.uuid = str(uuid.uuid1())

    def save_data(self, data: dict, repo):
        """
        Saves the data json to a file with the name of the repository
        """
        repo_name = repo.full_name.replace("/", "__")
        data_path = os.path.join(self.data_path, f"{repo_name}-{repo.pull_number}.json")
        with open(data_path, "w") as f:
            json.dump(data, f, indent=4)

    def handle_pr(self, pr: PullRequest):
        logger.info(f"Cloning {pr.repo.full_name} - {pr.repo.clone_url}")
        repo_path = os.path.join(
            tempfile.gettempdir(), self.uuid, pr.repo.full_name.replace("/", "-")
        )

        data = {
            "repository": pr.repo.full_name,
            "stars": pr.repo.stargazers_count,
            "language": pr.repo.language.strip().lower(),
            "size": pr.repo.size,
            "clone_url": pr.repo.clone_url,
            "pull_number": pr.pull_number,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
            "clone_success": False,
            "number_of_actions": 0,
            "number_of_test_actions": 0,
            "actions_successful": {},
            "actions_run": {},
        }

        repo_clone = clone_repo(pr.repo.clone_url, repo_path)
        logger.info(f"Checkout out at commit: {pr.base_commit}")
        checkout_commit(repo_clone, pr.base_commit)

        try:
            data["clone_success"] = True

            actions = GitHubActions(repo_path, pr.repo.language)
            data["number_of_actions"] = len(actions.workflows)
            data["actions_build_tools"] = [
                x.get_build_tool() for x in actions.workflows
            ]
            data["number_of_test_actions"] = len(actions.test_workflows)
            data["actions_test_build_tools"] = [
                x.get_build_tool() for x in actions.test_workflows
            ]
            actions.save_workflows()
            num_test_workflows = len(actions.test_workflows)
            if num_test_workflows > 0:
                logger.info(f"Running {num_test_workflows} actions for {pr.full_name}")
                for i, test_workflow in enumerate(actions.test_workflows):
                    logger.info(f"Running test workflow {i}: {test_workflow.path}")
                    # Act creates names for the containers by hashing the content of the workflows
                    # To avoid conflicts between threads, we randomize the name
                    actions.test_workflows[i].doc["name"] = str(uuid.uuid4())
                    actions.save_workflows()

                    act_cache_dir = ActCacheDirManager.acquire_act_cache_dir()
                    try:
                        act_run = actions.run_workflow(
                            actions.test_workflows[i],
                            act_cache_dir=act_cache_dir,
                            act_fail_strategy=ActCheckCodeFailureStrategy(),
                        )
                    finally:
                        ActCacheDirManager.return_act_cache_dir(act_cache_dir)

                    data["actions_successful"][test_workflow.path] = not act_run.failed
                    data["actions_run"][test_workflow.path] = act_run.asdict()
            else:
                logger.info("No test workflows")
            delete_repo_clone(repo_clone)
            self.save_data(data, pr)

        except Exception as e:
            logger.error(
                f"Error while processing {pr.repo.full_name}: {traceback.format_exc()}"
            )

            delete_repo_clone(repo_clone)
            self.save_data(data, pr)
