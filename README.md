<<<<<<< HEAD
# 🛡️ AuthGuard & MascoteIA - Google OAuth 2.0 & Mascote Desktop PyQt

Aplicação completa em Python composta por duas frentes integradas:
1. **Painel Web Seguro (Flask)**: Autenticação OAuth 2.0 com Google, Google Calendar API e Gemini Pro com chaves seguras e isoladas.
2. **Mascote Flutuante Desktop (PyQt6)**: Janela sem bordas (*frameless*), sempre no topo (*always-on-top*), fundo transparente, robô animado com física de flutuação e suporte a comandos por **texto** e **áudio via microfone**.

---

## 🤖 Mascote Desktop Flutuante (PyQt6)

O Mascote Desktop é um assistente virtual flutuante e interativo que roda sobreposto à sua área de trabalho:

- **Frameless & Always-on-Top**: Não possui barra de título tradicional e permanece sempre visível acima de qualquer outro programa.
- **Fundo 100% Translúcido**: O robô flutua livremente na tela sem fundos quadrados.
- **Arrasto Suave (Drag & Drop)**: Clique e arraste o robô para qualquer canto ou monitor segurando o botão esquerdo do mouse.
- **Expressões e Animações Dinâmicas**:
  - *IDLE*: Flutuação senoidal suave, olhos OLED ciano, piscar de olhos aleatório e acompanhamento do cursor do mouse.
  - *LISTENING*: Anéis de radar e antena brilhando em âmbar/laranja, pulsando em tempo real conforme a intensidade da sua voz no microfone.
  - *THINKING*: Olhos giratórios em púrpura/violeta durante o processamento do comando ou IA.
  - *SPEAKING*: Olhos felizes (`^ ^`) e ondas sonoras animadas na boca enquanto fala.
  - *ERROR*: Olhos vermelhos caso o áudio não seja compreendido.
- **Comandos de Voz por Microfone**: Gravação e transcrição em português via `sounddevice` e `speech_recognition`.
- **Síntese de Voz Nativa (TTS)**: O robô responde em voz alta através da API SAPI nativa do Windows em thread assíncrona.
- **Menu de Contexto Completo (Botão Direito)**:
  - 🎙️ Falar com Microfone
  - 💬 Alternar Caixa de Texto
  - 🔇 Ativar/Desativar Som
  - 🎨 Trocar Cor dos Olhos/LEDs (Ciano, Roxo Cyberpunk, Verde Matrix, Âmbar)
  - 📍 Reposicionar na tela
  - ❌ Fechar Mascote

### Como Iniciar o Mascote Desktop:

```powershell
.venv\Scripts\python mascot_app.py
```

---

## 🔒 Princípios de Segurança e Blindagem Contra Vazamentos

Este projeto foi construído seguindo as diretrizes da **OWASP** e do Google Identity Security:

| Camada de Segurança | Mecanismo Implementado | O que previne |
| :--- | :--- | :--- |
| **Isolamento de Segredos** | Variáveis de ambiente lidas via `dotenv`, `.gitignore` estrito e `.env.example` sanitizado. | Evita vazamento acidental em repositórios Git públicos ou privados. |
| **Criptografia Simétrica de Tokens** | Credenciais OAuth (`access_token`, `refresh_token`) são criptografadas em repouso com **Fernet (AES-128-CBC + HMAC-SHA256)**. | Impede leitura de tokens mesmo em caso de dump de memória ou acesso ao storage de sessão. |
| **Sessão Server-Side (CacheLib)** | Dados de sessão armazenados exclusivamente no servidor (`instance/flask_session/`), com ID opaco e assinado no cliente. | Tokens nunca trafegam em cookies no navegador do cliente. |
| **Proteção de Cookies** | Cookies configurados com `HttpOnly=True`, `SameSite=Lax` e `Secure=True` em produção. | Bloqueia roubo de sessão via ataques XSS e mitiga requisições CSRF. |
| **Defesa Anti-CSRF no OAuth** | Parâmetro criptográfico `state` de alta entropia (`secrets.token_urlsafe(32)`) gerado na ida e validado no callback. | Impede injeção de credenciais e ataques de troca de conta no fluxo OAuth. |
| **Revogação Ativa de Tokens** | Ao efetuar logout, a aplicação contata `https://oauth2.googleapis.com/revoke` para invalidar a chave diretamente no Google. | Evita reutilização de tokens abandonados. |
| **Headers HTTP de Segurança** | Content-Security-Policy (CSP), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Permissions-Policy`. | Previne Clickjacking, Sniffing de MIME e injeções de script não autorizadas. |
| **Sanitização de Erros e Logs** | Handlers de erro customizados (400, 403, 404, 500) e utilitário de mascaramento de credenciais na UI. | Evita vazamento de stacktraces, caminhos de arquivo ou segredos na tela do usuário. |

---

## 📁 Estrutura do Projeto

```text
d:\MascoteIA\
├── .env                      # Chaves e variáveis reais (NUNCA comitar!)
├── .env.example              # Modelo sanitizado de configuração
├── .gitignore                # Proteção de arquivos confidenciais
├── requirements.txt          # Dependências do projeto
├── config.py                 # Validador e carregador de configurações
├── security.py               # Utilitários criptográficos e headers OWASP
├── app.py                    # Aplicação Flask principal e rotas
├── test_security.py          # Bateria de testes de segurança automatizados
├── services/
│   ├── google_auth.py        # Fluxo OAuth 2.0 (Login, Callback, Refresh, Revoke)
│   ├── google_calendar.py    # Consumo seguro da API Google Calendar
│   └── gemini_service.py     # Cliente oficial Google GenAI (Gemini Pro)
└── templates/
    ├── base.html             # Layout com Tailwind CSS e badges de segurança
    ├── index.html            # Painel interativo de gerenciamento e testes
    └── error.html            # Tratamento visual seguro de exceções
```

---

## 🚀 Como Configurar e Rodar

## 🚀 Experiência Zero-Configuração (1 Único Clique)

A aplicação foi adaptada para **usuários leigos**:
- **Credenciais Pré-Configuradas**: O aplicativo já vem configurado de fábrica com o cliente oficial do Google Desktop ADC, eliminando a necessidade de criar projetos no Google Cloud Console ou preencher IDs e Secrets manuais.
- **Botão Único "Conectar Conta Google"**: Ao clicar no mascote ou no botão de login, o navegador abre **diretamente a tela oficial do Google** para você selecionar seu email e autorizar o acesso.
- **Sincronização Automática**: Assim que você faz o login no navegador, o mascote desktop é liberado na mesma hora, sem exigir nenhuma configuração técnica adicional.

### 2. Obter a Chave do Gemini Pro (Alta Requisição)

1. Acesse o [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Clique em **Get API key** / **Create API key**.
3. Se você possui faturamento ativo ou plano Pro, certifique-se de vincular o projeto do Google Cloud com a forma de pagamento ativada para usufruir dos limites altos de RPM (Requests Per Minute) e TPM (Tokens Per Minute).
4. Copie a chave gerada.

### 3. Configurar o Arquivo `.env`

Abra o arquivo `.env` na raiz do projeto e preencha:

```ini
FLASK_ENV=development
FLASK_SECRET_KEY=sua_chave_secreta_longa
FERNET_ENCRYPTION_KEY=sua_chave_fernet_gerada

BASE_URL=http://localhost:5000
PORT=5000
OAUTHLIB_INSECURE_TRANSPORT=1

# Cole aqui suas credenciais do Google Cloud Console:
GOOGLE_CLIENT_ID=SEU_ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=SEU_SECRET
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/callback

# Cole aqui sua chave Pro do Gemini:
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.5-pro
```

*(Obs: Chaves criptográficas seguras já foram pré-geradas no `.env` local para sua comodidade!)*

### 4. Executar a Aplicação

Se você estiver utilizando o ambiente virtual `.venv` pré-configurado:

```powershell
# Ativar o ambiente virtual (opcional se invocar diretamente o binário)
.venv\Scripts\activate

# Executar a aplicação Flask
python app.py
```

Ou diretamente via comando único:

```powershell
.venv\Scripts\python app.py
```

Abra o navegador em: **`http://localhost:5000`**

---

## 🧪 Testes de Segurança Automatizados

Para validar toda a camada de segurança criptográfica, headers OWASP e proteção anti-CSRF:

```powershell
.venv\Scripts\python test_security.py
```

---

## 🌐 Práticas Recomendadas para Produção

Quando for publicar esta aplicação em um servidor público (ex: VPS, Cloud Run, AWS, Heroku):

1. **Ativar HTTPS Obrigatório**:
   - Altere `FLASK_ENV=production` no `.env`.
   - Defina `OAUTHLIB_INSECURE_TRANSPORT=0`.
   - A URL base passará a ser `https://seudominio.com` e a URI de retorno `https://seudominio.com/auth/callback`.
2. **Servidor WSGI de Produção**:
   - Utilize Gunicorn ou Waitress:
     ```powershell
     pip install waitress
     waitress-serve --port=5000 app:create_app
     ```
3. **Gerenciador de Segredos em Nuvem**:
   - Em produção corporativa, injete as variáveis `GOOGLE_CLIENT_SECRET` e `GEMINI_API_KEY` através do **Google Secret Manager**, **AWS Secrets Manager** ou variáveis do seu provedor de nuvem, nunca salvando em disco.

=======
# MascoteIA
>>>>>>> bb9fad195f1c03f012f471ebb3b4e6534f41cce4
