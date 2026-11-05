"""
Aplicação Principal Flask - Google OAuth 2.0 & Gemini Pro
Arquitetura segura com:
- Sessão Server-side (Flask-Session)
- Criptografia simétrica de tokens (Fernet)
- Proteção anti-CSRF e Headers OWASP
- Isolamento estrito de variáveis de ambiente
"""

import os
from datetime import datetime, timezone
from flask import (
    Flask,
    render_template,
    redirect,
    request,
    session,
    flash,
    url_for,
    abort,
)
from flask_session import Session

from config import Config
from security import SecurityManager
from services.google_auth import GoogleAuthService
from services.google_calendar import GoogleCalendarService
from services.gemini_service import GeminiService
from services.token_manager import TokenManager

# Instância do gerenciador criptográfico
security_manager = SecurityManager(Config.FERNET_KEY)


def create_app() -> Flask:
    """Fábrica de aplicação Flask com configurações estritas de segurança."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Cria diretório de sessões com segurança
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

    # Inicializa sessão server-side
    Session(app)

    # --------------------------------------------------------------------------
    # Middlewares de Segurança
    # --------------------------------------------------------------------------
    @app.after_request
    def set_security_headers(response):
        """Aplica headers de segurança e desativa cache em rotas confidenciais."""
        response = SecurityManager.apply_security_headers(
            response, is_production=Config.IS_PRODUCTION
        )
        if request.path.startswith(("/auth", "/api")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # --------------------------------------------------------------------------
    # Helpers de Sessão
    # --------------------------------------------------------------------------
    def get_authenticated_credentials():
        """Recupera, descriptografa e atualiza credenciais via TokenManager e sessão."""
        # Prioriza o TokenManager compartilhado entre Web e Desktop
        shared_creds = TokenManager.get_credentials()
        if shared_creds:
            return shared_creds

        encrypted_token = session.get("encrypted_credentials")
        if not encrypted_token:
            return None

        cred_dict = security_manager.decrypt_json(encrypted_token)
        if not cred_dict:
            session.pop("encrypted_credentials", None)
            return None

        try:
            credentials = GoogleAuthService.credentials_from_dict(cred_dict)
            if credentials.token != cred_dict.get("token"):
                updated_dict = GoogleAuthService.credentials_to_dict(credentials)
                session["encrypted_credentials"] = security_manager.encrypt_json(updated_dict)
                TokenManager.save_tokens(updated_dict, session.get("user_info"))
            return credentials
        except Exception:
            session.pop("encrypted_credentials", None)
            return None

    # --------------------------------------------------------------------------
    # Rotas do Painel Principal
    # --------------------------------------------------------------------------
    @app.route("/")
    def index():
        """Exibe o painel de controle com status das conexões e dados da API."""
        # Se recebeu o redirecionamento do Google OAuth na raiz /
        if request.args.get("code"):
            return callback()

        credentials = get_authenticated_credentials()
        is_authenticated = credentials is not None
        user_info = session.get("user_info", {})

        calendar_events = []
        calendar_permission_needed = False
        if is_authenticated:
            try:
                calendar_events = GoogleCalendarService.list_upcoming_events(credentials)
            except PermissionError as e:
                calendar_permission_needed = True
                flash(str(e), "warning")
            except Exception as e:
                err_msg = str(e)
                if "403" in err_msg or "insufficient" in err_msg.lower():
                    calendar_permission_needed = True
                    flash("Permissões insuficientes no Google Calendar. Faça login novamente para autorizar o acesso à agenda.", "warning")
                else:
                    flash(f"Aviso ao carregar Google Agenda: {err_msg}", "warning")

        # Recupera resposta anterior do Gemini se houver
        gemini_result = session.pop("gemini_result", None)

        return render_template(
            "index.html",
            is_authenticated=is_authenticated,
            user_info=user_info,
            oauth_ready=Config.is_oauth_configured(),
            gemini_ready=Config.is_gemini_configured(),
            gemini_model=Config.GEMINI_MODEL,
            gemini_key_masked=SecurityManager.mask_string(Config.GEMINI_API_KEY),
            redirect_uri=Config.GOOGLE_REDIRECT_URI,
            calendar_events=calendar_events,
            calendar_permission_needed=calendar_permission_needed,
            gemini_result=gemini_result,
        )

    # --------------------------------------------------------------------------
    # Fluxo OAuth 2.0 (Google Identity)
    # --------------------------------------------------------------------------
    @app.route("/setup", methods=["POST"])
    def setup_credentials():
        """Salva as credenciais do Google Cloud fornecidas pelo formulário ou upload de JSON."""
        import json

        client_id = request.form.get("google_client_id", "").strip()
        client_secret = request.form.get("google_client_secret", "").strip()
        gemini_key = request.form.get("gemini_api_key", "").strip()
        gemini_model = request.form.get("gemini_model", "").strip()

        # Verifica se o usuário fez upload do arquivo client_secret.json
        uploaded_file = request.files.get("credentials_json")
        if uploaded_file and uploaded_file.filename:
            try:
                data = json.load(uploaded_file.stream)
                client_info = data.get("web") or data.get("installed") or data
                client_id = client_info.get("client_id", client_id)
                client_secret = client_info.get("client_secret", client_secret)
            except Exception as e:
                flash(f"Erro ao ler o arquivo JSON de credenciais: {e}", "error")
                return redirect(url_for("index"))

        # Atualiza credenciais no .env
        Config.update_credentials(
            client_id=client_id,
            client_secret=client_secret,
            gemini_key=gemini_key,
            gemini_model=gemini_model,
        )

        if gemini_key and not client_id and not client_secret:
            flash("Chave GEMINI_API_KEY atualizada com sucesso no .env!", "success")
            return redirect(url_for("index"))

        flash("Credenciais configuradas com sucesso no .env! Iniciando autenticação com o Google...", "success")
        return redirect(url_for("login"))

    @app.route("/auth/login")
    def login():
        """Inicia o fluxo OAuth 2.0 automático com a Google e proteção anti-CSRF."""
        # Gera token criptográfico único para validar o callback e impedir CSRF
        state = SecurityManager.generate_csrf_state()
        session["oauth_state"] = state

        authorization_url, code_verifier = GoogleAuthService.get_authorization_url(state=state)
        session["code_verifier"] = code_verifier

        return redirect(authorization_url)

    @app.route("/auth/callback")
    def callback():
        """Trata o redirecionamento do Google, valida state e troca code por tokens."""
        error = request.args.get("error")
        if error:
            flash(f"Acesso não concedido pelo Google: {error}", "error")
            return redirect(url_for("index"))

        code = request.args.get("code")
        received_state = request.args.get("state")
        expected_state = session.pop("oauth_state", None)
        code_verifier = session.pop("code_verifier", None)

        if not code or not received_state:
            flash("Parâmetros de autenticação inválidos no retorno do Google.", "error")
            return redirect(url_for("index"))

        try:
            # Valida CSRF, PKCE e obtém tokens
            cred_dict = GoogleAuthService.exchange_code_for_credentials(
                code=code,
                expected_state=expected_state,
                received_state=received_state,
                code_verifier=code_verifier,
            )

            # Reconstrói objeto Credentials para buscar perfil do usuário
            credentials = GoogleAuthService.credentials_from_dict(cred_dict)
            user_info = GoogleAuthService.fetch_user_info(credentials)

            # Criptografa credenciais antes de armazenar na sessão server-side
            session["encrypted_credentials"] = security_manager.encrypt_json(cred_dict)
            session["user_info"] = user_info

            # Sincroniza imediatamente com o TokenManager central (para o Mascote Desktop)
            TokenManager.save_tokens(cred_dict, user_info)

            # Se a requisição veio do Mascote Desktop ou navegador direto, exibe tela de sucesso
            return render_template("auth_success.html", user_info=user_info)
        except PermissionError as e:
            flash(str(e), "error")
        except Exception as e:
            flash(f"Falha na troca de credenciais OAuth: {str(e)}", "error")

        return redirect(url_for("index"))

    @app.route("/auth/logout")
    def logout():
        """Encerra a sessão e revoga o token no servidor do Google e no TokenManager."""
        TokenManager.revoke_and_clear()
        session.clear()
        flash("Sessão finalizada com sucesso e token revogado no Google.", "success")
        return redirect(url_for("index"))

    @app.route("/auth/status")
    def auth_status():
        """Retorna o estado de autenticação em formato JSON para o Mascote Desktop."""
        is_auth = TokenManager.is_authenticated()
        user_info = TokenManager.get_user_info() if is_auth else None
        return {
            "authenticated": is_auth,
            "user": user_info,
        }

    # --------------------------------------------------------------------------
    # Rotas de Integração: Google Calendar
    # --------------------------------------------------------------------------
    @app.route("/api/calendar/refresh", methods=["POST"])
    def calendar_refresh():
        """Atualiza a lista de eventos da agenda."""
        return redirect(url_for("index"))

    @app.route("/api/calendar/create", methods=["POST"])
    def calendar_create():
        """Agenda um novo compromisso na agenda do usuário conectado."""
        credentials = get_authenticated_credentials()
        if not credentials:
            flash("Você precisa estar autenticado com o Google para agendar compromissos.", "error")
            return redirect(url_for("index"))

        summary = request.form.get("summary", "").strip()
        start_time = request.form.get("start_time", "").strip()
        end_time = request.form.get("end_time", "").strip()
        description = request.form.get("description", "").strip()

        if not summary or not start_time or not end_time:
            flash("Preencha o título e as datas de início e término.", "warning")
            return redirect(url_for("index"))

        try:
            # Converte inputs para formato ISO 8601
            start_iso = datetime.fromisoformat(start_time).astimezone().isoformat()
            end_iso = datetime.fromisoformat(end_time).astimezone().isoformat()

            created = GoogleCalendarService.create_event(
                credentials=credentials,
                summary=summary,
                start_time_iso=start_iso,
                end_time_iso=end_iso,
                description=description,
            )
            flash(f"Evento '{created['summary']}' agendado com sucesso na sua conta Google!", "success")
        except Exception as e:
            flash(f"Erro ao criar evento na agenda: {str(e)}", "error")

        return redirect(url_for("index"))

    # --------------------------------------------------------------------------
    # Rotas de Integração: Gemini Pro / Flash API
    # --------------------------------------------------------------------------
    @app.route("/api/gemini/configure", methods=["POST"])
    def gemini_configure():
        """Salva a chave GEMINI_API_KEY e o modelo no .env em tempo real."""
        gemini_key = request.form.get("gemini_api_key", "").strip()
        gemini_model = request.form.get("gemini_model", "").strip()

        if not gemini_key:
            flash("Informe uma chave GEMINI_API_KEY válida para salvar.", "warning")
            return redirect(url_for("index"))

        Config.set_gemini_key(gemini_key=gemini_key, gemini_model=gemini_model)
        flash("Chave GEMINI_API_KEY salva com sucesso no .env e ativada imediatamente!", "success")
        return redirect(url_for("index"))

    @app.route("/api/gemini/prompt", methods=["POST"])
    def gemini_prompt():
        """Executa consultas reais ao Gemini usando as chaves de ambiente seguras."""
        is_ajax = (
            request.is_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or "application/json" in request.headers.get("Accept", "")
        )
        json_data = request.get_json(silent=True) or {}
        prompt = (json_data.get("prompt") or request.form.get("prompt", "")).strip()
        action = json_data.get("action") or request.form.get("action", "generate")

        if not prompt:
            msg = "Por favor, digite um prompt para o Gemini."
            if is_ajax:
                return {"success": False, "error": msg, "text": msg}, 400
            flash(msg, "warning")
            return redirect(url_for("index"))

        if not Config.is_gemini_configured():
            msg = "Configure GEMINI_API_KEY no arquivo .env para consultar o Gemini."
            if is_ajax:
                return {"success": False, "error": msg, "text": msg}, 400
            flash(msg, "error")
            return redirect(url_for("index"))

        try:
            if action == "analyze_calendar":
                credentials = get_authenticated_credentials()
                events = []
                if credentials:
                    try:
                        events = GoogleCalendarService.list_upcoming_events(credentials)
                    except Exception:
                        pass
                result = GeminiService.analyze_calendar_with_ai(events=events, user_question=prompt)
            else:
                result = GeminiService.generate_response(prompt=prompt)

            if is_ajax:
                status_code = 200 if result.get("success") else 500
                return result, status_code

            if result.get("success"):
                session["gemini_result"] = result
                flash(f"Resposta gerada com sucesso pelo Gemini ({result.get('model', 'IA')})!", "success")
            else:
                flash(result.get("text") or result.get("error", "Erro ao consultar Gemini."), "error")

        except Exception as e:
            err_msg = f"Falha na chamada ao Gemini: {str(e)}"
            if is_ajax:
                return {"success": False, "error": err_msg, "text": err_msg}, 500
            flash(err_msg, "error")

        return redirect(url_for("index"))

    # --------------------------------------------------------------------------
    # Tratamento Seguro de Erros (Evita vazar stacktraces aos clientes)
    # --------------------------------------------------------------------------
    @app.errorhandler(400)
    def bad_request(e):
        return render_template("error.html", error_title="Requisição Inválida (400)", error_message="Os dados enviados são inválidos."), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", error_title="Acesso Negado (403)", error_message="Você não possui permissão para acessar este recurso."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", error_title="Página Não Encontrada (404)", error_message="O endereço solicitado não existe."), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("error.html", error_title="Erro Interno (500)", error_message="Ocorreu um erro no servidor. Verifique os logs internos."), 500

    return app


if __name__ == "__main__":
    app = create_app()
    print(f"\n========================================================")
    print(f"  🔐 Servidor Seguro Iniciado na porta {Config.PORT}")
    print(f"  🌐 URL do Painel: {Config.BASE_URL}")
    print(f"  📌 Redirecionamento OAuth: {Config.GOOGLE_REDIRECT_URI}")
    print(f"  🛡️ Criptografia Fernet & Sessão Server-side Ativas")
    print(f"========================================================\n")
    app.run(host="127.0.0.1", port=Config.PORT, debug=(Config.FLASK_ENV == "development"))
