from typing import List, Tuple
from junitparser import TestCase
from pathlib import Path
import re

from code_data_utils.gitbugactions.actions.workflow import GitHubWorkflow
from code_data_utils.gitbugactions.actions.multi.junitxmlparser import JUnitXMLParser


class NpmWorkflow(GitHubWorkflow):
    BUILD_TOOL_KEYWORDS = ["npm"]
    __COMMAND_PATTERNS = [
        r"npm\s+(([^\s]+\s+)*)?",
    ]
    REPORT_LOCATION = "report.xml"

    def _is_test_command(self, command) -> bool:
        return self.__is_command(command, ["test"])[0]

    def __is_command(self, command: str, keywords: List[str]) -> Tuple[bool, str]:
        for keyword in keywords:
            for pattern in NpmWorkflow.__COMMAND_PATTERNS:
                if re.search(pattern + keyword, command):
                    return True, keyword
        return False, ""

    def instrument_online_execution(self):
        if self.has_tests():
            for _, job in self.doc["jobs"].items():
                if "steps" in job:
                    for step in job["steps"]:
                        if "run" in step and self._is_test_command(step["run"]):
                            break
                    else:
                        continue

                    job["steps"].insert(
                        0,
                        {
                            "name": "gitbug-actions install mocha-junit-reporter",
                            "run": "npm install mocha-junit-reporter --save-dev",
                        },
                    )
                    return

    def instrument_test_steps(self):
        if "jobs" in self.doc:
            for _, job in self.doc["jobs"].items():
                if "steps" in job:
                    for step in job["steps"]:
                        if "run" in step and self._is_test_command(step["run"]):
                            step["run"] = step["run"].strip()

                            if "--reporter mocha-junit-reporter" not in step["run"]:
                                step["run"] += " --reporter mocha-junit-reporter"

                            if "--reporter-options" not in step["run"]:
                                step["run"] += " --reporter-options mochaFile=report.xml"

    def get_test_results(self, repo_path) -> List[TestCase]:
        parser = JUnitXMLParser()
        return parser.get_test_results(str(Path(repo_path, "report.xml")))

    def get_build_tool(self) -> str:
        return "npm"

    def get_report_location(self) -> str:
        return self.REPORT_LOCATION
