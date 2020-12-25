
## MoodleAPI
API de publicação automática de VPL's no Moodle/Moodle2

É necessário primeiro baixar a biblioteca [Mechanize](https://github.com/python-mechanize/mechanize)

    pip install mechanize

E tambem a biblioteca [Beautifulsoup4](https://pypi.org/project/beautifulsoup4/)

	pip install beautifulsoup4

## Configurações do ambiente
Crie um arquivo `.mapirc` no seu diretório de usuário (`~`) com o formato:
```
{
    "username": "seu_login",
    "password": "sua_senha",
    "course": "numero_do_curso",
    "url": "url_do_moodle"
}
```

Exemplo:

```
{
    "username": "jiraya",
    "password": "espadaOlimpica123",
    "course": "516",
    "url": "https://moodle2.quixada.ufc.br"
}
```

Se já quiser, pode deixar o campo password com valor null `"password": null`. O script vai perguntar sua senha em cada operação.
```
senha=sua_senha
```

## Configurando o Moodle
- Modificar o editor padrão do moodle para *Área de texto simples* **(Meu Perfil > Modificar Perfil > Preferências > editor de texto)**

Obs.: Já compatível com Moodle2.

## Modelo de questões
O caminho do arquivo que contém as questões a serem publicadas no Moodle.

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

## Estruturas de diretório de uma questão
- Readme.md
    - A primeira linha deve ter o título da questão.
    - Se houver um `index`, ele deve ser a primeira palavra e iniciar com @
    - Ex: `@017 #01_sel Quem é o irmão mais velho?`
        - O `index` nesse caso é `@017`
            - Esse dado é utilizado para atualizar as questões no moodle.
        - A descrição da questão será dada pelo conteúdo do Readme.
        - A conversão do markdown para html é feita pelo Pandoc.

