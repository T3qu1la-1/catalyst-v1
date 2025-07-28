
#!/usr/bin/env python3
"""
Script para gerenciar o sistema de coleta de sessões
"""

import asyncio
import sys
from session_collector import SessionCollector

async def main_menu():
    collector = SessionCollector()
    
    while True:
        print("\n" + "="*50)
        print("🤖 GERENCIADOR DE SESSÕES COLETADAS")
        print("="*50)
        print("1. Coletar usuários de grupos públicos")
        print("2. Criar sessões para usuários coletados")
        print("3. Listar sessões disponíveis")
        print("4. Testar sessões")
        print("5. Limpar sessões inválidas")
        print("6. Sair")
        print("="*50)
        
        choice = input("Escolha uma opção: ").strip()
        
        if choice == "1":
            api_id = int(input("Digite seu API ID: "))
            api_hash = input("Digite seu API Hash: ")
            phone = input("Digite seu telefone (+55...): ")
            
            await collector.collect_from_groups(api_id, api_hash, phone)
            
        elif choice == "2":
            print("⚠️ Esta funcionalidade requer configuração manual")
            print("As sessões são criadas automaticamente quando necessário")
            
        elif choice == "3":
            sessions = collector.get_available_sessions(50)
            print(f"\n📊 Sessões disponíveis: {len(sessions)}")
            
            for i, session in enumerate(sessions[:10], 1):
                print(f"{i}. ID: {session[1]} | Nome: {session[4]} {session[5]} | Reports: {session[9]}")
            
            if len(sessions) > 10:
                print(f"... e mais {len(sessions) - 10} sessões")
                
        elif choice == "4":
            print("🧪 Função de teste em desenvolvimento")
            
        elif choice == "5":
            # Implementar limpeza de sessões inválidas
            print("🧹 Limpeza de sessões inválidas em desenvolvimento")
            
        elif choice == "6":
            print("👋 Saindo...")
            break
            
        else:
            print("❌ Opção inválida!")

if __name__ == "__main__":
    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        print("\n👋 Programa finalizado pelo usuário")
