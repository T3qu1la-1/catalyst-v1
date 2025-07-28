
import asyncio
import json
import random
import time
from telethon import TelegramClient
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.types import (
    InputReportReasonSpam,
    InputReportReasonFake,
    InputReportReasonViolence,
    InputReportReasonPornography,
    InputReportReasonChildAbuse,
    InputReportReasonCopyright,
    InputReportReasonIllegalDrugs,
    InputReportReasonPersonalDetails,
    InputReportReasonOther
)

# Configurações das contas
ACCOUNTS = [
    {
        'api_id': '23877053',
        'api_hash': '989c360358b981dae46a910693ab2f4c',
        'phone': '+5511999999999',
        'session_name': 'account1'
    },
    {
        'api_id': '25317254',
        'api_hash': 'bef2f48bb6b4120c9189ecfd974eb820',
        'phone': '+5511888888888',
        'session_name': 'account2'
    },
    # Adicione mais contas conforme necessário
]

# Razões de report disponíveis
REPORT_REASONS = {
    1: ("I don't like it", InputReportReasonOther()),
    2: ("Child abuse", InputReportReasonChildAbuse()),
    3: ("Violence", InputReportReasonViolence()),
    4: ("Illegal goods", InputReportReasonIllegalDrugs()),
    5: ("Illegal adult content", InputReportReasonPornography()),
    6: ("Personal data", InputReportReasonPersonalDetails()),
    7: ("Terrorism", InputReportReasonViolence()),
    8: ("Scam or spam", InputReportReasonSpam()),
    9: ("Copyright", InputReportReasonCopyright()),
    10: ("Other", InputReportReasonOther())
}

class MassReportSystem:
    def __init__(self):
        self.clients = []
        self.active_accounts = 0
        
    async def initialize_accounts(self):
        """Inicializa todas as contas configuradas"""
        print("🔄 Inicializando contas...")
        
        for i, account in enumerate(ACCOUNTS):
            try:
                client = TelegramClient(
                    f"sessions/{account['session_name']}", 
                    account['api_id'], 
                    account['api_hash']
                )
                
                await client.start(phone=account['phone'])
                
                # Verificar se a conta está funcionando
                me = await client.get_me()
                print(f"✅ Conta {i+1} conectada: {me.first_name} (@{me.username})")
                
                self.clients.append({
                    'client': client,
                    'info': me,
                    'account_data': account
                })
                self.active_accounts += 1
                
            except Exception as e:
                print(f"❌ Erro ao conectar conta {i+1}: {e}")
                continue
        
        print(f"📊 Total de contas ativas: {self.active_accounts}")
        return self.active_accounts > 0

    async def report_target(self, target_username, reason_id, reports_per_account=5, delay_between_reports=2):
        """Reporta um alvo usando todas as contas ativas"""
        if not self.clients:
            print("❌ Nenhuma conta ativa!")
            return False
            
        if reason_id not in REPORT_REASONS:
            print("❌ ID de razão inválido!")
            return False
            
        reason_text, reason_obj = REPORT_REASONS[reason_id]
        
        # Adicionar @ se não tiver
        if not target_username.startswith('@'):
            target_username = '@' + target_username
        
        print(f"🎯 Iniciando reports para: {target_username}")
        print(f"⚠️ Razão: {reason_text}")
        print(f"🔢 Reports por conta: {reports_per_account}")
        print(f"👥 Contas ativas: {self.active_accounts}")
        print(f"📊 Total de reports: {self.active_accounts * reports_per_account}")
        
        total_success = 0
        total_errors = 0
        
        # Processar cada conta
        for i, account_data in enumerate(self.clients):
            client = account_data['client']
            user_info = account_data['info']
            
            print(f"\n📱 Processando conta {i+1}: {user_info.first_name}")
            
            try:
                # Obter entidade do alvo
                target_entity = await client.get_entity(target_username)
                target_name = getattr(target_entity, 'title', getattr(target_entity, 'first_name', target_username))
                
                # Enviar reports desta conta
                for report_num in range(reports_per_account):
                    try:
                        await client(ReportPeerRequest(
                            peer=target_entity,
                            reason=reason_obj,
                            message=f"Reported for {reason_text}"
                        ))
                        
                        total_success += 1
                        print(f"   ✅ Report {report_num + 1}/{reports_per_account} enviado")
                        
                        # Delay entre reports
                        if report_num < reports_per_account - 1:
                            await asyncio.sleep(delay_between_reports + random.uniform(0.5, 1.5))
                            
                    except Exception as e:
                        total_errors += 1
                        print(f"   ❌ Erro no report {report_num + 1}: {e}")
                        continue
                
                # Delay entre contas
                if i < len(self.clients) - 1:
                    delay = random.uniform(5, 10)
                    print(f"   ⏳ Aguardando {delay:.1f}s antes da próxima conta...")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                print(f"   ❌ Erro ao processar conta {i+1}: {e}")
                total_errors += reports_per_account
                continue
        
        # Estatísticas finais
        print(f"\n📊 RELATÓRIO FINAL:")
        print(f"✅ Reports enviados com sucesso: {total_success}")
        print(f"❌ Erros: {total_errors}")
        print(f"🎯 Taxa de sucesso: {(total_success/(total_success+total_errors)*100):.1f}%")
        
        return total_success > 0

    async def report_multiple_targets(self, targets_file, reason_id, reports_per_account=5):
        """Reporta múltiplos alvos de um arquivo"""
        try:
            with open(targets_file, 'r', encoding='utf-8') as f:
                targets = [line.strip() for line in f if line.strip()]
            
            print(f"📋 Carregados {len(targets)} alvos do arquivo")
            
            for i, target in enumerate(targets, 1):
                print(f"\n🎯 Processando alvo {i}/{len(targets)}: {target}")
                
                success = await self.report_target(target, reason_id, reports_per_account)
                
                if not success:
                    print(f"⚠️ Falha ao reportar {target}")
                
                # Delay entre alvos
                if i < len(targets):
                    delay = random.uniform(30, 60)
                    print(f"⏳ Aguardando {delay:.1f}s antes do próximo alvo...")
                    await asyncio.sleep(delay)
                    
        except FileNotFoundError:
            print(f"❌ Arquivo {targets_file} não encontrado!")
        except Exception as e:
            print(f"❌ Erro ao processar arquivo: {e}")

    async def report_post(self, post_link, reason_id, reports_per_account=5):
        """Reporta um post específico"""
        if not post_link.startswith("https://t.me/"):
            print("❌ Link deve começar com https://t.me/")
            return False
            
        try:
            # Extrair canal e ID da mensagem
            parts = post_link.replace("https://t.me/", "").split("/")
            if len(parts) != 2 or not parts[1].isdigit():
                print("❌ Formato de link inválido")
                return False
                
            channel_username = parts[0]
            message_id = int(parts[1])
            
            reason_text, reason_obj = REPORT_REASONS[reason_id]
            
            print(f"🎯 Reportando post: {post_link}")
            print(f"📢 Canal: @{channel_username}")
            print(f"📝 Mensagem ID: {message_id}")
            print(f"⚠️ Razão: {reason_text}")
            
            total_success = 0
            total_errors = 0
            
            for i, account_data in enumerate(self.clients):
                client = account_data['client']
                user_info = account_data['info']
                
                print(f"\n📱 Processando conta {i+1}: {user_info.first_name}")
                
                try:
                    channel = await client.get_entity(channel_username)
                    
                    for report_num in range(reports_per_account):
                        try:
                            await client(ReportPeerRequest(
                                peer=channel,
                                reason=reason_obj,
                                message=f"Reported post ID {message_id} for {reason_text}"
                            ))
                            
                            total_success += 1
                            print(f"   ✅ Report {report_num + 1}/{reports_per_account} enviado")
                            
                            await asyncio.sleep(2 + random.uniform(0.5, 1.5))
                            
                        except Exception as e:
                            total_errors += 1
                            print(f"   ❌ Erro no report {report_num + 1}: {e}")
                            continue
                    
                    if i < len(self.clients) - 1:
                        await asyncio.sleep(random.uniform(5, 10))
                        
                except Exception as e:
                    print(f"   ❌ Erro ao processar conta {i+1}: {e}")
                    total_errors += reports_per_account
                    continue
            
            print(f"\n📊 RELATÓRIO FINAL:")
            print(f"✅ Reports enviados: {total_success}")
            print(f"❌ Erros: {total_errors}")
            
            return total_success > 0
            
        except Exception as e:
            print(f"❌ Erro ao reportar post: {e}")
            return False

    async def close_all_sessions(self):
        """Fecha todas as sessões ativas"""
        print("🔄 Fechando sessões...")
        for account_data in self.clients:
            try:
                await account_data['client'].disconnect()
            except:
                pass
        print("✅ Todas as sessões fechadas")

async def main():
    import os
    
    # Criar diretório de sessões
    os.makedirs("sessions", exist_ok=True)
    
    system = MassReportSystem()
    
    try:
        # Inicializar contas
        if not await system.initialize_accounts():
            print("❌ Nenhuma conta pôde ser inicializada!")
            return
        
        while True:
            print("\n" + "="*50)
            print("🤖 MASS REPORT SYSTEM")
            print("="*50)
            print("1. Reportar usuário/canal")
            print("2. Reportar post específico")
            print("3. Reportar múltiplos alvos (arquivo)")
            print("4. Listar razões de report")
            print("5. Sair")
            print("="*50)
            
            choice = input("Escolha uma opção: ").strip()
            
            if choice == "1":
                target = input("Digite o username do alvo (@usuario): ").strip()
                
                print("\nRazões disponíveis:")
                for num, (reason, _) in REPORT_REASONS.items():
                    print(f"{num}. {reason}")
                
                try:
                    reason_id = int(input("ID da razão: "))
                    reports_per_account = int(input("Reports por conta (padrão: 5): ") or "5")
                    
                    await system.report_target(target, reason_id, reports_per_account)
                except ValueError:
                    print("❌ Valores inválidos!")
                    
            elif choice == "2":
                post_link = input("Cole o link do post: ").strip()
                
                print("\nRazões disponíveis:")
                for num, (reason, _) in REPORT_REASONS.items():
                    print(f"{num}. {reason}")
                
                try:
                    reason_id = int(input("ID da razão: "))
                    reports_per_account = int(input("Reports por conta (padrão: 5): ") or "5")
                    
                    await system.report_post(post_link, reason_id, reports_per_account)
                except ValueError:
                    print("❌ Valores inválidos!")
                    
            elif choice == "3":
                targets_file = input("Nome do arquivo com alvos (um por linha): ").strip()
                
                print("\nRazões disponíveis:")
                for num, (reason, _) in REPORT_REASONS.items():
                    print(f"{num}. {reason}")
                
                try:
                    reason_id = int(input("ID da razão: "))
                    reports_per_account = int(input("Reports por conta (padrão: 5): ") or "5")
                    
                    await system.report_multiple_targets(targets_file, reason_id, reports_per_account)
                except ValueError:
                    print("❌ Valores inválidos!")
                    
            elif choice == "4":
                print("\n📋 RAZÕES DE REPORT:")
                for num, (reason, _) in REPORT_REASONS.items():
                    print(f"  {num}. {reason}")
                    
            elif choice == "5":
                break
                
            else:
                print("❌ Opção inválida!")
                
    except KeyboardInterrupt:
        print("\n👋 Programa interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro crítico: {e}")
    finally:
        await system.close_all_sessions()

if __name__ == "__main__":
    asyncio.run(main())
