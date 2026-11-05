"""
Gerenciador Central de Tokens e Autenticação Google
Armazena, renova e compartilha as credenciais OAuth 2.0 criptografadas
entre o Servidor Web Flask e a Aplicação Desktop MascoteIA.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional
from google.oauth2.credentials import Credentials
import google.auth.transport.requests

from config import Config, BASE_DIR
from security import SecurityManager

security_manager = SecurityManager(Config.FERNET_KEY)
TOKEN_FILE = Path(BASE_DIR) / "instance" / "google_credentials.enc"


class TokenManager:
    """Gerenciador seguro de persistência e ciclo de vida dos tokens OAuth."""

    @classmethod
    def get_token_file_path(cls) -> Path:
        os.makedirs(TOKEN_FILE.parent, exist_ok=True)
        return TOKEN_FILE

    @classmethod
    def save_tokens(cls, cred_dict: Dict[str, Any], user_info: Optional[Dict[str, Any]] = None) -> bool:
        """Criptografa e salva as credenciais e dados do usuário em disco."""
        try:
            payload = {
                "credentials": cred_dict,
                "user_info": user_info or {},
            }
            encrypted_str = security_manager.encrypt_json(payload)
            path = cls.get_token_file_path()
            with open(path, "w", encoding="utf-8") as f:
                f.write(encrypted_str)
            return True
        except Exception as e:
            print(f"[TokenManager] Erro ao salvar tokens criptografados: {e}")
            return False

    @classmethod
    def load_data(cls) -> Optional[Dict[str, Any]]:
        """Lê e descriptografa os dados salvos."""
        path = cls.get_token_file_path()
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                encrypted_str = f.read().strip()
            return security_manager.decrypt_json(encrypted_str)
        except Exception:
            return None

    @classmethod
    def get_user_info(cls) -> Optional[Dict[str, Any]]:
        """Retorna o perfil do usuário Google conectado (nome, email, avatar)."""
        data = cls.load_data()
        if data and "user_info" in data:
            return data["user_info"]
        return None

    @classmethod
    def get_credentials(cls) -> Optional[Credentials]:
        """
        Retorna o objeto Credentials pronto para consumo de APIs.
        Realiza refresh automático se o access_token estiver expirado.
        """
        data = cls.load_data()
        if not data or "credentials" not in data:
            return None

        cred_dict = data["credentials"]
        try:
            credentials = Credentials(
                token=cred_dict.get("token"),
                refresh_token=cred_dict.get("refresh_token"),
                token_uri=cred_dict.get("token_uri") or "https://oauth2.googleapis.com/token",
                client_id=cred_dict.get("client_id") or Config.GOOGLE_CLIENT_ID,
                client_secret=cred_dict.get("client_secret") or Config.GOOGLE_CLIENT_SECRET,
                scopes=cred_dict.get("scopes") or Config.GOOGLE_SCOPES,
            )

            # Se expirou, renova o access token com o Google
            if credentials.expired and credentials.refresh_token:
                request = google.auth.transport.requests.Request()
                credentials.refresh(request)
                # Salva a nova chave atualizada
                from services.google_auth import GoogleAuthService
                updated_dict = GoogleAuthService.credentials_to_dict(credentials)
                cls.save_tokens(updated_dict, data.get("user_info"))

            return credentials
        except Exception as e:
            print(f"[TokenManager] Falha ao reconstruir credenciais: {e}")
            return None

    @classmethod
    def is_authenticated(cls) -> bool:
        """Verifica se existe uma conta Google autenticada e com token válido."""
        creds = cls.get_credentials()
        return creds is not None and bool(creds.token)

    @classmethod
    def get_access_token(cls) -> Optional[str]:
        """Retorna o access token atual da conta Google logada."""
        creds = cls.get_credentials()
        return creds.token if creds else None

    @classmethod
    def revoke_and_clear(cls) -> bool:
        """Revoga no Google e apaga o arquivo criptografado de tokens."""
        creds = cls.get_credentials()
        if creds and creds.token:
            from services.google_auth import GoogleAuthService
            GoogleAuthService.revoke_token(creds.token)

        path = cls.get_token_file_path()
        if path.exists():
            try:
                os.remove(path)
            except OSError:
                pass
        return True
