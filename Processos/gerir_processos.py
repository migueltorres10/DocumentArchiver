import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import tkinter as tk
from tkinter import ttk, messagebox
from utils import obter_clientes
from config import connect_bd



class GestorDeProcessos:
    def __init__(self):
        self.clientes = obter_clientes()
        self.processos = self.carregar_processos()
        self.index_atual = 0
        self.inicializar_interface()

    def carregar_processos(self):
        try:
            conn = connect_bd("D")
            cursor = conn.cursor()
            cursor.execute("SELECT referencia, nif_cliente, descricao FROM processos ORDER BY referencia")
            return cursor.fetchall()
        except Exception as e:
            messagebox.showerror("Erro BD", f"Erro ao carregar processos: {e}")
            return []

    def inicializar_interface(self):
        self.root = tk.Tk()
        self.root.title("Gestor de Processos")
        self.root.geometry("450x350")

        self.referencia_var = tk.StringVar()
        self.nif_cliente_var = tk.StringVar()
        self.descricao_text = tk.Text(self.root, height=5, width=45)

        # Referência
        tk.Label(self.root, text="Referência:").pack()
        self.entry_referencia = tk.Entry(self.root, textvariable=self.referencia_var)
        self.entry_referencia.pack()

        # Cliente
        tk.Label(self.root, text="Cliente (NIF):").pack()
        self.combo_clientes = ttk.Combobox(self.root, textvariable=self.nif_cliente_var, width=50)
        self.combo_clientes["values"] = [f"{nif} - {nome}" for nif, nome in self.clientes.items()]
        self.combo_clientes.pack()
        self.combo_clientes.bind("<KeyRelease>", self.filtrar_clientes)

        # Descrição
        tk.Label(self.root, text="Descrição:").pack()
        self.descricao_text.pack()

        # Navegação
        nav_frame = tk.Frame(self.root)
        nav_frame.pack(pady=10)
        tk.Button(nav_frame, text="◀ Anterior", command=self.anterior, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(nav_frame, text="▶ Próximo", command=self.proximo, width=12).pack(side=tk.LEFT, padx=5)

        # Ações
        action_frame = tk.Frame(self.root)
        action_frame.pack(pady=5)
        tk.Button(action_frame, text="➕ Novo Processo", command=self.novo_processo, width=25).pack(pady=2)
        tk.Button(action_frame, text="💾 Atualizar", command=self.atualizar_processo, width=25).pack(pady=2)
        tk.Button(action_frame, text="🗑 Eliminar", command=self.eliminar_processo, width=25).pack(pady=2)

        # Fechar
        tk.Button(self.root, text="Fechar", command=self.root.destroy, width=25).pack(pady=10)

        if self.processos:
            self.mostrar_processo()

        self.root.mainloop()

    def mostrar_processo(self):
        if not self.processos:
            return

        ref, nif, desc = self.processos[self.index_atual]
        self.referencia_var.set(ref)
        self.nif_cliente_var.set(f"{nif} - {self.clientes.get(nif, 'Desconhecido')}")
        self.descricao_text.delete("1.0", tk.END)
        self.descricao_text.insert(tk.END, desc)

    def anterior(self):
        if self.index_atual > 0:
            self.index_atual -= 1
            self.mostrar_processo()

    def proximo(self):
        if self.index_atual < len(self.processos) - 1:
            self.index_atual += 1
            self.mostrar_processo()

    def novo_processo(self):
        self.referencia_var.set("")
        self.nif_cliente_var.set("")
        self.descricao_text.delete("1.0", tk.END)
        self.index_atual = -1  # Fora da lista atual

    def atualizar_processo(self):
        referencia = self.referencia_var.get().strip()
        cliente_str = self.nif_cliente_var.get()
        descricao = self.descricao_text.get("1.0", tk.END).strip()

        if not all([referencia, cliente_str]):
            messagebox.showwarning("Campos obrigatórios", "Preencha a referência e selecione um cliente.")
            return

        nif_cliente = cliente_str.split(" - ")[0]

        try:
            conn = connect_bd("D")
            cursor = conn.cursor()

            # Verifica se é novo processo (referência não existe)
            cursor.execute("SELECT COUNT(*) FROM processos WHERE referencia = ?", (referencia,))
            existe = cursor.fetchone()[0]

            if existe:
                # Atualiza processo existente
                cursor.execute("""
                    UPDATE processos SET nif_cliente = ?, descricao = ?
                    WHERE referencia = ?
                """, (nif_cliente, descricao, referencia))
                messagebox.showinfo("Atualizado", "Processo atualizado com sucesso.")
            else:
                # Insere novo processo
                cursor.execute("""
                    INSERT INTO processos (referencia, nif_cliente, descricao)
                    VALUES (?, ?, ?)
                """, (referencia, nif_cliente, descricao))
                messagebox.showinfo("Criado", "Novo processo criado com sucesso.")
                # Atualiza a lista local para incluir o novo processo
                self.processos.append({
                    "referencia": referencia,
                    "nif_cliente": nif_cliente,
                    "descricao": descricao
                })
                self.index_atual = len(self.processos) - 1

            conn.commit()
            conn.close()

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar processo: {e}")

    def eliminar_processo(self):
        ref = self.referencia_var.get().strip()
        if not ref:
            return

        confirmar = messagebox.askyesno("Confirmar", f"Deseja eliminar o processo '{ref}'?")
        if confirmar:
            try:
                conn = connect_bd("D")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM processos WHERE referencia = ?", (ref,))
                conn.commit()
                conn.close()

                messagebox.showinfo("Eliminado", "Processo eliminado com sucesso.")
                del self.processos[self.index_atual]
                if self.index_atual >= len(self.processos):
                    self.index_atual = len(self.processos) - 1
                self.mostrar_processo()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao eliminar: {e}")

    def filtrar_clientes(self, event):
        texto = self.nif_cliente_var.get().lower()
        valores_filtrados = [f"{nif} - {nome}" for nif, nome in self.clientes.items() if texto in nome.lower() or texto in nif.lower()]
        self.combo_clientes["values"] = valores_filtrados


if __name__ == "__main__":
    GestorDeProcessos()
