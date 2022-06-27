#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse
from typing import List, Optional
import json
from enum import Enum


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
    def __init__(self, title: str, description: str):
        self.title: str = title
        self.description: str = description
        self.upload: List[JsonFile] = []
        self.keep: List[JsonFile] = []
        self.required: List[JsonFile] = []

    def add_file(self, ftype: JsonFileType, exec_file: str, rename=""):
        with open(exec_file) as f:
            file_name = rename if rename != "" else exec_file.split(os.sep)[-1]
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



def build(args) -> JsonVPL:
    with open(args.description) as f:
        description = f.read()
    jvpl = JsonVPL(args.title, description)
    if args.tests:
        jvpl.add_file(JsonFileType.UPLOAD, args.tests, "vpl_evaluate.cases")
    if args.keep is not None:
        for entry in args.keep:
            jvpl.add_file(JsonFileType.KEEP, entry)
    if args.upload is not None:
        for entry in args.upload:
            jvpl.add_file(JsonFileType.UPLOAD, entry)
    if args.required:
        file, filename = args.required
        if file != "":
            jvpl.add_file(JsonFileType.REQUIRED, file, filename)
    return jvpl
    

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('title', type=str, help="title")
    parser.add_argument('description', type=str, help="path to .html file with description")
    parser.add_argument('-t', '--tests', type=str, help="path of file with vpl cases")
    parser.add_argument('-u', '--upload', type=str, nargs='*', action='store', help='files to upload')
    parser.add_argument('-k', '--keep', type=str, nargs='*', action='store', help='files to upload and keep in execution')
    parser.add_argument('-r', '--required', nargs=2, metavar=('required', 'rename'), type=str, help='file to require from student')
    parser.add_argument('-o', '--output', type=str, help="path of output file")
    args = parser.parse_args()

    jvpl = build(args)
    content = str(jvpl) + '\n'
    if args.output is None:
        print(content)
    else:
        with open(args.output, "w") as f:
            f.write(content)


if __name__ == '__main__':
    main()

