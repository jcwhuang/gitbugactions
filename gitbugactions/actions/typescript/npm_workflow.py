from typing import List, Tuple
import re

from gitbugactions.actions.typescript.package_workflow import PackageWorkflow
from gitbugactions.logger import get_logger

logger = get_logger(__name__)


class NpmWorkflow(PackageWorkflow):
    BUILD_TOOL_KEYWORDS = ["npm"]
    __COMMAND_PATTERNS = [
        r"npm\s+(([^\s]+\s+)*)?",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__("npm", *args, **kwargs)

    def _is_test_command(self, command) -> bool:
        return self.__is_command(command, ["test", "run test"])[0]

    def _is_install_command(self, command):
        pass

    def get_install_step(self):
        return None

    def __is_command(self, command: str, keywords: List[str]) -> Tuple[bool, str]:
        for keyword in keywords:
            for pattern in NpmWorkflow.__COMMAND_PATTERNS:
                if re.search(pattern + keyword, command):
                    return True, keyword
        return False, ""
