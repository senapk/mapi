#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import argparse
from typing import List, Optional
from os.path import join, getmtime
import json
from enum import Enum


from subprocess import PIPE

def build_cfg(args) -> str:
    return json.dumps({
                    "markdown": args.markdown, 
                    "tests": args.tests, 
                    "upload": args.upload, 
                    "keep": args.keep, 
                    "required": args.required
                }, indent=4) + "\n"


def load_folder(args) -> str:
    folder = args.folder
    files = os.listdir(folder)
    files = [f for f in files if os.path.isfile(os.path.join(folder, f))] # filter folders
    files = [f for f in files if not f.startswith(".")] # filter .

    #args.markdown = os.path.join(folder, "Readme.md")
    args.markdown = "Readme.md"

    vpl_files = [f for f in files if f.endswith(".vpl") or f.endswith(".tio")]
    if len(vpl_files) > 0:
        args.tests = vpl_files[0]

        # args.tests = os.path.join(folder, vpl_files[0])
    else:
        args.tests = None

    args.upload = []
    # args.upload = [os.path.join(folder, f) for f in files if f.lower().startswith("solver")]

    args.keep = [f for f in files if f.lower().startswith("lib")]
    args.keep += [f for f in files if f.lower().startswith("main")]
    # args.keep = [os.path.join(folder, f) for f in args.keep]

    args.required  = [f for f in files if f.lower().startswith("student")]
    # args.required = [os.path.join(folder, f) for f in args.required]
    
    args.keep  = [f for f in files if f.lower().startswith("data")]
    # args.keep = [os.path.join(folder, f) for f in args.keep]

    return build_cfg(args)


def main():
    parent_basic = argparse.ArgumentParser(add_help=False)
    parent_basic.add_argument('--output', '-o', type=str, help="output file")

    parser = argparse.ArgumentParser(description='Generate .json to define files to be uploaded to moodle')
    subparsers = parser.add_subparsers(title='subcommands', help='help for subcommand.')
    
    parser_load = subparsers.add_parser('load', parents=[parent_basic], help='load using predefined patterns')
    parser_load.add_argument('folder', type=str, help="folder to parse")
    parser_load.set_defaults(func=load_folder)


    parser_build = subparsers.add_parser('build', parents=[parent_basic], help='choose the files to be uploaded')
    parser_build.add_argument('markdown', type=str, help="path of markdown file")
    parser_build.add_argument('-t', '--tests', type=str, help="path of file with vpl content")
    parser_build.add_argument('-u', '--upload', type=str, nargs='*', action='store', help='files to upload')
    parser_build.add_argument('-k', '--keep', type=str, nargs='*', action='store', help='files to upload and keep in execution')
    parser_build.add_argument('-r', '--required', type=str, nargs='*', action='store', help='files to upload and require from student')
    parser_build.set_defaults(func=build_cfg)
    
    args = parser.parse_args()
    json_data = ""
    if len(sys.argv) > 1:
        json_data = args.func(args)
    else:
        parser.print_help()
        exit(1)

    if args.output is None:
        print(json_data)
    else:
        with open(args.output, 'w') as f:
            f.write(json_data)

if __name__ == '__main__':
    main()
