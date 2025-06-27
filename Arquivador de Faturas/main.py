# main.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import dividir_e_mover_pdf
from visualizadorv2 import VizualizadorFaturas

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pasta_entrada = os.path.join(base_dir, "entrada")
    pasta_obsoletos = os.path.join(base_dir, "obsoletos")
    pasta_separados = os.path.join(base_dir, "separados")

    print("🔄 Movendo PDFs da entrada para separados...")
    arquivos_processados = dividir_e_mover_pdf(
        pasta_origem=pasta_entrada,
        pasta_obsoletos=pasta_obsoletos,
        pasta_separados=pasta_separados
    )

    if arquivos_processados:
        print(f"✅ {len(arquivos_processados)} arquivos processados.")
    else:
        print("⚠️ Nenhum PDF processado da entrada.")

    # Abrir visualizador de guias
    VizualizadorFaturas(pasta_pdf=pasta_separados, base_dir=base_dir)

if __name__ == "__main__":
    main()

