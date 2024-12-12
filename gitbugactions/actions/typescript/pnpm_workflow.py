from typing import List, Tuple
import re

from gitbugactions.actions.typescript.package_workflow import PackageWorkflow


class NpmWorkflow(PackageWorkflow):
    BUILD_TOOL_KEYWORDS = ["pnpm"]
    __COMMAND_PATTERNS = [
        r"pnpm\s+(([^\s]+\s+)*)?",
    ]

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

    def get_build_tool(self) -> str:
        return "pnpm"
