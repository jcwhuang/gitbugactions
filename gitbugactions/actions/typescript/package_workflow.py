from abc import abstractmethod
from junitparser import TestCase
from pathlib import Path
from typing import List, Optional
import json
import subprocess

from gitbugactions.actions.workflow import GitHubWorkflow
from gitbugactions.actions.multi.junitxmlparser import JUnitXMLParser
from gitbugactions.actions.typescript.package_junitxml import add_junit_xml
from gitbugactions.logger import get_logger

logger = get_logger(__name__)


class PackageWorkflow(GitHubWorkflow):

    REPORT_LOCATION = "junit.xml"

    def __init__(self, build_tool_keyword, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.build_tool_keyword = build_tool_keyword
        self.test_command = ""
        self.test_name = ""

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
                    return

    def instrument_test_steps(self):
        if "jobs" in self.doc:
            for _, job in self.doc["jobs"].items():
                if "steps" in job:
                    for step in job["steps"]:
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
                            self.test_name = self._get_test_keyword(run_command)
                            logger.info(
                                f"Looking under package.json['scripts']['{self.test_name}']"
                            )
                            test_command = package_json.get("scripts", {}).get(
                                self.test_name, ""
                            )
                            logger.info(f"Test command is {test_command}")
                            self.test_command = test_command.split(" ")[0]
                            if test_command:
                                test_command = add_junit_xml(test_command)
                                # Update package.json with the modified test command
                                package_json["scripts"][self.test_name] = test_command
                                logger.info(f"New test command is {test_command}")
                                with open(package_json_path, "w") as f:
                                    package_json = json.dump(package_json, f)
                            else:
                                logger.info("No test command found in package.json.")

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

    def get_additional_files(self) -> Optional[list[str]]:
        return [str(Path(self.repo_path) / "package.json")]
