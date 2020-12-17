#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from bs4 import BeautifulSoup
import mechanize
import json
import os
import argparse
import sys
import zipfile
import shutil
import getpass #get pass
import pathlib

class MoodleAPI(object):
    def __init__(self, configData, section):
        self.username = configData["username"] #puxa do config
        self.password = configData["password"]
        self.course = configData["course"] #id do curso (344)
        self.section = section #parametro utilizado por exemplo na hora de add o vpl, para escolher onde inserir
        self.urlBase = configData["url"] # https://moodle.quixada.ufc.br
        self.urlCourse = self.urlBase + "/course/view.php?id=" + self.course
        self.urlNewVpl = self.urlBase + "/course/modedit.php?add=vpl&type=&course=" + self.course + "&section=" + self.section + "&return=0&sr=0"
        self.urlUpdateVpl = self.urlBase + '/course/modedit.php?update=ID_QUESTAO'
        self.urlNewTest = self.urlBase + "/mod/vpl/forms/testcasesfile.php?id=ID_QUESTAO&edit=3" #troca ID_QUESTAO na hora do insert
        self.urlTestSave = self.urlBase + "/mod/vpl/forms/testcasesfile.json.php?id=ID_QUESTAO&action=save" #para fazer o download do teste
        self.urlFilesSave = self.urlBase + '/mod/vpl/forms/executionfiles.json.php?id=ID_QUESTAO&action=save' # para enviar os arquivos de execução
        self.urlReqFilesSave = self.urlBase + '/mod/vpl/forms/requiredfiles.json.php?id=ID_QUESTAO&action=save' # para enviar os arquivos requeridos
        self.browser = mechanize.Browser()
        self.browser.set_handle_robots(False)

    def login(self):
        try:
            self.browser.select_form(action=(self.urlBase + '/login/index.php'))
            self.browser['username'] = self.username
            self.browser['password'] = self.password
            self.browser.submit()
            print(self.browser.title())
        except mechanize.FormNotFoundError as e:
            pass
        
    def addVpl(self, vpl):
        print("Enviando a questão %s para a seção %s" %(vpl.name, self.section))
        
        self.submitVpl(self.urlNewVpl, vpl)

        print("Questão adicionada com sucesso!!")

    def update(self, vpl):
        print("Atualizando a questão %s" % (vpl.name))
        
        self.submitVpl(self.urlUpdateVpl.replace("ID_QUESTAO", vpl.id), vpl)

        print("Questão atualizada com sucesso!!")

    def submitVpl(self, url, vpl):
        self.browser.open(url)
        self.login()

        try:
            self.browser.select_form(action='modedit.php')
        except mechanize.FormNotFoundError as e:
            print("erro no login")
            exit(1)
            
        print(self.browser.title())

        self.browser['name'] = vpl.name
        self.browser['introeditor[text]'] = vpl.description
        self.browser["duedate[enabled]"] = []
        self.browser.submit()

        print("Enviando os arquivos de execuções...")

        #todo: fazer isso funcionar mesmo quando não houver indice
        if(not vpl.id):
            vpl.id = self.getVplId(vpl.name)

        self.sendVplFiles(self.urlFilesSave.replace("ID_QUESTAO", vpl.id), vpl.executionFiles)

        vplFiles = []

        if(vpl.requiredFile):
            vplFiles.append(vpl.requiredFile)
        
        self.sendVplFiles(self.urlReqFilesSave.replace("ID_QUESTAO", vpl.id), vplFiles)

    def sendVplFiles(self, url, vplFiles):
        params = {'files': vplFiles,
                  'comments':''}
        files = json.dumps(params, default=self.__dumper, indent=2)

        self.browser.open(url, data=files)

    def listAll(self):
        self.browser.open(self.urlCourse)
        self.login()

        soup = BeautifulSoup(self.browser.response().read(), 'html.parser')
        topics = soup.find('ul', {'class:', 'topics'})
        print(topics)
        childrens = topics.contents

        for section in childrens:
            id_section = section['id']
            desc_section = section['aria-label']
            print('- %s: %s' % (id_section.replace('section-', ''), desc_section))

            activities = soup.select('#' + id_section + ' > div.content > ul > li > div > div.mod-indent-outer > div > div.activityinstance > a')
            for activity in activities:
                if not activity['href'].startswith(self.urlBase + '/mod/vpl/view.php?id='):
                    continue
                id_activity = activity['href'].replace(self.urlBase + '/mod/vpl/view.php?id=', '')
                text = activity.get_text().replace(' Laboratório Virtual de Programação', '')
                print('    - %s: [%s](%s)' %(id_activity, text, activity['href']))

    def getVplId(self, title):
        index = title.split(" ")[0]
        if index[0] != '@':
            return -1

        self.browser.open(self.urlCourse)
        self.login()
        for l in self.browser.links():
            if(l.url.startswith(self.urlBase + "/mod/vpl/view.php?id=")):
                text = l.text.replace(" Laboratório Virtual de Programação", "")
                qid = l.url.replace(self.urlBase + "/mod/vpl/view.php?id=" , "")
                if ord(text[0]) == 65279:
                    text = text[1:]
                qindex = text.split(" ")[0]
                if qindex.startswith("@"):
                    if qindex == index:
                        return qid
        return -1

    def __dumper(self, obj):
        try:
            return obj.toJSON()
        except:
            return obj.__dict__

class VPL(object):
    def __init__(self, name = "", shortdescription = "", description = "", tests = "", executionFiles = []):
        self.id = ""
        self.name = name
        self.description = description
        self.tests = tests
        self.executionFiles = executionFiles
        self.requiredFile = None

    def load(self, path):
        if os.path.isfile(path + ".json"):
            path = path + ".json"

        with open(path, encoding='utf-8') as f:
            data = json.load(f)
            self.name = data["title"]
            self.description = data["description"]
            self.executionFiles = data["executionFiles"]

            for entry in self.executionFiles:
                entry['encoding'] = 0
            if data["requiredFile"] != None:
                self.requiredFile = data["requiredFile"]
        return self

    def __str__(self):
        out = "title: " + self.name + "\n" + "description: " + self.description
        for file in self.executionFiles:
            out += "----" + file["name"] + "\n" + file["contents"] + "\n"
        if self.requiredFile != None:
            out += "----" + self.requiredFile["name"] + "\n" + self.requiredFile["contents"]
        return out

def loadConfig():
    config = {} # ["username"] ["url"] ["course"] ["password"]
    home_mapirc = str(pathlib.Path.home()) + os.sep + '.mapirc'
    if not os.path.isfile(home_mapirc):
        print("Conforme instruções do Readme, crie o arquivo " + home_mapirc)
        exit(1)

    try:
        with open(home_mapirc) as f:
            config = json.load(f)
    except:
        print("Conforme instruções do Readme, crie o arquivo " + home_mapirc)
        exit(1)

    if config["password"] is None:
        config["password"] = getpass.getpass()
    return config

def main_add(args):
    api = MoodleAPI(loadConfig(), args.section)
    for file in args.questoes:
        vpl = VPL().load(file)
        print(vpl.name)
        qid = api.getVplId(vpl.name)
        if qid == -1:
            print("Adicionando nova questão")
            api.addVpl(vpl)
        else:
            vpl.id = qid
            print("Atualizando questao", qid)
            api.update(vpl)

def main_update(args):
    api = MoodleAPI(loadConfig(), '')
    for file in args.questoes:
        vpl = VPL().load(file)
        print(vpl.name)
        qid = api.getVplId(vpl.name)
        if qid == -1:
            print("index not found on moodle, skipping")
        else:
            vpl.id = qid
            print("index found on ", qid)
            api.update(vpl)

def main_list(args):
    api = MoodleAPI(loadConfig(), "")
    api.listAll()

def main():
    desc = ("Gerenciar vpls do moodle de forma automatizada\n"
            "Use \"./MoodleAPI.py comando -h\" para obter informações do comando específico.\n\n"
            "Exemplos:\n"
            "    ./MoodleAPI.py add questao.txt -s 2   #Insere a questão contida em \"Questão.txt\" na seção 2 do curso informado no config.ini\n"
            "    ./MoodleAPI.py list                   #Lista todas as questões cadastradas no curso e seus respectivos ids\n"
            )

    parser = argparse.ArgumentParser(
        prog='mapi.py', description=desc, formatter_class=argparse.RawTextHelpFormatter)

    subparsers = parser.add_subparsers(
        title="subcommands", help="help for subcommand")

    # add
    desc_add = ("Enviar questões para o moodle \n"
                "Ex.: ./mapi.py add questão.txt [questão.txt ...] [-s X]\n"
                "insere as questões na seção X\n"
                "-s para definir a seção\n"
                "questão.txt - arquivo ou diretório contendo as questões a serem enviadas (Ex.: https://github.com/brunocarvalho7/moodleAPI \n"
                )

    parser_add = subparsers.add_parser('add', help=desc_add)
    parser_add.add_argument('questoes', type=str, nargs='+', action='store', help='Pacote de questões')
    parser_add.add_argument('-s', '--section', metavar='COD_SECTION', default='0', type=str, action='store', help="Código da seção onde a questão será inserida")
    parser_add.set_defaults(func=main_add)


    parser_update = subparsers.add_parser('update', help=desc_add)
    parser_update.add_argument('questoes', type=str, nargs='+', action='store', help='Pacote de questões')
    parser_update.set_defaults(func=main_update)

    parser_list = subparsers.add_parser('list', help='Lista todas as questões cadastradas no curso e seus respectivos ids')
    parser_list.set_defaults(func=main_list)

    args = parser.parse_args()

    if(len(sys.argv) > 1):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
