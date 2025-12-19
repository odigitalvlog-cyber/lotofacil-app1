import kivy
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.core.clipboard import Clipboard
from kivy.graphics import Color, Rectangle, Line
from kivy.clock import Clock
import random
import requests
import threading
import urllib3
import json

# Desabilita avisos SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CORES ---
COR_FUNDO = (0.95, 0.98, 0.95, 1)
COR_PRIMARIA = (0.13, 0.55, 0.13, 1)
COR_SECUNDARIA = (1, 0.84, 0, 1)       # Dourado
COR_TEXTO = (0.2, 0.2, 0.2, 1)
COR_SAIR = (0.8, 0.2, 0.2, 1)
COR_ACERTO = "00aa00"
COR_ERRO = "bbbbbb"

Window.clearcolor = COR_FUNDO

# Valores fixos da Lotofácil
VALORES_FIXOS = {11: 6.00, 12: 12.00, 13: 30.00}
tabela_premios_global = VALORES_FIXOS.copy()

# --- ESTATÍSTICA (TOP 18 NÚMEROS MAIS SORTEADOS) ---
POOL_NUMEROS_QUENTES = [20, 10, 25, 11, 13, 24, 14, 1, 3, 4, 5, 12, 2, 22, 9, 18, 6, 21]

def limpar_valor_moeda(valor):
    try:
        if isinstance(valor, (int, float)): return float(valor)
        if isinstance(valor, str):
            v = valor.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
            return float(v)
    except: return 0.0
    return 0.0

def formatar_moeda(valor):
    try:
        val_float = limpar_valor_moeda(valor)
        if val_float == 0: return "R$ 0,00"
        return f"R$ {val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ --"

def gerar_jogo_lotofacil(qtd_dezenas=15, modo_estrategia="Misto"):
    todos_numeros = set(range(1, 26))
    
    if modo_estrategia == "Aleatório":
        jogo = set(random.sample(list(todos_numeros), qtd_dezenas))
        
    elif modo_estrategia == "Só Fortes":
        pool_disponivel = set(POOL_NUMEROS_QUENTES)
        qtd_do_pool = min(qtd_dezenas, len(pool_disponivel))
        escolhidos = random.sample(list(pool_disponivel), qtd_do_pool)
        jogo = set(escolhidos)
        if len(jogo) < qtd_dezenas:
            faltam = qtd_dezenas - len(jogo)
            resto = todos_numeros - jogo
            jogo.update(random.sample(list(resto), faltam))
            
    else: # Misto
        qtd_quentes = int(qtd_dezenas * 0.70)
        qtd_zebras = qtd_dezenas - qtd_quentes
        escolhidos_quentes = random.sample(POOL_NUMEROS_QUENTES, qtd_quentes)
        pool_zebras = list(todos_numeros - set(POOL_NUMEROS_QUENTES))
        escolhidos_zebras = random.sample(pool_zebras, qtd_zebras)
        jogo = set(escolhidos_quentes + escolhidos_zebras)

    return sorted(jogo)

class CardResultado(BoxLayout):
    def __init__(self, numero_jogo, numeros, **kwargs):
        super().__init__(**kwargs)
        self.numeros_do_jogo = numeros
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 110 
        self.padding = 10
        self.spacing = 5
        
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
            self.cor_borda = Color(0.8, 0.8, 0.8, 1)
            self.borda = Line(rectangle=(self.x, self.y, self.width, self.height), width=1.5)
        self.bind(pos=self.atualizar_rect, size=self.atualizar_rect)

        top_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=35)
        qtd = len(numeros)
        txt_titulo = f"JOGO #{numero_jogo:02} ({qtd} Dezenas)"
        self.lbl_titulo = Label(text=txt_titulo, color=COR_PRIMARIA, bold=True, font_size='14sp', halign='left')
        self.lbl_titulo.bind(size=self.lbl_titulo.setter('text_size'))
        
        self.lbl_acertos = Label(text="", color=(0,0,0,1), font_size='14sp', bold=True, halign='right')
        self.lbl_acertos.bind(size=self.lbl_acertos.setter('text_size'))
        
        top_box.add_widget(self.lbl_titulo)
        top_box.add_widget(self.lbl_acertos)
        self.add_widget(top_box)

        tamanho_fonte = '16sp' if len(numeros) > 17 else '19sp'
        self.lbl_nums = Label(text=self.formatar_numeros_simples(), color=(0,0,0,1), markup=True, font_size=tamanho_fonte, bold=True)
        self.add_widget(self.lbl_nums)

    def formatar_numeros_simples(self):
        return " - ".join(f"{num:02}" for num in self.numeros_do_jogo)

    def conferir(self, sorteio_oficial, tabela_premios):
        """Calcula acertos, atualiza visual e RETORNA o valor ganho"""
        acertos = 0
        texto_formatado = []
        for num in self.numeros_do_jogo:
            if num in sorteio_oficial:
                texto_formatado.append(f"[b][color={COR_ACERTO}]{num:02}[/color][/b]")
                acertos += 1
            else:
                texto_formatado.append(f"[color={COR_ERRO}]{num:02}[/color]")
        
        self.lbl_nums.text = "  ".join(texto_formatado)
        premio_bruto = tabela_premios.get(acertos, 0.0)
        
        # Garante valores fixos se a API falhou
        if premio_bruto == 0 and acertos in VALORES_FIXOS:
            premio_bruto = VALORES_FIXOS[acertos]

        if acertos >= 11:
            valor_fmt = formatar_moeda(premio_bruto)
            self.lbl_acertos.text = f"🏆 {acertos} PONTOS\n{valor_fmt}"
            self.lbl_acertos.color = COR_SECUNDARIA
            self.cor_borda.rgba = COR_SECUNDARIA
            self.borda.width = 3
        else:
            self.lbl_acertos.text = f"{acertos} acertos"
            self.lbl_acertos.color = (0.5, 0.5, 0.5, 1)
            self.cor_borda.rgba = (0.8, 0.8, 0.8, 1)
            self.borda.width = 1.5
            
        return premio_bruto

    def atualizar_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
        self.borda.rectangle = (self.x, self.y, self.width, self.height)

class LotofacilProApp(App):
    def build(self):
        self.title = "LotoFácil Master"
        root = BoxLayout(orientation="vertical", padding=15, spacing=10)

        # 1. Barra Superior
        top_bar = BoxLayout(size_hint_y=None, height=50)
        titulo = Label(text="🍀 LOTO MASTER", font_size='18sp', bold=True, color=COR_PRIMARIA, halign='left')
        titulo.bind(size=titulo.setter('text_size'))
        btn_sair = Button(text="SAIR", size_hint_x=None, width=70, background_normal='', background_color=COR_SAIR, font_size='12sp', bold=True)
        btn_sair.bind(on_press=self.fechar_app)
        top_bar.add_widget(titulo)
        top_bar.add_widget(btn_sair)
        root.add_widget(top_bar)

        # 2. Configurações
        cfg_box = BoxLayout(size_hint_y=None, height=60, spacing=5)
        self.entry_qtd = TextInput(text="5", multiline=False, input_filter='int', halign='center', font_size='20sp', size_hint_x=0.15)
        self.spinner_dezenas = Spinner(text='15', values=('15', '16', '17', '18', '19', '20'), size_hint_x=0.2, background_normal='', background_color=(0.2, 0.6, 0.8, 1), bold=True)
        self.spinner_estrategia = Spinner(text='Misto', values=('Aleatório', 'Misto', 'Só Fortes'), size_hint_x=0.35, background_normal='', background_color=(1, 0.6, 0.2, 1), color=(1,1,1,1), bold=True)
        self.spinner_estrategia.bind(text=self.atualizar_legenda)
        btn_gerar = Button(text="GERAR", background_normal='', background_color=COR_PRIMARIA, bold=True, size_hint_x=0.3)
        btn_gerar.bind(on_press=self.gerar_jogos)
        
        cfg_box.add_widget(self.entry_qtd)
        cfg_box.add_widget(self.spinner_dezenas)
        cfg_box.add_widget(self.spinner_estrategia)
        cfg_box.add_widget(btn_gerar)
        root.add_widget(cfg_box)

        # 3. Legenda da Estratégia
        self.lbl_stats = Label(text="Misto: Equilibra números fortes e zebras.", color=(0.4, 0.4, 0.4, 1), font_size='12sp', size_hint_y=None, height=20)
        root.add_widget(self.lbl_stats)

        # 4. Conferência + DESTAQUE TOTAL GANHO
        conferir_box = BoxLayout(orientation='vertical', size_hint_y=None, height=130)
        
        # --- Painel de Destaque (AGORA É TOTAL GANHO) ---
        self.lbl_total_ganho = Label(text="💰 TOTAL GANHO: R$ 0,00", color=COR_SECUNDARIA, font_size='18sp', bold=True, size_hint_y=None, height=30)
        
        lbl_info = Label(text="Resultado Oficial:", color=COR_TEXTO, size_hint_y=None, height=20, font_size='14sp')
        box_botoes_conf = BoxLayout(spacing=10)
        self.entry_sorteio = TextInput(hint_text="Aguardando...", multiline=False, font_size='14sp')
        self.btn_auto = Button(text="BUSCAR AUTO ($)", size_hint_x=0.45, background_normal='', background_color=(1, 0.5, 0, 1), bold=True)
        self.btn_auto.bind(on_press=self.iniciar_busca_automatica)
        btn_conf = Button(text="OK", size_hint_x=0.2, background_normal='', background_color=(0.2, 0.3, 0.7, 1), bold=True)
        btn_conf.bind(on_press=self.conferir_resultados)
        
        box_botoes_conf.add_widget(self.entry_sorteio)
        box_botoes_conf.add_widget(self.btn_auto)
        box_botoes_conf.add_widget(btn_conf)
        
        conferir_box.add_widget(self.lbl_total_ganho) # Painel no topo
        conferir_box.add_widget(lbl_info)
        conferir_box.add_widget(box_botoes_conf)
        root.add_widget(conferir_box)

        # 5. Lista
        self.scroll = ScrollView()
        self.lista_widgets = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.lista_widgets.bind(minimum_height=self.lista_widgets.setter('height'))
        self.scroll.add_widget(self.lista_widgets)
        root.add_widget(self.scroll)

        # 6. Copiar
        self.btn_copiar = Button(text="Copiar Jogos", size_hint_y=None, height=50, background_normal='', background_color=COR_SECUNDARIA, color=(0,0,0,1), disabled=True)
        self.btn_copiar.bind(on_press=self.copiar)
        root.add_widget(self.btn_copiar)

        self.cache_texto = ""
        return root

    def fechar_app(self, instance):
        App.get_running_app().stop()

    def atualizar_legenda(self, spinner, text):
        if text == 'Aleatório': self.lbl_stats.text = "Sorte pura: Qualquer número pode sair."
        elif text == 'Só Fortes': self.lbl_stats.text = "Agressivo: Usa APENAS os 18 números mais frequentes."
        else: self.lbl_stats.text = "Misto: Equilibra números fortes e zebras."

    def gerar_jogos(self, instance):
        self.lista_widgets.clear_widgets()
        self.cache_texto = ""
        # Reseta o total ganho ao gerar novos jogos
        self.lbl_total_ganho.text = "💰 TOTAL GANHO: R$ 0,00"
        try:
            qtd_jogos = int(self.entry_qtd.text)
            qtd_dezenas = int(self.spinner_dezenas.text)
            modo = self.spinner_estrategia.text
            
            for i in range(1, qtd_jogos + 1):
                jogo = gerar_jogo_lotofacil(qtd_dezenas, modo)
                card = CardResultado(numero_jogo=i, numeros=jogo)
                self.lista_widgets.add_widget(card)
                self.cache_texto += f"Jogo {i:02}: {jogo}\n"
            self.btn_copiar.disabled = False
            self.btn_copiar.text = "Copiar Jogos"
        except ValueError: pass

    def iniciar_busca_automatica(self, instance):
        self.btn_auto.text = "..."
        self.btn_auto.disabled = True
        self.entry_sorteio.text = "Buscando..."
        threading.Thread(target=self.thread_api_blindada).start()

    def thread_api_blindada(self):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
        try:
            url1 = "https://api.guideloterias.com.br/game/lotofacil/latest"
            r = requests.get(url1, headers=headers, verify=False, timeout=8)
            if r.status_code == 200:
                self.processar_dados(r.json(), 'guide')
                return
        except: pass 
        try:
            url2 = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
            r = requests.get(url2, headers=headers, verify=False, timeout=8)
            if r.status_code == 200:
                self.processar_dados(r.json(), 'caixa')
                return
            else:
                Clock.schedule_once(lambda dt: self.pos_busca(f"Erro: {r.status_code}", True))
        except:
            Clock.schedule_once(lambda dt: self.pos_busca("Erro Conexão", True))

    def processar_dados(self, dados, fonte):
        try:
            global tabela_premios_global
            tabela_premios_global = VALORES_FIXOS.copy()
            dezenas = ""

            if fonte == 'guide':
                info = dados.get('data', {})
                dezenas = " ".join(info.get("numbers", []))
                for p in info.get("prizes", []):
                    pts = p.get('hits')
                    val = limpar_valor_moeda(p.get('value'))
                    if pts and val > 0: tabela_premios_global[pts] = val

            elif fonte == 'caixa':
                dezenas = " ".join(dados.get("listaDezenas", []))
                for faixa in dados.get("listaRateioPremio", []):
                    pts = faixa.get("faixaDezenas")
                    val = limpar_valor_moeda(faixa.get("valorPremio"))
                    if pts and val > 0: tabela_premios_global[pts] = val
            
            Clock.schedule_once(lambda dt: self.pos_busca(dezenas, False))
        except:
            Clock.schedule_once(lambda dt: self.pos_busca("Erro Dados", True))

    def pos_busca(self, texto, erro):
        self.entry_sorteio.text = texto
        self.btn_auto.text = "BUSCAR AUTO ($)"
        self.btn_auto.disabled = False
        if not erro: self.conferir_resultados(None)

    def conferir_resultados(self, instance):
        texto_input = self.entry_sorteio.text.replace(',', ' ').replace('-', ' ')
        try:
            sorteio = [int(n) for n in texto_input.split() if n.isdigit()]
            if len(sorteio) < 15:
                if instance: self.entry_sorteio.text = "Erro: Preciso de 15 números!"
                return
            
            total_ganho = 0.0
            
            for card in self.lista_widgets.children:
                if isinstance(card, CardResultado):
                    # O método conferir agora retorna o valor ganho pelo cartão
                    valor_card = card.conferir(sorteio, tabela_premios_global)
                    total_ganho += valor_card
            
            # Atualiza o painel superior com a SOMA
            self.lbl_total_ganho.text = f"💰 TOTAL GANHO: {formatar_moeda(total_ganho)}"
            
        except: self.entry_sorteio.text = "Erro nos números!"

    def copiar(self, instance):
        if self.cache_texto:
            Clipboard.copy(self.cache_texto)
            instance.text = "Copiado!"

if __name__ == "__main__":
    LotofacilProApp().run()