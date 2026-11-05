"""
Serviço de Autenticação OAuth 2.0 com Google
Gerencia o fluxo de autorização, troca do authorization code por tokens,
renovação automática (refresh_token) e revogação segura (logout).
"""

import json
from typing import Any, Dict, Optional, Tuple
import requests
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from config import Config


class GoogleAuthService:
    """Encapsula operações do fluxo OAuth 2.0 da Google com foco em segurança."""

    @staticmethod
    def _create_flow(state: Optional[str] = None) -> Flow:
        """Cria e configura a instância do Google OAuth Flow a partir das configs."""
        client_config = {
            "installed": {
                "client_id": Config.GOOGLE_CLIENT_ID,
                "client_secret": Config.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [Config.GOOGLE_REDIRECT_URI, "http://localhost", "http://127.0.0.1"],
            }
        }
        flow = Flow.from_client_config(
            client_config=client_config,
            scopes=Config.GOOGLE_SCOPES,
            state=state,
        )
        flow.redirect_uri = Config.GOOGLE_REDIRECT_URI
        return flow

    @classmethod
    def get_authorization_url(cls, state: str) -> Tuple[str, Optional[str]]:
        """
        Gera a URL de consentimento do Google e o code_verifier PKCE.
        - access_type='offline' garante a emissão do refresh_token.
        - prompt='consent' garante a emissão do refresh_token mesmo se o usuário já autorizou antes.
        """
        flow = cls._create_flow(state=state)
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return authorization_url, flow.code_verifier

    @classmethod
    def exchange_code_for_credentials(
        cls,
        code: str,
        expected_state: str,
        received_state: str,
        code_verifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Troca o authorization code temporário pelos tokens de acesso e renovação.
        Valida estritamente o estado (state) para impedir ataques CSRF e valida com PKCE.
        """
        if not expected_state or expected_state != received_state:
            raise PermissionError("Falha de validação CSRF: state do OAuth inválido ou expirado.")

        flow = cls._create_flow(state=expected_state)
        if code_verifier:
            flow.code_verifier = code_verifier

        flow.fetch_token(code=code)
        credentials = flow.credentials

        return cls.credentials_to_dict(credentials)

    @staticmethod
    def credentials_to_dict(credentials: Credentials) -> Dict[str, Any]:
        """Converte o objeto de Credenciais da Google para formato serializável seguro."""
        return {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
        }

    @classmethod
    def credentials_from_dict(cls, data: Dict[str, Any]) -> Credentials:
        """Reconstrói o objeto Credentials e realiza refresh automático se necessário."""
        credentials = Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri") or "https://oauth2.googleapis.com/token",
            client_id=data.get("client_id") or Config.GOOGLE_CLIENT_ID,
            client_secret=data.get("client_secret") or Config.GOOGLE_CLIENT_SECRET,
            scopes=data.get("scopes") or Config.GOOGLE_SCOPES,
        )

        # Se o token estiver expirado e tivermos refresh_token, renova
        if credentials.expired and credentials.refresh_token:
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)

        return credentials

    @staticmethod
    def fetch_user_info(credentials: Credentials) -> Dict[str, Any]:
        """Recupera dados básicos seguros do perfil (nome, email, avatar)."""
        headers = {"Authorization": f"Bearer {credentials.token}"}
        resp = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        return {
            "name": "Usuário Autenticado",
            "email": "Desconhecido",
            "picture": None,
        }

    @staticmethod
    def revoke_token(token: Optional[str]) -> bool:
        """
        Revoga o token diretamente nos servidores do Google.
        Crucial no logout para garantir que a sessão anterior não possa ser reutilizada.
        """
        if not token:
            return True
        try:
            resp = requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": token},
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            # Em caso de falha de rede na revogação, o descarte local na sessão ainda protege o usuário
            return False

