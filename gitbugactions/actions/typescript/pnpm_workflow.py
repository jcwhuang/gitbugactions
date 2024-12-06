from typing import List, Tuple
from junitparser import TestCase
from pathlib import Path
import re

from gitbugactions.actions.workflow import GitHubWorkflow
from gitbugactions.actions.multi.junitxmlparser import JUnitXMLParser


class NpmWorkflow(GitHubWorkflow):
    BUILD_TOOL_KEYWORDS = ["pnpm"]
    __COMMAND_PATTERNS = [
        r"pnpm\s+(([^\s]+\s+)*)?",
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
        pass

    def instrument_test_steps(self):
        pass

    def get_test_results(self, repo_path) -> List[TestCase]:
        pass
        # parser = JUnitXMLParser()
        # return parser.get_test_results(str(Path(repo_path, "report.xml")))

    def get_build_tool(self) -> str:
        return "pnpm"

    def get_report_location(self) -> str:
        return self.REPORT_LOCATION
