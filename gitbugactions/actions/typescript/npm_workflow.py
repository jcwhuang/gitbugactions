from typing import List, Tuple
from junitparser import TestCase
from pathlib import Path
import re
import subprocess

from gitbugactions.actions.typescript.package_workflow import PackageWorkflow
from gitbugactions.actions.multi.junitxmlparser import JUnitXMLParser
from gitbugactions.logger import get_logger

logger = get_logger(__name__)


class NpmWorkflow(PackageWorkflow):
    BUILD_TOOL_KEYWORDS = ["npm"]
    __COMMAND_PATTERNS = [
        r"npm\s+(([^\s]+\s+)*)?",
    ]
    REPORT_LOCATION = "report.xml"

    def __init__(self, *args, **kwargs):
        super().__init__("npm", *args, **kwargs)

    def _is_test_command(self, command) -> bool:
        return self.__is_command(command, ["test", "run test"])[0]

    def __is_command(self, command: str, keywords: List[str]) -> Tuple[bool, str]:
        for keyword in keywords:
            for pattern in NpmWorkflow.__COMMAND_PATTERNS:
                if re.search(pattern + keyword, command):
                    return True, keyword
        return False, ""

    def get_test_results(self, repo_path) -> List[TestCase]:
        parser = JUnitXMLParser()
        logger.info(f"Looking for test results at {repo_path}")
        run = subprocess.run(f"ls {repo_path}", shell=True, capture_output=True)
        logger.info(f"Results of ls {repo_path}: {run.stdout}")
        return parser.get_test_results(str(Path(repo_path, "junit.xml")))

    def get_report_location(self) -> str:
        return self.REPORT_LOCATION
