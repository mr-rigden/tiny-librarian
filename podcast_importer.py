import datetime
import json
import os

from slugify import slugify

import rss_to_dict

CONFIG_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config")


def render_page(episode, pages_path):
    meta = {}
    meta["title"] = episode["title"]
    meta["slug"] = slugify(meta["title"])
    file_name = meta["slug"] + ".json"
    file_path = os.path.join(pages_path, file_name)
    if os.path.exists(file_path):
        return

    meta["created"] = episode["pubDate_datetime"].strftime("%Y-%m-%d")
    meta["audio"] = episode["enclosure"]["url"]
    meta["tags"] = []
    contents = (
        json.dumps(meta, indent=4, sort_keys=True)
        + "\nʕ •ᴥ•ʔ\n"
        + episode["description"]
    )
    with open(file_path, "w") as f:
        f.write(contents)


if __name__ == "__main__":
    for each in os.listdir(CONFIG_DIR):
        print("Loading: " + each)
        file_path = os.path.join(CONFIG_DIR, each)
        with open(file_path) as f:
            config = json.load(f)
        if not config["paths"]["pages"]:
            print("pages path is empty")
            continue
        if config["type"] == "podcast":
            if not config["podcast"]["rss_url"]:
                print("Config is missing rss_url")
                continue
            podcast = rss_to_dict.parse(config["podcast"]["rss_url"])
            for episode in podcast["episodes"]:
                render_page(episode, config["paths"]["pages"])
        else:
            print("Not a podcast")
