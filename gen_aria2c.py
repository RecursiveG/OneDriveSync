#!/usr/bin/env python3

from absl import app
from absl import flags
from pathlib import Path
import urllib.parse
import json
import dateutil.parser
import datetime

FLAGS = flags.FLAGS
flags.DEFINE_string("current_listing", "tree_metadata.json", "A json file containing uptodate remote listing")
flags.DEFINE_string("aria2c_list", "aria2c.txt", "Output file for Aria2")
flags.DEFINE_string("req_prefix", "", "Only files matches this prefix will be downloaded")
flags.DEFINE_string("cookie_file", "cookie.json", "Containing cookie and base_url")
flags.DEFINE_string("download_path", "download", "Where to store the downloaded files")

#flags.mark_flag_as_required("current_listing")
#flags.mark_flag_as_required("cookie_file")
#flags.mark_flag_as_required("aria2c_list")
#flags.mark_flag_as_required("download_path")

class bcolors:
    GREY = '\033[38;5;242m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    RESET = '\033[0m'

def file_content_url(base_url, relative_path):
    idx = base_url.find("/personal/")
    return base_url[:idx] + urllib.parse.quote(relative_path) + "?download=1"
    # return "{}/GetFileByServerRelativePath(decodedurl='{}')/$value".format(
    #     base_url,
    #     relative_path.replace("'", "''").replace("#", "%23")
    # )

def startwith(s, prefix):
    return s[:len(prefix)] == prefix

def gen(obj, local_path: Path, aria2c_f, req_prefix:str, base_url:str):
    if "Length" in obj:
        rel_path = obj["ServerRelativeUrl"]
        
        while True:
            if not startwith(rel_path, req_prefix):
                #print(f"{bcolors.GREY}SKIP:PREFIX {rel_path}{bcolors.RESET}")
                return

            if not local_path.exists():
                print(f"{bcolors.GREEN}NEW {rel_path}{bcolors.RESET}")
                break

            st = local_path.stat()
            expect_mtime = dateutil.parser.parse(obj["TimeLastModified"])
            expect_size = int(obj["Length"])
            actual_mtime = datetime.datetime.fromtimestamp(st.st_mtime, expect_mtime.tzinfo)
            # if st.st_size == expect_size and actual_mtime >= expect_mtime:
            if st.st_size == expect_size:
                #print(f"{bcolors.GREY}SKIP:SAME_SIZE {rel_path}{bcolors.RESET}")
                return

            print(f"{bcolors.YELLOW}UPDATE {rel_path}{bcolors.RESET}")
            print(f"{bcolors.GREY}ServerTime={expect_mtime} LocalTime={actual_mtime} ServerSize={expect_size} LocalSize={st.st_size}{bcolors.RESET}")
            break

        url = file_content_url(base_url, rel_path)
        aria2c_f.write(url+"\n")
        aria2c_f.write(f'  out={obj["Name"]}\n')
        aria2c_f.write(f'  dir={str(local_path.parent)}\n\n')
    else:
        for k,v in obj["Files"].items():
            lp = local_path / v["Name"]
            gen(v, lp, aria2c_f, req_prefix, base_url)
        for k,v in obj["Folders"].items():
            lp = local_path / v["Name"]
            gen(v, lp, aria2c_f, req_prefix, base_url)

def main(argv):
    del argv  # Unused.
    with open(FLAGS.current_listing, "r") as f:
        cur = json.load(f)
    with open(FLAGS.cookie_file, "r") as f:
        cookie_obj = json.load(f)
    with open(FLAGS.aria2c_list, "w") as output_f:
        gen(cur, Path(FLAGS.download_path), output_f, cookie_obj["base_folder"]+FLAGS.req_prefix,
            cookie_obj["base_url"])
    print(f'aria2c --header \'Cookie: {cookie_obj["cookie_fed_auth"]}\' ' +
          f'--input-file {FLAGS.aria2c_list} --split=1 --remote-time '+
          '--save-session=aria2c_session.txt --save-session-interval=10 --allow-overwrite true')

if __name__ == '__main__':
  app.run(main)
  
