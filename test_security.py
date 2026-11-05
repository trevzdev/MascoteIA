"""
Testes Automatizados de Segurança, Integridade das Rotas, Gemini AI e Google Calendar
Executa verificação dos mecanismos de defesa, headers OWASP, criptografia,
captura dinâmica de GEMINI_API_KEY do .env e escopos do Google Calendar.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from config import Config
from security import SecurityManager
from app import create_app
from services.gemini_service import GeminiService
from services.google_calendar import GoogleCalendarService
from googleapiclient.errors import HttpError


class TestSecurityAndAuth(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.security_manager = SecurityManager(Config.FERNET_KEY)

    def test_security_headers_present(self):
        """Verifica se os headers de segurança OWASP são aplicados a cada resposta."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(response.headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertIn("Content-Security-Policy", response.headers)
        self.assertIn("Permissions-Policy", response.headers)

    def test_cache_control_on_auth_and_api(self):
        """Verifica se rotas sensíveis desativam cache para evitar vazamento em proxies."""
        resp = self.client.get("/auth/login")
        self.assertIn("no-store", resp.headers.get("Cache-Control", ""))

    def test_fernet_encryption_roundtrip(self):
        """Verifica se o payload de tokens é criptografado e descriptografado fielmente."""
        test_payload = {
            "token": "ya29.sample_test_token_1234567890",
            "refresh_token": "1//sample_refresh_token_0987654321",
            "client_id": "test_client_id.apps.googleusercontent.com",
        }
        encrypted = self.security_manager.encrypt_json(test_payload)
        self.assertIsInstance(encrypted, str)
        self.assertNotIn("ya29.sample", encrypted)

        decrypted = self.security_manager.decrypt_json(encrypted)
        self.assertEqual(decrypted["token"], test_payload["token"])
        self.assertEqual(decrypted["refresh_token"], test_payload["refresh_token"])

    def test_tampered_fernet_fails_gracefully(self):
        """Verifica que dados adulterados na sessão não quebram o app nem vazam exceção."""
        tampered_token = "gAAAAABfake_tampered_token_string"
        result = self.security_manager.decrypt_json(tampered_token)
        self.assertIsNone(result)

    def test_masking_utility(self):
        """Verifica se chaves sensíveis são mascaradas para visualização segura."""
        key = "AIzaSyD-TestKey123456789SecretKeyEnd"
        masked = SecurityManager.mask_string(key, 4, 4)
        self.assertTrue(masked.startswith("AIza..."))
        self.assertTrue(masked.endswith("yEnd (protegido)"))
        self.assertNotIn("SecretKey", masked)

    def test_csrf_state_protection_on_callback(self):
        """Verifica que callback sem state válido é barrado."""
        resp = self.client.get("/auth/callback?code=mock_code&state=fake_state")
        self.assertEqual(resp.status_code, 302)

    def test_404_error_page_does_not_leak_stacktrace(self):
        """Verifica que erro 404 retorna página amigável sem revelar estrutura interna."""
        resp = self.client.get("/pagina-inexistente-12345")
        self.assertEqual(resp.status_code, 404)
        self.assertIn(b"P\xc3\xa1gina N\xc3\xa3o Encontrada", resp.data)

    # --------------------------------------------------------------------------
    # Testes dos Ajustes Críticos (Google Calendar Escopos e Gemini Real)
    # --------------------------------------------------------------------------
    def test_google_calendar_scopes_configuration(self):
        """Valida que os escopos completos do Google Calendar estão incluídos no OAuth."""
        scopes = Config.GOOGLE_SCOPES
        self.assertIn("https://www.googleapis.com/auth/calendar", scopes)
        self.assertIn("https://www.googleapis.com/auth/calendar.events", scopes)
        self.assertIn("https://www.googleapis.com/auth/userinfo.email", scopes)

    def test_calendar_insufficient_scope_triggers_permission_error(self):
        """Valida que o erro 403 de escopos insuficientes é capturado e lança PermissionError."""
        mock_creds = MagicMock()
        with patch.object(GoogleCalendarService, "get_calendar_service") as mock_build:
            mock_service = MagicMock()
            mock_resp = MagicMock()
            mock_resp.status = 403
            mock_content = b'{"error": {"code": 403, "message": "Request had insufficient authentication scopes."}}'
            http_err = HttpError(resp=mock_resp, content=mock_content)
            mock_service.events().list().execute.side_effect = http_err
            mock_build.return_value = mock_service

            with self.assertRaises(PermissionError) as ctx:
                GoogleCalendarService.list_upcoming_events(mock_creds)

            self.assertIn("Permissão insuficiente", str(ctx.exception))
            self.assertIn("Google Calendar", str(ctx.exception))

    def test_gemini_api_key_dynamic_capture_from_env(self):
        """Verifica que a chave GEMINI_API_KEY é lida dinamicamente do .env."""
        test_key = "AIzaSy_TEST_MOCK_GEMINI_KEY_123456"
        with patch.dict(os.environ, {"GEMINI_API_KEY": test_key, "GEMINI_MODEL": "gemini-1.5-flash"}):
            self.assertEqual(Config.get_gemini_api_key(), test_key)
            self.assertEqual(Config.GEMINI_API_KEY, test_key)
            self.assertEqual(Config.get_gemini_model(), "gemini-1.5-flash")
            self.assertTrue(Config.is_gemini_configured())

    def test_gemini_service_calls_real_api_model(self):
        """Valida que quando configurada, o GeminiService conecta à API real do Gemini."""
        test_key = "AIzaSy_VALID_TEST_KEY_123456789"
        with patch.dict(os.environ, {"GEMINI_API_KEY": test_key, "GEMINI_MODEL": "gemini-1.5-flash"}):
            with patch("services.gemini_service.genai.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.text = "Python surgiu em 1991, criado por Guido van Rossum."
                mock_client.models.generate_content.return_value = mock_response
                mock_client_cls.return_value = mock_client

                res = GeminiService.generate_response("quando surgiu o Python?")
                self.assertTrue(res["success"])
                self.assertIn("1991", res["text"])
                self.assertEqual(res["model"], "gemini-1.5-flash")
                # Confirma que genai.Client foi instanciado com a chave do .env
                mock_client_cls.assert_called_with(api_key=test_key)

    def test_gemini_without_key_prompts_env_configuration(self):
        """Verifica que sem chave no .env, o sistema solicita configuração em vez de mock genérico."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            res = GeminiService.generate_response("quando surgiu o Python?")
            self.assertFalse(res["success"])
            self.assertIn("GEMINI_API_KEY", res["text"])
            self.assertIn(".env", res["text"])
            # Garante que não é a resposta mockada genérica antiga
            self.assertNotIn("Excelente pergunta", res["text"])


if __name__ == "__main__":
    unittest.main()
