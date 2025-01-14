from typing import List
from junitparser import TestCase
from pathlib import Path
import re
import subprocess

from gitbugactions.actions.workflow import GitHubWorkflow
from gitbugactions.actions.multi.junitxmlparser import JUnitXMLParser
from gitbugactions.logger import get_logger

logger = get_logger(__name__)


class MavenWorkflow(GitHubWorkflow):
    BUILD_TOOL_KEYWORDS = ["maven", "mvn", "mavenw", "mvnw"]
    # Regex patterns to match maven test commands
    __TESTS_COMMAND_PATTERNS = [
        r"(maven|mvn|mavenw|mvnw)\s+(([^\s]+\s+)*)?(test|package|verify|install)",
    ]
    REPORT_LOCATION = "target/surefire-reports"

    def _is_test_command(self, command) -> bool:
        # Checks if the given command matches any of the tests command patterns
        for pattern in MavenWorkflow.__TESTS_COMMAND_PATTERNS:
            if re.search(pattern, command):
                return True
        return False

    def instrument_test_steps(self):
        pass

    def instrument_offline_execution(self):
        # Add an "--offline" option to the test command
        if "jobs" in self.doc:
            for _, job in self.doc["jobs"].items():
                if "steps" in job:
                    for step in job["steps"]:
                        if "run" in step and self._is_test_command(step["run"]):
                            step["run"] += " -offline"

    def get_test_results(self, repo_path) -> List[TestCase]:
        parser = JUnitXMLParser()
        test_path = str(Path(repo_path, "target", "surefire-reports"))
        logger.info(f"Looking for test results at repo_path: {repo_path}")
        run = subprocess.run(f"ls {repo_path}", shell=True, capture_output=True)
        logger.info(f"Results of ls {repo_path}: {run.stdout}")
        logger.info(f"Looking for test results at test_path: {test_path}")
        run = subprocess.run(f"ls {test_path}", shell=True, capture_output=True)
        logger.info(f"Results of ls {test_path}: {run.stdout}")
        return parser.get_test_results(test_path)

    def get_build_tool(self) -> str:
        return "maven"

    def get_report_location(self) -> str:
        return self.REPORT_LOCATION
