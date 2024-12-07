from typing import List, Tuple
from junitparser import TestCase
from pathlib import Path
import json
import re
import subprocess

from gitbugactions.actions.workflow import GitHubWorkflow
from gitbugactions.actions.multi.junitxmlparser import JUnitXMLParser
from gitbugactions.logger import get_logger

logger = get_logger(__name__)


class NpmWorkflow(GitHubWorkflow):
    BUILD_TOOL_KEYWORDS = ["npm"]
    __COMMAND_PATTERNS = [
        r"npm\s+(([^\s]+\s+)*)?",
    ]
    REPORT_LOCATION = "report.xml"

    def _is_test_command(self, command) -> bool:
        return self.__is_command(command, ["test", "run test"])[0]

    def __is_command(self, command: str, keywords: List[str]) -> Tuple[bool, str]:
        for keyword in keywords:
            for pattern in NpmWorkflow.__COMMAND_PATTERNS:
                if re.search(pattern + keyword, command):
                    return True, keyword
        return False, ""

    def instrument_online_execution(self):
        if self.has_tests():
            package_json_path = Path(self.repo_path) / "package.json"
            if package_json_path.exists():
                with open(package_json_path, "r") as f:
                    package_json = json.load(f)
            else:
                logger.warning("Couldn't find package.json")
                return

            # Get the test command from package.json
            test_cmd = package_json.get("scripts", {}).get("test", "")

            for _, job in self.doc["jobs"].items():
                if "steps" in job:
                    for i, step in enumerate(job["steps"]):
                        if "run" in step and self._is_test_command(step["run"]):
                            break
                    else:
                        continue

                    # Job with tests
                    # Insert steps to install dependencies for generating JUnit XML output
                    if "jest" in test_cmd:
                        logger.info(
                            "Jest detected, adding jest-junit installation step..."
                        )
                        job["steps"].insert(
                            i,
                            {
                                "name": "gitbug-actions Install jest-junit",
                                "run": "npm add jest-junit",
                            },
                        )
                    elif "mocha" in test_cmd:
                        logger.info(
                            "Mocha detected, adding mocha-junit-reporter installation step..."
                        )
                        job["steps"].insert(
                            i,
                            {
                                "name": "gitbug-actions Install mocha-junit-reporter",
                                "run": "npm add mocha-junit-reporter",
                            },
                        )
                    elif "vite" in test_cmd or "vitest" in test_cmd:
                        logger.info(
                            "Vitest detected, adding vite-plugin-junit-reporter installation step..."
                        )
                        logger.info["steps"].insert(
                            i,
                            {
                                "name": "gitbug-actions Install vite-plugin-junit-reporter",
                                "run": "npm add vite-plugin-junit-reporter",
                            },
                        )
                    else:
                        logger.error(
                            "No recognized test framework found in the test command."
                        )
                        return

                    # Insert a npm install step to install all dependencies
                    job["steps"].insert(
                        i + 1,
                        {
                            "name": "gitbug-actions List files in the directory",
                            "run": f"ls -alh",  # -a for all files, -l for detailed listing, -h for human-readable sizes
                        },
                    )
                    job["steps"].insert(
                        i + 1,
                        {
                            "name": "gitbug-actions Install dependencies",
                            "run": f"npm install",
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
                            # Check if the test command is defined in package.json
                            package_json_path = Path(self.repo_path) / "package.json"
                            if package_json_path.exists():
                                with open(package_json_path, "r") as f:
                                    package_json = json.load(f)
                            else:
                                logger.warning("Couldn't find package.json")
                                return

                            # Extract the test command from the "scripts" section
                            test_command = package_json.get("scripts", {}).get(
                                "test", ""
                            )
                            logger.info(f"Original test command: {test_command}")
                            npm_test_command = step["run"]

                            if test_command:
                                # Update the test command to output junitxml results
                                if "jest" in test_command:
                                    # Jest: Add reporter to output in junitxml format
                                    if "--reporters" not in test_command:
                                        test_command = (
                                            test_command
                                            + " --reporters=default --reporters=jest-junit --outputFile report.xml"
                                        )
                                    else:
                                        test_command = test_command.replace(
                                            "--reporters=default",
                                            "--reporters=default --reporters=jest-junit --outputFile report.xml",
                                        )
                                elif "mocha" in test_command:
                                    # Mocha: Add reporter to output in junitxml format
                                    if "--reporter" not in test_command:
                                        test_command = (
                                            test_command
                                            + " --reporter mocha-junit-reporter --reporter-options mochaFile=report.xml"
                                        )
                                    else:
                                        test_command = test_command.replace(
                                            "--reporter",
                                            "--reporter mocha-junit-reporter",
                                        )
                                elif "vitest" in test_command or "vite" in test_command:
                                    # Vitest/Vite: Add reporter for JUnit XML output
                                    if "--reporter" not in test_command:
                                        test_command = (
                                            test_command
                                            + " --reporter vite-plugin-junit-reporter --reporter-options output=report.xml"
                                        )
                                    else:
                                        test_command = test_command.replace(
                                            "--reporter",
                                            "--reporter vite-plugin-junit-reporter --reporter-options output=report.xml",
                                        )

                                # Update the step with the modified test command directly
                                # step["run"] = step["run"].replace(
                                #     npm_test_command, test_command
                                # )
                                # Update package.json with the modified test command
                                package_json["scripts"]["test"] = test_command
                                with open(package_json_path, "w") as f:
                                    package_json = json.dump(package_json, f)
                            else:
                                print("No test command found in package.json.")

    def get_test_results(self, repo_path) -> List[TestCase]:
        parser = JUnitXMLParser()
        logger.info(f"Looking for test results at {repo_path}")
        run = subprocess.run(f"ls {repo_path}", shell=True, capture_output=True)
        logger.info(f"Results of ls {repo_path}: {run.stdout}")
        return parser.get_test_results(str(Path(repo_path, "junit.xml")))

    def get_build_tool(self) -> str:
        return "npm"

    def get_report_location(self) -> str:
        return self.REPORT_LOCATION
