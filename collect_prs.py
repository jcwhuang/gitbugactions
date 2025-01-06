from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import re
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
from gitbugactions.actions.multi.unknown_workflow import UnknownWorkflow
from gitbugactions.logger import get_logger

logger = get_logger(__name__)
CURRENT_VERSION = 1


@dataclass
class WorkflowInfo:
    test_workflow_paths: list[str]
    actions_test_build_tools: list[str]
    num_test_workflows: int
    num_workflows: int
    num_unknown_workflows: int
    head_language: str
    base_language: str
    language: str
    commit_sha: str
    repo: str
    report_locations: list[str]
    workflow_contents: list[str]
    instance_id: str
    version: int = CURRENT_VERSION

    def to_json(self) -> str:
        dict_copy = self.__dict__.copy()
        return dict_copy


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
    def __init__(self, data_path: str, base_image: str):
        self.data_path = data_path
        self.base_image = base_image
        self.runner_image = f"gitbugactions:{re.sub(':', '-', self.base_image)}"
        self.uuid = str(uuid.uuid1())

    def make_instance_id(self, repo: MinimalRepository):
        repo_name = repo.full_name.replace("/", "__")
        return {repo_name} - {repo.pull_number}

    def save_workflow_info(self, data: dict):
        data_path = os.path.join(self.data_path, "workflow_info.json")
        with open(data_path, "w") as f:
            json.dump(data, f)

    def save_data(self, data: dict, repo: MinimalRepository):
        """
        Saves the data json to a file with the name of the repository
        """
        instance_id = self.make_instance_id(repo)
        data_path = os.path.join(self.data_path, f"{instance_id}.json")
        with open(data_path, "w") as f:
            json.dump(data, f)

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
            "base_commit": pr.base_commit,
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

            actions = GitHubActions(
                repo_path,
                pr.repo.language,
                runner_image=self.runner_image,
                base_image=self.base_image,
            )
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
                logger.info(
                    f"Running {num_test_workflows} actions for {pr.repo.full_name}"
                )
                for i, test_workflow in enumerate(actions.test_workflows):
                    relative_workflow_path = str(
                        Path(test_workflow.path).relative_to(repo_path)
                    )
                    logger.info(f"Running test workflow {i}: {relative_workflow_path}")
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

                    data["actions_successful"][
                        relative_workflow_path
                    ] = not act_run.failed
                    data["actions_run"][relative_workflow_path] = act_run.asdict()
            else:
                logger.info("No test workflows")

            workflow_info = self.make_workflow_info(actions, repo_path, pr, data)
            delete_repo_clone(repo_clone)
            self.save_data(data, pr.repo)
            self.save_workflow_info(workflow_info)

        except Exception as e:
            logger.error(
                f"Error while processing {pr.repo.full_name}: {traceback.format_exc()}"
            )

            delete_repo_clone(repo_clone)
            self.save_data(data, pr.repo)

    def make_workflow_info(
        self, actions: GitHubActions, repo_path: str, pr: PullRequest, data: dict
    ):
        num_unknown_workflows = sum(
            [1 for w in actions.workflows if isinstance(w, UnknownWorkflow)]
        )
        test_workflow_paths = [
            Path(workflow.path) for workflow in actions.test_workflows
        ]
        relative_test_workflow_paths = [
            workflow_path.relative_to(repo_path)
            for workflow_path in test_workflow_paths
        ]
        report_locations = [
            workflow.get_report_location() for workflow in actions.test_workflows
        ]
        workflow_contents = [workflow.doc for workflow in actions.test_workflows]
        actions_test_build_tools = [
            workflow.get_build_tool() for workflow in actions.test_workflows
        ]
        workflow_info = WorkflowInfo(
            test_workflow_paths=list(map(str, relative_test_workflow_paths)),
            num_test_workflows=len(actions.test_workflows),
            num_workflows=len(actions.workflows),
            num_unknown_workflows=num_unknown_workflows,
            head_language=data["language"],
            base_language=data["language"],
            language=data["language"],
            commit_sha=data["base_commit"],
            repo=pr.repo.full_name,
            report_locations=report_locations,
            workflow_contents=workflow_contents,
            instance_id=self.make_instance_id(pr.repo.full_name),
            actions_test_build_tools=actions_test_build_tools,
        )
        return workflow_info
