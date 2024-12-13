import pytest
from gitbugactions.actions.typescript.package_junitxml import add_junit_xml


@pytest.mark.parametrize(
    "input_command, expected_command",
    [
        (
            "vitest",
            "vitest --reporter=default --reporter=junit --outputFile.junit=junit.xml",
        ),
        # rename outputFile.junit, add default reporter
        (
            "vitest --reporter=junit --outputFile.junit=oldfile.xml",
            "vitest --reporter=junit --outputFile.junit=junit.xml --reporter=default",
        ),
        # existing default reporter, add junit reporter
        (
            "vitest --reporter=default",
            "vitest --reporter=default --reporter=junit --outputFile.junit=junit.xml",
        ),
        # no change
        (
            "vitest --reporter=default --reporter=junit --outputFile.junit=junit.xml",
            "vitest --reporter=default --reporter=junit --outputFile.junit=junit.xml",
        ),
        (
            "mocha",
            "mocha --reporter mocha-junit-reporter --reporter-options mochaFile=junit.xml",
        ),
        # rename mochaFile
        (
            "mocha --reporter mocha-junit-reporter --reporter-options mochaFile=random.xml",
            "mocha --reporter mocha-junit-reporter --reporter-options mochaFile=junit.xml",
        ),
        # replace reporter, replace reporter-options
        (
            "mocha --reporter random --reporter-options random=random --other-arg value",
            "mocha --reporter mocha-junit-reporter --reporter-options mochaFile=junit.xml --other-arg value",
        ),
        (
            "mocha --reporter mocha-junit-reporter --reporter-options mochaFile=junit.xml",
            "mocha --reporter mocha-junit-reporter --reporter-options mochaFile=junit.xml",
        ),
        (
            "jest",
            "jest --reporters=default --reporters=jest-junit",
        ),
        (
            "jest --reporters=default",
            "jest --reporters=default --reporters=jest-junit",
        ),
        (
            "jest --reporters=random",
            "jest --reporters=random --reporters=default --reporters=jest-junit",
        ),
        (
            "jest --reporters=default --reporters=jest-junit",
            "jest --reporters=default --reporters=jest-junit",
        ),
    ],
)
def test_update_test_command(input_command, expected_command):
    assert add_junit_xml(input_command) == expected_command
