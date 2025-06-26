import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox

# Adicionar caminho do projeto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import obter_clientes
from config import connect_bd

class GestorProcessos:
    def __init__(self):
        self.clientes = obter_clientes()
        self.processos = self.carregar_processos()
        self.referencia_selecionada = None
        self.inicializar_interface()

    def carregar_processos(self):
        conn = connect_bd("D")
        cursor = conn.cursor()
        cursor.execute("SELECT referencia, nif_cliente, descricao FROM processos")
        dados = cursor.fetchall()
        conn.close()

        processos = []
        for ref, nif, desc in dados:
            nome = self.clientes.get(nif, "Desconhecido")
            processos.append({
                "referencia": ref,
                "nif_cliente": nif,
                "nome_cliente": nome,
                "descricao": desc
            })
        return processos

    def inicializar_interface(self):
        self.root = tk.Tk()
        self.root.title("Gestor de Processos")
        self.root.geometry("600x450")

        # Campo de pesquisa
        tk.Label(self.root, text="Pesquisar:").pack(pady=2)
        self.pesquisa_var = tk.StringVar()
        self.entry_pesquisa = tk.Entry(self.root, textvariable=self.pesquisa_var)
        self.entry_pesquisa.pack(fill=tk.X, padx=10)
        self.entry_pesquisa.bind("<KeyRelease>", self.atualizar_lista)

        # Listbox de processos
        self.listbox = tk.Listbox(self.root, height=8)
        self.listbox.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)
        self.listbox.bind("<<ListboxSelect>>", self.carregar_detalhes)

        self.atualizar_lista()

        # Campos de edição
        frame_edicao = tk.Frame(self.root)
        frame_edicao.pack(pady=5)

        tk.Label(frame_edicao, text="Referência:").grid(row=0, column=0, sticky='e')
        self.referencia_var = tk.StringVar()
        tk.Entry(frame_edicao, textvariable=self.referencia_var, width=50).grid(row=0, column=1, padx=5)

        tk.Label(frame_edicao, text="Cliente (NIF):").grid(row=1, column=0, sticky='e')
        self.nif_cliente_var = tk.StringVar()
        self.combo_clientes = ttk.Combobox(frame_edicao, textvariable=self.nif_cliente_var, width=48)
        self.combo_clientes['values'] = [f"{nif} - {nome}" for nif, nome in self.clientes.items()]
        self.combo_clientes.grid(row=1, column=1, padx=5)
        self.combo_clientes.bind("<KeyRelease>", self.filtrar_clientes) 

        tk.Label(frame_edicao, text="Descrição:").grid(row=2, column=0, sticky='ne')
        self.descricao_text = tk.Text(frame_edicao, height=5, width=38)
        self.descricao_text.grid(row=2, column=1, padx=5, pady=5)

        # Botões
        frame_botoes = tk.Frame(self.root)
        frame_botoes.pack(pady=5)

        tk.Button(frame_botoes, text="Novo", command=self.novo_processo).grid(row=0, column=0, padx=5)
        tk.Button(frame_botoes, text="Salvar", command=self.salvar_processo).grid(row=0, column=1, padx=5)
        tk.Button(frame_botoes, text="Eliminar", command=self.eliminar_processo).grid(row=0, column=2, padx=5)
        tk.Button(frame_botoes, text="Fechar", command=self.root.destroy).grid(row=0, column=3, padx=5)

        self.root.mainloop()

    def filtrar_clientes(self, event):
        texto = self.nif_cliente_var.get().lower()
        valores_filtrados = [f"{nif} - {nome}" for nif, nome in self.clientes.items() if texto in nome.lower() or texto in nif.lower()]
        self.combo_clientes["values"] = valores_filtrados

    def atualizar_lista(self, event=None):
        termo = self.pesquisa_var.get().lower()
        self.listbox.delete(0, tk.END)
        for p in self.processos:
            if termo in p['referencia'].lower() or termo in p['nome_cliente'].lower():
                texto = f"{p['referencia']} - {p['nome_cliente']}"
                self.listbox.insert(tk.END, texto)

    def carregar_detalhes(self, event):
        selecionado = self.listbox.curselection()
        if not selecionado:
            return

        texto = self.listbox.get(selecionado[0])
        referencia = texto.split(" - ")[0]
        processo = next((p for p in self.processos if p['referencia'] == referencia), None)

        if processo:
            self.referencia_selecionada = processo['referencia']
            self.referencia_var.set(processo['referencia'])
            self.nif_cliente_var.set(f"{processo['nif_cliente']} - {processo['nome_cliente']}")
            self.descricao_text.delete("1.0", tk.END)
            self.descricao_text.insert(tk.END, processo['descricao'])

    def novo_processo(self):
        self.referencia_selecionada = None
        self.referencia_var.set("")
        self.nif_cliente_var.set("")
        self.descricao_text.delete("1.0", tk.END)

    def salvar_processo(self):
        referencia = self.referencia_var.get().strip()
        cliente_str = self.nif_cliente_var.get()
        descricao = self.descricao_text.get("1.0", tk.END).strip()

        if not all([referencia, cliente_str]):
            messagebox.showwarning("Campos obrigatórios", "Preencha a referência e selecione o cliente.")
            return

        nif_cliente = cliente_str.split(" - ")[0]

        conn = connect_bd("D")
        cursor = conn.cursor()

        try:
            if self.referencia_selecionada and self.referencia_selecionada == referencia:
                cursor.execute("""
                    UPDATE processos
                    SET nif_cliente = ?, descricao = ?
                    WHERE referencia = ?
                """, (nif_cliente, descricao, referencia))
            else:
                cursor.execute("""
                    INSERT INTO processos (referencia, nif_cliente, descricao)
                    VALUES (?, ?, ?)
                """, (referencia, nif_cliente, descricao))

            conn.commit()
            self.processos = self.carregar_processos()
            self.atualizar_lista()
            messagebox.showinfo("Sucesso", "Processo salvo com sucesso.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {e}")
        finally:
            conn.close()

    def eliminar_processo(self):
        if not self.referencia_selecionada:
            messagebox.showwarning("Selecionar", "Selecione um processo primeiro.")
            return

        confirm = messagebox.askyesno("Confirmar", f"Deseja eliminar o processo '{self.referencia_selecionada}'?")
        if not confirm:
            return

        conn = connect_bd("D")
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM processos WHERE referencia = ?", (self.referencia_selecionada,))
            conn.commit()
            self.processos = self.carregar_processos()
            self.novo_processo()
            self.atualizar_lista()
            messagebox.showinfo("Removido", "Processo eliminado com sucesso.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao eliminar: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    GestorProcessos()
