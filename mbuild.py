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

def extract_title(readme_file):
    title = open(readme_file).read().split("\n")[0]
    parts = title.split("\n")
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
    #hook = os.path.abspath(input_file).split(os.sep)[-2]
    #lines = open(input_file).read().split("\n")
    #header = lines[0]
    #title = "@" + hook + " " + " ".join([word for word in header.split(" ") if not word.startswith("#")])
    #content = "\n".join(lines[1:])
    #tags = [word for word in header.split(" ") if word.startswith("#") and word.count("#") != len(word)]
    #temp_input = tempfile.mktemp(suffix=".md")

    #with open(temp_input, "w") as f:
    #    f.write("## " + title + " " + " ".join(tags) + "\n" + content)
    title = extract_title(input_file)
    fulltitle = title.replace('!', '\\!').replace('?', '\\?')
    cmd = ["pandoc", input_file, '--css', CssStyle.get_file(), '--metadata', 'pagetitle=' + fulltitle, '-s', '-o', output_file]
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



def mapi_build(title, description_file, tests_file, required_files, keep_files, upload_files, output_file: str):
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
    with open(output_file, "w") as f:
        f.write(str(jvpl) + "\n")






def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-m', '--markdown', type=str, help="readme.md with title and content")
    parser.add_argument('-t', '--tests', type=str, help="path of file with vpl content")
    parser.add_argument('-u', '--upload', type=str, nargs='*', default=[], action='store', help='files to upload')
    parser.add_argument('-k', '--keep', type=str, nargs='*', default=[], action='store', help='files to upload and keep in execution')
    parser.add_argument('-r', '--required', type=str, nargs='*', default=[], action='store', help='files to upload and require from student')
    
    parser.add_argument('-o', '--output', type=str, help="path of output file")
    parser.add_argument('-s', '--save', type=str, help="path of the config file")
    parser.add_argument('-l', '--load', type=str, help="path of the config file")
    parser.add_argument('-f', '--folder', type=str, help="path of the folder to execute default load")
    
    
    args = parser.parse_args()
    if (args.markdown is None and args.load is None and args.folder is None) or (args.output is None and args.save is None):
        print("You should inform [--markdown or --load or --folder] and [--output or --save]")
        exit(1)

    if args.save:
        with open(args.save, "w") as f:
            f.write(json.dumps({
                        "markdown": args.markdown, 
                        "tests": args.tests, 
                        "upload": args.upload, 
                        "keep": args.keep, 
                        "required": args.required
                    }, indent=4))

    if args.load:
        with open(args.folder) as f:
            config = json.load(f)
            if config["markdown"]:
                args.markdown = config["markdown"]
            if config["tests"]:
                args.tests = config["tests"]
            args.upload = config["upload"]
            args.keep = config["keep"]
            args.required = config["required"]
    
    if args.folder is not None:
        files = os.listdir(args.default)
        files = [f for f in files if os.path.isfile(f)] # filter folders
        files = [f for f in files if not f.startswith(".")] # filter .
        args.markdown = "Readme.md"
        args.tests = next([f for f in files if f.endswith(".vpl")], None)
        args.upload  = [f for f in files if f.lower().startswith("solver")]
        args.upload += [f for f in files if f.lower().startswith("lib")]
        args.upload += [f for f in files if f.lower().startswith("main")]
        args.required  = [f for f in files if f.lower().startswith("student")]
        args.keep  = [f for f in files if f.lower().startswith("data")]


    if args.output:
        temp_dir = tempfile.mkdtemp()
        desc_file = temp_dir + "/t.html"
        generate_html(args.markdown, desc_file, True)
        title = extract_title(args.markdown)
        mapi_build(title, desc_file, args.tests, args.required, args.keep, args.upload, args.output)


if __name__ == '__main__':
    main()
