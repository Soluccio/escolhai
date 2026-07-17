# Escolhaí

**Você escolhe, a gente encurta o caminho.**

## Visualizar
Abra `index.html`. As imagens ficam em `images/`.

## Editar produtos
Edite `products.json` e execute `python scripts/build_site.py`.

## GitHub Pages
Envie todo o conteúdo desta pasta para a raiz do repositório. Em Settings > Pages selecione `main` e `/ (root)`.

## Automação
O workflow não falha enquanto as credenciais não existirem. Depois de obter a API oficial, cadastre `SHOPEE_APP_ID` e `SHOPEE_APP_SECRET` nos GitHub Actions Secrets. A consulta real deverá ser ajustada ao schema autorizado para sua conta antes de ser ativada. Nunca grave o Secret no código.
