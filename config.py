"""
Módulo de Configuração Segura
Centraliza o carregamento de variáveis de ambiente com validação,
valores padrão seguros para desenvolvimento, recarregamento dinâmico do .env
e proteção contra vazamentos.
"""

import os
import secrets
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent

# Caminho do arquivo .env
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path, override=True)


class ConfigMeta(type):
    """Metaclasse para permitir acesso dinâmico a propriedades de classe atualizadas em tempo real."""

    @property
    def GEMINI_API_KEY(cls) -> str:
        return cls.get_gemini_api_key()

    @property
    def GEMINI_MODEL(cls) -> str:
        return cls.get_gemini_model()

    @property
    def GOOGLE_CLIENT_ID(cls) -> str:
        return cls.get_google_client_id()

    @property
    def GOOGLE_CLIENT_SECRET(cls) -> str:
        return cls.get_google_client_secret()


class Config(metaclass=ConfigMeta):
    """Configurações centrais da aplicação Flask e APIs Google."""

    # Ambiente
    FLASK_ENV = os.getenv("FLASK_ENV", "development").lower()
    IS_PRODUCTION = FLASK_ENV == "production"

    # Porta e Host
    PORT = int(os.getenv("PORT", 5000))
    BASE_URL = os.getenv("BASE_URL", f"http://localhost:{PORT}").rstrip("/")

    # Chave Secreta da Sessão Flask (Nunca deve ser estática ou vazia em produção)
    _secret_key = os.getenv("FLASK_SECRET_KEY")
    if not _secret_key:
        if IS_PRODUCTION:
            raise ValueError(
                "ERRO CRÍTICO: FLASK_SECRET_KEY obrigatória em ambiente de produção!"
            )
        _secret_key = secrets.token_hex(32)
    SECRET_KEY = _secret_key

    # Chave Fernet para Criptografia de Tokens no Servidor/Sessão
    _fernet_key = os.getenv("FERNET_ENCRYPTION_KEY")
    if not _fernet_key:
        if IS_PRODUCTION:
            raise ValueError(
                "ERRO CRÍTICO: FERNET_ENCRYPTION_KEY obrigatória em produção para criptografar tokens!"
            )
        _fernet_key = Fernet.generate_key().decode()
    FERNET_KEY = _fernet_key.encode() if isinstance(_fernet_key, str) else _fernet_key

    # Configuração de Sessão Server-Side (Flask-Session com CacheLib)
    SESSION_TYPE = "cachelib"
    SESSION_FILE_DIR = str(BASE_DIR / "instance" / "flask_session")
    from cachelib.file import FileSystemCache
    SESSION_CACHELIB = FileSystemCache(cache_dir=SESSION_FILE_DIR, threshold=1000)
    SESSION_PERMANENT = False

    # Segurança dos Cookies de Sessão (Mitigação de XSS e CSRF)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    SESSION_COOKIE_SAMESITE = "Lax"

    # Permissão para OAuth em HTTP local (Apenas em desenvolvimento)
    if not IS_PRODUCTION:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = os.getenv(
            "OAUTHLIB_INSECURE_TRANSPORT", "1"
        )
    else:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "0"

    # Credenciais OAuth 2.0 Google Automáticas para Desktop
    DEFAULT_CLIENT_ID = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
    DEFAULT_CLIENT_SECRET = "d-FL95Q19q7MQmFpd7hHD0Ty"

    GOOGLE_REDIRECT_URI = os.getenv(
        "GOOGLE_REDIRECT_URI", f"{BASE_URL}/auth/callback"
    )

    # Escopos OAuth 2.0 solicitados na autenticação Google
    # Inclui perfil de usuário e escopos completos de leitura e escrita do Google Calendar
    GOOGLE_SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
    ]

    @classmethod
    def get_google_client_id(cls) -> str:
        load_dotenv(dotenv_path=env_path, override=True)
        env_val = os.getenv("GOOGLE_CLIENT_ID", "").strip()
        if env_val and "cole_aqui" not in env_val.lower():
            return env_val
        return cls.DEFAULT_CLIENT_ID

    @classmethod
    def get_google_client_secret(cls) -> str:
        load_dotenv(dotenv_path=env_path, override=True)
        env_val = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
        if env_val and "cole_aqui" not in env_val.lower():
            return env_val
        return cls.DEFAULT_CLIENT_SECRET

    @classmethod
    def get_gemini_api_key(cls) -> str:
        """Captura dinamicamente a chave GEMINI_API_KEY do ambiente ou do arquivo .env."""
        if "GEMINI_API_KEY" in os.environ:
            key = os.environ.get("GEMINI_API_KEY", "").strip()
        elif "GOOGLE_API_KEY" in os.environ:
            key = os.environ.get("GOOGLE_API_KEY", "").strip()
        else:
            key = ""
            try:
                from dotenv import dotenv_values
                vals = dotenv_values(dotenv_path=env_path)
                key = (vals.get("GEMINI_API_KEY") or vals.get("GOOGLE_API_KEY") or "").strip()
                if key:
                    os.environ["GEMINI_API_KEY"] = key
            except Exception:
                pass

        # Remove aspas caso o usuário tenha inserido no .env
        if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
            key = key[1:-1].strip()
        return key

    @classmethod
    def get_gemini_model(cls) -> str:
        """Captura dinamicamente o modelo configurado no ambiente ou no .env (padrão: gemini-1.5-flash)."""
        if "GEMINI_MODEL" in os.environ:
            model = os.environ.get("GEMINI_MODEL", "").strip()
        else:
            model = ""
            try:
                from dotenv import dotenv_values
                vals = dotenv_values(dotenv_path=env_path)
                model = (vals.get("GEMINI_MODEL") or "").strip()
                if model:
                    os.environ["GEMINI_MODEL"] = model
            except Exception:
                pass

        if (model.startswith('"') and model.endswith('"')) or (model.startswith("'") and model.endswith("'")):
            model = model[1:-1].strip()
        return model or "gemini-2.5-flash"

    @classmethod
    def is_oauth_configured(cls) -> bool:
        """Sempre True: o aplicativo já vem com cliente Google Desktop configurado de fábrica."""
        return True

    @classmethod
    def is_gemini_configured(cls) -> bool:
        """Verifica se uma chave de API real do Gemini está presente no .env ou no ambiente."""
        key = cls.get_gemini_api_key().lower()
        return bool(
            key
            and "sua_chave" not in key
            and "cole_aqui" not in key
            and len(key) >= 15
        )

    @classmethod
    def set_gemini_key(cls, gemini_key: str, gemini_model: str = "") -> None:
        """Atualiza a chave do Gemini diretamente no .env e na memória ativa."""
        clean_key = gemini_key.strip()
        updates = {"GEMINI_API_KEY": clean_key}
        if gemini_model:
            updates["GEMINI_MODEL"] = gemini_model.strip()

        cls._persist_env_updates(updates)

    @classmethod
    def update_credentials(
        cls, client_id: str = "", client_secret: str = "", gemini_key: str = "", gemini_model: str = ""
    ) -> None:
        """Atualiza o arquivo .env e a configuração em memória de forma segura e não-destrutiva."""
        updates = {}
        if client_id and "cole_aqui" not in client_id.lower():
            updates["GOOGLE_CLIENT_ID"] = client_id.strip()
        if client_secret and "cole_aqui" not in client_secret.lower():
            updates["GOOGLE_CLIENT_SECRET"] = client_secret.strip()
        if gemini_key and "sua_chave" not in gemini_key.lower():
            updates["GEMINI_API_KEY"] = gemini_key.strip()
        if gemini_model:
            updates["GEMINI_MODEL"] = gemini_model.strip()

        cls._persist_env_updates(updates)

    @classmethod
    def _persist_env_updates(cls, updates: dict) -> None:
        """Escreve as atualizações de variáveis no arquivo .env mantendo comentários existentes."""
        env_file = BASE_DIR / ".env"
        lines = []
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

        updated_keys = set()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in updates:
                    new_lines.append(f"{key}={updates[key]}\n")
                    updated_keys.add(key)
                    continue
            new_lines.append(line)

        for k, v in updates.items():
            if k not in updated_keys:
                new_lines.append(f"{k}={v}\n")

        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        # Atualiza o ambiente em memória imediatamente
        for k, v in updates.items():
            os.environ[k] = v

        load_dotenv(dotenv_path=env_file, override=True)
