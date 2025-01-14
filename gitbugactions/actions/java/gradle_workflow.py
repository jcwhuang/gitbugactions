from typing import List
from junitparser import TestCase
from pathlib import Path
import re
import subprocess

from gitbugactions.actions.workflow import GitHubWorkflow
from gitbugactions.actions.multi.junitxmlparser import JUnitXMLParser
from gitbugactions.logger import get_logger

logger = get_logger(__name__)


class GradleWorkflow(GitHubWorkflow):
    BUILD_TOOL_KEYWORDS = ["gradle", "./gradlew"]
    # Regex patterns to match gradle commands
    __TESTS_COMMAND_PATTERNS = [
        r"(gradle|gradlew)\s+(([^\s]+\s+)*)?(test|check|build|buildDependents|buildNeeded)",
    ]
    REPORT_LOCATION = "build/test-results/test"

    def _is_test_command(self, command) -> bool:
        # Checks if the given command matches any of the tests command patterns
        for pattern in GradleWorkflow.__TESTS_COMMAND_PATTERNS:
            if re.search(pattern, command):
                return True
        return False

    def instrument_test_steps(self):
        if "jobs" in self.doc:
            for _, job in self.doc["jobs"].items():
                if "steps" in job:
                    for step in job["steps"]:
                        if "run" in step and self._is_test_command(step["run"]):
                            step["run"] = step["run"].strip()
                            if "-x test" in step["run"]:
                                step["run"] = step["run"].replace("-x test", "").strip()

    def instrument_offline_execution(self):
        # Add an "--offline" option to the test command
        if "jobs" in self.doc:
            for _, job in self.doc["jobs"].items():
                if "steps" in job:
                    for step in job["steps"]:
                        if "run" in step and self._is_test_command(step["run"]):
                            step["run"] += " --offline"

    def get_test_results(self, repo_path) -> List[TestCase]:
        parser = JUnitXMLParser()
        test_path = str(Path(repo_path, "build", "test-results", "test"))
        logger.info(f"Looking for test results at repo_path: {repo_path}")
        run = subprocess.run(f"ls {repo_path}", shell=True, capture_output=True)
        logger.info(f"Results of ls {repo_path}: {run.stdout}")
        logger.info(f"Looking for test results at test_path: {test_path}")
        run = subprocess.run(f"ls {test_path}", shell=True, capture_output=True)
        logger.info(f"Results of ls {test_path}: {run.stdout}")
        return parser.get_test_results(test_path)

    def get_build_tool(self) -> str:
        return "gradle"

    def get_report_location(self) -> str:
        return self.REPORT_LOCATION
