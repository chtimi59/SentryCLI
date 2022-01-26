import os
import re
import sys
import urllib.parse
from typing import Dict, List

import dotenv
import requests
from pydantic import BaseModel

dotenv.load_dotenv()


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


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


class Tag(BaseModel):
    value: str
    count: str


class Tags(BaseModel):
    __root__: List[Tag] = []


ORGANIZATION_SLUG = os.getenv("ORGANIZATION_SLUG")
if ORGANIZATION_SLUG is None:
    error("ORGANIZATION_SLUG is missing !")
PROJECT_SLUG = os.getenv("PROJECT_SLUG")
if PROJECT_SLUG is None:
    error("PROJECT_SLUG is missing !")
SENTRY_TOKEN = os.getenv("SENTRY_TOKEN")
if SENTRY_TOKEN is None:
    error("SENTRY_TOKEN is missing !")
URL_API0 = "https://sentry.io/api/0/"
URL_PROJECTS = URL_API0 + f"projects/{ORGANIZATION_SLUG}/{PROJECT_SLUG}/"


def next_url(link: str):
    """Sentry Pagination : https://docs.sentry.io/api/pagination/"""
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


# GET /api/0/projects/{organization_slug}/{project_slug}/issues/
def get_issues(query: str = "is:unresolved", page: int = 1) -> List[Issue]:
    result: List[Issue] = []
    url = URL_PROJECTS + "issues/?" + urllib.parse.urlencode({"query": query})
    while url is not None and page > 0:
        r = requests.get(url, headers={"Authorization": f"Bearer {SENTRY_TOKEN}"})
        if not r.status_code == 200:
            error(f"{url} returns HTTP {r.status_code}")
        url = next_url(r.headers["link"])
        payload = r.json()
        result.extend(Issues.parse_obj(payload).__root__)
        page -= 1
    return result


# GET /api/0/issues/{issue_id}/tags/{key}/values/
def get_tags(issue_id: int, tag_name: str, page: int = 1) -> Dict[str, int]:
    result: Dict[str, int] = {}
    url = URL_API0 + f"issues/{issue_id}/tags/{tag_name}/values/"
    while url is not None and page > 0:
        r = requests.get(url, headers={"Authorization": f"Bearer {SENTRY_TOKEN}"})
        if not r.status_code == 200:
            error(f"{url} returns HTTP {r.status_code}")
        url = next_url(r.headers["link"])
        payload = r.json()
        for tag in Tags.parse_obj(payload).__root__:
            result[tag.value] = tag.count
        page -= 1
    return result


# DELETE /api/0/projects/{organization_slug}/{project_slug}/issues/
def delete_issues(ids: List[int]):
    url = URL_PROJECTS + "issues/?" + "&".join(map(lambda id: f"id={id}", ids))
    r = requests.delete(url, headers={"Authorization": f"Bearer {SENTRY_TOKEN}"})
    if not r.status_code == 204:
        error(f"{url} returns HTTP {r.status_code}")
    print(f"deleted: {ids}")


def delete_from_query(query: str, count=1):
    while count > 0:
        # 5 pages of 100 entries
        issues = get_issues(page=5, query=query)
        for issue in issues:
            print(issue.title)
        # bullk delete (10)
        ids = list(map(lambda issue: issue.id, issues))
        for ids in chunks(ids, 10):
            delete_issues(ids)
        count -= 1


def main() -> None:
    delete_from_query("is:unresolved release:kd-dem@2201.5.0", count=10)


if __name__ == "__main__":
    main()
