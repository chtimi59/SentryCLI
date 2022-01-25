import os
import re
import sys
import urllib.parse
from typing import List

import dotenv
import requests
from pydantic import BaseModel

dotenv.load_dotenv()


def error(msg: str):
    print(msg, file=sys.stderr)
    exit(1)


class Issue(BaseModel):
    id: int
    title: str
    type: str
    count: str


class Issues(BaseModel):
    __root__: List[Issue] = []


ORGANIZATION_SLUG = os.getenv("ORGANIZATION_SLUG")
if ORGANIZATION_SLUG is None:
    error("ORGANIZATION_SLUG is missing !")
PROJECT_SLUG = os.getenv("PROJECT_SLUG")
if PROJECT_SLUG is None:
    error("PROJECT_SLUG is missing !")
SENTRY_TOKEN = os.getenv("SENTRY_TOKEN")
if SENTRY_TOKEN is None:
    error("SENTRY_TOKEN is missing !")
URL = f"https://sentry.io/api/0/projects/{ORGANIZATION_SLUG}/{PROJECT_SLUG}/"


# For pagination
# https://docs.sentry.io/api/pagination/
def getNextUrl(link: str):
    m = re.search(
        "^"
        + '<(?P<url1>.+)>; rel="(?P<rel1>.+)"; results="(?P<results1>.+)"; cursor="(?P<cursor1>.+)'
        + ", "
        + '<(?P<url2>.+)>; rel="(?P<rel2>.+)"; results="(?P<results2>.+)"; cursor="(?P<cursor2>.+)"'
        + "$",
        link,
    )
    idx = 1 if m.group("rel1") == "next" else 2
    return m.group(f"url{idx}") if m.group(f"results{idx}") == "true" else None


def getIssues(query: str = "is:unresolved", page: int = 1) -> List[Issue]:
    result: List[Issue] = []
    url = URL + "issues/?" + urllib.parse.urlencode({"query": query})
    while url is not None and page > 0:
        r = requests.get(url, headers={"Authorization": f"Bearer {SENTRY_TOKEN}"})
        if not r.status_code == 200:
            error(f"{url} returns HTTP {r.status_code}")
        url = getNextUrl(r.headers["link"])
        result.extend(Issues.parse_obj(r.json()).__root__)
        page -= 1
    return result


def main() -> None:
    data = getIssues(page=2)
    # "is:unresolved release:2201.6.0")
    print(f"size = {len(data)}")
    # for p in data:
    #    print(p.title)


if __name__ == "__main__":
    main()
