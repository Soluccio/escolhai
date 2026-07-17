from pathlib import Path
import json,os,sys
R=Path(__file__).resolve().parents[1]
if not os.getenv('SHOPEE_APP_ID') or not os.getenv('SHOPEE_APP_SECRET'):
 print('Credenciais da Shopee ainda não configuradas; catálogo atual preservado.')
 sys.exit(0)
print('Credenciais encontradas. Ajuste a consulta conforme o schema liberado no Explorer oficial da sua conta antes de ativar a sincronização real.')
