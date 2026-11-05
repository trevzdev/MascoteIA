"""
Testes Unitários Automatizados para o Mascote Desktop Flutuante (PyQt6)
Testa todas as funcionalidades avançadas:
1. Customização Visual Modular, Encaixe e Skins Heroicas (ModularMascotPainter)
2. Persistência de Configurações Locais (SettingsManager)
3. 6 Vozes Neurais Distintas: estritamente 3 Masculinas e 3 Femininas (TTSEngine)
4. 7 Personalidades e Incorporação Obrigatória do Nome do Usuário (PersonalityManager)
5. Atalhos de Arquivos e Executáveis do Windows (ShortcutManager)
6. Controle Inteligente do Spotify (SpotifyManager)
7. Agenda e Alerta Ativo do Robô (AgendaManager)
8. Janela Flutuante Frameless, Balão e Diálogo de Configurações 4 Abas
"""

import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QImage, QPainter

# Garante instância única de QApplication para os testes de interface
app = QApplication.instance() or QApplication(sys.argv)

from services.token_manager import TokenManager
from services.gemini_service import GeminiService
from desktop_ui.settings_manager import SettingsManager
from desktop_ui.personality_manager import PersonalityManager
from desktop_ui.modular_mascot import ModularMascotPainter, SKINS
from desktop_ui.tts_engine import TTSEngine
from desktop_ui.shortcut_manager import ShortcutManager
from desktop_ui.spotify_manager import SpotifyManager
from desktop_ui.agenda_manager import AgendaManager
from desktop_ui.mascot_widget import MascotWidget, MascotState
from desktop_ui.speech_bubble import SpeechBubble
from desktop_ui.command_handler import CommandHandler
from desktop_ui.floating_window import FloatingMascotWindow
from desktop_ui.settings_dialog import SettingsDialog


class TestMascotDesktop(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tempfile
        from pathlib import Path
        cls._test_dir = tempfile.mkdtemp()
        cls._test_settings = Path(cls._test_dir) / "mascot_settings.json"
        cls._test_token = Path(cls._test_dir) / "google_credentials.enc"

        cls._p1 = patch.object(SettingsManager, "get_file_path", return_value=cls._test_settings)
        cls._p2 = patch.object(TokenManager, "get_token_file_path", return_value=cls._test_token)
        cls._p1.start()
        cls._p2.start()
        SettingsManager._cached_settings = None

    @classmethod
    def tearDownClass(cls):
        cls._p1.stop()
        cls._p2.stop()
        SettingsManager._cached_settings = None
        import shutil
        shutil.rmtree(cls._test_dir, ignore_errors=True)

    def setUp(self):
        TokenManager.revoke_and_clear()
        SettingsManager.set_user_name("Everton")
        SettingsManager.set_robot_name("Laranja")

    def tearDown(self):
        TokenManager.revoke_and_clear()

    # --------------------------------------------------------------------------
    # 1. Testes de Vozes (Exatamente 3 Masculinas e 3 Femininas)
    # --------------------------------------------------------------------------
    def test_six_voices_and_three_male_three_female(self):
        """Valida que existem exatamente 6 vozes divididas em 3 masculinas e 3 femininas."""
        voices = TTSEngine.VOICE_PROFILES
        self.assertEqual(len(voices), 6, "Devem existir exatamente 6 opções de vozes.")

        male_voices = [v for v in voices.values() if v.get("gender") == "male"]
        female_voices = [v for v in voices.values() if v.get("gender") == "female"]

        self.assertEqual(len(male_voices), 3, "Devem ser exatamente 3 vozes masculinas.")
        self.assertEqual(len(female_voices), 3, "Devem ser exatamente 3 vozes femininas.")

        # Verifica IDs
        expected_ids = {"male_1", "male_2", "male_3", "female_1", "female_2", "female_3"}
        self.assertEqual(set(voices.keys()), expected_ids)

    # --------------------------------------------------------------------------
    # 2. Testes de Personalidades e Nome do Usuário
    # --------------------------------------------------------------------------
    def test_seven_personalities_and_user_name_usage(self):
        """Valida que existem 7 personalidades distintas e que o nome do usuário é sempre incluído."""
        personalities = PersonalityManager.PERSONALITIES
        self.assertEqual(len(personalities), 7, "Devem existir exatamente 7 personalidades.")

        expected_keys = {"amigavel", "elegante", "grosso", "sarcastico", "zueiro", "robotico", "sabio"}
        self.assertEqual(set(personalities.keys()), expected_keys)

        user_name = "Mariana"
        for p_id in expected_keys:
            # Testa saudação de wake word
            greeting = PersonalityManager.format_wake_response(p_id, user_name)
            self.assertIn(user_name, greeting, f"A saudação da personalidade {p_id} deve conter o nome do usuário.")

            # Testa formatação de resposta
            reply = PersonalityManager.format_response(p_id, "Comando executado com sucesso.", user_name)
            self.assertIn(user_name, reply, f"A resposta da personalidade {p_id} deve conter o nome do usuário.")

    # --------------------------------------------------------------------------
    # 3. Testes do Sistema Modular e Skins Heroicas
    # --------------------------------------------------------------------------
    def test_modular_mascot_rendering_and_skins(self):
        """Valida a renderização sem erros das 5 skins heroicas e variações modulares."""
        expected_skins = {"iron_armor", "patriot", "spider", "thunder_god", "night_vigilante"}
        for skin_id in expected_skins:
            self.assertIn(skin_id, SKINS, f"Skin heróica {skin_id} não encontrada.")

        img = QImage(160, 160, QImage.Format.Format_ARGB32_Premultiplied)
        painter = QPainter(img)

        # Testa renderizar cada skin heroica
        for skin_id in expected_skins:
            skin_data = dict(SKINS[skin_id])
            ModularMascotPainter.paint_robot(
                painter=painter,
                center=QPointF(80, 80),
                config=skin_data,
                state_str="idle",
                amplitude=0.5,
                is_blinking=False,
                look_offset=QPointF(2, -1),
                pulse_radius=5.0,
                tick=2.0
            )

        painter.end()
        self.assertFalse(img.isNull())

    # --------------------------------------------------------------------------
    # 4. Testes de Atalhos do Windows
    # --------------------------------------------------------------------------
    def test_shortcut_manager_detection(self):
        """Valida o cadastro e disparo de atalhos personalizados pelo nome de gatilho."""
        SettingsManager.add_shortcut(trigger="Abacate", path="notepad.exe", description="Bloco de Notas")

        # Testa padrões de fala rígidos e variações naturais por intenções (NLP leve)
        test_inputs = [
            "abra o Abacate",
            "abrir Abacate",
            "iniciar Abacate",
            "executar Abacate",
            "Abacate",
            "Ei Laranja, roda o Abacate pra mim",
            "inicia o abacate por favor",
            "abre o abacate aí",
        ]
        for cmd in test_inputs:
            result = ShortcutManager.find_and_launch(cmd)
            self.assertIsNotNone(result, f"Deveria ter reconhecido o comando '{cmd}'.")
            msg, ok = result
            self.assertTrue(ok)
            self.assertIn("Abacate", msg)

    # --------------------------------------------------------------------------
    # 5. Testes do Spotify Manager
    # --------------------------------------------------------------------------
    def test_spotify_manager_commands(self):
        """Valida a interpretação inteligente de comandos de música e playlists do Spotify."""
        # 1. Tocar música padrão
        res_music = SpotifyManager.handle_command("toque a música Bohemian Rhapsody")
        self.assertIsNotNone(res_music)
        msg_music, _ = res_music
        self.assertIn("Bohemian Rhapsody", msg_music)
        self.assertIn("Spotify", msg_music)

        # 2. Variação natural complexa (NLP leve com stopwords e intenção flexível)
        res_labareda = SpotifyManager.handle_command("Ei Laranja, coloca aquela música Labareda de fogo pra mim")
        self.assertIsNotNone(res_labareda)
        msg_labareda, _ = res_labareda
        self.assertIn("Labareda de fogo", msg_labareda)

        # 3. Tocar playlist
        res_pl = SpotifyManager.handle_command("toque a playlist Rock Clássico")
        self.assertIsNotNone(res_pl)
        msg_pl, _ = res_pl
        self.assertIn("Rock Clássico", msg_pl)

        # 4. Pausar / Play
        res_pause = SpotifyManager.handle_command("pausar spotify")
        self.assertIsNotNone(res_pause)

        # 5. Próxima música
        res_next = SpotifyManager.handle_command("próxima música")
        self.assertIsNotNone(res_next)

    # --------------------------------------------------------------------------
    # 6. Testes da Agenda e Alertas Ativos
    # --------------------------------------------------------------------------
    def test_agenda_manager_reminders(self):
        """Valida o cadastro de compromissos e disparo do alerta ativo falado pelo robô."""
        agenda_mgr = AgendaManager()

        # Cria compromisso que já está no momento de alertar (ex: daqui a 5 minutos com aviso de 10m)
        target_dt = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
        item = agenda_mgr.add_appointment(
            title="Apresentação de Projeto",
            datetime_str=target_dt,
            notify=True,
            frequency="10m",
            description="Reunião com diretoria"
        )

        triggered = []
        agenda_mgr.reminder_triggered.connect(lambda it: triggered.append(it))
        agenda_mgr.check_reminders()

        self.assertTrue(len(triggered) > 0, "O alerta de compromisso deveria ter sido disparado.")
        self.assertTrue(
            any(it.get("title") == "Apresentação de Projeto" for it in triggered),
            "O alerta específico de 'Apresentação de Projeto' deveria ter sido disparado.",
        )
        agenda_mgr.stop_monitoring()

    # --------------------------------------------------------------------------
    # 7. Testes da Janela Flutuante, Balão e Diálogo de Configurações
    # --------------------------------------------------------------------------
    def test_settings_dialog_tabs(self):
        """Verifica se o diálogo de configurações possui as 4 abas solicitadas."""
        settings_mgr = SettingsManager()
        dialog = SettingsDialog(settings_mgr)
        self.assertEqual(dialog.tabs.count(), 4, "O painel deve conter exatamente 4 abas.")
        self.assertIn("Visual", dialog.tabs.tabText(0))
        self.assertIn("Voz", dialog.tabs.tabText(1))
        self.assertIn("Atalhos", dialog.tabs.tabText(2))
        self.assertIn("Agenda", dialog.tabs.tabText(3))
        dialog.close()

    def test_floating_window_flags(self):
        """Verifica se a janela flutuante possui as flags frameless, always-on-top, smart positioning e remoção de engrenagem na cabeça."""
        win = FloatingMascotWindow()
        flags = win.windowFlags()
        self.assertTrue(bool(flags & Qt.WindowType.FramelessWindowHint))
        self.assertTrue(bool(flags & Qt.WindowType.WindowStaysOnTopHint))
        self.assertTrue(win.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))

        # Verifica remoção da engrenagem na cabeça do robô e manutenção única no balão
        self.assertFalse(hasattr(win.mascot, "_hover_gear"), "A engrenagem na cabeça do robô deve ser removida.")
        self.assertIsNotNone(win.bubble.settings_btn, "A engrenagem acima do chat deve ser o único gatilho mantido.")

        # Verifica Smart Positioning
        win._update_bubble_side(True)
        self.assertTrue(win._bubble_on_left)
        win._update_bubble_side(False)
        self.assertFalse(win._bubble_on_left)

        # 1 Clique no robô abre o chat sem abrir o navegador
        with patch.object(win, "open_google_login") as mock_login:
            win.bubble.hide()
            self.assertTrue(win.bubble.isHidden())
            win._on_mascot_clicked()
            self.assertFalse(win.bubble.isHidden(), "Um clique no robô deve abrir o balão de chat.")
            mock_login.assert_not_called()

        win.close()

    def test_speech_bubble_login_state(self):
        """Verifica alternância visual do balão entre modo bloqueado (login) e liberado."""
        bubble = SpeechBubble()
        bubble.show()
        self.assertFalse(bubble._is_authenticated)
        self.assertFalse(bubble.login_frame.isHidden())
        self.assertFalse(bubble.input_field.isEnabled())

        # Conecta usuário
        bubble.set_authenticated_state(True, {"name": "Carlos", "email": "carlos@google.com"})
        self.assertTrue(bubble._is_authenticated)
        self.assertTrue(bubble.login_frame.isHidden())
        self.assertTrue(bubble.input_field.isEnabled())
        self.assertIn("Carlos", bubble.bot_label.text())
        bubble.close()

    def test_unauthenticated_blocks_commands(self):
        """Verifica que o mascote bloqueia comandos até que o login Google seja feito."""
        handler = CommandHandler()
        resp, should_speak = handler.process("que horas são?")
        self.assertIn("fazer login com a sua conta Google", resp)

    def test_authenticated_commands_and_recipe(self):
        """Verifica se o mascote responde com sucesso a comandos e receitas quando autenticado."""
        mock_creds = {
            "token": "mock_access_token_12345",
            "refresh_token": "mock_refresh_token_67890",
        }
        mock_user = {"name": "Everton", "email": "everton@gmail.com"}
        TokenManager.save_tokens(mock_creds, mock_user)

        handler = CommandHandler()
        resp, should_speak = handler.process("que horas são?")
        self.assertIn("Agora são", resp)
        self.assertTrue(should_speak)

        # Receita autônoma
        resp_feijao, _ = handler.process("Como fazer feijão")
        self.assertIn("feijão", resp_feijao.lower())
        self.assertNotIn("API key not valid", resp_feijao)

    def test_gemini_503_retry_and_404_handling(self):
        """Verifica a identificação de erro 503 e 404 e o tratamento amigável de erros."""
        err_503 = Exception("503 UNAVAILABLE: This model is currently experiencing high demand.")
        err_404 = Exception("404 NOT_FOUND: models/gemini-2.0-flash is no longer available.")
        err_generic = Exception("Generic error occurred")

        self.assertTrue(GeminiService._is_503_error(err_503))
        self.assertFalse(GeminiService._is_503_error(err_404))

        self.assertTrue(GeminiService._is_404_error(err_404))
        self.assertFalse(GeminiService._is_404_error(err_503))

        # Teste de retry com simulação de 503
        with patch("config.Config.is_gemini_configured", return_value=True), \
             patch("config.Config.get_gemini_api_key", return_value="test_key"), \
             patch("services.gemini_service.time.sleep") as mock_sleep, \
             patch("google.genai.Client") as mock_client_cls:

            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            # Falha com 503 na primeira vez e sucede na segunda
            mock_resp = MagicMock()
            mock_resp.text = "Resposta após retry com sucesso!"
            mock_client.models.generate_content.side_effect = [
                Exception("503 UNAVAILABLE: This model is currently experiencing high demand."),
                mock_resp,
            ]

            result = GeminiService.generate_response("Pergunta com pico")
            self.assertTrue(result["success"])
            self.assertEqual(result["text"], "Resposta após retry com sucesso!")
            # Confirma que time.sleep(2) foi chamado para o retry
            mock_sleep.assert_called_with(2)

        # Teste de fallback seguro quando o 503 persiste em todos os modelos remotos
        with patch("config.Config.is_gemini_configured", return_value=True), \
             patch("config.Config.get_gemini_api_key", return_value="test_key"), \
             patch("services.gemini_service.time.sleep"), \
             patch("google.genai.Client") as mock_client_cls:

            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.models.generate_content.side_effect = Exception("503 UNAVAILABLE: This model is currently experiencing high demand.")

            result_fallback = GeminiService.generate_response("Qual a velocidade da luz no vácuo?")
            self.assertTrue(result_fallback["success"], "Mesmo com 503 em todos os modelos, o fallback deve retornar success=True")
            self.assertIn("Everton", result_fallback["text"])
            self.assertIn("demanda", result_fallback["text"])
            self.assertEqual(result_fallback["model"], "MascoteIA Fallback Seguro (Google 503)")


if __name__ == "__main__":
    unittest.main()
