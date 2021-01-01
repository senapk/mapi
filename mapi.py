#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Optional, Any, Dict
from bs4 import BeautifulSoup
import mechanize
import json
import os
import argparse
import sys
import getpass  # get pass
import pathlib
import requests
from types import SimpleNamespace  # to load json


class URLHandler:
    def __init__(self, url_base: str, course_id: str):
        self._url_base: str = url_base
        self.course_id: str = course_id

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

    def delete_vpl(self, id: int):
        return self.delete_action() + "?sr=0&delete=" + str(id)

    def new_vpl(self, section: int):
        return self._url_base + "/course/modedit.php?add=vpl&type=&course=" + self.course_id + "&section=" + \
               str(section) + "&return=0&sr=0 "

    def view_vpl(self, id: int):
        return self._url_base + '/mod/vpl/view.php?id=' + str(id)

    def update_vpl(self, id: int):
        return self._url_base + '/course/modedit.php?update=' + str(id)

    def new_test(self, id: int):
        return self._url_base + "/mod/vpl/forms/testcasesfile.php?id=" + str(id) + "&edit=3"

    # def test_save(self, id: int):
    #     return self._url_base + "/mod/vpl/forms/testcasesfile.json.php?id=" + str(id) + "&action=save"

    def execution_files(self, id: int):
        return self._url_base + '/mod/vpl/forms/executionfiles.json.php?id=' + str(id) + '&action=save'

    def required_files(self, id: int):
        return self._url_base + '/mod/vpl/forms/requiredfiles.json.php?id=' + str(id) + '&action=save'

    def execution_options(self, id: int):
        return self._url_base + "/mod/vpl/forms/executionoptions.php?id=" + str(id)

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
            print("Crie seu arquivo com suas credenciais de acesso: " + mapirc)
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
        return json.loads(text, object_hook=lambda d: SimpleNamespace(**d))

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
        print("fail: target invalido " + target)
        exit(1)


# class VPL:
#     def __init__(self, name="", description="", tests=""):
#         self.id: str = ""
#         self.name: str = name
#         self.description: str = description
#         self.tests: str = tests
#         self.executionFiles: List[JsonFile] = []
#         self.requiredFile:  = None
#
#     def load(self, path):
#         if os.path.isfile(path + ".json"):
#             path = path + ".json"
#
#         data = VplLoader.load(path)
#         self.name = data["title"]
#         self.description = data["description"]
#         self.executionFiles = data["executionFiles"]
#
#         for entry in self.executionFiles:
#             entry['encoding'] = 0
#         if data["requiredFile"] is not None:
#             self.requiredFile = data["requiredFile"]
#         return self
#
#     def __str__(self):
#         out = "title: " + self.name + "\n" + "description: " + self.description
#         for file in self.executionFiles:
#             out += "----" + file["name"] + "\n" + file["contents"] + "\n"
#         if self.requiredFile is not None:
#             out += "----" + self.requiredFile["name"] + "\n" + self.requiredFile["contents"]
#         return out

    # def __eq__(self, value):
    #     response = value.name == self.name
    #     # print("NAME:","OK" if resposta else "FAIL")
    #
    #     value_parsed_descrp = BeautifulSoup(value.description, 'html.parser')
    #     parsed_descrp = BeautifulSoup(self.description, 'html.parser')
    #     response = response and (parsed_descrp.get_text() == value_parsed_descrp.get_text())
    #
    #     # print("DESCRIPT:","OK" if resposta else "FAIL")
    #
    #     for arq in self.executionFiles:
    #         parsed_f = BeautifulSoup(arq["contents"], 'html.parser')  # Converte HTML para formato BeautifulSoup
    #         for search_file in value.executionFiles:  # Itera do segundo VPL
    #             if search_file["name"] == arq["name"]:  # Encontrado
    #                 search_file_contents_parsed = BeautifulSoup(search_file["contents"], 'html.parser').get_text()
    #                 response = response and (parsed_f.get_text() == search_file_contents_parsed)  # equal content
    #     # print("F_CONTENTS:","OK" if resposta else "FAIL")
    #
    #     if self.requiredFile is not None or value.requiredFile is not None:
    #         if self.requiredFile is not None and value.requiredFile is not None:
    #             response = response and (self.requiredFile["name"] == value.requiredFile["name"])  # Mesmo nome
    #
    #         self_req_cont = None
    #         value_req_cont = None
    #         if self.requiredFile is not None:
    #             self_req_cont = BeautifulSoup(self.requiredFile["contents"], 'html.parser').get_text()
    #         if value.requiredFile is not None:
    #             value_req_cont = BeautifulSoup(value.requiredFile["contents"], 'html.parser').get_text()
    #         response = response and (self_req_cont == value_req_cont)
    #     # print("REQUIREDFILE:","OK" if resposta else "FAIL")
    #
    #     return response

# to print loading bar
class Bar:
    @staticmethod
    def open():
        print("    - [ ", end='', flush=True)

    @staticmethod
    def send(text: str):
        print(text.center(15, '.') + " ", end='', flush=True)

    @staticmethod
    def done(text=""):
        print("] DONE" + text)

    @staticmethod
    def fail(text=""):
        print("] FAIL" + text)


class StructureItem:
    def __init__(self, section: int, id: int, title: str):
        self.section: int = section
        self.id: int = id
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
    def __init__(self, soup):
        self.soup = soup
        topics = soup.find('ul', {'class:', 'topics'})
        self.childrens = topics.contents

        self.section_item_list: List[List[StructureItem]] = self._make_entries_by_section()
        self.section_labels: List[str] = self._make_section_labels()
        # redundant info
        self.ids_dict: Dict[int, StructureItem] = self._make_ids_dict()

    def add_entry(self, section: int, id: int, title: str):
        if id not in self.ids_dict.keys():
            item = StructureItem(section, id, title)
            self.section_item_list[section].append(item)
            self.ids_dict[id] = item

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

    def get_item(self, id: int) -> StructureItem:
        return self.ids_dict[id]

    def has_id(self, id: int, section: Optional[int] = None) -> bool:
        if section is None:
            return id in self.ids_dict.keys()
        return id in self.get_id_list(section)

    def rm_item(self, id: int):
        if self.has_id(id):
            item = self.ids_dict[id]
            del self.ids_dict[id]
            new_section_list = [item for item in self.section_item_list[item.section] if item.id != id]
            self.section_item_list[item.section] = new_section_list

    def get_number_of_sections(self):
        return len(self.section_labels)

    def _make_section_labels(self) -> List[str]:
        return [section['aria-label'] for section in self.childrens]

    def _make_entries_by_section(self) -> List[List[StructureItem]]:
        output: List[List[StructureItem]] = []
        for section_index, section in enumerate(self.childrens):
            comp = ' > div.content > ul > li > div > div.mod-indent-outer > div > div.activityinstance > a'
            activities = self.soup.select('#' + section['id'] + comp)
            section_entries: List[StructureItem] = []
            for activity in activities:
                if not URLHandler.is_vpl_url(activity['href']):
                    continue
                id: int = int(URLHandler.parse_id(activity['href']))
                title: str = activity.get_text().replace(' Laboratório Virtual de Programação', '')
                section_entries.append(StructureItem(section_index, id, title))
            output.append(section_entries)
        return output

    def _make_ids_dict(self) -> Dict[int, StructureItem]:
        entries: Dict[int, StructureItem] = {}
        for item_list in self.section_item_list:
            for item in item_list:
                entries[item.id] = item
        return entries


# formatting structure to list
class Viewer:
    def __init__(self, structure: Structure, url_handler: URLHandler, show_url: bool):
        self.structure = structure
        self.url_handler = url_handler
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
        self.urlHandler = URLHandler(self.credentials.url, self.credentials.course)
        self.browser = mechanize.Browser()
        self.browser.set_handle_robots(False)
        self.logged: bool = False

    def open_url(self, url: str, data_files: Optional[Any] = None):
        if data_files is None:
            self.browser.open(url, timeout=MoodleAPI.default_timeout)
        else:
            self.browser.open(url, timeout=MoodleAPI.default_timeout, data=data_files)
        self._login()

    def _login(self):
        if self.logged:
            return
        try:
            self.browser.select_form(action=(self.urlHandler.login()))
            self.browser['username'] = self.credentials.username
            self.browser['password'] = self.credentials.password
            self.browser.submit()
            self.logged = True
        except mechanize.FormNotFoundError as _e:
            pass

    def delete(self, id: int):
        Bar.send("loading")
        self.open_url(self.urlHandler.delete_vpl(id))
        Bar.send("submitting")
        try:
            self.browser.select_form(action=self.urlHandler.delete_action())
            self.browser.submit()
        except mechanize.FormNotFoundError as e:
            print("Erro no login", e)
            exit(1)

    def download_vpl(self, vplid: int) -> JsonVPL:
        url = self.urlHandler.view_vpl(vplid)

        Bar.send("opening")
        self.open_url(url)
        Bar.send("parsing")
        soup = BeautifulSoup(self.browser.response().read(), 'html.parser')
        arqs = soup.findAll('h4', {'id': lambda value: value and value.startswith("fileid")})
        title = soup.find('a', {'href': self.browser.geturl()}).get_text()
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
        self.browser["duedate[year]"] = [year]
        self.browser["duedate[month]"] = [month]
        self.browser["duedate[day]"] = [day]
        self.browser["duedate[hour]"] = [hour]
        self.browser["duedate[minute]"] = [minute]

    def send_basic_info(self, url: str, vpl: JsonVPL, duedate: Optional[str] = None) -> int:
        Bar.send("openning")
        self.open_url(url)
        Bar.send("filling")
        try:
            self.browser.select_form(action='modedit.php')
        except mechanize.FormNotFoundError as _e:
            print("erro no login")
            exit(1)

        self.browser['name'] = vpl.title
        self.browser['introeditor[text]'] = vpl.description
        if duedate is None:
            self.browser["duedate[enabled]"] = 0
        else:
            self.set_duedate(duedate)

        Bar.send("submitting")
        self.browser.submit(name="submitbutton")

        id = URLHandler.parse_id(self.browser.geturl())
        return int(id)

    def send_extra_files(self, vpl: JsonVPL, id: int):
        self.send_execution_files(vpl, id)
        self.send_required_files(vpl, id)
        self.set_execution_options(id)

    def send_execution_files(self, vpl: JsonVPL, id: int):
        self.send_vpl_files(self.urlHandler.execution_files(id), vpl.executionFiles)

    def send_required_files(self, vpl: JsonVPL, id: int):
        if vpl.requiredFile:
            self.send_vpl_files(self.urlHandler.required_files(id), [vpl.requiredFile])

    def set_execution_options(self, id):
        Bar.send("enabling")
        self.open_url(self.urlHandler.execution_options(id))

        try:
            self.browser.select_form(action='executionoptions.php')
        except mechanize.FormNotFoundError as _e:
            print("erro no login")
            exit(1)
        self.browser['run'] = ["1"]
        self.browser['evaluate'] = ["1"]
        self.browser.submit()

    def send_vpl_files(self, url: str, vpl_files: List[JsonFile]):
        Bar.send("sending")

        params = {'files': vpl_files, 'comments': ''}
        files = json.dumps(params, default=self.__dumper, indent=2)
        self.open_url(url, files)
#        self.browser.open(url, data=files, timeout=MoodleAPI.default_timeout)
        self._login()

    def get_course_structure(self) -> Structure:
        while(True):
            try:
                print("- Loading course structure")
                Bar.open()
                Bar.send("loading")
                self.open_url(self.urlHandler.course())
                Bar.send("parsing")
                soup = BeautifulSoup(self.browser.response().read(), 'html.parser')
                Bar.done()
                return Structure(soup)
            except mechanize.URLError as _e:
                Bar.fail(": timeout")

    @staticmethod
    def __dumper(obj):
        try:
            return obj.to_json()
        except AttributeError:
            return obj.__dict__


class Add:
    def __init__(self, section: Optional[str], duedate: Optional[str], remote: bool, op_ignore: bool, op_update: bool):
        self.section: Optional[int] = section
        self.duedate = duedate
        self.remote: bool = remote
        self.op_ignore: bool = op_ignore
        self.op_update: bool = op_update
        self.on_going_id: Optional[int] = None  # used to assure return to id if add_new break in middle
        self.structure = MoodleAPI().get_course_structure()

    def new_vpl(self, api: MoodleAPI, vpl: JsonVPL, section: int) -> int:
        Bar.open()
        url = api.urlHandler.new_vpl(section)
        id = api.send_basic_info(url, vpl, self.duedate)
        self.on_going_id = id
        Bar.send("id:" + str(id))
        api.send_extra_files(vpl, id)
        self.on_going_id = None
        Bar.done()
        return id

    def update(self, api: MoodleAPI, vpl: JsonVPL, id: int):
        Bar.open()
        url = api.urlHandler.update_vpl(id)
        api.send_basic_info(url, vpl, self.duedate)
        api.send_extra_files(vpl, id)
        self.on_going_id = None
        Bar.done()

    def apply_action(self, vpl: JsonVPL, item: Optional[StructureItem]):
        api = MoodleAPI()  # creating new browser for each attempt to avoid some weird timeout
        if self.on_going_id:
            print("    - Retrying: " + str(self.on_going_id))
            self.update(api, vpl, self.on_going_id)
        elif item is not None and self.op_update:
            print("    - Updating: Label found in " + str(item.id) + ": " + item.title)
            self.update(api, vpl, item.id)
        elif item is not None and self.op_ignore:
            print("    - Skipping: Label found in " + str(item.id) + ": " + item.title)
        else:
            print("    - Creating: New entry with title: " + vpl.title)
            id = self.new_vpl(api, vpl, self.section)
            self.structure.add_entry(self.section, id, vpl.title)

    def add_target(self, target: str):
        print("- Target: " + target)
        vpl = JsonVplLoader.load(target, self.remote)
        itens_label_match = self.structure.search_by_label(StructureItem.parse_label(vpl.title), self.section)
        item = None if len(itens_label_match) == 0 else itens_label_match[0]
        while True:
            try:
                self.apply_action(vpl, item)
                return
            except mechanize.URLError as _e:
                Bar.fail(": timeout")


class Actions:

    @staticmethod
    def add(args):
        action = Add(args.section, args.duedate, args.remote, args.ignore, args.update)
        for target in args.targets:
            action.add_target(target)

    @staticmethod
    def down(args):
        args_ids: List[int] = args.ids
        args_section: Optional[int] = args.section
        args_all: bool = args.all
        args_output: str = args.output

        item_list: List[StructureItem] = []
        api = MoodleAPI()
        structure = api.get_course_structure()

        if args_all:
            item_list = structure.get_itens()
        elif args_section:
            item_list = structure.get_itens(args_section)
        elif args_ids:
            for id in args_ids:
                if structure.has_id(id):
                    item_list.append(structure.get_item(id))
                else:
                    print("    - id not found: ", id)

        i = 0
        while i < len(item_list):
            item = item_list[i]
            path = os.path.normpath(os.path.join(args_output, str(item.id) + ".json"))
            print("- Saving id " + str(item.id))
            print("    -", str(item))
            try:
                Bar.open()
                data = api.download_vpl(item.id)
                open(path, "w").write(str(data))
                i += 1
                Bar.done(": " + path)
            except mechanize.URLError as _e:
                Bar.fail(": timeout")

    @staticmethod
    def rm(args):
        args_ids: List[int] = args.ids
        args_section: Optional[int] = args.section
        args_all: bool = args.all

        item_list: List[StructureItem] = []
        api = MoodleAPI()
        structure = api.get_course_structure()

        if args_all:
            item_list = structure.get_itens()
        elif args_section:
            item_list = structure.get_itens(args_section)
        elif args_ids:
            for id in args_ids:
                if structure.has_id(id):
                    item_list.append(structure.get_item(id))
                else:
                    print("    - id not found", id)

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
            except mechanize.URLError as _e:
                Bar.fail(": timeout")

    @staticmethod
    def list(args):
        args_section: Optional[int] = args.section
        args_url: bool = args.url
        api = MoodleAPI()
        viewer = Viewer(api.get_course_structure(), api.urlHandler, args_url)
        if args_section:
            viewer.list_section(args_section)
        else:
            viewer.list_all()


def main():
    p_config = argparse.ArgumentParser(add_help=False)
    p_config.add_argument('-c', '--config', type=str, help="config file path")
    p_config.add_argument('-t', '--timeout', type=int, help="config file path")

    p_section = argparse.ArgumentParser(add_help=False)
    p_section.add_argument('-s', '--section', metavar='SECTION', type=int, help="")

    p_out = argparse.ArgumentParser(add_help=False)
    p_out.add_argument('-o', '--output', type=str, default='.', action='store', help='Pasta de destino')

    desc = ("Gerenciar vpls do moodle de forma automatizada\n"
            "Use \"./mapi comando -h\" para obter informações do comando específico.\n\n"
            "Exemplos:\n"
            "    ./mapi.py add q.json -s 2   #Insere a questão contida em \"q.json\" na seção 2\n"
            "    ./mapi.py list              #Lista todas as entradas do curso com seus ids\n"
            )

    parser = argparse.ArgumentParser(prog='mapi.py', description=desc, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-c', '--config', type=str, help="config file path")

    subparsers = parser.add_subparsers(title="subcommands", help="help for subcommand")

    parser_add = subparsers.add_parser('add', parents=[p_config, p_section], help="add")
    parser_add.add_argument('targets', type=str, nargs='+', action='store', help='file, folder ou remote with lab')
    parser_add.add_argument('-r', '--remote', action='store_true', help="Use remote repository")
    parser_add.add_argument('-d', '--duedate', type=str, default=None, action='store', help='duedate yyyy:m:d:y:m')
    group_add = parser_add.add_mutually_exclusive_group()
    group_add.add_argument('-i', '--ignore', action='store_true', help="Ignore if found same label in section")
    group_add.add_argument('-u', '--update', action='store_true', help="Update if found same label in section")
    parser_add.set_defaults(func=Actions.add)

    parser_list = subparsers.add_parser('list', parents=[p_config, p_section], help='list')
    parser_list.add_argument('-u', '--url', action='store_true', help="Show urls")
    parser_list.set_defaults(func=Actions.list)

    parser_rm = subparsers.add_parser('rm', parents=[p_config], help="Remove from Moodle")
    group_rm = parser_rm.add_mutually_exclusive_group()
    group_rm.add_argument('-i', '--ids', type=int, metavar='ID', nargs='*', action='store', help='Índices ')
    group_rm.add_argument('--all', action='store_true', help="Remove all vpls from course")
    group_rm.add_argument('-s', '--section', metavar='SECTION', type=int, help="")
    parser_rm.set_defaults(func=Actions.rm)

    parser_down = subparsers.add_parser('down', parents=[p_config, p_out], help='Download de vpl.')
    group_down = parser_down.add_mutually_exclusive_group()
    group_down.add_argument('-i', '--ids', type=int, metavar='ID', nargs='*', action='store', help='Indices')
    group_down.add_argument('--all', action='store_true', help="Remove all vpls from course")
    group_down.add_argument('-s', '--section', metavar='SECTION', type=int, help="")
    parser_down.set_defaults(func=Actions.down)

    args = parser.parse_args()
    if args.config:
        Credentials.config_path = args.config
    if args.timeout:
        MoodleAPI.default_timeout = args.timeout

    if len(sys.argv) > 1:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
