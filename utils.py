from config import connect_bd
import pytesseract
from datetime import datetime
from pathlib import Path
import os
import pdfplumber  # Para extração de texto de PDFs baseados em texto
from pdf2image import convert_from_path
import re
import shutil  # Para mover arquivos
from pyzbar.pyzbar import decode
import fitz  # PyMuPDF

# utils.py

QR_FIELD_MAP = {
    "A": "nif_emitente",
    "B": "nif_adquirente",
    "C": "pais_emitente",
    "D": "tipo_doc",
    "E": "tem_iva",
    "F": "data_doc",
    "G": "numero_doc",
    "H": "hash",
    "I1": "pais_adquirente",
    "I7": "valor_tributavel",
    "I8": "valor_iva",
    "N": "total_iva",
    "O": "total_doc",
    "Q": "chave_seguranca",
    "R": "regime_iva"
}

# Caminhos das dependências
POPPLER_PATH = r"C:\poppler\poppler-24.08.0\Library\bin"
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
SUMATRA_PATH = r"C:\\Users\\FGS\\AppData\\Local\\SumatraPDF\\SumatraPDF.exe"

def obter_fornecedores():
    """
    Retorna um dicionário {NIF: Nome do Fornecedor} da base de dados.
    """
    conn = connect_bd("S")  # Conecta ao banco de dados de fornecedores
    if not conn:
        return {}

    fornecedores = {}
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT RTRIM(ncont), RTRIM(nome) FROM fl")
        for row in cursor.fetchall():
            fornecedores[row[0]] = row[1]
        print("✅ Fornecedores carregados com sucesso.")
    except Exception as e:
        print(f"❌ Erro ao carregar fornecedores: {e}")
    finally:
        conn.close()
    
    return fornecedores

def obter_clientes():
    """
    Retorna um dicionário {NIF: Nome do clientes} da base de dados.
    """
    conn = connect_bd("S")  # Conecta ao banco de dados de fornecedores
    if not conn:
        return {}

    clientes = {}
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT RTRIM(ncont), RTRIM(nome) FROM cl")
        for row in cursor.fetchall():
            clientes[row[0]] = row[1]
        print("✅ clientes carregados com sucesso.")
    except Exception as e:
        print(f"❌ Erro ao carregar clientes: {e}")
    finally:
        conn.close()
    
    return clientes

def carregar_processos():
    conn = connect_bd("D")
    cursor = conn.cursor()
    cursor.execute("SELECT referencia, nif_cliente, descricao FROM processos")
    dados = cursor.fetchall()
    conn.close()

    clientes = obter_clientes()

    processos = []
    for ref, nif, desc in dados:
        nome = clientes.get(nif, "Desconhecido")
        processos.append({
            "referencia": ref,
            "nif_cliente": nif,
            "nome_cliente": nome,
            "descricao": desc
        })
    return processos

def dividir_e_mover_pdf(pasta_origem, pasta_obsoletos, pasta_separados):
    """
    Divide cada PDF multi-página em páginas únicas usando PyMuPDF (fitz).
    Salva cada página como novo PDF na pasta 'separados/'.
    Move o original para 'obsoletos/'.
    """
    Path(pasta_obsoletos).mkdir(parents=True, exist_ok=True)
    Path(pasta_separados).mkdir(parents=True, exist_ok=True)

    arquivos_processados = []

    for arquivo in os.listdir(pasta_origem):
        if not arquivo.lower().endswith(".pdf"):
            continue

        caminho_pdf = os.path.join(pasta_origem, arquivo)
        destino_obsoleto = os.path.join(pasta_obsoletos, arquivo)
        nome_base = Path(arquivo).stem

        try:
            doc = fitz.open(caminho_pdf)
            for i in range(len(doc)):
                nova_pagina = fitz.open()              # novo PDF vazio
                nova_pagina.insert_pdf(doc, from_page=i, to_page=i)

                novo_nome = f"{nome_base}_p{i+1}.pdf"
                caminho_saida = os.path.join(pasta_separados, novo_nome)
                nova_pagina.save(caminho_saida)
                nova_pagina.close()

                print(f"✅ Página {i+1}/{len(doc)} salva: {caminho_saida}")

            doc.close()

            # Mover original para obsoletos
            shutil.move(caminho_pdf, destino_obsoleto)
            print(f"📁 Original movido para: {destino_obsoleto}")
            arquivos_processados.append(arquivo)

        except Exception as e:
            print(f"❌ Erro ao dividir {arquivo}: {e}")

    return arquivos_processados

def verificar_se_pdf_tem_texto(pdf_path):
    """
    Verifica se o PDF contém texto antes de aplicar OCR.
    Retorna True se for um PDF de texto, False se for baseado em imagem.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                texto = page.extract_text()
                if texto and texto.strip():
                    return True  # PDF já contém texto
    except Exception:
        pass
    return False  # PDF é baseado em imagem

def pdf_para_texto(pdf_path):
    """
    Converte um PDF para texto.
    - Se for baseado em texto, usa pdfplumber para preservar formatação.
    - Se for baseado em imagem, usa OCR com Tesseract após ajuste de orientação.
    """
    print(f"📌 Extraindo texto do PDF: {pdf_path}")

    # 📌 Extração de Texto para PDFs Baseados em Texto
    if verificar_se_pdf_tem_texto(pdf_path):
        try:
            with pdfplumber.open(pdf_path) as pdf:
                texto_extraido = "\n".join([page.extract_text() or "" for page in pdf.pages])
                print("✅ Texto extraído usando pdfplumber (mantendo formatação)")
                return texto_extraido
        except Exception as e:
            print(f"❌ Erro ao extrair texto com pdfplumber: {e}")

    # 📌 Extração de Texto para PDFs Baseados em Imagem (OCR)
    print("📌 PDF baseado em imagem detectado. Convertendo para imagem...")
    try:
        imagens = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
        texto_final = []

        for img in imagens:
            texto_corrigido = pytesseract.image_to_string(img, lang="por", config="--oem 3 --psm 6").strip()
            texto_final.append(texto_corrigido)

        print("✅ Texto extraído usando OCR")
        return "\n".join(texto_final)
    
    except Exception as e:
        print(f"❌ Erro ao converter imagem para texto: {e}")
        return None

def parse_qrcode_para_dicionario(texto_qrcode):
    try:
        partes = texto_qrcode.strip().split("*")
        dados_raw = {p.split(":")[0]: p.split(":")[1] for p in partes if ":" in p}
        dados_mapeados = {QR_FIELD_MAP.get(k, k): v for k, v in dados_raw.items()}
        return dados_mapeados
    except Exception as e:
        print(f"❌ Erro ao parsear QR Code: {e}")
        return {}
    
def extrair_ano(data_doc=None):
    """
    Extrai o ano de uma string no formato AAAAMMDD.
    Se não for fornecido, retorna o ano atual.
    """
    if data_doc and len(data_doc) >= 4:
        return data_doc[:4]
    return str(datetime.now().year)

def gravar_guia_bd(fornecedor, numero, ano, data, processo, caminho_pdf):
    try:
        conn = connect_bd("D")
        cursor = conn.cursor()
        data_registo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO guias (fornecedor, numero_doc, data_doc, ano, processo, caminho_ficheiro, data_insercao)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (fornecedor, numero, data, ano, processo, caminho_pdf, data_registo))

        conn.commit()
        conn.close()
        print("✅ Documento registado com sucesso na base de dados.")
    except Exception as e:
        print(f"❌ Erro ao gravar documento: {e}")

def gravar_fatura_bd(fornecedor, tipo_doc, numero, ano, data, base, iva, total, processo, caminho_pdf):
    try:
        conn = connect_bd("D")
        cursor = conn.cursor()
        data_registo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO documentos_faturacao (fornecedor, tipo_doc, numero_doc, ano, data_doc, valor_base, iva, total, processo, caminho_ficheiro, data_insercao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)
        """, (fornecedor, tipo_doc, numero, ano, data, base, iva, total, processo, caminho_pdf, data_registo))
        conn.commit()
        conn.close()
        print("✅ Documento registado com sucesso na base de dados.")
    except Exception as e:
        print(f"❌ Erro ao gravar documento: {e}")

def limpar_nome_ficheiro(nome):
    """
    Remove caracteres inválidos para nomes de ficheiros no Windows.
    Substitui espaços múltiplos por um só underscore.
    """
    nome_limpo = re.sub(r'[\\/*?:"<>|]', '', nome)        # Remove proibidos
    nome_limpo = re.sub(r'\s+', '_', nome_limpo.strip())  # Espaços → underscore
    return nome_limpo

def mover_pdf_para_pasta_destino(caminho_pdf, fornecedor, ano, pasta_base):
    """
    Move o PDF para a pasta: pasta_base/ano/fornecedor/
    Mantém o nome original do ficheiro.
    """
    if not all([fornecedor, ano]):
        raise ValueError("Fornecedor e ano são obrigatórios para mover o PDF.")

    pasta_destino = os.path.join(pasta_base, ano, fornecedor)
    os.makedirs(pasta_destino, exist_ok=True)

    nome_original = os.path.basename(caminho_pdf)
    novo_caminho = os.path.join(pasta_destino, nome_original)

    # Evita sobrescrever sem confirmação
    if os.path.exists(novo_caminho):
        raise FileExistsError(f"O ficheiro já existe em: {novo_caminho}")

    shutil.move(caminho_pdf, novo_caminho)
    print(f"✅ Ficheiro movido para: {novo_caminho}")
    return novo_caminho

def renomear_pdf(caminho_pdf, numero, ano):
    """
    Renomeia o ficheiro para GR_<numero>_<ano>.pdf na mesma pasta.
    """
    if not all([numero, ano]):
        raise ValueError("Número e ano são obrigatórios.")

    numero_limpo = limpar_nome_ficheiro(numero)

    novo_nome = f"GR_{numero_limpo}.pdf"
    pasta = os.path.dirname(caminho_pdf)
    novo_caminho = os.path.join(pasta, novo_nome)

    # Substituição opcional com confirmação externa
    if os.path.exists(novo_caminho):
        raise FileExistsError(f"O ficheiro já existe: {novo_caminho}")

    os.rename(caminho_pdf, novo_caminho)
    print(f"✅ Ficheiro renomeado para: {novo_caminho}")
    return novo_caminho

def extrair_dados_qrcode_de_pdf(pdf_path):
    try:
        imagens = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
        for img in imagens:
            resultado_qr = decode(img)
            if resultado_qr:
                texto = resultado_qr[0].data.decode("utf-8")
                return parse_qrcode_para_dicionario(texto)
    except Exception as e:
        print(f"Erro ao extrair QR code: {e}")
    return {}