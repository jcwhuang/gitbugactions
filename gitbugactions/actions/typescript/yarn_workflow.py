from typing import List, Tuple
from junitparser import TestCase
from pathlib import Path
import re

from gitbugactions.actions.typescript.package_workflow import PackageWorkflow
from gitbugactions.actions.multi.junitxmlparser import JUnitXMLParser


class YarnWorkflow(PackageWorkflow):
    BUILD_TOOL_KEYWORDS = ["yarn"]
    __COMMAND_PATTERNS = [
        r"yarn\s+(([^\s]+\s+)*)?",
    ]
    REPORT_LOCATION = "report.xml"

    def __init__(self, *args, **kwargs):
        super().__init__("yarn", *args, **kwargs)

    def _is_test_command(self, command) -> bool:
        return self.__is_command(command, ["test", "run test"])[0]

    def _is_install_command(self, command) -> bool:
        return self.__is_command(command, ["install"])[0]

    def __is_command(self, command: str, keywords: List[str]) -> Tuple[bool, str]:
        for keyword in keywords:
            for pattern in YarnWorkflow.__COMMAND_PATTERNS:
                if re.search(pattern + keyword, command):
                    return True, keyword
        return False, ""

    def get_test_results(self, repo_path) -> List[TestCase]:
        parser = JUnitXMLParser()
        return parser.get_test_results(str(Path(repo_path, "report.xml")))

    def get_install_step(self):
        return {"name": "Install yarn", "run": "npm install --global yarn"}

    def get_build_tool(self) -> str:
        return "yarn"

    def get_report_location(self) -> str:
        return self.REPORT_LOCATION
