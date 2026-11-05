"""
Janela Flutuante Principal (Frameless & Always-on-Top)
Integrada com:
- Autenticação Obrigatória Google OAuth 2.0 e Servidor Local Flask
- Painel de Customização e Abas (acessado pela mini engrenagem ⚙)
- Sistema Modular de Encaixe Perfeito com Skins Heróicas
- Escuta Contínua de Wake Word ("Ei Laranja" / "Eai Laranja")
- Identificação Obrigatória do Usuário e 7 Personalidades
- 6 Vozes Neurais Distintas (3 Masculinas e 3 Femininas)
- Atalhos do Windows (.exe, .msc, .txt, .csv, etc.)
- Controle do Spotify (músicas, playlists, pausar, avançar)
- Agenda e Lembretes Ativos Falados pelo Robô
"""

import socket
import threading
import webbrowser
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QAction, QColor, QCursor
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QMenu,
    QApplication,
)

from config import Config
from services.token_manager import TokenManager
from desktop_ui.settings_manager import SettingsManager
from desktop_ui.personality_manager import PersonalityManager
from desktop_ui.mascot_widget import MascotWidget, MascotState
from desktop_ui.speech_bubble import SpeechBubble
from desktop_ui.audio_listener import AudioListener
from desktop_ui.tts_engine import TTSEngine
from desktop_ui.command_handler import CommandHandler
from desktop_ui.agenda_manager import AgendaManager
from desktop_ui.settings_dialog import SettingsDialog


def is_port_in_use(port: int) -> bool:
    """Verifica se a porta local já está ocupada."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def ensure_flask_server_running():
    """Garante que o servidor OAuth do Flask esteja ativo em background."""
    if not is_port_in_use(Config.PORT):
        from app import create_app
        flask_app = create_app()

        server_thread = threading.Thread(
            target=lambda: flask_app.run(
                host="127.0.0.1",
                port=Config.PORT,
                debug=False,
                use_reloader=False,
            ),
            daemon=True,
        )
        server_thread.start()


class FloatingMascotWindow(QWidget):
    """Janela flutuante sem bordas que permanece sempre sobreposta à tela."""

    def __init__(self):
        super().__init__()

        # Inicia servidor Flask local se ainda não estiver ativo
        ensure_flask_server_running()

        # 1. Configurações da Janela: Sem bordas, Sempre no Topo e Fundo Transparente
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # 2. Inicialização dos Gerenciadores e Motores
        self.settings = SettingsManager()
        self.agenda = AgendaManager(self.settings)
        self.tts = TTSEngine(self, voice_id=self.settings.get_voice())
        self.command_handler = CommandHandler(self.settings, self.agenda)
        self.audio_listener = AudioListener(
            self,
            duration=5.0,
            robot_name=self.settings.get_robot_name(),
            wake_enabled=self.settings.is_wake_word_enabled(),
        )

        # Variáveis de Arraste da Janela e Posicionamento Inteligente do Balão
        self._is_dragging = False
        self._drag_start_pos = QPoint()
        self._has_prompted_login = False
        self._settings_dialog = None
        self._bubble_on_left = False

        # 3. Layout Principal da Janela
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(12)

        # Widget do Mascote Animado Modular
        self.mascot = MascotWidget(self, size=130, settings_manager=self.settings)
        self.layout.addWidget(self.mascot)

        # Balão de Fala e Entrada de Comandos (Smart Positioning)
        self.bubble = SpeechBubble(self)
        self.layout.addWidget(self.bubble)

        # 4. Timer de Verificação Contínua da Autenticação Google
        self.auth_timer = QTimer(self)
        self.auth_timer.timeout.connect(self._check_auth_status)
        self.auth_timer.start(800)

        # Pré-aquecimento da mensagem de boas-vindas para fala instantânea (cache local)
        try:
            pers_id = self.settings.get_personality()
            user_name = self.settings.get_user_name()
            w_msg = PersonalityManager.format_welcome(pers_id, user_name)
            self.tts.prewarm(w_msg)
        except Exception:
            pass

        # 5. Conexões de Sinais e Eventos
        self._connect_signals()

        # 6. Sincroniza Estado Inicial de Autenticação
        self._check_auth_status()

        # 7. Posicionamento Padrão no Canto Inferior Direito da Tela
        self._position_bottom_right()

    def _connect_signals(self):
        # Cliques no Mascote e na mini engrenagem
        self.mascot.clicked.connect(self._on_mascot_clicked)
        self.mascot.double_clicked.connect(self._start_listening)
        self.mascot.settings_clicked.connect(self.open_settings_dialog)

        # Ações do Balão
        self.bubble.text_submitted.connect(self._handle_user_command)
        self.bubble.mic_clicked.connect(self._start_listening)
        self.bubble.mute_toggled.connect(self.tts.toggle_mute)
        self.bubble.settings_clicked.connect(self.open_settings_dialog)
        self.bubble.close_requested.connect(self._toggle_bubble)
        self.bubble.login_requested.connect(self.open_google_login)

        # Eventos do Microfone e Reconhecimento
        self.audio_listener.listening_started.connect(self._on_mic_started)
        self.audio_listener.listening_stopped.connect(self._on_mic_stopped)
        self.audio_listener.amplitude_updated.connect(self.mascot.set_amplitude)
        self.audio_listener.transcription_success.connect(self._on_speech_recognized)
        self.audio_listener.transcription_error.connect(self._on_speech_error)

        # Ativação por Voz Contínua (Wake Word: "Ei Laranja" / "Eai Laranja")
        self.audio_listener.wake_word_detected.connect(self._on_wake_word_triggered)

        # Alerta Ativo de Compromisso da Agenda
        self.agenda.reminder_triggered.connect(self._on_agenda_reminder_fired)

        # Eventos de Voz (TTS)
        self.tts.speech_started.connect(lambda _: self.mascot.set_state(MascotState.SPEAKING))
        self.tts.speech_finished.connect(self._on_tts_finished)

    def _on_tts_finished(self):
        self.mascot.set_state(MascotState.IDLE)
        if getattr(self, "_listen_after_wake", False):
            self._listen_after_wake = False
            self._start_listening()

    def _check_auth_status(self):
        """Sincroniza o estado de autenticação entre o TokenManager e a interface."""
        is_auth = TokenManager.is_authenticated()
        user_info = TokenManager.get_user_info() if is_auth else None

        # Detectou novo login com sucesso
        if is_auth and not self.bubble._is_authenticated:
            self.bubble.set_authenticated_state(True, user_info)
            user_name = self.settings.get_user_name()
            if user_name in ("Usuário", "") and user_info:
                g_name = (user_info.get("name") or "").split()[0]
                if g_name:
                    user_name = g_name
                    self.settings.set_user_name(user_name)

            pers_id = self.settings.get_personality()
            welcome_msg = PersonalityManager.format_welcome(pers_id, user_name)
            self.bubble.display_interaction(bot_text=welcome_msg)
            self.tts.speak(welcome_msg)
            self.mascot.set_state(MascotState.SPEAKING)
            self.auth_timer.setInterval(3000)

        elif not is_auth and self.bubble._is_authenticated:
            self.bubble.set_authenticated_state(False, None)
            self.mascot.set_state(MascotState.IDLE)
            self.auth_timer.setInterval(800)
        elif not is_auth and not self.bubble._is_authenticated:
            self.bubble.set_authenticated_state(False, None)
            self.auth_timer.setInterval(800)

    def _on_mascot_clicked(self):
        """Um clique no robô abre/alterna a exibição do balão de chat sem disparar o navegador."""
        self._toggle_bubble()

    def open_google_login(self):
        """Abre a URL de consentimento OAuth 2.0 no navegador padrão."""
        login_url = f"{Config.BASE_URL}/auth/login"
        self.mascot.set_state(MascotState.THINKING)
        self.bubble.display_interaction(
            bot_text="Abrindo o navegador para você fazer login na sua conta Google com segurança máxima..."
        )
        self.tts.speak("Abrindo o navegador para você conectar sua conta Google.")
        webbrowser.open(login_url)

    def open_settings_dialog(self):
        """Abre o diálogo de personalização e abas com a mini engrenagem."""
        if not self._settings_dialog or not self._settings_dialog.isVisible():
            self._settings_dialog = SettingsDialog(self.settings, self.tts, self)
            self._settings_dialog.settings_saved.connect(self._apply_updated_settings)
            self._settings_dialog.show()
        else:
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()

    def _apply_updated_settings(self):
        """Aplica alterações visuais, de voz, wake word e nomes instantaneamente."""
        self.mascot.update_visual_config(self.settings.get_visual_config())
        self.audio_listener.update_robot_name(self.settings.get_robot_name())
        self.audio_listener.set_wake_word_enabled(self.settings.is_wake_word_enabled())
        self.tts.set_voice(self.settings.get_voice())

        # Atualiza título do balão com o nome do robô
        robot_name = self.settings.get_robot_name()
        user_name = self.settings.get_user_name()
        self.bubble.title_label.setText(f"{robot_name} • {user_name}")

    def _update_bubble_side(self, on_left: bool):
        """Alterna dinamicamente a posição do balão para a esquerda ou direita do robô."""
        if self._bubble_on_left == on_left:
            return
        self._bubble_on_left = on_left

        self.layout.removeWidget(self.mascot)
        self.layout.removeWidget(self.bubble)

        if on_left:
            self.layout.addWidget(self.bubble)
            self.layout.addWidget(self.mascot)
        else:
            self.layout.addWidget(self.mascot)
            self.layout.addWidget(self.bubble)

    def _adjust_smart_positioning(self, target_pos: QPoint = None) -> QPoint:
        """
        Calcula o posicionamento inteligente (Smart Positioning):
        - Se o robô estiver próximo à borda direita da tela, o balão abre para a ESQUERDA do robô.
        - Se estiver próximo à borda esquerda, o balão abre para a DIREITA.
        - Ajusta verticalmente (clamping) garantindo que 100% do conteúdo fique visível sem cortes.
        """
        curr_pos = target_pos if target_pos is not None else self.pos()
        screen = QApplication.screenAt(curr_pos) or QApplication.primaryScreen()
        if not screen:
            return curr_pos

        avail = screen.availableGeometry()

        # Determina a posição central do robô na tela
        w = self.width()
        h = self.height()
        robot_x = curr_pos.x() + (w - 70 if self._bubble_on_left else 70)

        # Se o robô estiver na metade direita da tela, balão fica à esquerda do robô
        screen_mid_x = avail.left() + (avail.width() / 2.0)
        should_be_on_left = robot_x > screen_mid_x

        if self.bubble.isVisible() and self._bubble_on_left != should_be_on_left:
            self._update_bubble_side(should_be_on_left)
            self._sync_window_size()
            w = self.width()
            h = self.height()

        # Clamping vertical e horizontal para que nunca corte nas bordas da tela
        clamped_x = max(avail.left(), min(curr_pos.x(), avail.right() - w + 1))
        clamped_y = max(avail.top(), min(curr_pos.y(), avail.bottom() - h + 1))
        return QPoint(clamped_x, clamped_y)

    def _position_bottom_right(self):
        """Posiciona a janela próxima ao canto inferior direito com o balão inteligentemente à esquerda."""
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry()
        self._update_bubble_side(True)
        self._sync_window_size()
        w = max(self.minimumWidth(), self.sizeHint().width())
        h = max(self.minimumHeight(), self.sizeHint().height())
        self.resize(w, h)
        x = avail.right() - w - 20
        y = avail.bottom() - h - 30
        clamped_pos = self._adjust_smart_positioning(QPoint(x, y))
        self.move(clamped_pos)

    def _sync_window_size(self):
        """Ajusta o tamanho respeitando o sizeHint e limites do layout sem alertas do Windows."""
        hint = self.sizeHint()
        w = max(self.minimumWidth(), hint.width())
        h = max(self.minimumHeight(), hint.height())
        self.resize(w, h)

    def _toggle_bubble(self):
        """Alterna a visibilidade do balão de interação com recálculo de posicionamento inteligente."""
        if self.bubble.isVisible():
            self.bubble.hide()
            self._sync_window_size()
        else:
            self.bubble.show()
            self._sync_window_size()
            clamped_pos = self._adjust_smart_positioning(self.pos())
            self.move(clamped_pos)

    # --------------------------------------------------------------------------
    # Fluxo de Áudio, Wake Word e Alerta da Agenda
    # --------------------------------------------------------------------------
    def _start_listening(self):
        """Ativa a gravação do microfone se autenticado."""
        if not TokenManager.is_authenticated():
            if not self.bubble.isVisible():
                self._toggle_bubble()
            self.bubble.display_interaction(bot_text="Clique no botão 'Conectar Conta Google' acima para autorizar o microfone.")
            return

        if not self.bubble.isVisible():
            self._toggle_bubble()
        self.audio_listener.toggle_listening()

    def _on_mic_started(self):
        self.mascot.set_state(MascotState.LISTENING)
        self.bubble.set_listening_state(True)

    def _on_mic_stopped(self):
        self.bubble.set_listening_state(False)
        self.mascot.set_amplitude(0.0)
        self.mascot.set_state(MascotState.THINKING)

    def _on_speech_recognized(self, text: str):
        self._handle_user_command(text)

    def _on_speech_error(self, error_msg: str):
        self.mascot.set_state(MascotState.ERROR)
        self.bubble.display_interaction(bot_text=error_msg)
        QTimer.singleShot(3000, lambda: self.mascot.set_state(MascotState.IDLE))

    def _on_wake_word_triggered(self, detected_phrase: str):
        """
        Ao ser chamado pelo wake word (ex: "Ei Laranja"), responde imediatamente com a voz
        e o tom de personalidade escolhidos (ex: "Diga, [Seu Nome]!") e abre a escuta.
        """
        user_name = self.settings.get_user_name()
        pers_id = self.settings.get_personality()
        wake_reply = PersonalityManager.format_wake_response(pers_id, user_name)

        if not self.bubble.isVisible():
            self.bubble.show()
            self._sync_window_size()

        self.bubble.display_interaction(user_text=detected_phrase, bot_text=wake_reply)
        self._listen_after_wake = True
        self.tts.speak(wake_reply)

        # Fallback de segurança se a fala do robô falhar ou for silenciada
        def _fallback_wake_mic():
            if getattr(self, "_listen_after_wake", False):
                self._listen_after_wake = False
                self._start_listening()

        QTimer.singleShot(4000, _fallback_wake_mic)

    def _on_agenda_reminder_fired(self, reminder_item: dict):
        """
        Dispara alerta ativo quando o tempo do lembrete expira:
        'Ei [Seu Nome], não esqueça do seu compromisso: [Título do Compromisso]'.
        """
        user_name = self.settings.get_user_name()
        title = reminder_item.get("title", "Compromisso Agendado")
        alert_msg = f"Ei {user_name}, não esqueça do seu compromisso: {title}!"

        if not self.bubble.isVisible():
            self.bubble.show()
            self._sync_window_size()

        self.bubble.display_interaction(
            user_text="⏰ Alerta de Compromisso",
            bot_text=alert_msg
        )
        self.tts.speak(alert_msg)
        self.mascot.set_state(MascotState.SPEAKING)

    def _handle_user_command(self, text: str):
        """Executa o comando recebido via texto ou voz."""
        if not TokenManager.is_authenticated():
            self.bubble.display_interaction(
                user_text=text,
                bot_text="Você precisa conectar sua conta Google primeiro. Clique no botão azul 'Conectar Conta Google' acima."
            )
            return

        self.mascot.set_state(MascotState.THINKING)
        response_text, should_speak = self.command_handler.process(text)
        self.bubble.display_interaction(user_text=text, bot_text=response_text)

        if should_speak:
            self.tts.speak(response_text)
        else:
            self.mascot.set_state(MascotState.IDLE)

    # --------------------------------------------------------------------------
    # Arrasto com Mouse (Drag & Drop para Frameless Window)
    # --------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            target_pos = event.globalPosition().toPoint() - self._drag_start_pos
            clamped_pos = self._adjust_smart_positioning(target_pos)
            self.move(clamped_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.unsetCursor()
            event.accept()

    # --------------------------------------------------------------------------
    # Menu de Contexto (Botão Direito)
    # --------------------------------------------------------------------------
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0284c7;
            }
        """)

        # Configurações e Customização
        settings_action = QAction("⚙️ Personalizar e Configurações...", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        menu.addAction(settings_action)

        menu.addSeparator()

        # Ação de Login / Desconectar
        if TokenManager.is_authenticated():
            user_info = TokenManager.get_user_info() or {}
            user_email = user_info.get("email", "Google")
            user_action = QAction(f"👤 Conectado como: {user_email}", self)
            user_action.setEnabled(False)
            menu.addAction(user_action)

            logout_action = QAction("🚪 Desconectar Conta Google", self)
            logout_action.triggered.connect(self._logout_google)
            menu.addAction(logout_action)
        else:
            login_action = QAction("🔑 Fazer Login com o Google", self)
            login_action.triggered.connect(self.open_google_login)
            menu.addAction(login_action)

        menu.addSeparator()

        mic_action = QAction("🎙️ Falar com Microfone", self)
        mic_action.triggered.connect(self._start_listening)
        menu.addAction(mic_action)

        bubble_action = QAction("💬 Alternar Caixa de Texto", self)
        bubble_action.triggered.connect(self._toggle_bubble)
        menu.addAction(bubble_action)

        mute_action = QAction("🔇 Ativar/Desativar Som", self)
        mute_action.triggered.connect(self.bubble._on_mute_clicked)
        menu.addAction(mute_action)

        menu.addSeparator()

        reset_pos_action = QAction("📍 Reposicionar na Tela", self)
        reset_pos_action.triggered.connect(self._position_bottom_right)
        menu.addAction(reset_pos_action)

        exit_action = QAction("❌ Fechar Mascote", self)
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)

        menu.exec(event.globalPos())

    def _logout_google(self):
        """Desconecta a conta Google."""
        TokenManager.revoke_and_clear()
        self.bubble.set_authenticated_state(False, None)
        self.bubble.display_interaction(bot_text="Conta Google desconectada. Clique em Login para reconectar.")
        self.tts.speak("Conta desconectada com sucesso.")

    def closeEvent(self, event):
        """Encerra threads secundárias e timers com segurança."""
        self.auth_timer.stop()
        self.agenda.stop_monitoring()
        self.audio_listener.shutdown()
        self.tts.shutdown()
        super().closeEvent(event)
