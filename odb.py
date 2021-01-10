#!/usr/bin/env python3

import urllib.parse
import json
import requests
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import dateutil.parser
import time
from absl import app
from absl import flags
import sys
from natsort import natsorted, ns

FLAGS = flags.FLAGS
flags.DEFINE_string("login_url", None, "Login URL")
flags.DEFINE_string("cookie_file", None, "Cookie file to save/restore")

flags.DEFINE_string("tree", None, "List folder tree as json")
flags.DEFINE_bool("recursive", False, "Recursively list tree")

flags.DEFINE_string("print_tree", None, "Read ODB tree from json then pretty_print")

flags.DEFINE_string("output", None, "Print to file instead of stdout")
flags.DEFINE_bool("verbose", False, "")

class bcolors:
    GREY = '\033[38;5;242m'
    RED = '\033[31m'
    YELLOW = '\033[33m'
    RESET = '\033[0m'

class OdbShare:

    def login_via_url(self, url:str, cookie_file=None):
        # URL: https://xxx-my.sharepoint.com/:f:/g/personal/yyy/zzz
        # Base URL: https://xxx-my.sharepoint.com/personal/yyy/_api/web/
        # Base Folder: /personal/yyy/Documents/...
        # Cookie: FedAuth=...
        redirect_rsp = requests.get(url, allow_redirects=False)
        assert redirect_rsp.status_code == 302
        cookie = redirect_rsp.headers["Set-Cookie"].split(';')[0]
        url_parsed = urllib.parse.urlparse(redirect_rsp.headers["Location"])
        query_parsed = urllib.parse.parse_qs(url_parsed.query)
        idx = url_parsed.path.find("/_layouts")
        assert idx > 0

        self.cookie_fed_auth = cookie
        self.base_url = f"https://{url_parsed.netloc}{url_parsed.path[:idx]}/_api/web"
        self.base_folder = query_parsed["id"][0]
        if cookie_file is not None:
            cookie_file.write(json.dumps(dict(
                cookie_fed_auth=self.cookie_fed_auth,
                base_url = self.base_url,
                base_folder = self.base_folder
            ), indent=2))

        print("Base URL:", self.base_url)
        print("Base Folder:", self.base_folder)
        print("Cookie:\n" + self.cookie_fed_auth)
        print("=====")

    def login_via_file(self, cookie_file):
        obj = json.load(cookie_file)
        self.cookie_fed_auth = obj["cookie_fed_auth"]
        self.base_url = obj["base_url"]
        self.base_folder = obj["base_folder"]
        print("Base URL:", self.base_url)
        print("Base Folder:", self.base_folder)
        print("Cookie:\n" + self.cookie_fed_auth)
        print("=====")

    def http_get(self, url: str):
        headers = {
            "cache-control": "no-cache",
            "accept": "application/json;odata=verbose",
            "cookie": self.cookie_fed_auth
        }
        # if FLAGS.verbose:
        #     print(bcolors.GREY+"==> GET", url, bcolors.RESET)
        try_cnt = 0
        while True:
            try_cnt += 1
            assert try_cnt < 10
            try:
                r = requests.get(url, headers=headers, timeout=5)
                if not r.ok:
                    print(url)
                    print(r.status_code)
                    print(r.text)
                    print(r.headers)
                    print("=====")
                    time.sleep(3)
                    continue
                break
            except Exception as e:
                print(url)
                print(e)
                print("=====")
                time.sleep(3)
        return r

    def compose_folder_url(self, relative_path, suffix=""):
        return "{}/GetFolderByServerRelativePath(decodedurl='{}'){}".format(
            self.base_url,
            relative_path.replace("'", "''").replace("#", "%23"),
            suffix)

    def GetFolderByServerRelativeUrl(self, rel_path: str, recursive=False, dir_obj=None, depth=0):
        # rel_path = /personal/yyy/Documents/...
        url = self.compose_folder_url(rel_path)
        if dir_obj is None:
            dir_obj = self.http_get(url).json()['d']

        folder_result = self.http_get(url+"/Folders").json()["d"]["results"]
        folder_map = {x["Name"]:x for x in folder_result}
        assert len(folder_map) == len(folder_result), json.dumps(folder_result, indent=2, ensure_ascii=False)
        dir_obj["Folders"] = folder_map

        file_result = self.http_get(url+"/Files").json()["d"]["results"]
        file_map = {x["Name"]:x for x in file_result}
        assert len(file_map) == len(file_result), json.dumps(file_result, indent=2, ensure_ascii=False)
        dir_obj["Files"] = file_map

        if recursive:
            folder_len = len(folder_map)
            for idx, (k, v) in enumerate(folder_map.items()):
                if FLAGS.verbose:
                    print(f'{"="*(depth+1)}> Fetching [{idx+1}/{folder_len}] {v["Name"]}')
                self.GetFolderByServerRelativeUrl(v["ServerRelativeUrl"], recursive, v, depth+1)

        return dir_obj


def print_tree(obj, prefix: str, out_f):
    def readable_size(i):
        i = float(i)
        if i < 1024: return f"[{i:5.1f}B]"
        i /= 1024
        if i < 1024: return f"[{i:5.1f}KiB]"
        i /= 1024
        if i < 1024: return f"[{i:5.1f}MiB]"
        i /= 1024
        return f"[{i:5.1f}GiB]"

    name = obj["Name"]
    if 'Length' in obj:
        name = readable_size(int(obj["Length"])) + " " + name
        out_f.write(prefix+name+"\n")
    else:
        folder_list = natsorted(list(obj["Folders"]), alg=ns.IGNORECASE)
        file_list = natsorted(list(obj["Files"]), alg=ns.IGNORECASE)

        folder_c = len(obj["Folders"])
        file_c = len(obj["Files"])
        out_f.write(prefix+name+"\n")

        if len(prefix) == 0:
            prefix_base = ""
        elif prefix[-4:] == "├── ":
            prefix_base = prefix[:-4] + "│   "
        else:
            prefix_base = prefix[:-4] + "    "

        for idx, folder in enumerate(folder_list):
            if idx == folder_c -1 and file_c == 0:
                print_tree(obj["Folders"][folder], prefix_base + "└── ", out_f)
            else:
                print_tree(obj["Folders"][folder], prefix_base + "├── ", out_f)

        for idx, filee in enumerate(file_list):
            if idx == file_c - 1:
                print_tree(obj["Files"][filee], prefix_base + "└── ", out_f)
            else:
                print_tree(obj["Files"][filee], prefix_base + "├── ", out_f)


def main(argv):
    del argv  # Unused.
    o = OdbShare()
    if FLAGS.login_url is None:
        if FLAGS.cookie_file is None:
            pass
        else:
            with open(FLAGS.cookie_file, "r") as f:
                o.login_via_file(f)
    else:
        if FLAGS.cookie_file is None:
            o.login_via_url(FLAGS.login_url)
        else:
            with open(FLAGS.cookie_file, "w") as f:
                o.login_via_url(FLAGS.login_url, f)

    if FLAGS.tree is not None:
        if FLAGS.login_url is None and FLAGS.cookie_file is None:
            print("Warning: No login info")
            return
        rel_path = o.base_folder + FLAGS.tree
        if FLAGS.tree == '/':
            rel_path = o.base_folder
        dir_obj = o.GetFolderByServerRelativeUrl(rel_path, FLAGS.recursive)
        if FLAGS.output is not None:
            with open(FLAGS.output, "w") as f:
                json.dump(dir_obj, f, indent=2, ensure_ascii=False)
        else:
            print(json.dumps(dir_obj, indent=2, ensure_ascii=False))
        return
    
    if FLAGS.print_tree is not None:
        with open(FLAGS.print_tree, "r") as f:
            obj = json.load(f)
        if FLAGS.output is not None:
            with open(FLAGS.output, "w") as f:
                print_tree(obj, "", f)
        else:
            print_tree(obj, "", sys.stdout)
        return

if __name__ == '__main__':
  app.run(main)

