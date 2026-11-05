"""
Módulo de Segurança e Criptografia
Implementa:
1. Criptografia simétrica com Fernet (AES-128-CBC + HMAC-SHA256) para tokens de acesso/refresh.
2. Geração e validação de tokens anti-CSRF (OAuth State).
3. Headers HTTP de segurança (OWASP) e proteção contra vazamento de cabeçalhos confidenciais.
4. Funções de mascaramento de chaves para auditoria visual sem risco de vazamento.
"""

import json
import secrets
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet, InvalidToken
from flask import Response


class SecurityManager:
    """Gerenciador de utilitários criptográficos e proteção contra vazamentos."""

    def __init__(self, fernet_key: bytes):
        self.fernet = Fernet(fernet_key)

    def encrypt_json(self, data: Dict[str, Any]) -> str:
        """Criptografa um dicionário Python (ex: credenciais OAuth) para string segura."""
        raw_bytes = json.dumps(data).encode("utf-8")
        encrypted_bytes = self.fernet.encrypt(raw_bytes)
        return encrypted_bytes.decode("utf-8")

    def decrypt_json(self, encrypted_str: str) -> Optional[Dict[str, Any]]:
        """Descriptografa uma string encriptada de volta para dicionário."""
        if not encrypted_str:
            return None
        try:
            decrypted_bytes = self.fernet.decrypt(encrypted_str.encode("utf-8"))
            return json.loads(decrypted_bytes.decode("utf-8"))
        except (InvalidToken, json.JSONDecodeError, ValueError):
            return None

    @staticmethod
    def generate_csrf_state() -> str:
        """Gera um token criptograficamente seguro para o parâmetro `state` do OAuth 2.0."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def mask_string(val: Optional[str], visible_start: int = 4, visible_end: int = 4) -> str:
        """
        Mascara strings sensíveis (chaves de API, Client IDs, tokens) para exibição segura.
        Exemplo: 'AIzaSyD-1234567890abcdef' -> 'AIza...cdef [MASCARADO]'
        """
        if not val:
            return "[NÃO CONFIGURADO]"
        val_str = str(val).strip()
        if len(val_str) <= (visible_start + visible_end):
            return "[PROTEGIDO]"
        return f"{val_str[:visible_start]}...{val_str[-visible_end:]} (protegido)"

    @staticmethod
    def apply_security_headers(response: Response, is_production: bool = False) -> Response:
        """Aplica cabeçalhos HTTP de segurança estritos recomendados pela OWASP."""
        # Evita detecção incorreta de MIME-type (MIME-Sniffing)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Previne que a página seja aberta dentro de iframes (Clickjacking)
        response.headers["X-Frame-Options"] = "DENY"

        # Ativa proteção contra cross-site scripting em navegadores legados
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Controla quais informações do referrer são transmitidas
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Desativa funcionalidades perigosas do navegador que não usamos
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )

        # Content Security Policy (CSP) robusta
        # Permite Tailwind CSS e Alpine.js/Google Fonts de forma controlada
        csp = (
            "default-src 'self'; "
            "img-src 'self' data: https://lh3.googleusercontent.com https://avatars.googleusercontent.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp

        # Se for produção, força HTTPS estrito (HSTS)
        if is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response

