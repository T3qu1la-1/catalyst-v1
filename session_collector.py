
import asyncio
import os
import sqlite3
from telethon import TelegramClient
from telethon.tl.functions.contacts import GetContactsRequest
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
import hashlib
from datetime import datetime
import random

class SessionCollector:
    def __init__(self):
        self.db_path = "database/collected_sessions.db"
        self.sessions_dir = "collected_sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Inicializa o banco de dados para armazenar sessões coletadas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS collected_accounts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER UNIQUE,
            phone TEXT,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            session_file TEXT,
            api_id INTEGER,
            api_hash TEXT,
            status TEXT DEFAULT 'active',
            reports_sent INTEGER DEFAULT 0,
            last_used TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        conn.commit()
        conn.close()
    
    async def collect_from_groups(self, main_api_id, main_api_hash, main_phone):
        """Coleta usuários de grupos públicos grandes"""
        client = TelegramClient(f"{self.sessions_dir}/collector_main", main_api_id, main_api_hash)
        
        try:
            await client.start(phone=main_phone)
            print("✅ Cliente principal conectado")
            
            # Lista de grupos públicos grandes para coletar usuários
            target_groups = [
                "@telegram", "@durov", "@BotsNews", "@TelegramTips",
                "@BotNews", "@BotSupport", "@developers", "@design"
            ]
            
            collected_count = 0
            
            for group in target_groups:
                try:
                    print(f"🔍 Coletando usuários de {group}...")
                    entity = await client.get_entity(group)
                    
                    # Obter participantes
                    participants = await client(GetParticipantsRequest(
                        entity, ChannelParticipantsSearch(''), 0, 100, hash=0
                    ))
                    
                    for user in participants.users:
                        if user.bot or not user.phone:
                            continue
                        
                        # Salvar informações do usuário
                        await self.save_user_info(user)
                        collected_count += 1
                        
                        if collected_count >= 500:  # Limite de coleta
                            break
                    
                    await asyncio.sleep(2)  # Delay entre grupos
                    
                except Exception as e:
                    print(f"❌ Erro ao coletar de {group}: {e}")
                    continue
            
            print(f"✅ Coletados {collected_count} usuários")
            
        except Exception as e:
            print(f"❌ Erro na coleta: {e}")
        finally:
            await client.disconnect()
    
    async def save_user_info(self, user):
        """Salva informações do usuário no banco"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''INSERT OR IGNORE INTO collected_accounts 
                (user_id, phone, username, first_name, last_name, session_file) 
                VALUES (?, ?, ?, ?, ?, ?)''',
                (user.id, user.phone, user.username, user.first_name, 
                 user.last_name, f"user_{user.id}.session"))
            conn.commit()
        except Exception as e:
            print(f"❌ Erro ao salvar usuário {user.id}: {e}")
        finally:
            conn.close()
    
    async def create_session_for_user(self, user_data, api_id, api_hash):
        """Cria uma sessão para um usuário específico"""
        session_path = f"{self.sessions_dir}/{user_data['session_file']}"
        
        try:
            client = TelegramClient(session_path, api_id, api_hash)
            await client.start(phone=user_data['phone'])
            
            # Testar se a sessão funciona
            me = await client.get_me()
            if me:
                print(f"✅ Sessão criada para {user_data['first_name']} (@{user_data['username']})")
                return True
            
        except Exception as e:
            print(f"❌ Erro ao criar sessão para {user_data['phone']}: {e}")
            return False
        finally:
            try:
                await client.disconnect()
            except:
                pass
    
    def get_available_sessions(self, limit=10):
        """Retorna sessões disponíveis para usar nos reports"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''SELECT * FROM collected_accounts 
            WHERE status = 'active' 
            ORDER BY reports_sent ASC, last_used ASC 
            LIMIT ?''', (limit,))
        
        sessions = cursor.fetchall()
        conn.close()
        
        return sessions
    
    def update_session_usage(self, user_id):
        """Atualiza o uso de uma sessão"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''UPDATE collected_accounts 
            SET reports_sent = reports_sent + 1, last_used = ? 
            WHERE user_id = ?''', (datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
    
    def mark_session_invalid(self, user_id):
        """Marca uma sessão como inválida"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''UPDATE collected_accounts 
            SET status = 'invalid' 
            WHERE user_id = ?''', (user_id,))
        
        conn.commit()
        conn.close()

# Função para usar no main.py
async def get_report_sessions(quantity=5):
    """Obtém sessões para usar nos reports"""
    collector = SessionCollector()
    sessions = collector.get_available_sessions(quantity)
    
    valid_clients = []
    
    for session_data in sessions:
        try:
            session_path = f"collected_sessions/{session_data[6]}"  # session_file
            client = TelegramClient(session_path, session_data[7], session_data[8])  # api_id, api_hash
            
            await client.start()
            
            # Verificar se ainda está válido
            me = await client.get_me()
            if me:
                valid_clients.append({
                    'client': client,
                    'user_id': session_data[1],
                    'info': me
                })
                collector.update_session_usage(session_data[1])
            else:
                collector.mark_session_invalid(session_data[1])
                await client.disconnect()
                
        except Exception as e:
            collector.mark_session_invalid(session_data[1])
            print(f"❌ Sessão inválida {session_data[1]}: {e}")
    
    return valid_clients
