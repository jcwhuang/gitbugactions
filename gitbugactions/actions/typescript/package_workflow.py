from abc import abstractmethod
from junitparser import TestCase
from pathlib import Path
from typing import List
import json
import re
import subprocess

from gitbugactions.actions.workflow import GitHubWorkflow
from gitbugactions.actions.multi.junitxmlparser import JUnitXMLParser
from gitbugactions.logger import get_logger

logger = get_logger(__name__)


class PackageWorkflow(GitHubWorkflow):

    REPORT_LOCATION = "junit.xml"

    def __init__(self, build_tool_keyword, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.build_tool_keyword = build_tool_keyword
        self.test_command = ""

    def instrument_online_execution(self):
        if self.has_tests():
            for _, job in self.doc["jobs"].items():
                if "steps" in job:
                    for i, step in enumerate(job["steps"]):
                        if "run" in step and self._is_test_command(step["run"]):
                            break
                    else:
                        continue

                    job["steps"].insert(
                        i,
                        {
                            "name": "gitbug-actions Install jest-junit",
                            "run": f"{self.build_tool_keyword} add jest-junit",
                        },
                    )

                    job["steps"].insert(
                        i,
                        {
                            "name": "gitbug-actions Install mocha-junit-reporter",
                            "run": f"{self.build_tool_keyword} add mocha-junit-reporter",
                        },
                    )

                    # Insert a npm install step to install all dependencies
                    job["steps"].insert(
                        i + 1,
                        {
                            "name": "gitbug-actions Install dependencies",
                            "run": f"{self.build_tool_keyword} install",
                        },
                    )
                    return

    def instrument_test_steps(self):
        if "jobs" in self.doc:
            for _, job in self.doc["jobs"].items():
                if "steps" in job:
                    for i, step in enumerate(job["steps"]):
                        if "run" in step and self._is_test_command(step["run"]):
                            step["run"] = step["run"].strip()
                            package_json_path = Path(self.repo_path) / "package.json"
                            if package_json_path.exists():
                                with open(package_json_path, "r") as f:
                                    package_json = json.load(f)
                            else:
                                logger.warning("Couldn't find root-level package.json")
                                return

                            # Extract the test command from the "scripts" section based on the
                            # npm/yarn (run)? test(something)?
                            run_command = step["run"].strip()
                            test_name = self._get_test_keyword(run_command)
                            logger.info(
                                f"Looking under package.json['scripts']['{test_name}']"
                            )
                            test_command = package_json.get("scripts", {}).get(
                                test_name, ""
                            )
                            logger.info(f"Test command is {test_command}")
                            self.test_command = test_command.split(" ")[0]
                            if test_command:
                                test_command = self._add_junit_xml(test_command)
                                # Update package.json with the modified test command
                                package_json["scripts"][test_name] = test_command
                                logger.info(f"New test command is {test_command}")
                                with open(package_json_path, "w") as f:
                                    package_json = json.dump(package_json, f)
                            else:
                                logger.info("No test command found in package.json.")
                            return

    def _add_junit_xml(self, test_command: str) -> str:
        """Depending on what testing library is used, add relevant flags to enable junit xml reporting."""
        # Update the test command to output junitxml results
        if "jest" in test_command:
            # Jest: Add reporter to output in junitxml format
            # See https://jestjs.io/docs/cli#--reporters
            # default output file name (unconfigurable) is junit.xml
            if "--reporters" not in test_command:
                test_command = (
                    test_command + " --reporters=default --reporters=jest-junit"
                )
            else:
                test_command = test_command.replace(
                    "--reporters=default",
                    "--reporters=default --reporters=jest-junit",
                )
        elif "mocha" in test_command:
            # Mocha: Add reporter to output in junitxml format
            if "--reporter" not in test_command:
                # If there's no reporter, add mocha-junit-reporter with reporter options
                test_command += " --reporter mocha-junit-reporter --reporter-options mochaFile=junit.xml"
            elif "--reporter mocha-junit-reporter" in test_command:
                # If mocha-junit-reporter is already specified, ensure the correct options
                if "--reporter-options" in test_command:
                    # Replace existing mochaFile option if present
                    test_command = re.sub(
                        r"--reporter-options.*mochaFile=[^\s,]+",
                        "--reporter-options mochaFile=junit.xml",
                        test_command,
                    )
                else:
                    # Add reporter-options if missing
                    test_command += " --reporter-options mochaFile=junit.xml"
            else:
                # If there's a different reporter, replace it with mocha-junit-reporter
                test_command = re.sub(
                    r"--reporter [^\s]+",
                    "--reporter mocha-junit-reporter",
                    test_command,
                )
                # Add or update reporter-options
                if "--reporter-options" in test_command:
                    test_command = re.sub(
                        r"--reporter-options.*mochaFile=[^\s,]+",
                        "--reporter-options mochaFile=junit.xml",
                        test_command,
                    )
                else:
                    test_command += " --reporter-options mochaFile=junit.xml"
        elif "vitest" in test_command or "vite" in test_command:
            # See https://vitest.dev/guide/reporters.html#junit-reporter
            # Documentation suggests we can just use outputFile, but I did not observe
            # any junit.xml output without outputFile.junit
            if "--reporter=junit" not in test_command:
                test_command = (
                    test_command
                    + " --reporter=default --reporter=junit --outputFile.junit=junit.xml"
                )
            elif "--reporter=junit" in test_command:
                test_command = re.sub(
                    r"--outputFile.junit=[^\s]+",
                    "--outputFile.junit=junit.xml",
                    test_command,
                )
        return test_command

    def get_build_tool(self) -> str:
        return f"{self.build_tool_keyword}, {self.test_command}"

    def get_test_results(self, repo_path) -> List[TestCase]:
        parser = JUnitXMLParser()
        logger.info(f"Looking for test results at {repo_path}")
        run = subprocess.run(f"ls {repo_path}", shell=True, capture_output=True)
        logger.info(f"Results of ls {repo_path}: {run.stdout}")
        return parser.get_test_results(str(Path(repo_path, "junit.xml")))

    def get_report_location(self) -> str:
        return self.REPORT_LOCATION

    @abstractmethod
    def _get_test_keyword(self, command: str) -> str:
        pass
