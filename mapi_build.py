#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import os
import tempfile
import shutil
import argparse
import subprocess
from typing import List, Optional
from os.path import join, getmtime
import json
from enum import Enum

import subprocess
from subprocess import PIPE

default_config_save_file = ".mapirc.json"

def extract_title(readme_file):
    title = open(readme_file).read().split("\n")[0]
    parts = title.split(" ")
    if parts[0].count("#") == len(parts[0]):
        del parts[0]
    title = " ".join(parts)
    return title

class CssStyle:
    data = "body,li{color:#000}body{line-height:1.4em;max-width:42em;padding:1em;margin:auto}li{margin:.2em 0 0;padding:0}h1,h2,h3,h4,h5,h6{border:0!important}h1,h2{margin-top:.5em;margin-bottom:.5em;border-bottom:2px solid navy!important}h2{margin-top:1em}code,pre{border-radius:3px}pre{overflow:auto;background-color:#f8f8f8;border:1px solid #2f6fab;padding:5px}pre code{background-color:inherit;border:0;padding:0}code{background-color:#ffffe0;border:1px solid orange;padding:0 .2em}a{text-decoration:underline}ol,ul{padding-left:30px}em{color:#b05000}table.text td,table.text th{vertical-align:top;border-top:1px solid #ccc;padding:5px}"
    path = None
    @staticmethod
    def get_file():
        if CssStyle.path is None:
            CssStyle.path = tempfile.mktemp(suffix=".css")
            with open(CssStyle.path, "w") as f:
                f.write(CssStyle.data)
        return CssStyle.path

def generate_html(input_file: str, output_file: str, enable_latex: bool):
    title = extract_title(input_file)
    fulltitle = title.replace('!', '\\!').replace('?', '\\?')
    cmd = ["pandoc", input_file, '--css', CssStyle.get_file(), '--metadata', 'pagetitle=' + fulltitle,
           '-s', '-o', output_file]
    if enable_latex:
        cmd.append("--mathjax")
    try:
        p = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        stdout, stderr = p.communicate()
        if stdout != "" or stderr != "":
            print(stdout)
            print(stderr)
    except Exception as e:
        print("Erro no comando pandoc:", e)
        exit(1)


# Format used to send additional files to VPL
class JsonFile:
    def __init__(self, name: str, contents: str):
        self.name: str = name
        self.contents: str = contents
        self.encoding: int = 0

    def __str__(self):
        return self.name + ":" + self.contents + ":" + str(self.encoding)


class JsonFileType(Enum):
    UPLOAD = 1
    KEEP = 2
    REQUIRED = 3


class JsonVPL:
    def __init__(self, title: str, description: str, tests: str = ""):
        self.title: str = title
        self.description: str = description
        self.upload: List[JsonFile] = [JsonFile("vpl_evaluate.cases", tests)]
        self.keep: List[JsonFile] = []
        self.required: List[JsonFile] = []
        
    def add_file(self, exec_file, ftype: JsonFileType):
        with open(exec_file) as f:
            file_name = exec_file.split(os.sep)[-1]
            jfile = JsonFile(file_name, f.read())
            if ftype == JsonFileType.UPLOAD:
                self.upload.append(jfile)
            elif ftype == JsonFileType.KEEP:
                self.keep.append(jfile)
            else:
                self.required.append(jfile)

    def to_json(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    def __str__(self):
        return self.to_json()



def mapi_build(title, description_file, tests_file, required_files, keep_files, upload_files):
    with open(description_file) as f:
            description = f.read()
    with open(tests_file) as f:
        tests = f.read()
    jvpl = JsonVPL(title, description, tests)
    for entry in keep_files:
        jvpl.add_file(entry, JsonFileType.KEEP)
    for entry in upload_files:
        jvpl.add_file(entry, JsonFileType.UPLOAD)
    for entry in required_files:
        jvpl.add_file(entry, JsonFileType.REQUIRED)
    return str(jvpl) + "\n"


def make_config_content(args) -> str:
    return json.dumps({
                    "markdown": args.markdown, 
                    "tests": args.tests, 
                    "upload": args.upload, 
                    "keep": args.keep, 
                    "required": args.required
                }, indent=4) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cfgfile", type=str, help="file with configuration")
    parser.add_argument('--output', '-o', type=str, help="path of output file")
    parser.add_argument('--savehtml', '-s', type=str, help="store html generated file")
    
    args = parser.parse_args()
    with open(args.cfgfile) as f:
        config = json.load(f)
    
    dir_name = os.path.dirname(args.cfgfile)
    config["markdown"] = os.path.join(dir_name, config["markdown"])
    config["tests"] = os.path.join(dir_name, config["tests"])
    config["upload"] = [os.path.join(dir_name, entry) for entry in config["upload"]]
    config["keep"] = [os.path.join(dir_name, entry) for entry in config["keep"]]
    config["required"] = [os.path.join(dir_name, entry) for entry in config["required"]]

    desc_file = args.savehtml
    if desc_file is None:
        temp_dir = tempfile.mkdtemp()
        desc_file = temp_dir + "/q.html"
    generate_html(config["markdown"], desc_file, True)
    title = extract_title(config["markdown"])
    content = mapi_build(title, desc_file, 
                config["tests"], config["required"], config["keep"], config["upload"])
    if args.output is None:
        print(content)
    else:
        with open(args.output, "w") as f:
            f.write(content)


if __name__ == '__main__':
    main()
