from dataclasses import dataclass
import fire
import json
import os
import sys
from collect_repos import CollectReposStrategy

@dataclass
class MyRepository:
    full_name: str
    clone_url: str
    stargazers_count: int
    language: str
    size: str


def handle_repos(
    prdata_filename: str, out_path: str = "./out/"
):
    os.makedirs(out_path)
    strategy = CollectReposStrategy(out_path)
    with open(prdata_filename) as f:
        prdata = json.load(f)
    repo = MyRepository(
        full_name=prdata["head"]["repo"]["full_name"],
        clone_url=prdata["head"]["repo"]["clone_url"],
        stargazers_count=prdata["head"]["repo"]["stargazers_count"],
        language=prdata["head"]["repo"]["language"],
        size=prdata["head"]["repo"]["size"],
        pull_number=prdata["number"]
    )
    strategy.handle_repo(repo, prdata["base"]["sha"])


def main():
    fire.Fire(handle_repos)


if __name__ == "__main__":
    sys.exit(main())
