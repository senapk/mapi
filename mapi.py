#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Optional, Any, Dict
import mechanicalsoup
import json
import os
import argparse
import sys
import getpass  # get pass
import pathlib
import requests
import urllib.request
import urllib.error
import tempfile
from enum import Enum


class SourceMode(Enum):
    LOCAL = 0
    REMOTE = 1


class MergeMode(Enum):
    DUPLICATE = 0
    SKIP = 1
    UPDATE = 2


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
    def parse_id_from_update(url) -> str:
        return url.split("update=")[1]

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
    def load_default_config_path():
        return str(pathlib.Path.home()) + os.sep + '.mapirc'

    @staticmethod
    def load_file(path):
        config = {}
        try:
            if not os.path.isfile(path):
                raise FileNotFoundError
            with open(path) as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print("Create a file with your access credentials: " + path)
            print(e)
            exit(1)
        if "password" not in config or config["password"] is None:
            config["password"] = None
        if "remote" not in config:
            config["remote"] = ""
        return Credentials(config["username"], config["password"], config["url"], config["course"], config["remote"])

    @staticmethod
    def update_config(username, password, url, course, remote):
        if Credentials.config_path is None:
            Credentials.config_path = Credentials.load_default_config_path()
        mapirc = Credentials.config_path
        if not os.path.isfile(mapirc):
            with open(mapirc, "w") as f:
                f.write(json.dumps({"username": "", "password": None, "url": "", "course": "", "remote": ""}, indent=4))

        credentials = Credentials.load_file(mapirc)
        if username is not None:
            credentials.username = username
        if password is not None:
            credentials.password = password
        if url is not None:
            credentials.url = url
        if course is not None:
            credentials.course = course
        if remote is not None:
            credentials.remote = remote

        with open(mapirc, "w") as f:
            f.write(json.dumps({"username": credentials.username,
                                "password": credentials.password, "url": credentials.url,
                                "course": credentials.course, "remote": credentials.remote}, indent=4) + "\n")

    @staticmethod
    def load_credentials():
        if Credentials.instance is not None:
            return Credentials.instance
        if Credentials.config_path is None:
            Credentials.config_path = Credentials.load_default_config_path()
        Credentials.instance = Credentials.load_file(Credentials.config_path)
        if Credentials.instance.password is None:
            print("Digite sua senha:")
            Credentials.instance.password = getpass.getpass()
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
        self.upload: List[JsonFile] = []
        self.required: List[JsonFile] = []
        self.keep: List[JsonFile] = []
        
        if tests is not None:
            self.set_test_cases(tests)

    def set_test_cases(self, tests: str):
        file = next((file for file in self.upload if file.name == JsonVPL.test_cases_file_name), None)
        if file is not None:
            file.contents = tests
            return
        self.upload.append(JsonFile("vpl_evaluate.cases", tests))

    def to_json(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    def __str__(self):
        return self.to_json()


class JsonVplLoader:
    @staticmethod
    def _load_from_string(text: str) -> JsonVPL:
        data = json.loads(text)
        vpl = JsonVPL(data["title"], data["description"])
        for f in data["upload"]:
            vpl.upload.append(JsonFile(f["name"], f["contents"]))
        for f in data["keep"]:
            vpl.keep.append(JsonFile(f["name"], f["contents"]))
        for f in data["required"]:
            vpl.required.append(JsonFile(f["name"], f["contents"]))
        return vpl

    @staticmethod
    def save_as(file_url, filename) -> bool:
        try:
            urllib.request.urlretrieve(file_url, filename)
        except urllib.error.HTTPError:
            return False
        return True

    # remote is like https://raw.githubusercontent.com/qxcodefup/moodle/master/base/
    @staticmethod
    def load(target: str, source_mode: SourceMode) -> JsonVPL:
        if source_mode == SourceMode.REMOTE:
            remote_url = Credentials.load_credentials().remote
            url = os.path.join(remote_url, target + "/.cache/mapi.json")            
            _fd, path = tempfile.mkstemp(suffix = "_" + target + '.json')
            print("    - Loading from remote in"    + path + " ... ", end = "")
            if JsonVplLoader.save_as(url, path):
                print("done")
                return JsonVplLoader._load_from_string(open(path).read())
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
            if len(ttl) > 0 and ttl[0] == '@':
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
        if label == "":
            return []
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
        soup = api.browser.page  # BeautifulSoup(api.browser.response().read(), 'html.parser')
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
                vpl.required.append(file)
            else:
                vpl.upload.append(file)
        return vpl

    def set_duedate_field_in_form(self, duedate: Optional[str]):
        if duedate is None:  # unchange default
            return

        if duedate == "0":  # disable
            self.browser["duedate[enabled]"] = False
            return
        self.browser["duedate[enabled]"] = True
        year, month, day, hour, minute = duedate.split(":")

        self.browser["duedate[year]"] = year
        self.browser["duedate[month]"] = str(int(month))  # tranform 05 to 5
        self.browser["duedate[day]"] = str(int(day))
        self.browser["duedate[hour]"] = str(int(hour))
        self.browser["duedate[minute]"] = str(int(minute))

    def update_duedate_only(self, url: str, duedate: Optional[str] = None):
        Bar.send("duedate")
        self.open_url(url)
        self.browser.select_form(nr=0)
        self.set_duedate_field_in_form(duedate)
        self.browser.form.choose_submit("submitbutton")
        self.browser.submit_selected()

    def send_basic_info(self, url: str, vpl: JsonVPL, duedate: Optional[str] = None) -> int:
        self.open_url(url)
        Bar.send("info")

        self.browser.select_form(nr=0)
        self.browser['name'] = vpl.title
        self.browser['introeditor[text]'] = vpl.description
        self.set_duedate_field_in_form(duedate)
        self.browser['maxfiles'] = max(len(vpl.keep), 3)
        self.browser.form.choose_submit("submitbutton")
        self.browser.submit_selected()

        if url.find("update") != -1:
            qid = URLHandler.parse_id_from_update(url)
        else:
            url2 = self.browser.get_url()
            qid = URLHandler.parse_id(url2)
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
        self._send_vpl_files(self.urlHandler.execution_files(qid), vpl.keep + vpl.upload)  # don't change this order
        if len(vpl.required) > 0:
            self._send_vpl_files(self.urlHandler.required_files(qid), vpl.required)

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
        Bar.send("exec")

    @staticmethod
    def __dumper(obj):
        try:
            return obj.to_json()
        except AttributeError:
            return obj.__dict__


class Add:
    def __init__(self, section: Optional[int], duedate: Optional[str], source_mode: SourceMode, merge_mode: MergeMode,
                 structure=None):
        self.section: Optional[int] = 0 if section is None else section
        self.duedate = "0" if duedate is None else duedate
        self.source_mode = source_mode
        self.merge_mode = merge_mode
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
                print(type(_e))  # debug
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

        if item is not None and self.merge_mode == MergeMode.UPDATE:
            print("    - Updating: Label found in " + str(item.id) + ": " + item.title)
            url = api.urlHandler.update_vpl(item.id)
            Bar.open()
            self.send_basic(api, vpl, url)
            self.update_extra(api, vpl, item.id)
            self.set_keep(api, item.id, len(vpl.keep))
            Bar.done()
        elif item is not None and self.merge_mode == MergeMode.SKIP:
            print("    - Skipping: Label found in " + str(item.id) + ": " + item.title)
        else:  # new
            print("    - Creating: New entry with title: " + vpl.title)
            Bar.open()
            url = api.urlHandler.new_vpl(self.section)
            qid = self.send_basic(api, vpl, url)
            Bar.send(str(qid))
            self.update_extra(api, vpl, qid)
            self.set_keep(api, qid, len(vpl.keep))
            self.structure.add_entry(self.section, qid, vpl.title)
            Bar.done()

    def add_target(self, target: str):
        print("- Target: " + target)
        vpl = JsonVplLoader.load(target, self.source_mode)
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


class Update:

    @staticmethod
    def load_itens(args_all, args_section, args_ids, args_labels, structure):
        item_list = []
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
        return item_list

    @staticmethod
    def from_remote(item_list, duedate, structure):
        for item in item_list:
            print("- Updating: " + str(item))
            if item.label == "":
                print("    - Skipping: No label found")
                continue
            action = Add(item.section, duedate=duedate, source_mode=SourceMode.REMOTE, merge_mode=MergeMode.UPDATE,
                         structure=structure)
            action.add_target(item.label)

    @staticmethod
    def exec_or_duedate(item_list, args_exec_options, args_duedate):
        i = 0
        api = MoodleAPI()
        while i < len(item_list):
            item = item_list[i]
            print("- Change execution options for " + str(item.id))
            print("    -", str(item))
            try:
                Bar.open()
                if args_exec_options:
                    api.set_execution_options(item.id)

                if args_duedate:
                    url = api.urlHandler.update_vpl(item.id)
                    api.update_duedate_only(url, args_duedate)

                i += 1
                Bar.done()
            except Exception as _e:
                api = MoodleAPI()
                print(type(_e))  # debug
                print(_e)
                Bar.fail(": timeout")


class Actions:

    @staticmethod
    def add(args):
        merge_mode = MergeMode.UPDATE
        if args.skip:
            merge_mode = MergeMode.SKIP
        elif args.duplicate:
            merge_mode = MergeMode.DUPLICATE
        
        source_mode = SourceMode.REMOTE
        action = Add(args.section, args.duedate, source_mode, merge_mode)
        for target in args.targets:
            action.add_target(target)

    @staticmethod
    def setup(args):
        Credentials.update_config(args.username, args.password, args.url, args.course, args.remote)

    # @staticmethod
    # def define(args):
    #     if args.upload is None:
    #         args.upload = []
    #     if args.keep is None:
    #         args.keep = []
    #     data = {"keep": args.keep, "upload": args.upload, "required": args.required}
    #     with open(".mapi", "w") as f:
    #         f.write(json.dumps(data, indent=4) + "\n")

    @staticmethod
    def update(args):
        args_exec_options = args.exec_options
        args_duedate = args.duedate
        args_content = args.content

        if (not args.exec_options and not args.duedate and not args.content):
            print("no action (-c(content), -d(duedate), -e(exec_options)) selected")
            return

        structure = StructureLoader.load()
        item_list = Update.load_itens(args.all, args.sections, args.ids, args.labels, structure)

        if args_content:
            Update.from_remote(item_list, args_duedate, structure)

        if args_exec_options or args_duedate:
            Update.exec_or_duedate(item_list, args_exec_options, args_duedate)

    @staticmethod
    def down(args):
        args_output: str = args.output

        api = MoodleAPI()
        structure = StructureLoader.load()
        item_list = Update.load_itens(args.all, args.sections, args.ids, args.labels, structure)

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
        structure = StructureLoader.load()
        item_list = Update.load_itens(args.all, args.sections, args.ids, args.labels, structure)

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

    p_selection = argparse.ArgumentParser(add_help=False)
    selection_group = p_selection.add_mutually_exclusive_group()
    selection_group.add_argument('--all', action='store_true', help="All vpls")
    selection_group.add_argument('-i', '--ids', type=int, metavar='ID', nargs='*', action='store')
    selection_group.add_argument('-l', '--labels', type=str, metavar='LABEL', nargs='*', action='store')
    selection_group.add_argument('-s', '--sections', metavar='SECTION', nargs='*', type=int, help="")

    p_duedate = argparse.ArgumentParser(add_help=False)
    p_duedate.add_argument('-d', '--duedate', type=str, action='store', 
                           help='duedate 0 to disable or duedate yyyy:m:d:h:m')

    p_out = argparse.ArgumentParser(add_help=False)
    p_out.add_argument('-o', '--output', type=str, default='.', action='store', help='Output directory')

    desc = ("Gerenciar vpls do moodle de forma automatizada\n"
            "Use \"./mapi comando -h\" para obter informações do comando específico.\n\n"
            )

    parser = argparse.ArgumentParser(prog='mapi.py', description=desc, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-c', '--config', type=str, help="config file path")
    parser.add_argument('-t', '--timeout', type=int, help="max timeout to way moodle response")

    subparsers = parser.add_subparsers(title="subcommands", help="help for subcommand")

    parser_add = subparsers.add_parser('add', parents=[p_section, p_duedate], help="add")
    parser_add.add_argument('targets', type=str, nargs='+', action='store', help='file, folder ou remote with lab')

    group_add = parser_add.add_mutually_exclusive_group()
    group_add.add_argument('--update', action='store_true', help="Default: update if label conflict")
    group_add.add_argument('--skip', action='store_true', help="skip if label conflict")
    group_add.add_argument('--duplicate', action='store_true', help="duplicate if label conflict")
    parser_add.set_defaults(func=Actions.add)

    parser_list = subparsers.add_parser('list', parents=[p_section], help='list')
    parser_list.add_argument('-u', '--url', action='store_true', help="Show vpl urls")
    parser_list.set_defaults(func=Actions.list)

    parser_rm = subparsers.add_parser('rm', parents=[p_selection], help="Remove from Moodle")
    parser_rm.set_defaults(func=Actions.rm)

    parser_down = subparsers.add_parser('down', parents=[p_selection, p_out], help='Download vpls')
    parser_down.set_defaults(func=Actions.down)

    parser_update = subparsers.add_parser('update', parents=[p_selection, p_duedate], help='Update vpls')
    parser_update.add_argument('-c', '--content', action='store_true', help="update question content")
    parser_update.add_argument('-e', '--exec-options', action='store_true', help="enable all execution options")
    parser_update.set_defaults(func=Actions.update)

    parser_setup = subparsers.add_parser('setup', help='config default .mapirc file')
    parser_setup.add_argument("--username", type=str, help='username')
    parser_setup.add_argument("--password", type=str, help="password")
    parser_setup.add_argument("--url", type=str, help="moodle root url")
    parser_setup.add_argument("--course", type=str, help="course number")
    parser_setup.add_argument("--remote", type=str, help="remote server")
    parser_setup.set_defaults(func=Actions.setup)

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
