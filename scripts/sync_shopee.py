import os
print('Credenciais configuradas.' if os.getenv('SHOPEE_APP_ID') else 'Sem credenciais; catálogo preservado.')
