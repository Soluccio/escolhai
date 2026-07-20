# Importador manual da Shopee

Este importador tenta ler metadados públicos e conteúdo renderizado de uma página individual da Shopee. Ele não contorna CAPTCHA, login, bloqueios ou proteções anti-bot.

## Instalação

```bash
python -m pip install -r requirements-importador.txt
python -m playwright install chromium
```

## Uso

Adicionar como novo produto:

```bash
python importar_shopee.py "URL_DO_PRODUTO" --category "Eletrônicos" --headed
```

Substituir o produto de ID 9:

```bash
python importar_shopee.py "URL_DO_PRODUTO" --id 9 --headed
```

O script atualiza `products.json` e tenta baixar a imagem para `images/`.
Sempre revise o resultado antes de fazer commit.
