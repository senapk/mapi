<!--TOC_BEGIN-->
- [Configurações da ferramenta](#configurações-da-ferramenta)
- [Configurando acesso ao curso](#configurando-acesso-ao-curso)
- [Listando estrutura de um curso](#listando-estrutura-de-um-curso)
- [Adicionando](#adicionando)
    - [Utilizando labels](#utilizando-labels)
    - [Inserindo questões duplicadas](#inserindo-questões-duplicadas)
    - [Definindo horário de finalizar atividade](#definindo-horário-de-finalizar-atividade)
- [Removendo](#removendo)
- [Update](#update)
- [Criando suas próprias questões](#criando-suas-próprias-questões)
<!--TOC_END-->

# MoodleAPI


API de publicação automática de VPL's no Moodle/Moodle2

É necessário primeiro baixar as bibliotecas mechanize e bs4 usando o pip

## Configurações da ferramenta
Instale o python e o pip. Depois instale as dependências com

```
pip install mechanize bs4
```

baixe o arquivo `mapi.py`, coloque como executável, e adicione a algum lugar do seu path.

## Configurando acesso ao curso

Crie um arquivo `curso.json` com o seguinte formato.
```
{
    "username": "seu_login",
    "password": "sua_senha",
    "course": "numero_do_curso",
    "url": "url_do_moodle",
    "remote": "url do repositório remoto de questões"
}
```

Para obter o número do curso, basta olhar o último número na URL do seu curso do moodle.

![](resources/curso.png)

Se estiver utilizando o moodle2 da UFC de Quixadá e for trabalhar com a disciplina FUP, seu arquivo será igual a esse, mudando apenas os três primeiros campos.

```
{
    "username": "jiraya",
    "password": "espadaOlimpica123",
    "course": "516",
    "url": "https://moodle2.quixada.ufc.br",
    "remote": "https://raw.githubusercontent.com/qxcodefup/moodle/master/base"
}
```

Se preferir, pode deixar o campo password com valor null `"password": null`. O script vai perguntar sua senha em cada operação.


## Listando estrutura de um curso

Para saber se está funcionando, você pode listar as questões do seu curso. Você pode ter múltiplos arquivos de configuração, um para cada curso.

```
$ mapi.py -c curso.json list
```

Quando estiver povoado, a saída será como a da figura abaixo.
![](resources/list.png)

Você pode salvar o arquivo de configuração no seu diretório `home` como `.mapirc` e será o arquivo carregado por default caso não seja explicitado outro arquivo.

```
$ mapi.py list
```

Para todo o resto do tutorial, vamos omitir o parâmetro do arquivo de configuração.

## Adicionando

### Utilizando labels

O procedimento padrão para inserção é utilizando as questões do repositório remoto configurado no arquivo de configurações. Para FUP, o repositório padrão está no [github](https://github.com/qxcodefup/arcade#qxcodefup). Depois, você vai aprender a criar e formatar as próprias questões. No repositório, cada questão tem um `label` único no formato de `@xxx`.

![](resources/exemplo.png)

Para enviar a questão `@192 A idade de Dona Mônica` para a seção 5 do seu curso do moodle use:

```
$ mapi.py add 195 --section 5
```

Ou de forma resumida

```
$ mapi.py add 195 -s 5
```

É possível enviar várias questões ao mesmo tempo com o mesmo comando. Para enviar 002, 003, 004 e 006 para a seção 5:

```
$ mapi.py add 002 003 004 006 -s 5
```

### Inserindo questões duplicadas
O procedimento default se você enviar duas questões com o mesmo label para a mesma seção, o procedimento padrão é de atualizar a questão pre-existente. Você pode forçar a inserção duplicada com `--force` ou pular a questão caso ela já exista com `--skip` para o comando `add`.

### Definindo horário de finalizar atividade

Por default, as questões são inseridas sem prazo para fechamento da atividade. No caso de provas ou testes, você pode inserir questões definindo o horário de fechamento com o parâmetro `--duedate yyyy:m:d:h:m`.

## Removendo
```bash
# para remover todos os vpls da seção 4
$ mapi.py rm -s 4

# para remover as questões passando os IDS
$ mapi.py rm -i 19234 18234 19234

# para remover TODOS os vpls do curso
$ mapi.py rm --all
```

## Update
Update pode ser utilizado para
- Habilitar as opções de execução das questões que você criou manualmente
- Atualizar as questões utilizando o label e buscando no repositório por updates.

Você pode solicitar atualização por label, índice ou para todos as questões de uma seção.

## Criando suas próprias questões

Se quiser criar suas próprias questões manualmente, deve criar um arquivo .json com as informações necessárias usando o modelo a seguir.

```json
{
  "title": "@001 #4_fun Faca a função soma2",
  "description": "Leia dois números um por linha e faça a função soma\n",
  "executionFiles": [
    {
      "name": "vpl_evaluate.cases",
      "contents": "conteudo dos testes"
    },
    {
      "name": "solver.c.txt",
      "contents": "conteudo do solver"
    }
  ], 
  "requiredFile": {
    "name": "lib.c",
    "contents": "conteudo da lib.c"
  }
}
```

Se não houver arquivo requerido, ponha `"requiredFile" = null`.

Depois, basta enviar usando o parâmtro `--local` no comando `add`.

