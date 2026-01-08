import requests
import pandas as pd
from io import StringIO

# 1. URL Limpa: Removi o '//' duplo e a âncora '#' inútil
url = "https://docs.google.com/spreadsheets/d/1QBMPQZ6jZJm5hEKHtRwtI1V3vZZcIkCHAqPe45N0YFE/export?format=csv&gid=23360391"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7"
}

try:
    print("Tentando baixar dados...")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response.encoding = 'utf-8'
    df = pd.read_csv(StringIO(response.text))

    # 2. SUCESSO: Agora sim processamos os dados
    print("Download concluído com sucesso!")
    
    # Vamos ver o que veio? (Debug rápido no terminal)
    print("-" * 30)
    print(f"Conteúdo recebido (primeiros 100 chars): {response.text[:100]}")
    print("-" * 30)

    # Se o conteúdo parecer HTML (<!DOCTYPE html...), o bloqueio continua.
    # Se parecer CSV (USERNAME,PASSWORD...), funcionou.
    
    if "<!DOCTYPE html>" in response.text:
        print("ALERTA: O Google ainda está mandando a página de bloqueio HTML, não o CSV.")
        # Salva o HTML para você ver o erro
        with open("bloqueio_google.html", "w", encoding="utf-8") as f:
            f.write(response.text)
    else:
        print("Sucesso! Parece um CSV. Carregando no Pandas...")
        df = pd.read_csv(StringIO(response.text))
        print(df.head()) # Mostra as primeiras linhas do DataFrame

except Exception as e:
    print(f"Erro Fatal na Requisição: {e}")