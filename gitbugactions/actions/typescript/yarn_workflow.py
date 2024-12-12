from typing import List, Tuple
import re

from gitbugactions.actions.typescript.package_workflow import PackageWorkflow


class YarnWorkflow(PackageWorkflow):
    BUILD_TOOL_KEYWORDS = ["yarn"]
    __COMMAND_PATTERNS = [
        r"yarn\s+(([^\s]+\s+)*)?",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__("yarn", *args, **kwargs)

    def _is_test_command(self, command) -> bool:
        return self.__is_command(command, ["test", "run test"])[0]

    def __is_command(self, command: str, keywords: List[str]) -> Tuple[bool, str]:
        for keyword in keywords:
            for pattern in YarnWorkflow.__COMMAND_PATTERNS:
                if re.search(pattern + keyword, command):
                    return True, keyword
        return False, ""

    def _get_test_keyword(self, command) -> str:
        return self.__get_test_keyword(command, ["test", "run test"])[1]

    def __get_test_keyword(self, command: str, keywords: List[str]) -> Tuple[bool, str]:
        for keyword in keywords:
            for pattern in YarnWorkflow.__COMMAND_PATTERNS:
                match = re.search(pattern + rf"({keyword}[^\s]*)", command)
                if match:
                    # eg. 'yarn nx test:coverage @affine/monorepo'
                    # group(1) is nx
                    # group(2) is nx
                    # group(3) is test:coverage
                    command = match.group(3).strip()
                    return True, command
        return False, ""
