from typing import List, Tuple
from junitparser import TestCase
from pathlib import Path
import re

from gitbugactions.actions.workflow import GitHubWorkflow
from gitbugactions.actions.multi.junitxmlparser import JUnitXMLParser


class CargoWorkflow(GitHubWorkflow):
    BUILD_TOOL_KEYWORDS = ["cargo"]
    # Regex patterns to match cargo test commands
    __COMMAND_PATTERNS = [
        r"cargo\s+(([^\s]+\s+)*)?",
    ]
    GITBUG_CACHE = "~/gitbug-cache"

    REPORT_LOCATION = "results.xml"

    def _is_test_command(self, command) -> bool:
        return self.__is_command(command, ["test"])[0]

    def __is_command(self, command: str, keywords: list[str]) -> Tuple[bool, str]:
        # Checks if the given command matches any of the command patterns
        for keyword in keywords:
            for pattern in CargoWorkflow.__COMMAND_PATTERNS:
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

                    # Job with tests
                    # Install cargo2junit to generate JUnit XML reports
                    job["steps"].insert(
                        0,
                        {
                            "name": "Install cargo2junit",
                            "run": "cargo install cargo2junit",
                        },
                    )
                    # Cache dependencies to speed up builds
                    job["steps"].append(
                        {
                            "name": "Cache dependencies",
                            "run": f"mkdir -p {CargoWorkflow.GITBUG_CACHE} && "
                            + f"cp Cargo.lock {CargoWorkflow.GITBUG_CACHE} || : && "
                            + f"cp Cargo.toml {CargoWorkflow.GITBUG_CACHE} || :",
                        }
                    )
                    return

    def instrument_offline_execution(self):
        if self.has_tests():
            for _, job in self.doc["jobs"].items():
                if "steps" in job:
                    for step in job["steps"]:
                        # Remove actions added in online execution
                        if "name" in step and step["name"] in [
                            "Install cargo2junit",
                            "Cache dependencies",
                        ]:
                            job["steps"].remove(step)

                        if "run" not in step:
                            continue

                        is_mod_command, keyword = self.__is_command(
                            step["run"], ["build", "run", "test"]
                        )
                        if is_mod_command:
                            step["run"] = f"{step['run']} --locked"

                    job["steps"].insert(
                        0,
                        {
                            "name": "Restore dependencies",
                            "run": f"cp {CargoWorkflow.GITBUG_CACHE}/Cargo.lock . || : && "
                            + f"cp {CargoWorkflow.GITBUG_CACHE}/Cargo.toml . || :",
                        },
                    )

    def instrument_test_steps(self):
        if "jobs" in self.doc:
            for _, job in self.doc["jobs"].items():
                if "steps" in job:
                    for step in job["steps"]:
                        if "run" in step and self._is_test_command(step["run"]):
                            step["run"] = step["run"].strip()

                            # Add cargo2junit for JUnit XML output
                            if "cargo test" in step["run"] and "| cargo2junit" not in step["run"]:
                                step["run"] = step["run"] + " | cargo2junit > results.xml"

    def get_test_results(self, repo_path) -> List[TestCase]:
        parser = JUnitXMLParser()
        return parser.get_test_results(str(Path(repo_path, "results.xml")))

    def get_build_tool(self) -> str:
        return "cargo"

    def get_report_location(self) -> str:
        return self.REPORT_LOCATION
