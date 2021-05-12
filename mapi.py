#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Optional, Any, Dict
from bs4 import BeautifulSoup
import mechanicalsoup
import json
import os
import argparse
import sys
import getpass  # get pass
import pathlib
import requests


class URLHandler:
    def __init__(self):
        credentials: Credentials = Credentials.load_credentials()
        self._url_base: str = credentials.url
        self.course_id: str = credentials.course

    def __str__(self):
        return self._url_base + ":" + self.course_id

    def base(self):
        return self._url_base

    def course(self):
        return self._url_base + "/course/view.php?id=" + self.course_id

    def login(self):
        return self._url_base + '/login/index.php'

    def delete_action(self):
        return self._url_base + "/course/mod.php"

    def delete_vpl(self, qid: int):
        return self.delete_action() + "?sr=0&delete=" + str(qid)

    def keep_files(self, qid: int):
        return self._url_base + '/mod/vpl/forms/executionkeepfiles.php?id=' + str(qid)

    def new_vpl(self, section: int):
        return self._url_base + "/course/modedit.php?add=vpl&type=&course=" + self.course_id + "&section=" + \
               str(section) + "&return=0&sr=0 "

    def view_vpl(self, qid: int):
        return self._url_base + '/mod/vpl/view.php?id=' + str(qid)

    def update_vpl(self, qid: int):
        return self._url_base + '/course/modedit.php?update=' + str(qid)

    def new_test(self, qid: int):
        return self._url_base + "/mod/vpl/forms/testcasesfile.php?id=" + str(qid) + "&edit=3"

    # def test_save(self, id: int):
    #     return self._url_base + "/mod/vpl/forms/testcasesfile.json.php?id=" + str(id) + "&action=save"

    def execution_files(self, qid: int):
        return self._url_base + '/mod/vpl/forms/executionfiles.json.php?id=' + str(qid) + '&action=save'

    def required_files(self, qid: int):
        return self._url_base + '/mod/vpl/forms/requiredfiles.json.php?id=' + str(qid) + '&action=save'

    def execution_options(self, qid: int):
        return self._url_base + "/mod/vpl/forms/executionoptions.php?id=" + str(qid)

    @staticmethod
    def parse_id(url) -> str:
        return url.split("id=")[1].split("&")[0]

    @staticmethod
    def is_vpl_url(url) -> bool:
        return '/mod/vpl/view.php?id=' in url


class Credentials:
    config_path = None
    instance = None

    def __init__(self, username: str, password: str, url: str, course: str, remote: str):
        self.username = username
        self.password = password
        self.url = url
        self.course = course
        self.remote = remote

    @staticmethod
    def load_credentials():
        if Credentials.instance is not None:
            return Credentials.instance
        config = {}  # ["username"] ["url"] ["course"] ["password"]
        if Credentials.config_path is None:
            Credentials.config_path = str(pathlib.Path.home()) + os.sep + '.mapirc'
        mapirc = Credentials.config_path
        try:
            if not os.path.isfile(mapirc):
                raise FileNotFoundError
            with open(mapirc) as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print("Create a file with your access credentials: " + mapirc)
            print(e)
            exit(1)

        if "password" not in config or config["password"] is None:
            config["password"] = getpass.getpass()
        if "remote" not in config:
            config["remote"] = ""
        Credentials.instance = Credentials(config["username"], config["password"], config["url"], config["course"],
                                           config["remote"])

        return Credentials.instance

    def __str__(self):
        return self.username + ":" + self.password + ":" + self.url + ":" + self.course


# Format used to send additional files to VPL
class JsonFile:
    def __init__(self, name: str, contents: str):
        self.name: str = name
        self.contents: str = contents
        self.encoding: int = 0

    def __str__(self):
        return self.name + ":" + self.contents + ":" + str(self.encoding)


class JsonVPL:
    test_cases_file_name = "vpl_evaluate.cases"

    def __init__(self, title: str, description: str, tests: Optional[str] = None):
        self.title: str = title
        self.description: str = description
        self.executionFiles: List[JsonFile] = []
        self.requiredFile: Optional[JsonFile] = None
        self.keep_size: int = 0
        if tests is not None:
            self.set_test_cases(tests)

    def set_test_cases(self, tests: str):
        file = next((file for file in self.executionFiles if file.name == JsonVPL.test_cases_file_name), None)
        if file is not None:
            file.contents = tests
            return
        self.executionFiles.append(JsonFile("vpl_evaluate.cases", tests))

    def to_json(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    def __str__(self):
        return self.to_json()


class JsonVplLoader:
    @staticmethod
    def _load_from_string(text: str) -> JsonVPL:
        data = json.loads(text)
        vpl = JsonVPL(data["title"], data["description"])
        for f in data["executionFiles"]:
            vpl.executionFiles.append(JsonFile(f["name"], f["contents"]))
        if data["requiredFile"] is not None:
            vpl.requiredFile = JsonFile(data["requiredFile"]["name"], data["requiredFile"]["contents"])
        if "keep_size" not in data:
            vpl.keep_size = 0
        else:
            vpl.keep_size = data["keep_size"]
        return vpl

    # remote is like https://raw.githubusercontent.com/qxcodefup/moodle/master/base/
    @staticmethod
    def load(target: str, remote: bool) -> JsonVPL:
        if remote:
            remote_url = Credentials.load_credentials().remote
            url = os.path.join(remote_url, target + "/mapi.json")
            print("    - Loading from remote")
            response = requests.get(url, allow_redirects=True)
            if response.text != "404: Not Found":
                return JsonVplLoader._load_from_string(response.text)
        if os.path.isdir(target):
            target = os.path.join(target, "mapi.json")
        if os.path.isfile(target):
            with open(target, encoding='utf-8') as f:
                return JsonVplLoader._load_from_string(f.read())
        print("fail: invalid target " + target)
        exit(1)


# to print loading bar
class Bar:
    @staticmethod
    def open():
        print("    - [ ", end='', flush=True)

    @staticmethod
    def send(text: str, fill: int = 0):
        print(text.center(fill, '.') + " ", end='', flush=True)

    @staticmethod
    def done(text=""):
        print("] DONE" + text)

    @staticmethod
    def fail(text=""):
        print("] FAIL" + text)


class StructureItem:
    def __init__(self, section: int, qid: int, title: str):
        self.section: int = section
        self.id: int = qid
        self.title: str = title
        self.label: str = StructureItem.parse_label(title)

    def __str__(self):
        return "section={}, id={}, label={}, title={}".format(self.section, self.id, self.label, self.title)

    # "@123 ABCDE..." -> 123
    # "" se não tiver label
    @staticmethod
    def parse_label(title) -> str:
        ttl_splt = title.strip().split(" ")
        for ttl in ttl_splt:
            if ttl[0] == '@':
                return ttl[1:]
        return ""


# save course structure: sections, ids, titles
class Structure:
    def __init__(self, section_item_list: List[List[StructureItem]], section_labels: List[str]):
        self.section_item_list: List[List[StructureItem]] = section_item_list
        self.section_labels: List[str] = section_labels
        # redundant info
        self.ids_dict: Dict[int, StructureItem] = self._make_ids_dict()

    def add_entry(self, section: int, qid: int, title: str):
        if qid not in self.ids_dict.keys():
            item = StructureItem(section, qid, title)
            self.section_item_list[section].append(item)
            self.ids_dict[qid] = item

    def search_by_label(self, label: str, section: Optional[int] = None) -> List[StructureItem]:
        if section is None:
            return [item for item in self.ids_dict.values() if item.label == label]
        return [item for item in self.section_item_list[section] if item.label == label]

    def get_id_list(self, section: Optional[int] = None) -> List[int]:
        if section is None:
            return list(self.ids_dict.keys())
        return [item.id for item in self.section_item_list[section]]

    def get_itens(self, section: Optional[int] = None) -> List[StructureItem]:
        if section is None:
            return list(self.ids_dict.values())
        return self.section_item_list[section]

    def get_item(self, qid: int) -> StructureItem:
        return self.ids_dict[qid]

    def has_id(self, qid: int, section: Optional[int] = None) -> bool:
        if section is None:
            return qid in self.ids_dict.keys()
        return qid in self.get_id_list(section)

    def rm_item(self, qid: int):
        if self.has_id(qid):
            item = self.ids_dict[qid]
            del self.ids_dict[qid]
            new_section_list = [item for item in self.section_item_list[item.section] if item.id != qid]
            self.section_item_list[item.section] = new_section_list

    def get_number_of_sections(self):
        return len(self.section_labels)

    def _make_ids_dict(self) -> Dict[int, StructureItem]:
        entries: Dict[int, StructureItem] = {}
        for item_list in self.section_item_list:
            for item in item_list:
                entries[item.id] = item
        return entries


class StructureLoader:
    @staticmethod
    def load() -> Structure:
        api = MoodleAPI()
        print("- Loading course structure")
        Bar.open()
        Bar.send("load")
        while True:
            try:
                api.open_url(api.urlHandler.course())
                break
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                Bar.send("!", 0)
                api = MoodleAPI()

        Bar.send("parse")
        soup = api.browser.page #BeautifulSoup(api.browser.response().read(), 'html.parser')
        topics = soup.find('ul', {'class:', 'topics'})
        section_item_list = StructureLoader._make_entries_by_section(soup, topics.contents)
        section_labels: List[str] = StructureLoader._make_section_labels(topics.contents)
        Bar.done()
        print(soup.title.string)
        return Structure(section_item_list, section_labels)

    @staticmethod
    def _make_section_labels(childrens) -> List[str]:
        return [section['aria-label'] for section in childrens]

    @staticmethod
    def _make_entries_by_section(soup, childrens) -> List[List[StructureItem]]:
        output: List[List[StructureItem]] = []
        for section_index, section in enumerate(childrens):
            comp = ' > div.content > ul > li > div > div.mod-indent-outer > div > div.activityinstance > a'
            activities = soup.select('#' + section['id'] + comp)
            section_entries: List[StructureItem] = []
            for activity in activities:
                if not URLHandler.is_vpl_url(activity['href']):
                    continue
                qid: int = int(URLHandler.parse_id(activity['href']))
                title: str = activity.get_text().replace(' Laboratório Virtual de Programação', '')
                section_entries.append(StructureItem(section_index, qid, title))
            output.append(section_entries)
        return output


# formatting structure to list
class Viewer:
    def __init__(self, show_url: bool):
        self.url_handler = URLHandler()
        self.structure = StructureLoader.load()
        self.show_url = show_url

    def list_section(self, index: int):
        print("- %02d. %s" % (index, self.structure.section_labels[index]))
        for item in self.structure.get_itens(section=index):
            if self.show_url:
                url = self.url_handler.view_vpl(item.id)
                print('    - %d: [%s](%s)' % (item.id, item.title, url))
            else:
                print('    - %d: %s' % (item.id, item.title))

    def list_all(self):
        for i in range(self.structure.get_number_of_sections()):
            self.list_section(i)


class MoodleAPI:
    default_timeout: int = 10

    def __init__(self):
        self.credentials = Credentials.load_credentials()
        self.urlHandler = URLHandler()
        self.browser = mechanicalsoup.StatefulBrowser(user_agent='MechanicalSoup')
        self.browser.set_user_agent('Mozilla/5.0')
        self._login()

    def open_url(self, url: str, data_files: Optional[Any] = None):
        if MoodleAPI.default_timeout != 0:
            if data_files is None:
                self.browser.open(url, timeout=MoodleAPI.default_timeout)
            else:
                self.browser.open(url, timeout=MoodleAPI.default_timeout, data=data_files)
        else:
            if data_files is None:
                self.browser.open(url)
            else:
                self.browser.open(url, data=data_files)

    def _login(self):
        self.browser.open(self.urlHandler.login())
        self.browser.select_form(nr=0)
        self.browser['username'] = self.credentials.username
        self.browser['password'] = self.credentials.password
        self.browser.submit_selected()
        if self.browser.get_url() == self.urlHandler.login():
            print("Erro de login, verifique login e senha")
            exit(0)

    def delete(self, qid: int):
        Bar.send("load")
        self.open_url(self.urlHandler.delete_vpl(qid))
        Bar.send("submit")
        self.browser.select_form(nr=0)
        self.browser.submit_selected()

    def download(self, vplid: int) -> JsonVPL:
        url = self.urlHandler.view_vpl(vplid)

        Bar.send("open")
        self.open_url(url)
        Bar.send("parse")
        soup = self.browser.page
        arqs = soup.findAll('h4', {'id': lambda value: value and value.startswith("fileid")})
        title = soup.find('a', {'href': self.browser.get_url()}).get_text()
        descr = soup.find('div', {'class': 'box py-3 generalbox'}).find('div', {'class': 'no-overflow'}).get_text()

        vpl = JsonVPL(title, descr)
        for arq in arqs:
            cont = soup.find('pre', {'id': 'code' + arq.get('id')})
            file = JsonFile(name=arq.get_text(), contents=cont.get_text())
            if arq.find_previous_sibling('h2').get_text() == "Arquivos requeridos":
                vpl.required = file
            else:
                vpl.executionFiles.append(file)
        return vpl

    def set_duedate(self, duedate: str):
        year, month, day, hour, minute = duedate.split(":")

        self.browser["duedate[year]"] = year
        self.browser["duedate[month]"] = str(int(month)) # tranform 05 to 5
        self.browser["duedate[day]"] = str(int(day))
        self.browser["duedate[hour]"] = str(int(hour))
        self.browser["duedate[minute]"] = str(int(minute))


    def send_basic_info(self, url: str, vpl: JsonVPL, duedate: Optional[str] = None) -> int:
        Bar.send("1")
        self.open_url(url)

        Bar.send("2")

        self.browser.select_form(nr=0)
        self.browser['name'] = vpl.title
        self.browser['introeditor[text]'] = vpl.description
        if duedate is None:
            self.browser["duedate[enabled]"] = False
        else:
            self.browser["duedate[enabled]"] = True
            self.set_duedate(duedate)

        Bar.send("3")
        self.browser.form.choose_submit("submitbutton")
        self.browser.submit_selected()
#        self.browser.submit(name="submitbutton")
        qid = URLHandler.parse_id(self.browser.get_url())
        return int(qid)

    def _send_vpl_files(self, url: str, vpl_files: List[JsonFile]):
        params = {'files': vpl_files, 'comments': ''}
        files = json.dumps(params, default=self.__dumper, indent=2)
        self.open_url(url, files)

    def set_keep(self, qid: int, keep_size: int):
        self.open_url(self.urlHandler.keep_files(qid))
        self.browser.select_form(nr=0)
        for index in range(4, 4 + keep_size):
            self.browser["keepfile" + str(index)] = "1"
        self.browser.submit_selected()

    def send_files(self, vpl: JsonVPL, qid: int):
        self._send_vpl_files(self.urlHandler.execution_files(qid), vpl.executionFiles)
        if vpl.requiredFile:
            self._send_vpl_files(self.urlHandler.required_files(qid), [vpl.requiredFile])

    def set_execution_options(self, qid):
        self.open_url(self.urlHandler.execution_options(qid))

        self.browser.select_form(nr=0)

        self.browser['run'] = "1"
        self.browser['debug'] = "1"
        self.browser['evaluate'] = "1"
        # self.browser.submit()
        #
        # self.browser.select_form(action='executionoptions.php')
        self.browser['automaticgrading'] = "1"
        self.browser.submit_selected()
        Bar.send("ok")

    @staticmethod
    def __dumper(obj):
        try:
            return obj.to_json()
        except AttributeError:
            return obj.__dict__


class Add:
    def __init__(self, section: Optional[int], duedate: Optional[str], op_local: bool, op_skip: bool, op_force: bool,
                 structure=None):
        self.section: Optional[int] = 0 if section is None else section
        self.duedate = duedate
        self.remote: bool = not op_local
        self.op_ignore: bool = op_skip
        self.op_update: bool = not op_force
        if structure is None:
            self.structure = StructureLoader.load()
        else:
            self.structure = structure

    def send_basic(self, api: MoodleAPI, vpl: JsonVPL, url: str) -> int:
        Bar.send("description")
        while True:
            try:
                qid = api.send_basic_info(url, vpl, self.duedate)
                break
            except Exception as _e:
                print(type(_e)) # debug
                print(_e)
                api = MoodleAPI()
                Bar.send("!", 0)
        return qid

    @staticmethod
    def set_keep(api: MoodleAPI, qid: int, keep_size: int):
        Bar.send("setkeep")
        while True:
            try:
                api.set_keep(qid, keep_size)
                break
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                api = MoodleAPI()
                Bar.send("!", 0)

    @staticmethod
    def update_extra(api: MoodleAPI, vpl: JsonVPL, qid: int):
        Bar.send("enable")
        while True:
            try:
                api.set_execution_options(qid)
                break
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                api = MoodleAPI()
                Bar.send("!", 0)

        Bar.send("send")
        while True:
            try:
                api.send_files(vpl, qid)
                break
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                api = MoodleAPI()
                Bar.send("!", 0)

    def apply_action(self, vpl: JsonVPL, item: Optional[StructureItem]):
        api = MoodleAPI()  # creating new browser for each attempt to avoid some weird timeout

        if item is not None and self.op_update:
            print("    - Updating: Label found in " + str(item.id) + ": " + item.title)
            url = api.urlHandler.update_vpl(item.id)
            Bar.open()
            self.send_basic(api, vpl, url)
            self.update_extra(api, vpl, item.id)
            self.set_keep(api, item.id, vpl.keep_size)
            Bar.done()
        elif item is not None and self.op_ignore:
            print("    - Skipping: Label found in " + str(item.id) + ": " + item.title)
        else:
            print("    - Creating: New entry with title: " + vpl.title)
            Bar.open()
            url = api.urlHandler.new_vpl(self.section)
            qid = self.send_basic(api, vpl, url)
            Bar.send(str(qid))
            self.update_extra(api, vpl, qid)
            self.set_keep(api, qid, vpl.keep_size)
            self.structure.add_entry(self.section, qid, vpl.title)
            Bar.done()

    def add_target(self, target: str):
        print("- Target: " + target)
        vpl = JsonVplLoader.load(target, self.remote)
        itens_label_match = self.structure.search_by_label(StructureItem.parse_label(vpl.title), self.section)
        item = None if len(itens_label_match) == 0 else itens_label_match[0]
        while True:
            try:
                self.apply_action(vpl, item)
                return
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                Bar.fail(":" + str(_e))


class Actions:

    @staticmethod
    def add(args):
        action = Add(args.section, args.duedate, args.local, args.skip, args.force)
        for target in args.targets:
            action.add_target(target)

    @staticmethod
    def define(args):
        if args.upload is None:
            args.upload = []
        if args.keep is None:
            args.keep = []
        data = {"keep": args.keep, "upload": args.upload, "required": args.required}
        with open(".mapi", "w") as f:
            f.write(json.dumps(data, indent=4) + "\n")
            print("file .mapi created")

    @staticmethod
    def update(args):
        args_ids: List[int] = args.ids
        args_section: List[int] = args.section
        args_all: bool = args.all
        args_exec_options = args.exec_options
        args_remote = args.remote
        #args_duedate = args.duedate
        args_labels: List[str] = args.labels

        item_list: List[StructureItem] = []
        structure = StructureLoader.load()

        if args_all:
            item_list = structure.get_itens()
        elif args_section is not None and len(args_section) > 0:
            for section in args_section:
                item_list += structure.get_itens(section)
        elif args_ids:
            for qid in args_ids:
                if structure.has_id(qid):
                    item_list.append(structure.get_item(qid))
                else:
                    print("    - id not found: ", qid)
        if args_labels:
            for label in args_labels:
                item_list += [item for item in structure.get_itens() if item.label == label]
        
        if args_remote:
            i = 0
            while i < len(item_list):
                item = item_list[i]
                action = Add(item.section, None, True, False, True, structure)
                action.add_target(item.label)
                i += 1
        
        # if args_duedate:
        #     i = 0
        #     while i < len(item_list):
        #         item = item_list[i]
        #         action = Add(item.section, args_duedate, True, False, True, structure)
        #         action.add_target(item.label)
        #         i += 1

        if args_exec_options:
            i = 0
            while i < len(item_list):
                item = item_list[i]
                print("- Change execution options for " + str(item.id))
                print("    -", str(item))
                try:
                    Bar.open()
                    api = MoodleAPI()
                    api.set_execution_options(item.id)
                    i += 1
                    Bar.done()
                except Exception as _e:
                    print(type(_e))  # debug
                    print(_e)
                    Bar.fail(": timeout")

    @staticmethod
    def down(args):
        args_ids: List[int] = args.ids
        args_section: Optional[int] = args.section
        args_all: bool = args.all
        args_output: str = args.output

        item_list: List[StructureItem] = []
        api = MoodleAPI()
        structure = StructureLoader.load()

        if args_all:
            item_list = structure.get_itens()
        elif args_section:
            item_list = structure.get_itens(args_section)
        elif args_ids:
            for qid in args_ids:
                if structure.has_id(qid):
                    item_list.append(structure.get_item(qid))
                else:
                    print("    - id not found: ", qid)

        i = 0
        while i < len(item_list):
            item = item_list[i]
            path = os.path.normpath(os.path.join(args_output, str(item.id) + ".json"))
            print("- Saving id " + str(item.id))
            print("    -", str(item))
            try:
                Bar.open()
                data = api.download(item.id)
                open(path, "w").write(str(data))
                i += 1
                Bar.done(": " + path)
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                Bar.fail(": timeout")

    @staticmethod
    def rm(args):
        args_ids: List[int] = args.ids
        args_section: Optional[int] = args.section
        args_all: bool = args.all

        item_list: List[StructureItem] = []
        structure = StructureLoader.load()

        if args_all:
            item_list = structure.get_itens()
        elif args_section:
            item_list = structure.get_itens(args_section)
        elif args_ids:
            for qid in args_ids:
                if structure.has_id(qid):
                    item_list.append(structure.get_item(qid))
                else:
                    print("    - id not found", qid)

        i = 0
        while i < len(item_list):
            api = MoodleAPI()
            item = item_list[i]
            print("- Removing id " + str(item.id))
            print("    -", str(item))
            try:
                Bar.open()
                api.delete(item.id)
                i += 1
                Bar.done()
            except Exception as _e:
                print(type(_e))  # debug
                print(_e)
                Bar.fail(": timeout")

    @staticmethod
    def list(args):
        args_section: Optional[int] = args.section
        args_url: bool = args.url
        viewer = Viewer(args_url)
        if args_section is not None:
            viewer.list_section(args_section)
        else:
            viewer.list_all()


def main():
    # p_config = argparse.ArgumentParser(add_help=False)
    # p_config.add_argument('-c', '--config', type=str, help="config file path")

    p_section = argparse.ArgumentParser(add_help=False)
    p_section.add_argument('-s', '--section', metavar='SECTION', type=int, help="")

    p_out = argparse.ArgumentParser(add_help=False)
    p_out.add_argument('-o', '--output', type=str, default='.', action='store', help='Output directory')

    desc = ("Gerenciar vpls do moodle de forma automatizada\n"
            "Use \"./mapi comando -h\" para obter informações do comando específico.\n\n"
            )

    parser = argparse.ArgumentParser(prog='mapi.py', description=desc, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-c', '--config', type=str, help="config file path")
    parser.add_argument('-t', '--timeout', type=int, help="max timeout to way moodle response")

    subparsers = parser.add_subparsers(title="subcommands", help="help for subcommand")

    parser_add = subparsers.add_parser('add', parents=[p_section], help="add")
    parser_add.add_argument('targets', type=str, nargs='+', action='store', help='file, folder ou remote with lab')
    parser_add.add_argument('-l', '--local', action='store_true', help="Use local json instead remote repository")
    parser_add.add_argument('-d', '--duedate', type=str, default=None, action='store', help='duedate yyyy:m:d:h:m')
    group_add = parser_add.add_mutually_exclusive_group()
    group_add.add_argument('--skip', action='store_true', help="Skip insertion if found same label in section")
    group_add.add_argument('--force', action='store_true', help="Force insertion if found same label in section")
    parser_add.set_defaults(func=Actions.add)

    parser_list = subparsers.add_parser('list', parents=[p_section], help='list')
    parser_list.add_argument('-u', '--url', action='store_true', help="Show vpl urls")
    parser_list.set_defaults(func=Actions.list)

    parser_rm = subparsers.add_parser('rm', help="Remove from Moodle")
    group_rm = parser_rm.add_mutually_exclusive_group()
    group_rm.add_argument('-i', '--ids', type=int, metavar='ID', nargs='*', action='store', help='')
    group_rm.add_argument('--all', action='store_true', help="All vpls")
    group_rm.add_argument('-s', '--section', metavar='SECTION', type=int, help="")
    parser_rm.set_defaults(func=Actions.rm)

    parser_down = subparsers.add_parser('down', parents=[p_out], help='Download vpls')
    group_down = parser_down.add_mutually_exclusive_group()
    group_down.add_argument('-i', '--ids', type=int, metavar='ID', nargs='*', action='store', help='Indexes')
    group_down.add_argument('--all', action='store_true', help="All vpls")
    group_down.add_argument('-s', '--section', metavar='SECTION', type=int, help="")
    parser_down.set_defaults(func=Actions.down)

    parser_update = subparsers.add_parser('update', help='Update vpls')
    group_update = parser_update.add_mutually_exclusive_group()
    group_update.add_argument('-i', '--ids', type=int, metavar='ID', nargs='*', action='store', help='Indexes')
    group_update.add_argument('-l', '--labels', type=str, metavar='ID', nargs='*', action='store', help='Labels')
    group_update.add_argument('--all', action='store_true', help="All vpls")
    group_update.add_argument('-s', '--section', metavar='SECTION', type=int, nargs='*', help="")
    parser_update.add_argument('--remote', action='store_true', help="update by label using remote")
    parser_update.add_argument('--exec-options', action='store_true', help="enable all execution options")
    #parser_update.add_argument('--duedate', type=str, default=None, action='store', help='duedate yyyy:m:d:h:m')
    parser_update.set_defaults(func=Actions.update)

    parser_define = subparsers.add_parser('define', help='define .mapi for question')
    parser_define.add_argument("--required", "-r", type=str, help='required file')
    parser_define.add_argument("--upload", "-u", type=str, nargs="*", help="system files to Upload")
    parser_define.add_argument("--keep", "-k", type=str, nargs="*", help="user files to Keep in execution")
    parser_define.set_defaults(func=Actions.define)

    args = parser.parse_args()
    if args.config:
        Credentials.config_path = args.config
    if args.timeout is not None:
        MoodleAPI.default_timeout = args.timeout

    if len(sys.argv) > 1:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
