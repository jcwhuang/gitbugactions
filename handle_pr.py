import fire
import json
import os
import sys
from collect_prs import HandlePullRequestsStrategy, PullRequest, MinimalRepository
from gitbugactions.logger import get_logger

logger = get_logger(__name__)


def handle_repos(
    prdata_filename: str,
    out_path: str = "../out/",
):
    os.makedirs(out_path)
    strategy = HandlePullRequestsStrategy(out_path)
    with open(prdata_filename) as f:
        prdata = json.load(f)
    repo = MinimalRepository(
        full_name=prdata["head"]["repo"]["full_name"],
        clone_url=prdata["head"]["repo"]["clone_url"],
        stargazers_count=prdata["head"]["repo"]["stargazers_count"],
        language=prdata["head"]["repo"]["language"],
        size=prdata["head"]["repo"]["size"],
        pull_number=prdata["number"],
    )
    pr = PullRequest(
        repo=repo, pull_number=prdata["number"], base_commit=prdata["base"]["sha"]
    )
    strategy.handle_pr(pr)


def main():
    fire.Fire(handle_repos)


if __name__ == "__main__":
    sys.exit(main())
