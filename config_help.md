
# 🔧 Como Configurar o Bot

## ⚠️ IMPORTANTE: Configure as Variáveis de Ambiente

Para o bot funcionar, você precisa configurar as seguintes variáveis no **Secrets** do Replit:

### 1. Obter API_ID e API_HASH do Telegram

1. Acesse [https://my.telegram.org](https://my.telegram.org)
2. Faça login com seu número de telefone
3. Vá em "API Development Tools"
4. Crie um novo app (se não tiver)
5. Copie o `API ID` e `API Hash`

### 2. Criar um Bot no Telegram

1. Converse com [@BotFather](https://t.me/BotFather) no Telegram
2. Digite `/newbot`
3. Escolha um nome e username para seu bot
4. Copie o **token** que será fornecido

### 3. Configurar no Replit

1. Abra a aba **"Secrets"** no painel lateral do Replit
2. Adicione as seguintes chaves:

```
API_ID = seu_api_id_aqui
API_HASH = seu_api_hash_aqui
BOT_TOKEN = seu_bot_token_aqui
MEU_ID = seu_id_telegram_aqui (opcional)
```

### 4. Reiniciar o Bot

Após configurar, clique em **"Run"** novamente.

## ✅ Comandos Disponíveis

- `/start` - Iniciar o bot
- `/search [url]` - Buscar logins
- `/report` - Reports do Telegram
- `/reportwpp` - Reports do WhatsApp
- `/reset` - Resetar dados
