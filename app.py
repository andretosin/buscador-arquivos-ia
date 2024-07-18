import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import google.generativeai as genai
from PIL import Image, ImageTk
import re
import logging
import tempfile
import textwrap

# Configuração de log
log_file = os.path.join(tempfile.gettempdir(), 'app.log')
logging.basicConfig(filename=log_file, level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("Iniciando aplicação")

class RoundedEntry(tk.Canvas):
    def __init__(self, master, width, height, corner_radius, padding=8, **kwargs):
        super().__init__(master, width=width, height=height, highlightthickness=0, bg=master['bg'], **kwargs)
        self.corner_radius = corner_radius

        self.create_rounded_rect(0, 0, width, height, fill='white')

        self.entry = tk.Entry(self, width=width-padding*2, bd=0, highlightthickness=0, **kwargs)
        self.create_window(padding, height//2, anchor='w', window=self.entry)

    def create_rounded_rect(self, x1, y1, x2, y2, **kwargs):
        points = [
            x1+self.corner_radius, y1,
            x1+self.corner_radius, y1,
            x2-self.corner_radius, y1,
            x2-self.corner_radius, y1,
            x2, y1,
            x2, y1+self.corner_radius,
            x2, y1+self.corner_radius,
            x2, y2-self.corner_radius,
            x2, y2-self.corner_radius,
            x2, y2,
            x2-self.corner_radius, y2,
            x2-self.corner_radius, y2,
            x1+self.corner_radius, y2,
            x1+self.corner_radius, y2,
            x1, y2,
            x1, y2-self.corner_radius,
            x1, y2-self.corner_radius,
            x1, y1+self.corner_radius,
            x1, y1+self.corner_radius,
            x1, y1
        ]
        return self.create_polygon(points, **kwargs, smooth=True)

    def get(self):
        return self.entry.get()

class RoundedText(tk.Frame):
    def __init__(self, master, width, height, corner_radius, padding=8, **kwargs):
        super().__init__(master, bg=master['bg'])
        self.width = width
        self.height = height

        self.canvas = tk.Canvas(self, width=width, height=height, highlightthickness=0, bg=master['bg'])
        self.canvas.pack(side="left", fill="both", expand=True)

        self.text = tk.Text(self.canvas, width=width-padding*2, height=height-padding*2, bd=0, highlightthickness=0, wrap=tk.WORD, **kwargs)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.create_window(padding, padding, anchor='nw', window=self.text)
        self.scrollbar.pack(side="right", fill="y")

        self.create_rounded_rect(0, 0, width, height, corner_radius, fill='white')

    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1+radius, y1,
            x1+radius, y1,
            x2-radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.canvas.create_polygon(points, **kwargs, smooth=True)

    def get(self, *args, **kwargs):
        return self.text.get(*args, **kwargs)

class ScrollableText(scrolledtext.ScrolledText):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

class FileSearchApp:
    def __init__(self, master):
        logging.info("Inicializando FileSearchApp")
        self.master = master
        master.title("Buscador de Arquivos AI")
        
        # Sua API key
        default_api_key = "AIzaSyB4P8OG6Kirw1Wu-pUhHhzs0r0b7Q2qDus"
        
        window_width = 800
        window_height = 800

        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()

        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)

        master.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        master.resizable(False, False)

        master.configure(bg='#003E7E')

        self.api_key = tk.StringVar(value=default_api_key)
        self.directory = tk.StringVar()

        tk.Label(master, text="API Key do Gemini:", bg='#003E7E', fg='white').pack(pady=5)
        self.api_key_entry = RoundedEntry(master, width=400, height=30, corner_radius=10)
        self.api_key_entry.pack()
        self.api_key_entry.entry.insert(0, default_api_key)  # Preenche o campo com a chave padrão

        tk.Label(master, text="Diretório:", bg='#003E7E', fg='white').pack(pady=5)
        self.directory_entry = RoundedEntry(master, width=400, height=30, corner_radius=10)
        self.directory_entry.pack()
        tk.Button(master, text="Selecionar Diretório", command=self.select_directory, bg='white').pack(pady=5)

        tk.Label(master, text="Lista de arquivos a buscar (um por linha):", bg='#003E7E', fg='white').pack(pady=5)
        self.search_query_text = RoundedText(master, width=400, height=100, corner_radius=10)
        self.search_query_text.pack()

        tk.Button(master, text="Buscar", command=self.search_files, bg='white').pack(pady=10)

        self.results_text = ScrollableText(master, width=90, height=20, wrap=tk.WORD)
        self.results_text.pack(pady=10, padx=10)

        try:
            self.logo_image = Image.open("abaco_logo.jpg")
            self.logo_image = self.logo_image.resize((100, 100))
            self.logo_photo = ImageTk.PhotoImage(self.logo_image)
            self.logo_label = tk.Label(master, image=self.logo_photo, bg='#003E7E')
            self.logo_label.pack(side=tk.BOTTOM, pady=10)
        except Exception as e:
            logging.error(f"Erro ao carregar a imagem: {e}")
            self.logo_label = tk.Label(master, text="ÁBACO", bg='#003E7E', fg='white', font=("Arial", 16, "bold"))
            self.logo_label.pack(side=tk.BOTTOM, pady=10)

    def select_directory(self):
        directory = filedialog.askdirectory()
        self.directory_entry.entry.delete(0, tk.END)
        self.directory_entry.entry.insert(0, directory)

    def search_files(self):
        api_key = self.api_key_entry.get()
        directory = self.directory_entry.get()
        queries = self.search_query_text.get("1.0", tk.END).strip().split('\n')

        if not self.validate_input(api_key, directory, queries):
            return

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            all_directories = self.get_all_directories(directory)
            logging.info(f"Número total de diretórios encontrados: {len(all_directories)}")

            # Primeira chamada à IA para obter diretórios relevantes
            relevant_dirs = self.get_relevant_directories(all_directories, queries, model)

            # Listar arquivos nos diretórios relevantes
            all_files = self.list_files_in_directories(relevant_dirs)

            # Segunda chamada à IA para obter arquivos relevantes
            results = self.get_relevant_files(all_files, queries, model)

            self.display_results(results)
        except Exception as e:
            logging.error(f"Erro durante a busca: {str(e)}")
            messagebox.showerror("Erro", str(e))

    def validate_input(self, api_key, directory, queries):
        if not api_key:
            messagebox.showerror("Erro", "Por favor, insira uma chave de API válida.")
            return False

        if not os.path.isdir(directory):
            messagebox.showerror("Erro", "O diretório especificado não existe.")
            return False

        if not queries:
            messagebox.showerror("Erro", "Por favor, insira pelo menos uma consulta de busca.")
            return False

        return True

    def get_all_directories(self, directory):
        all_directories = []
        for root, dirs, files in os.walk(directory):
            for dir in dirs:
                all_directories.append(os.path.join(root, dir))
        logging.info(f"Total de diretórios encontrados: {len(all_directories)}")
        return all_directories

    def get_relevant_directories(self, all_directories, queries, model):
        relevant_dirs = []
        for query in queries:
            prompt = self.create_prompt_for_directories(query, all_directories)
            try:
                response = model.generate_content(prompt)
                relevant_dirs.extend(self.extract_directory_paths(response.text))
            except Exception as e:
                logging.error(f"Erro na chamada da API para a query '{query}': {str(e)}")
        return list(set(relevant_dirs))  # Remover duplicatas

    def create_prompt_for_directories(self, query, all_directories):
        # Limitando o número de diretórios para evitar sobrecarregar o modelo
        max_directories = 1000
        directories_sample = all_directories[:max_directories]

        prompt = f"""Você é um assistente de IA especializado em recuperação de informações e compreensão de contexto em ambientes corporativos e de engenharia. Sua tarefa é analisar uma lista de caminhos de diretórios e identificar os mais relevantes para a consulta fornecida.

Consulta do usuário: "{query}"

IMPORTANTE: A estrutura dos diretórios geralmente é o inverso da consulta. Por exemplo, se a consulta for "Última versão da matrícula da área do condomínio Bariloche", os diretórios mais relevantes provavelmente serão algo como "BARILOCHE/MATRICULAS/[versão mais recente]".

Considere as seguintes diretrizes:
1. Analise profundamente o contexto da consulta, considerando termos técnicos, jargões de engenharia e estruturas organizacionais comuns.
2. Procure por sinônimos, termos relacionados e abreviações comuns no setor.
3. Considere a estrutura hierárquica dos diretórios, que muitas vezes reflete a organização de uma empresa ou projeto.
4. Para documentos técnicos ou de engenharia, considere diferentes nomenclaturas para o mesmo tipo de projeto.
5. Para documentos corporativos, atente-se a padrões de nomenclatura como datas, versões ou numerações.
6. Leve em conta possíveis erros de digitação ou variações na nomenclatura dos diretórios.
7. Preste atenção especial a indicadores de versões mais recentes, como números de versão mais altos ou datas mais recentes.
8. Jamais selecione diretórios marcados como "Antigos" ou similares, a menos que seja especificamente solicitado.
9. Se a consulta pedir a versão mais recente, certifique-se de comparar todas as versões disponíveis antes de fazer uma seleção.

Número total de diretórios: {len(all_directories)}
Amostra de diretórios (limitada a {max_directories}):
"""
        for directory in directories_sample:
            prompt += f"- \{directory}n"

        prompt += """
Apresente sua resposta no seguinte formato:

Diretórios relevantes:
[caminho completo do diretório 1 em uma única linha]
[caminho completo do diretório 2 em uma única linha]
...

IMPORTANTE: Certifique-se de que cada caminho de diretório seja fornecido em uma única linha, sem quebras."""
        return prompt

    def extract_directory_paths(self, response_text):
        directory_paths = []
        lines = response_text.strip().split('\n')
        for line in lines:
            if line.startswith('Diretórios relevantes:'):
                continue
            elif line.strip():
                directory_paths.append(line.strip())
        return directory_paths

    def list_files_in_directories(self, relevant_dirs):
        all_files = []
        for directory in relevant_dirs:
            for root, _, files in os.walk(directory):
                for file in files:
                    all_files.append(os.path.join(root, file))
        return all_files

    def get_relevant_files(self, all_files, queries, model):
        results = {}
        for query in queries:
            prompt = self.create_prompt_for_files(query, all_files)
            try:
                response = model.generate_content(prompt)
                results[query] = {
                    "raw_response": response.text,
                    "tokens": self.estimate_tokens(prompt) + self.estimate_tokens(response.text)
                }
                logging.info(f"Tokens usados para query '{query}': {results[query]['tokens']}")
            except Exception as e:
                logging.error(f"Erro na chamada da API para a query '{query}': {str(e)}")
                results[query] = {
                    "raw_response": f"Erro na chamada da API: {str(e)}",
                    "tokens": 0
                }
        return results

    def create_prompt_for_files(self, query, all_files):
        # Limitando o número de arquivos para evitar sobrecarregar o modelo
        max_files = 1000
        files_sample = all_files[:max_files]

        prompt = f"""Você é um assistente de IA especializado em recuperação de informações e compreensão de contexto em ambientes corporativos e de engenharia. Sua tarefa é analisar uma lista de caminhos de arquivos e identificar o mais relevante para a consulta fornecida.

    Consulta do usuário: "{query}"

    IMPORTANTE: O nome e a localização dos arquivos geralmente estão relacionados com o contexto da consulta. Por exemplo, se a consulta for "Última versão do relatório anual de vendas da filial de São Paulo", o arquivo mais relevante provavelmente será algo como "SAO_PAULO/VENDAS/RELATORIO_ANUAL_[ano mais recente].pdf".

    Considere as seguintes diretrizes:
    1. Analise profundamente o contexto da consulta, considerando termos técnicos, jargões de engenharia e estruturas organizacionais comuns.
    2. Procure por sinônimos, termos relacionados e abreviações comuns no setor.
    3. Considere a estrutura hierárquica dos diretórios e como ela se relaciona com a organização dos arquivos.
    4. Para documentos técnicos ou de engenharia, considere diferentes nomenclaturas para o mesmo tipo de projeto ou relatório.
    5. Para documentos corporativos, atente-se a padrões de nomenclatura como datas, versões, numerações ou códigos de identificação.
    6. Leve em conta possíveis erros de digitação ou variações na nomenclatura dos arquivos.
    7. Preste atenção especial a indicadores de versões mais recentes, como números de versão mais altos ou datas mais recentes.
    8. Jamais selecione arquivos marcados como "Antigos" ou similares, a menos que seja especificamente solicitado.
    9. Se a consulta pedir a versão mais recente, certifique-se de comparar todas as versões disponíveis antes de fazer uma seleção.

    Número total de arquivos: {len(all_files)}
    Amostra de arquivos (limitada a {max_files}):
    """
        for file in files_sample:
            prompt += f"- {file}\n"

        prompt += """
    Baseado na análise da consulta e na lista de arquivos fornecida, siga os passos abaixo:

    1. Raciocínio inicial:
    a) Identifique as palavras-chave e conceitos importantes na consulta do usuário.
    b) Liste os arquivos que parecem mais relevantes à primeira vista e explique por quê.
    c) Considere possíveis armadilhas ou interpretações errôneas da consulta.

    2. Análise comparativa:
    a) Compare os arquivos mais promissores, destacando seus pontos fortes e fracos em relação à consulta.
    b) Considere a estrutura hierárquica dos diretórios e como ela se relaciona com a organização dos arquivos.
    c) Avalie indicadores de versões ou datas, se relevantes.

    3. Seleção final:
    Com base no raciocínio acima, selecione o arquivo mais relevante e até dois alternativos, se aplicável.

    Apresente sua resposta no seguinte formato:
    Raciocínio inicial: [Seu raciocínio detalhado]

    Análise comparativa: [Sua análise detalhada]

    Arquivo mais relevante: [caminho completo do arquivo em uma única linha]
    Justificativa final: [Explicação concisa de 3-4 frases sobre a escolha final]

    Alternativas (se houver):
    1. [caminho do arquivo alternativo 1 em uma única linha]: [breve justificativa]
    2. [caminho do arquivo alternativo 2 em uma única linha]: [breve justificativa]

    IMPORTANTE: Certifique-se de que cada caminho de arquivo seja fornecido em uma única linha, sem quebras. Além disso, preste atenção em detalhes como extensões de arquivo (como .pdf, .docx, .xlsx) e use-os como pistas para identificar o tipo de arquivo mais relevante para a consulta."""
        return prompt

    def estimate_tokens(self, text):
        # Estimativa aproximada do número de tokens
        return len(re.findall(r'\w+|[^\w\s]', text))

    def display_results(self, results):
            self.results_text.delete("1.0", tk.END)
            for query, result in results.items():
                self.results_text.insert(tk.END, f"Para '{query}':\n\n", "bold")
                formatted_response = self.format_response(result['raw_response'])
                self.results_text.insert(tk.END, f"Resposta da IA:\n{formatted_response}\n\n")
                self.results_text.insert(tk.END, f"Tokens usados (estimativa): {result['tokens']}\n\n")
                self.results_text.insert(tk.END, "-" * 50 + "\n\n")
            self.results_text.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))

    def format_response(self, text):
        lines = text.split('\n')
        formatted_lines = []
        for line in lines:
            if line.startswith("Arquivo mais relevante:") or line.startswith("1. ") or line.startswith("2. "):
                # Não quebra linhas para caminhos de arquivo
                formatted_lines.append(line)
            else:
                # Quebra outras linhas normalmente
                wrapped_lines = textwrap.wrap(line, width=80)
                formatted_lines.extend(wrapped_lines)

        formatted_text = '\n'.join(formatted_lines)
        formatted_text = formatted_text.replace("Arquivo mais relevante:", "\nArquivo mais relevante:")
        formatted_text = formatted_text.replace("Justificativa final:", "\nJustificativa final:")
        formatted_text = formatted_text.replace("Alternativas (se houver):", "\nAlternativas (se houver):")
        formatted_text = formatted_text.replace("Raciocínio inicial:", "\nRaciocínio inicial:")
        formatted_text = formatted_text.replace("Análise comparativa:", "\nAnálise comparativa:")
        return formatted_text

def main():
    logging.info("Função main iniciada")
    try:
        root = tk.Tk()
        app = FileSearchApp(root)
        logging.info("Aplicação inicializada com sucesso")
        root.mainloop()
    except tk.TclError as e:
        logging.error(f"Erro Tkinter: {str(e)}")
        print(f"Erro ao iniciar a interface gráfica: {str(e)}")
    except Exception as e:
        logging.error(f"Erro inesperado: {str(e)}")
        error_message = f"Ocorreu um erro inesperado:\n{str(e)}\n\nDetalhes:\n{traceback.format_exc()}"
        temp_dir = tempfile.gettempdir()
        error_log_path = os.path.join(temp_dir, "error_log.txt")
        with open(error_log_path, "w") as f:
            f.write(error_message)
        print(f"Erro registrado em: {error_log_path}")
        print(error_message)
    finally:
        logging.info("Aplicação encerrada")
        input("Pressione Enter para fechar...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Erro crítico não capturado: {str(e)}")
        print(f"Erro crítico: {str(e)}")
        traceback.print_exc()