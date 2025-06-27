# visualizador.py
import sys
import os
import tkinter as tk
from tkinter import messagebox, ttk
from utils import (
    obter_fornecedores,
    extrair_dados_qrcode_de_pdf,
    gravar_guia_bd,
    mover_pdf_para_pasta_destino,
    renomear_pdf,
    carregar_processos,
    SUMATRA_PATH
)
import subprocess
import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Processos.gerir_processos import GestorProcessos


class VisualizadorGuias:
    def __init__(self, pasta_pdf, base_dir):
        self.pasta_pdf = pasta_pdf
        self.base_dir = base_dir
        print("📂 Buscando Guias na pasta:", self.pasta_pdf)
        self.pdfs = self.listar_pdfs()
        self.index_atual = 0
        self.viewer_process = None
        self.fornecedores = obter_fornecedores()
        self.processos = carregar_processos()


        if not self.pdfs:
            messagebox.showerror("Erro", "Nenhuma Guia encontrada na pasta 'separados'.")
            return

        self.inicializar_interface()
        self.abrir_pdf(self.pdfs[self.index_atual])
        self.root.mainloop()

    def inicializar_interface(self):
        self.root = tk.Tk()
        self.root.title("Visualizador de Guias de Transporte")
        self.root.geometry("300x600")
        self.root.eval('tk::PlaceWindow . center')
        self.root.attributes('-topmost', 1)

        self.fornecedor_var = tk.StringVar()
        self.entry_ano = tk.Entry(self.root)
        self.entry_numero = tk.Entry(self.root)
        self.entry_data = tk.Entry(self.root)
        self.processo_var = tk.StringVar()

        self._criar_widgets()

    def _criar_widgets(self):
        self._adicionar_label_entry("Fornecedor:", self.fornecedor_var, is_combobox=True)
        self._adicionar_label_entry("Ano:", self.entry_ano)
        self._adicionar_label_entry("Número da Guia:", self.entry_numero)
        self._adicionar_label_entry("Data da Guia:", self.entry_data)
        self._adicionar_label_entry("Número de Processo:", self.processo_var, is_combobox="processo")

        nav_frame = tk.Frame(self.root)
        nav_frame.pack(pady=10)
        tk.Button(nav_frame, text="◀ Anterior", width=12, command=self.mostrar_anterior).pack(side="left", padx=5)
        tk.Button(nav_frame, text="Próximo ▶", width=12, command=self.mostrar_proximo).pack(side="left", padx=5)
            # 🔹 Botão para abrir gestor de processos
        tk.Button(self.root, text="🧾 Gerir Processos", command=self.abrir_gestor_processos).pack(pady=5)

        action_frame = tk.Frame(self.root)
        action_frame.pack(pady=15)
        tk.Button(action_frame, text="💾 Salvar no Banco", width=25, command=self.salvar_dados).pack(pady=3)
        tk.Button(action_frame, text="Eliminar", width=25, fg="red", command=self.eliminar_pdf).pack(pady=3)
        tk.Button(action_frame, text="Terminar", width=25, command=self.terminar).pack(pady=3)

    def _adicionar_label_entry(self, texto, var, is_combobox=False):
        tk.Label(self.root, text=texto).pack(pady=5)
        if is_combobox:
            combo = ttk.Combobox(self.root, textvariable=var, state="normal", width=40)
            if texto.startswith("Fornecedor"):
                combo["values"] = list(self.fornecedores.values())
                combo.bind("<KeyRelease>", self.filtrar_fornecedores)
                self.combo_fornecedor = combo
            elif texto.startswith("Número de Processo"):
                valores_processo = [f"{p['referencia']} - {p['nome_cliente']}" for p in self.processos]
                combo["values"] = valores_processo
                combo.bind("<KeyRelease>", self.filtrar_processos)
                self.combo_processo = combo
            combo.pack(pady=5)
        else:
            var.pack(pady=5)

    def listar_pdfs(self):
        try:
            return [f for f in os.listdir(self.pasta_pdf) if f.lower().endswith('.pdf')]
        except FileNotFoundError:
            print("❌ Pasta 'separados' não encontrada.")
            return []

    def mostrar_pdf_atual(self):
        if self.index_atual < 0 or self.index_atual >= len(self.pdfs):
            messagebox.showerror("Erro", "Nenhum PDF disponível para mostrar.")

    def abrir_pdf(self, nome_arquivo):
        self.fechar_pdf_anterior()
        caminho_pdf = os.path.join(self.pasta_pdf, nome_arquivo)
        try:
            print(f"Abrindo PDF: {caminho_pdf}")
            self.viewer_process = subprocess.Popen([SUMATRA_PATH, "-reuse-instance", caminho_pdf])
            self.preencher_dados_do_qr(caminho_pdf)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o PDF: {e}")
        self.root.after(500, lambda: self.entry_numero.focus_set())

    def fechar_pdf_anterior(self):
        try:
            subprocess.run(["taskkill", "/IM", "SumatraPDF.exe", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Erro ao fechar SumatraPDF: {e}")

    def mostrar_anterior(self):
        if self.index_atual > 0:
            self.index_atual -= 1
            self.abrir_pdf(self.pdfs[self.index_atual])

    def mostrar_proximo(self):
        if self.index_atual < len(self.pdfs) - 1:
            self.index_atual += 1
            self.abrir_pdf(self.pdfs[self.index_atual])

    def terminar(self):
        self.fechar_pdf_anterior()
        self.root.destroy()
    
    def abrir_gestor_processos(self):
        # Abre a janela de gestão de processos sem bloquear esta janela
        self.root.after(100, GestorProcessos(on_close=self.recarregar_processos))

    def recarregar_processos(self):
        # Recarrega os processos após fechar a janela de gestão
        self.processos = carregar_processos()
        valores_processo = [f"{p['referencia']} - {p['nome_cliente']}" for p in self.processos]
        self.combo_processo["values"] = valores_processo        


    def salvar_dados(self):
        fornecedor_nome = self.fornecedor_var.get().strip()
        ano = self.entry_ano.get().strip()
        numero = self.entry_numero.get().strip()
        data = self.entry_data.get().strip()
        processo_str = self.processo_var.get().strip()
        processo = processo_str.split(" - ")[0] if processo_str else ""

        if not all([fornecedor_nome, ano, numero, data]):
            messagebox.showwarning("Campos obrigatórios", "Preencha todos os campos obrigatórios.")
            return

        fornecedor_nif = None
        for nif, nome in self.fornecedores.items():
            if nome == fornecedor_nome:
                fornecedor_nif = nif
                break

        if not fornecedor_nif:
            messagebox.showerror("Fornecedor inválido", "Fornecedor não encontrado na base de dados.")
            return

        try:
            data_formatada = datetime.datetime.strptime(data, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Erro de data", "Formato da data deve ser YYYY-MM-DD.")
            return

        nome_pdf = self.pdfs[self.index_atual]
        caminho_pdf = os.path.join(self.pasta_pdf, nome_pdf)

        try:
            nome_pasta_fornecedor = fornecedor_nome
            pasta_destino_base = os.path.join(self.base_dir, "arquivados")

            caminho_movido = mover_pdf_para_pasta_destino(
                caminho_pdf=caminho_pdf,
                fornecedor=nome_pasta_fornecedor,
                ano=ano,
                pasta_base=pasta_destino_base
            )

            caminho_final = renomear_pdf(
                caminho_pdf=caminho_movido,
                numero=numero,
                ano=ano
            )

            gravar_guia_bd(
                fornecedor=fornecedor_nif,
                numero=numero,
                ano=ano,
                data=data_formatada,
                processo=processo,
                caminho_pdf=caminho_final
            )

            messagebox.showinfo("Sucesso", "Guia gravada e movida com sucesso.")
            del self.pdfs[self.index_atual]

            if self.pdfs:
                if self.index_atual >= len(self.pdfs):
                    self.index_atual = len(self.pdfs) - 1
                self.abrir_pdf(self.pdfs[self.index_atual])
            else:
                messagebox.showinfo("Fim", "Nenhum PDF restante.")
                self.root.destroy()

        except FileExistsError as fe:
            messagebox.showerror("Erro", f"Já existe um ficheiro com esse nome: {fe}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar ou mover guia: {e}")

    def eliminar_pdf(self):
        if not self.pdfs:
            return

        nome_pdf = self.pdfs[self.index_atual]
        caminho_pdf = os.path.join(self.pasta_pdf, nome_pdf)

        confirm = messagebox.askyesno("Confirmar eliminação", f"Deseja eliminar o ficheiro '{nome_pdf}'?")
        if confirm:
            try:
                self.fechar_pdf_anterior()

                if os.path.exists(caminho_pdf):
                    os.remove(caminho_pdf)
                    print(f"✅ '{nome_pdf}' foi eliminado.")
                else:
                    print(f"⚠️ Ficheiro '{nome_pdf}' já não existe em: {caminho_pdf}")

                messagebox.showinfo("Removido", f"'{nome_pdf}' foi eliminado (ou já não existia).")
                del self.pdfs[self.index_atual]

                if self.pdfs:
                    if self.index_atual >= len(self.pdfs):
                        self.index_atual = len(self.pdfs) - 1
                    self.abrir_pdf(self.pdfs[self.index_atual])
                else:
                    messagebox.showinfo("Fim", "Nenhum PDF restante.")
                    self.root.destroy()

            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao eliminar: {e}")

    def preencher_dados_do_qr(self, caminho_pdf):
        self.fornecedor_var.set("")
        self.entry_data.delete(0, tk.END)
        self.entry_ano.delete(0, tk.END)
        self.entry_numero.delete(0, tk.END)
        self.processo_var.set("")

        dados_qr = extrair_dados_qrcode_de_pdf(caminho_pdf)
        if not dados_qr:
            print("⚠️ Nenhum dado encontrado no QR Code.")
            return

        nif = dados_qr.get("nif_emitente")
        fornecedor_nome = self.fornecedores.get(nif)
        if fornecedor_nome:
            self.fornecedor_var.set(fornecedor_nome)
        else:
            print(f"⚠️ NIF {nif} não encontrado nos fornecedores.")

        data_qr = dados_qr.get("data_doc", "").strip()
        data_formatada = None
        if data_qr:
            for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y%m%d"):
                try:
                    data_formatada = datetime.datetime.strptime(data_qr, formato).date()
                    break
                except ValueError:
                    continue

        self.entry_data.delete(0, tk.END)
        if data_formatada:
            self.entry_data.insert(0, data_formatada.isoformat())
            self.entry_ano.delete(0, tk.END)
            self.entry_ano.insert(0, str(data_formatada.year))
        else:
            print(f"⚠️ Data inválida ou ausente no QR: '{data_qr}'")

        ano = str(data_formatada.year) if data_formatada else str(datetime.datetime.now().year)
        self.entry_ano.delete(0, tk.END)
        self.entry_ano.insert(0, ano)

        numero = dados_qr.get("numero_doc", "")
        self.entry_numero.delete(0, tk.END)
        self.entry_numero.insert(0, numero)

    def filtrar_fornecedores(self, event):
        texto = self.fornecedor_var.get().lower()
        filtrados = [nome for nome in self.fornecedores.values() if texto in nome.lower()]
        self.combo_fornecedor["values"] = filtrados

    def filtrar_processos(self, event):
        texto = self.processo_var.get().lower()
        filtrados = [
            f"{p['referencia']} - {p['nome_cliente']}"
            for p in self.processos
            if texto in p['referencia'].lower() or texto in p['nome_cliente'].lower()
        ]
        self.combo_processo['values'] = filtrados

