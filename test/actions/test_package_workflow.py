from pathlib import Path
import json
import os
import pytest
import shutil
import tempfile
from gitbugactions.actions.workflow_factory import GitHubWorkflowFactory
from gitbugactions.actions.typescript.package_workflow import PackageWorkflow


def create_workflow(yml_file, language, repo_path):
    """Create a workflow object."""
    return GitHubWorkflowFactory.create_workflow(yml_file, language, repo_path)


@pytest.mark.parametrize(
    "repo_path, yml_file, build_tool, test_command",
    [
        (
            "test/resources/test_workflows/typescript/deltachat__deltachat-desktop-3905",
            "test.yml",
            "npm",
            "mocha",
        ),
        (
            "test/resources/test_workflows/typescript/toeverything__AFFiNE-4043",
            "build.yml",
            "yarn",
            "vitest",
        ),
    ],
)
def test_build_tool_and_test_command(
    repo_path: str, yml_file: str, build_tool: str, test_command: str
):
    """Test that the correct build tool and test command are identified."""
    # Copy workflow file and package.json to a new directory because
    # package.json gets modified in place
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"basename: {os.path.basename(repo_path)}")
        destination_dir = os.path.join(temp_dir, os.path.basename(repo_path))
        shutil.copytree(repo_path, destination_dir)
        workflow = create_workflow(
            os.path.join(destination_dir, yml_file), "typescript", destination_dir
        )
        assert isinstance(workflow, PackageWorkflow)
        assert workflow.get_build_tool() == f"{build_tool}, "
        workflow.instrument_test_steps()
        assert workflow.get_build_tool() == f"{build_tool}, {test_command}"


@pytest.mark.parametrize(
    "repo_path, yml_file, test_name, updated_test_command",
    [
        (
            "test/resources/test_workflows/typescript/deltachat__deltachat-desktop-3905",
            "test.yml",
            "test-unit",
            "mocha 'test/mocha/**/*.js' --reporter mocha-junit-reporter --reporter-options mochaFile=junit.xml",
        ),
        (
            "test/resources/test_workflows/typescript/toeverything__AFFiNE-4043",
            "build.yml",
            "test:coverage",
            "vitest run --coverage --reporter=default --reporter=junit --outputFile.junit=junit.xml",
        ),
    ],
)
def test_package_json_is_modified(
    repo_path: str, yml_file: str, test_name: str, updated_test_command: str
):
    """Test that the correct build tool and test command are identified."""
    # Copy workflow file and package.json to a new directory because
    # package.json gets modified in place
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"basename: {os.path.basename(repo_path)}")
        destination_dir = os.path.join(temp_dir, os.path.basename(repo_path))
        shutil.copytree(repo_path, destination_dir)
        workflow = create_workflow(
            os.path.join(destination_dir, yml_file), "typescript", destination_dir
        )
        assert isinstance(workflow, PackageWorkflow)
        workflow.instrument_test_steps()
        with open(Path(destination_dir) / "package.json") as f:
            modified_package_json = json.load(f)
        assert modified_package_json["scripts"][test_name] == updated_test_command
