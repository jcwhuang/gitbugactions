import copy
import re
import os
import yaml
from gitbugactions.actions.workflow import GitHubWorkflow
from gitbugactions.actions.multi.unknown_workflow import UnknownWorkflow
from gitbugactions.actions.java.maven_workflow import MavenWorkflow
from gitbugactions.actions.java.gradle_workflow import GradleWorkflow
from gitbugactions.actions.python.pytest_workflow import PytestWorkflow
from gitbugactions.actions.python.unittest_workflow import UnittestWorkflow
from gitbugactions.actions.go.go_workflow import GoWorkflow
from gitbugactions.actions.rust.cargo_workflow import CargoWorkflow
from gitbugactions.actions.typescript.npm_workflow import NpmWorkflow
from gitbugactions.actions.typescript.yarn_workflow import YarnWorkflow


class GitHubWorkflowFactory:
    """
    Factory class for creating workflow objects.
    """

    @staticmethod
    def _identify_build_tool(path: str, content: str = ""):
        """
        Identifies the build tool used by the workflow.
        """
        # Build tool keywords
        try:
            build_tool_keywords = {
                "maven": MavenWorkflow.BUILD_TOOL_KEYWORDS,
                "gradle": GradleWorkflow.BUILD_TOOL_KEYWORDS,
                "pytest": PytestWorkflow.BUILD_TOOL_KEYWORDS,
                "unittest": UnittestWorkflow.BUILD_TOOL_KEYWORDS,
                "go": GoWorkflow.BUILD_TOOL_KEYWORDS,
                "npm": NpmWorkflow.BUILD_TOOL_KEYWORDS,
                "yarn": YarnWorkflow.BUILD_TOOL_KEYWORDS,
                "cargo": CargoWorkflow.BUILD_TOOL_KEYWORDS,
            }
            aggregate_keywords = {kw for _ in build_tool_keywords.values() for kw in _}
            keyword_counts = {keyword: 0 for keyword in aggregate_keywords}
            aggregate_keyword_counts = {
                build_tool: 0 for build_tool in build_tool_keywords
            }

            def _update_keyword_counts(keyword_counts, phrase):
                if isinstance(phrase, str):
                    for name in phrase.strip().lower().split(" "):
                        for keyword in aggregate_keywords:
                            if keyword == name:
                                keyword_counts[keyword] += 1

            # Load the workflow
            doc = None
            if content == "":
                with open(path, "r") as stream:
                    doc = yaml.safe_load(stream)
            else:
                doc = yaml.safe_load(content)

            if doc is None:
                return None

            if True in doc:
                doc["on"] = doc[True]
                doc.pop(True)

            # Iterate over the workflow to find build tool names in the run commands
            if "jobs" in doc and isinstance(doc["jobs"], dict):
                for _, job in doc["jobs"].items():
                    if "steps" in job:
                        for step in job["steps"]:
                            if "run" in step:
                                _update_keyword_counts(keyword_counts, step["run"])

            # Aggregate keyword counts per build tool
            for build_tool in build_tool_keywords:
                for keyword in build_tool_keywords[build_tool]:
                    aggregate_keyword_counts[build_tool] += keyword_counts[keyword]

            # Return the build tool with the highest count
            max_build_tool = max(
                aggregate_keyword_counts, key=aggregate_keyword_counts.get
            )
            return (
                max_build_tool if aggregate_keyword_counts[max_build_tool] > 0 else None
            )
        except yaml.YAMLError:
            return None

    @staticmethod
    def create_workflow(
        path: str, language: str, repo_path: str, content: str = ""
    ) -> GitHubWorkflow:
        """
        Creates a workflow object according to the language and build system.
        """
        build_tool = GitHubWorkflowFactory._identify_build_tool(path, content=content)

        match (language, build_tool):
            case ("java", "maven"):
                return MavenWorkflow(path, repo_path=repo_path, workflow=content)
            case ("java", "gradle"):
                return GradleWorkflow(path, repo_path=repo_path, workflow=content)
            case ("python", "pytest"):
                return PytestWorkflow(path, repo_path=repo_path, workflow=content)
            case ("python", "unittest"):
                return UnittestWorkflow(path, repo_path=repo_path, workflow=content)
            case ("go", "go"):
                return GoWorkflow(path, repo_path=repo_path, workflow=content)
            case ("rust", "cargo"):
                return CargoWorkflow(path, repo_path=repo_path, workflow=content)
            case ("typescript", "npm"):
                return NpmWorkflow(path, repo_path=repo_path, workflow=content)
            case ("typescript", "yarn"):
                return YarnWorkflow(path, repo_path=repo_path, workflow=content)
            case (_, _):
                return UnknownWorkflow(path, repo_path=repo_path, workflow=content)

    @staticmethod
    def split_workflow_by_jobs(workflow: GitHubWorkflow) -> list[GitHubWorkflow]:

        new_workflows: list[GitHubWorkflow] = []
        if workflow.has_tests() and "jobs" in workflow.doc:
            for job_key, job in workflow.doc["jobs"].items():
                new_workflow = copy.deepcopy(workflow)
                new_workflow.doc["jobs"] = {job_key: job}
                # Update path with job key
                filename = os.path.basename(new_workflow.path)
                dirpath = os.path.dirname(new_workflow.path)
                new_filename = (
                    filename.split(".")[0]
                    + f"-{re.sub(' ', '', job_key)}."
                    + filename.split(".")[1]
                )
                new_path = os.path.join(dirpath, new_filename)
                new_workflow.path = new_path
                new_workflows.append(new_workflow)
        return new_workflows
