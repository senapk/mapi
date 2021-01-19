
## MoodleAPI
API de publicação automática de VPL's no Moodle/Moodle2

É necessário primeiro baixar as bibliotecas mechanize e bs4 usando o pip

```
pip install mechanize bs4
```

## Configurações do ambiente
Crie um arquivo `.mapirc` no seu diretório de usuário (`~`) com o formato.
```
{
    "username": "seu_login",
    "password": "sua_senha",
    "course": "numero_do_curso",
    "url": "url_do_moodle",
    "remote": "url do repositório remoto de questões"
}
```

Exemplo:

```
{
    "username": "jiraya",
    "password": "espadaOlimpica123",
    "course": "516",
    "url": "https://moodle2.quixada.ufc.br",
    "remote": "https://raw.githubusercontent.com/qxcodefup/moodle/master/base"
}
```

Se já quiser, pode deixar o campo password com valor null `"password": null`. O script vai perguntar sua senha em cada operação. Se preferir, você pode passar o arquivo de configuração por parâmetro:

```
$ mapi.py -c configfile
```

Para saber se está funcionando, você pode listar as questões do seu curso.

```
$ mapi.py -c configfile list
```

Para adicionar uma questão que já está no repositório remoto, basta ter colocado o remote do [qxcodefup](https://github.com/qxcodefup/moodle) no config e chamar o script com a operação `add` e a opção `--remote` ou apenas `-r`. No repositório, cada questão tem um label único no formato de `@xxx`.

![](resources/exemplo.png)

Para enviar a questão `@192 A idade de Dona Mônica` utilizando o repositório remoto, para a seção 5 do seu curso do moodle use:

```
$ mapi.py add 195 --section 5 --remote
```

Ou de forma resumida

```
$ mapi.py add 195 -s 5 -r
```

É possível enviar várias questões ao mesmo tempo com o mesmo comando. Para enviar 002, 003, 004 e 006 para a seção 5:

```
$ mapi.py add 002 003 004 006 -s 5 -r
```


## Modelo de questões
Se quiser criar suas próprias questões, deve criar um arquivo json com as informações necessárias usando o modelo a seguir.

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

## Exemplos e utilização
| Operação | Parâmetros |
| --- | --- |
| ./mapi.py add questao.json [q2.json] [...] [-s 0] | `-s` Seção de destino |
| ./mapi.py update questao.json [q2.json] [...] [-s 0] [-f, --force] | `-s` Seção de destino. <br/>`-f` Atualiza mesmo sem modificações aparentes. |
| ./mapi.py push questao.json [q2.json] [...] [-s 0] [-f, --force] | `-s` Seção de destino.<br/>`-f` Envia e atualiza mesmo sem modificações aparentes. |
| ./mapi.py list | Lista todas as questões cadastradas no curso e seus respectivos IDs. |

Obs¹: Arquivos no formato do [modelo de questões](#modelo-de-questões) ou pastas seguindo as [estruturas de diretório de uma questão](#estruturas-de-diretório-de-uma-questão) são aceitos.

