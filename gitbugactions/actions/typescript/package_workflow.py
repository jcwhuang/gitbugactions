from abc import abstractmethod
from pathlib import Path
import json

from gitbugactions.actions.workflow import GitHubWorkflow
from gitbugactions.logger import get_logger

logger = get_logger(__name__)


class PackageWorkflow(GitHubWorkflow):

    def __init__(self, build_tool_keyword, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.build_tool_keyword = build_tool_keyword
        self.test_command = ""

    @abstractmethod
    def _is_install_command(self):
        pass

    @abstractmethod
    def get_install_step(self) -> dict:
        pass

    def instrument_installation(self):
        for _, job in self.doc["jobs"].items():
            if "steps" in job:
                for i, step in enumerate(job["steps"]):
                    if "run" in step and self._is_install_command(step["run"]):
                        break
        if self.get_install_step() is not None:
            job["steps"].insert(i, self.get_install_step())

    def instrument_online_execution(self):
        if self.has_tests():
            # alias
            package_json_path = Path(self.repo_path) / "package.json"
            if package_json_path.exists():
                with open(package_json_path, "r") as f:
                    package_json = json.load(f)
            else:
                logger.warning("Couldn't find package.json")
                return

            # Get the test command from package.json
            test_cmd = package_json.get("scripts", {}).get("test", "")
            self.test_command = test_cmd.split(" ")[0]

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
                            # Rename test step
                            break

        job["steps"].insert(
            i,
            {
                "name": "gitbug-actions Print env",
                "run": "cat ~/.bashrc && echo \"source ~/.bashrc\" >> ~/.bash_profile",
            },
        )

        job["steps"].insert(
            i + 1,
            {
                "name": "gitbug-actions alias jest",
                "run": "type jest",
            },
        )

        # step["run"] = step["run"].strip()
        # # Check if the test command is defined in package.json
        # package_json_path = Path(self.repo_path) / "package.json"
        # if package_json_path.exists():
        #     with open(package_json_path, "r") as f:
        #         package_json = json.load(f)
        # else:
        #     logger.warning("Couldn't find package.json")
        #     return

        # # Extract the test command from the "scripts" section
        # test_command = package_json.get("scripts", {}).get(
        #     "test", ""
        # )
        # logger.info(f"Original test command: {test_command}")

        # if test_command:
        #     # Update the test command to output junitxml results
        #     if "jest" in test_command:
        #         # Jest: Add reporter to output in junitxml format
        #         # See https://jestjs.io/docs/cli#--reporters
        #         # default output file name (unconfigurable) is junit.xml
        #         if "--reporters" not in test_command:
        #             test_command = (
        #                 test_command
        #                 + " --reporters=default --reporters=jest-junit"
        #             )
        #         else:
        #             test_command = test_command.replace(
        #                 "--reporters=default",
        #                 "--reporters=default --reporters=jest-junit --outputName report.xml",
        #             )
        #     elif "mocha" in test_command:
        #         # Mocha: Add reporter to output in junitxml format
        #         if "--reporter" not in test_command:
        #             test_command = (
        #                 test_command
        #                 + " --reporter mocha-junit-reporter --reporter-options mochaFile=report.xml"
        #             )
        #         else:
        #             test_command = test_command.replace(
        #                 "--reporter",
        #                 "--reporter mocha-junit-reporter",
        #             )
        #     elif "vitest" in test_command or "vite" in test_command:
        #         # Vitest/Vite: Add reporter for JUnit XML output
        #         if "--reporter" not in test_command:
        #             test_command = (
        #                 test_command
        #                 + " --reporter vite-plugin-junit-reporter --reporter-options output=report.xml"
        #             )
        #         else:
        #             test_command = test_command.replace(
        #                 "--reporter",
        #                 "--reporter vite-plugin-junit-reporter --reporter-options output=report.xml",
        #             )

        #     # Update the step with the modified test command directly
        #     # step["run"] = step["run"].replace(
        #     #     npm_test_command, test_command
        #     # )
        #     # Update package.json with the modified test command
        #     package_json["scripts"]["test"] = test_command
        #     with open(package_json_path, "w") as f:
        #         package_json = json.dump(package_json, f)
        # else:
        #     print("No test command found in package.json.")
        # return

    def get_build_tool(self) -> str:
        return f"{self.build_tool_keyword}, {self.test_command}"
