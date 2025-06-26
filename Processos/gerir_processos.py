import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tkinter as tk
from tkinter import ttk, messagebox
from utils import obter_clientes
from config import connect_bd



class CriadorDeProcessos:
    def __init__(self):
        self.clientes = obter_clientes()
        self.inicializar_interface()

    def inicializar_interface(self):
        self.root = tk.Tk()
        self.root.title("Criar Novo Processo")
        self.root.geometry("400x300")

        # Variáveis
        self.referencia_var = tk.StringVar()
        self.nif_cliente_var = tk.StringVar()
        self.descricao_text = tk.Text(self.root, height=5, width=40)

        # Widgets
        tk.Label(self.root, text="Referência:").pack(pady=5)
        tk.Entry(self.root, textvariable=self.referencia_var).pack()

        # Combobox de clientes com filtro
        self.combo_clientes = ttk.Combobox(self.root, textvariable=self.nif_cliente_var, state="normal", width=50)
        self.combo_clientes["values"] = [f"{nif} - {nome}" for nif, nome in self.clientes.items()]
        self.combo_clientes.pack()
        self.combo_clientes.bind("<KeyRelease>", self.filtrar_clientes)  # <-- Aqui o filtro

        tk.Label(self.root, text="Descrição:").pack(pady=5)
        self.descricao_text.pack()

        tk.Button(self.root, text="Salvar Processo", command=self.salvar_processo).pack(pady=10)

        self.root.mainloop()

    def filtrar_clientes(self, event):
        texto_digitado = self.nif_cliente_var.get().lower()
        resultados = [f"{nif} - {nome}" for nif, nome in self.clientes.items() if texto_digitado in nome.lower()]
    
        self.combo_clientes["values"] = resultados

    def salvar_processo(self):
        referencia = self.referencia_var.get().strip()
        cliente_str = self.nif_cliente_var.get()
        descricao = self.descricao_text.get("1.0", tk.END).strip()

        if not all([referencia, cliente_str]):
            messagebox.showwarning("Campos obrigatórios", "Preencha a referência e escolha um cliente.")
            return

        nif_cliente = cliente_str.split(" - ")[0]  # extrair o NIF

        try:
            conn = connect_bd("D")
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO processos (referencia, nif_cliente, descricao)
                VALUES (?, ?, ?)
            """, (referencia, nif_cliente, descricao))

            conn.commit()
            conn.close()

            messagebox.showinfo("Sucesso", "Processo salvo com sucesso.")
            self.root.destroy()

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar processo: {e}")


if __name__ == "__main__":
    CriadorDeProcessos()
