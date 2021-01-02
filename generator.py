import datetime
from email.utils import format_datetime as rss_pubDate
import json
import os
from pathlib import Path
import sys

import argparse
from jinja2 import Environment, FileSystemLoader
from jinja2.environment import Template
import markdown
from slugify import slugify


file_loader = FileSystemLoader("templates")
env = Environment(loader=file_loader)
env.globals.update(rss_pubDate=rss_pubDate)
parser = argparse.ArgumentParser(description="This is a static static site generator")


parser.add_argument("-i", type=str, help="Initialize new site")
parser.add_argument("-p", type=str, help="Initialize new podcast")
parser.add_argument("-t", type=str, help="Render site from config")


GENERATOR = "Gazetteicorn 0.0.1 - https://github.com/"

BASE_CONFIG = {
    "base_url": "",
    "copyright": "",
    "default_author": "",
    "description": "",
    "paths": {
        "output": "",
        "pages": "",
    },
    "title": "",
    "bottom_menu": [{"name": "name", "url": "url"}, {"name": "name", "url": "url"}],
    "top_menu": [{"name": "name", "url": "url"}, {"name": "name", "url": "url"}],
    "type": "blog",
}

BASE_PODCAST_CONFIG = BASE_CONFIG.copy()
BASE_PODCAST_CONFIG["type"] = "podcast"
BASE_PODCAST_CONFIG["podcast"] = {
    "title": "",
    "cover": "",
    "description": "",
    "links": [
        {"name": "name", "url": "url"},
        {"name": "name", "url": "url"},
        {"name": "name", "url": "url"},
    ],
    "rss_url": "",
}

CONFIG_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config")


def get_page_template():
    meta = {"categories": [], "created": "1970-01-01", "title": "", "tags": []}
    x = json.dumps(meta, indent=4, sort_keys=True)
    template = json.dumps(meta, indent=4, sort_keys=True) + "\nʕ •ᴥ•ʔ\n" + "Lorem Ipsum"
    return template


class Page:
    def __init__(self, file_path):
        with open(file_path) as f:
            raw_string = f.read()
        [meta, body] = raw_string.split("ʕ •ᴥ•ʔ", 1)

        self.meta = json.loads(meta)
        self.categories = self.meta.get("categories", [])
        self.tags = self.meta.get("tags", [])

        created = self.meta.get("created", "1970-01-01")
        self.created = datetime.datetime.strptime(created, "%Y-%m-%d")
        updated = self.meta.get("created", self.created)
        self.updated = datetime.datetime.strptime(updated, "%Y-%m-%d")

        self.author = self.meta.get("author", None)

        self.title = self.meta["title"]
        self.slug = slugify(self.title)

        if Path(file_path).suffix == ".md":
            self.body = markdown.markdown(body)
        else:
            self.body = body

        self.related = []


class Site:
    def __init__(self, config_path):
        self.generator = GENERATOR

        self.config = self.load_config(config_path)
        self.base_url = self.config["base_url"]
        self.description = self.config["description"]
        self.title = self.config["title"]

        self.pages = self.load_pages()
        self.authors = self.load_meta_list("authors")
        self.categories = self.load_meta_list("categories")
        self.tags = self.load_meta_list("tags")
        self.tags_set = set(self.tags)
        for page in self.pages:
            page.related = self.find_related(page)

    def find_related(self, page):
        related_pages = []
        for i, each in enumerate(self.pages):
            if each.slug is page.slug:
                continue
            target_tags = set(each.tags)
            shared_tags = self.tags_set.intersection(target_tags)
            t = {}
            t["score"] = len(shared_tags)
            if t["score"] > 0:
                t["title"] = each.title
                t["slug"] = each.slug
                t["created"] = each.created
            related_pages.append(t)
        related_pages = sorted(related_pages, key=lambda i: i["score"], reverse=True)[
            :5
        ]

        return related_pages

    def load_meta_list(self, attribute):
        temp = []
        for page in self.pages:
            temp.extend(getattr(page, attribute, []))
        temp = list(set(temp))
        print(str(len(temp)) + " " + attribute + " found")
        return list(temp)

    def load_config(self, config_path):
        if not os.path.exists(config_path):
            print("Config file does not exit")
            exit()
        with open(config_path) as f:
            config = json.load(f)
        return config

    def load_pages(self):
        if not os.path.exists(self.config["paths"]["pages"]):
            print("Pages path does not exit: " + self.config["paths"]["pages"])
            exit()
        pages = []
        for each in os.listdir(self.config["paths"]["pages"]):
            file_path = os.path.join(self.config["paths"]["pages"], each)
            page = Page(file_path)
            pages.append(page)
        pages = sorted(pages, key=lambda i: i.created, reverse=True)
        print(str(len(pages)) + " files successfully loaded")
        return pages

    def load_tags(self):
        temp_tags = set()
        for page in self.pages:
            for tag in page["tags"]:
                temp_tags.add(tag)
        print(str(len(temp_tags)) + " tags found")
        return list(temp_tags)

    def render_all(self):
        if not self.config["paths"]["output"]:
            print("Output path is empty")
            return
        self.render_rss()
        self.render_sitemap()
        if self.config["type"] == "podcast":
            self.render_podcast_frontpage()
        else:
            self.render_frontpage()
        for page in self.pages:
            self.render_page(page)

    def render_podcast_frontpage(self):
        file_path = os.path.join(self.config["paths"]["output"], "index.html")
        template = env.get_template("podcast_frontpage.html")
        output = template.render(site=self)
        with open(file_path, "w") as f:
            f.write(output)

    def render_frontpage(self):
        file_path = os.path.join(self.config["paths"]["output"], "index.html")
        template = env.get_template("frontpage.html")
        output = template.render(site=self)
        with open(file_path, "w") as f:
            f.write(output)

    def render_page(self, page):
        page_path = os.path.join(self.config["paths"]["output"], page.slug)
        os.makedirs(page_path, exist_ok=True)
        file_path = os.path.join(page_path, "index.html")
        template = env.get_template("page.html")
        output = template.render(site=self, page=page)
        with open(file_path, "w") as f:
            f.write(output)

    def render_rss(self):
        file_path = os.path.join(self.config["paths"]["output"], "rss.xml")
        template = env.get_template("rss.xml")
        output = template.render(site=self)
        with open(file_path, "w") as f:
            f.write(output)

    def render_sitemap(self):
        file_path = os.path.join(self.config["paths"]["output"], "sitemap.xml")
        template = env.get_template("sitemap.xml")
        output = template.render(site=self)
        with open(file_path, "w") as f:
            f.write(output)

    @staticmethod
    def make_default_config(config_path):
        with open(config_path, "w") as f:
            json.dump(REQUIRED_CONFIG_KEYS, f, indent=4, sort_keys=True)


def initialize_new_site(name):
    file_name = slugify(name) + ".json"
    file_path = os.path.join(CONFIG_DIR, file_name)
    if os.path.isfile(file_path):
        print("config already exists")
        exit()
    with open(file_path, "w") as f:
        json.dump(BASE_CONFIG, f, indent=4, sort_keys=True)


def initialize_new_postcast(name):
    file_name = slugify(name) + ".json"
    file_path = os.path.join(CONFIG_DIR, file_name)
    print(file_path)
    if os.path.isfile(file_path):
        print("config already exists")
        exit()
    with open(file_path, "w") as f:
        json.dump(BASE_PODCAST_CONFIG, f, indent=4, sort_keys=True)


def render_target_site(config_path):
    site = Site(config_path)
    site.render_all()


def render_all_sites():
    for each in os.listdir(CONFIG_DIR):
        file_path = os.path.join(CONFIG_DIR, each)
        if os.path.isfile(file_path):
            render_target_site(file_path)


if __name__ == "__main__":
    args = parser.parse_args()
    if args.i:
        initialize_new_site(args.i)
    elif args.p:
        initialize_new_postcast(args.p)
    elif args.t:
        render_target_site(args.t)
    else:
        render_all_sites()
