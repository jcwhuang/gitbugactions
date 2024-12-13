import re


def update_jest_command(test_command: str) -> str:
    # Jest: Add reporter to output in junitxml format
    # See https://jestjs.io/docs/cli#--reporters
    # default output file name (unconfigurable) is junit.xml

    # Check if jest-junit is already present
    if "--reporters=jest-junit" not in test_command:
        # If there are no reporters, append both default and jest-junit
        if "--reporters=" not in test_command:
            test_command += " --reporters=default --reporters=jest-junit"
        else:
            # Ensure default and jest-junit are present
            if "--reporters=default" not in test_command:
                test_command += " --reporters=default"
            if "--reporters=jest-junit" not in test_command:
                test_command += " --reporters=jest-junit"

    # Remove any duplicate reporter options
    reporters = re.findall(r"--reporters=[^\s]+", test_command)
    unique_reporters = list(
        dict.fromkeys(reporters)
    )  # Remove duplicates while maintaining order
    test_command = re.sub(r"--reporters=[^\s]+", "", test_command).strip()
    test_command += " " + " ".join(unique_reporters)

    return test_command


def update_mocha_command(test_command):
    if "--reporter" not in test_command:
        # If there's no reporter, add mocha-junit-reporter with reporter options
        test_command += (
            " --reporter mocha-junit-reporter --reporter-options mochaFile=junit.xml"
        )
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
        # Replace or add reporter-options
        if "--reporter-options" in test_command:
            test_command = re.sub(
                r"--reporter-options [^\s]+",
                "--reporter-options mochaFile=junit.xml",
                test_command,
            )
        else:
            test_command += " --reporter-options mochaFile=junit.xml"
    return test_command


def update_vitest_command(test_command):
    # See https://vitest.dev/guide/reporters.html#junit-reporter
    # Documentation suggests we can just use outputFile, but I did not observe
    # any junit.xml output without outputFile.junit
    if "--reporter=junit" not in test_command:
        # Add default and junit reporters if not present
        if "--reporter=default" not in test_command:
            test_command += " --reporter=default"
        test_command += " --reporter=junit --outputFile.junit=junit.xml"
    else:
        # Ensure outputFile.junit has the correct value
        test_command = re.sub(
            r"--outputFile\.junit=[^\s]+",
            "--outputFile.junit=junit.xml",
            test_command,
        )
        # Add default reporter if missing
        if "--reporter=default" not in test_command:
            test_command += " --reporter=default"
    return test_command


def add_junit_xml(test_command: str) -> str:
    """Depending on what testing library is used, add relevant flags to enable junit xml reporting."""
    # Update the test command to output junitxml results
    if "jest" in test_command:
        test_command = update_jest_command(test_command)
    elif "mocha" in test_command:
        test_command = update_mocha_command(test_command)
    elif "vitest" in test_command or "vite" in test_command:
        test_command = update_vitest_command(test_command)
    return test_command
