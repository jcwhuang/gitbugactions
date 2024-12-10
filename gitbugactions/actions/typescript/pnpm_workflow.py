from typing import List, Tuple
from junitparser import TestCase
import re

from gitbugactions.actions.typescript.package_workflow import PackageWorkflow
from gitbugactions.actions.multi.junitxmlparser import JUnitXMLParser


class NpmWorkflow(PackageWorkflow):
    BUILD_TOOL_KEYWORDS = ["pnpm"]
    __COMMAND_PATTERNS = [
        r"pnpm\s+(([^\s]+\s+)*)?",
    ]
    REPORT_LOCATION = "report.xml"

    def __init__(self, *args, **kwargs):
        super().__init__("pnpm", *args, **kwargs)

    def _is_test_command(self, command) -> bool:
        return self.__is_command(command, ["test", "run test"])[0]

    def __is_command(self, command: str, keywords: List[str]) -> Tuple[bool, str]:
        for keyword in keywords:
            for pattern in NpmWorkflow.__COMMAND_PATTERNS:
                if re.search(pattern + keyword, command):
                    return True, keyword
        return False, ""

    def get_test_results(self, repo_path) -> List[TestCase]:
        pass
        # parser = JUnitXMLParser()
        # return parser.get_test_results(str(Path(repo_path, "report.xml")))

    def get_build_tool(self) -> str:
        return "pnpm"

    def get_report_location(self) -> str:
        return self.REPORT_LOCATION
