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

    def _is_install_command(self, command) -> bool:
        return self.__is_command(command, ["install"])[0]

    def __is_command(self, command: str, keywords: List[str]) -> Tuple[bool, str]:
        for keyword in keywords:
            for pattern in YarnWorkflow.__COMMAND_PATTERNS:
                if re.search(pattern + keyword, command):
                    return True, keyword
        return False, ""

    def get_install_step(self):
        # Note: may be able to remove this
        # return {"name": "Install yarn", "run": "npm install --global yarn"}
        return None

    def get_build_tool(self) -> str:
        return "yarn"
