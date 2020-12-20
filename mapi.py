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
        self.urlViewVpl = self.urlBase + '/mod/vpl/view.php?id=ID_QUESTAO'
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
            print("[AFL]",self.browser.title())
        except mechanize.FormNotFoundError as e:
            pass
    
    def addVpl(self, vpl):
        ''' Chamado pelo add '''
        print("Enviando a questão %s para a seção %s" %(vpl.name, self.section))
        
        self.submitVpl(self.urlNewVpl, vpl)

        print("Questão adicionada com sucesso!!")


    def update(self, vpl):
        ''' Chamado pelo update '''
        print("Atualizando a questão %s na seção %s" % (vpl.name, self.section))
        
        self.submitVpl(self.urlUpdateVpl.replace("ID_QUESTAO", vpl.id), vpl)

        print("Questão atualizada com sucesso!!")


    def downloadVpl(self, url, vplid):
        # print("<=",url)
        self.browser.open(url)
        self.login()

        arquivos = {}

        soup = BeautifulSoup(self.browser.response().read(), 'html.parser')

        arqs = soup.findAll('h4', {'id': lambda value: value and value.startswith("fileid")})
        titulo = soup.find('a', {'href': self.browser.geturl()}).get_text()
        descricao = soup.find('div', {'class': 'box py-3 generalbox'}).find('div',{'class':'no-overflow'}).get_text()
        required = None

        for arq in arqs:
            cont = soup.find('pre', {'id': 'code'+arq.get('id') })
            if arq.find_previous_sibling('h2').get_text() == "Arquivos requeridos":
                required = { 'name':arq.get_text(), 'contents':str(cont.get_text())}
            else:
                arquivos[arq.get_text()] = str(cont.get_text())
            # print('->',arq.get_text())
            # print('==',cont.get_text())
        # print(titulo)
        # print(descricao)
        # print("required",required)
        # print("arquivos",arquivos)

        # TODO: receber os arquivos do VPL online
        V = VPL( name=titulo, description=descricao )
        for arq in arquivos.keys():
            V.executionFiles.append({
                'name': arq,
                'contents': arquivos[arq],
                'encoding':0,
            })
        if required:
            V.requiredFile = required

        V.id = vplid
        return V

    def getVpl(self, qId):
        # print("BUSCANDO QID:",qId)
        vplId = -1
        qStions = self.listByQuestions()

        if (str(qId) in qStions) and (str(self.section) in qStions[str(qId)].keys()):
            vplId = qStions[str(qId)][str(self.section)]
        if vplId != -1:
            return self.downloadVpl(self.urlViewVpl.replace("ID_QUESTAO", vplId), vplId)
        return None


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
        # print("ID=",vpl.id)
        # print(vpl)

        if(not vpl.id):
            qStions = self.listByQuestions()
            qbTitle = MoodleAPI.getQByTitle(vpl.name) # @123
            if (str(qbTitle) in qStions) and (str(self.section) in qStions[str(qbTitle)].keys()):
                vpl.id = qStions[str(qbTitle)][str(self.section)]

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
        # print(topics)
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


    def listByQuestions(self):
        ''' { 'ID_QUESTAO' : { 'TOPICO': 'VPL', ... }, ... }\n
        ID_QUESTAO -> ID questão do GitHub;\n
        TOPICO -> ID do tópico;\n
        VPL -> ID da VPL para modificação.'''
        self.browser.open(self.urlCourse)
        self.login()

        soup = BeautifulSoup(self.browser.response().read(), 'html.parser')
        topics = soup.find('ul', {'class:', 'topics'})
        # print(topics)
        childrens = topics.contents
        struc = {}

        for section in childrens:
            id_section = section['id']
            desc_section = section['aria-label']
            # print('- %s: %s' % (id_section.replace('section-', ''), desc_section))

            activities = soup.select('#' + id_section + ' > div.content > ul > li > div > div.mod-indent-outer > div > div.activityinstance > a')
            for activity in activities:
                if not activity['href'].startswith(self.urlBase + '/mod/vpl/view.php?id='):
                    continue
                id_activity = activity['href'].replace(self.urlBase + '/mod/vpl/view.php?id=', '')
                text = activity.get_text().replace(' Laboratório Virtual de Programação', '')
                vplId = MoodleAPI.getQByTitle(text)
                # print("?",text,"| ID=",vplId)
                if str(id_activity).isnumeric() and vplId != -1:
                    if not str(vplId) in struc:
                        struc[str(vplId)] = {}
                    # print('struc[%s][%s]=%s' %(vplId, id_section.replace('section-', ''), id_activity))
                    struc[str(vplId)][str(id_section.replace('section-', ''))] = id_activity
        return struc

    @staticmethod
    def getQByTitle(title):
        ''' "@123 ABCDE..." -> 123 '''
        ttlSplt = title.split(" ")
        for ttl in ttlSplt:
            if ttl[0] == '@' and str(ttl[1:]).isnumeric():
                return int(ttl[1:])
        return -1

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

# Carrega o json
class JsonTarget: 
    class EFile:
        def __init__(self, name, contents):
            self.name = name
            self.contents = contents

    class Question:
        def __init__(self, title, description, tests):
            self.title = title
            self.description = description
            self.executionFiles = []
            self.requiredFile = None
            self.executionFiles.append(JsonTarget.EFile("evaluation.cases", tests))

    #receive a folder and retorn the json string
    @staticmethod 
    def _load_folder(folder):
        title = ""
        description = ""
        tests = ""
        with open(folder + os.sep + "Readme.md") as f:
            title = f.read().split("\n")[0]
            words = title.split(" ")
            if words[0].count("#") == len(words[0]): #only #
                del words[0]
            title = "@" + folder + " " + " ".join(words)
        with open(folder + os.sep + "t.html") as f:
            description = f.read()
        with open(folder + os.sep + "t.vpl") as f:
            tests = f.read()
        question = JsonTarget.Question(title, description, tests)
        s = json.dumps(question, default=lambda o: o.__dict__, indent=4)
        return s

    @staticmethod
    def load(target):
        data = ""
        if os.path.isfile(target):
            with open(target, encoding='utf-8') as f:
                data = json.load(f)
        elif os.path.isdir(target):
            data = json.loads(JsonTarget._load_folder(target))
        else:
            print("fail: target invalido " + target)
            exit(1)
        return data


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

        data = JsonTarget.load(path)
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

    def __eq__(self, value):
        resposta = value.name == self.name
        # print("NAME:","OK" if resposta else "FAIL")

        valueParsedDescrp = BeautifulSoup(value.description, 'html.parser')
        parsedDescrp = BeautifulSoup(self.description, 'html.parser')
        resposta = resposta and (parsedDescrp.get_text() == valueParsedDescrp.get_text())

        # print("DESCRIPT:","OK" if resposta else "FAIL")

        
        for arq in self.executionFiles:
            parsedF = BeautifulSoup(arq["contents"], 'html.parser') # Converte HTML para formato BeautifulSoup
            for searchFile in value.executionFiles: # Itera do segundo VPL
                if searchFile["name"] == arq["name"]: # Encontrado
                    searchFileContentsParsed = BeautifulSoup(searchFile["contents"], 'html.parser').get_text()
                    resposta = resposta and (parsedF.get_text() == searchFileContentsParsed) # Igualdade de conteúdo
        # print("F_CONTENTS:","OK" if resposta else "FAIL")
        
        if self.requiredFile != None or value.requiredFile != None:
            if self.requiredFile != None and value.requiredFile != None:
                resposta = resposta and (self.requiredFile["name"] == value.requiredFile["name"]) # Mesmo nome
            
            selfReqCont = None
            valueReqCont = None
            if self.requiredFile != None:
                selfReqCont = BeautifulSoup(self.requiredFile["contents"], 'html.parser').get_text()
            if value.requiredFile != None:
                valueReqCont = BeautifulSoup(value.requiredFile["contents"], 'html.parser').get_text()
            resposta = resposta and (selfReqCont == valueReqCont)
        # print("REQUIREDFILE:","OK" if resposta else "FAIL")

        return resposta


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

        qid = -1
        qStions = api.listByQuestions()
        qbTitle = MoodleAPI.getQByTitle(vpl.name) # @123

        if (str(qbTitle) in qStions) and (str(args.section) in qStions[str(qbTitle)].keys()):
            qid = qStions[str(qbTitle)][str(args.section)]

        # qid = api.getVplId(vpl.name)
        if qid == -1:
            print("Adicionando nova questão")
            api.addVpl(vpl)
        else:
            vpl.id = qid
            print("Atualizando questao", qid)
            api.update(vpl)



def main_down(args):
    api = MoodleAPI(loadConfig(), args.section)
    if args.qid != -1:
        vpl = api.getVpl(args.qid) 
        print(vpl)

def main_compare(args):
    api = MoodleAPI(loadConfig(), args.section)
    for file in args.questoes:
        vpl = VPL().load(file)
        qid = -1
        qStions = api.listByQuestions()
        qbTitle = MoodleAPI.getQByTitle(vpl.name) # @123

        vplRetrived = api.getVpl(qbTitle)

        if vplRetrived:
            # print("DOWN",vplRetrived)
            # print("JSON",vpl)

            if vplRetrived == vpl:
                print("IGUAIS")
            else:
                print("DIFERENTES")
        else:
            print("VPL não contido na seção %s" % args.section )

def main_update(args):
    api = MoodleAPI(loadConfig(), args.section)
    for file in args.questoes:
        vpl = VPL().load(file)
        qbTitle = MoodleAPI.getQByTitle(vpl.name) # @123
        print("Recebendo questão.")
        vplRetrived = api.getVpl(qbTitle)

        if vplRetrived:
            if vplRetrived == vpl:
                print("Não há mudanças a serem feitas.")
            else:
                print("Atualizando @%d, seção %s." % (qbTitle, args.section))
                vpl.id = vplRetrived.id
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

    desc_update = ("Atualiza questões no moodle \n"
                "Ex.: ./mapi.py update questao.json [questao2.json, questoes/, ...] [-s X]\n"
                "atualiza as questões na seção X\n"
                "-s para definir uma seção (0: padrão)\n"
                "questao - arquivo ou diretório contendo as questões a serem enviadas (Ex.: https://github.com/brunocarvalho7/moodleAPI \n"
                )

    parser_add = subparsers.add_parser('add', help=desc_add)
    parser_add.add_argument('questoes', type=str, nargs='+', action='store', help='Pacote de questões')
    parser_add.add_argument('-s', '--section', metavar='COD_SECTION', default='0', type=str, action='store', help="Código da seção onde a questão será inserida")
    parser_add.set_defaults(func=main_add)


    parser_update = subparsers.add_parser('update', help=desc_update)
    parser_update.add_argument('questoes', type=str, nargs='+', action='store', help='Pacote de questões')
    parser_update.add_argument('-s', '--section', metavar='COD_SECTION', default='0', type=str, action='store', help="Código da seção onde a questão será atualizada")
    parser_update.set_defaults(func=main_update)

    parser_list = subparsers.add_parser('list', help='Lista todas as questões cadastradas no curso e seus respectivos ids')
    parser_list.set_defaults(func=main_list)

    # DEBUG: Ver dados do VPL baixado
    # parser_down = subparsers.add_parser('down', help='DEBUG: Download de vpl.')
    # parser_down.add_argument('qid', type=int, metavar='qId', default='-1', action='store', help='URL da questão')
    # parser_down.add_argument('-s', '--section', metavar='COD_SECTION', default='0', type=str, action='store', help="Código da seção onde a questão será inserida")
    # parser_down.set_defaults(func=main_down)

    # DEBUG: Comparar .json com questão web
    # parser_compare = subparsers.add_parser('compare', help=desc_add)
    # parser_compare.add_argument('questoes', type=str, nargs='+', action='store', help='Pacote de questões')
    # parser_compare.add_argument('-s', '--section', metavar='COD_SECTION', default='0', type=str, action='store', help="Código da seção onde a questão será inserida")
    # parser_compare.set_defaults(func=main_compare)

    args = parser.parse_args()

    if(len(sys.argv) > 1):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
