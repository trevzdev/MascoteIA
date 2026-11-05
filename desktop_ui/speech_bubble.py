"""
Balão Interativo de Comandos (Texto e Áudio)
Interface moderna translúcida para exibir respostas da IA,
campo de entrada de texto, botão de microfone e fluxo obrigatório de login Google.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QFrame,
)


class SpeechBubble(QWidget):
    """Balão de interação flutuante acoplado ao mascote."""

    text_submitted = pyqtSignal(str)
    mic_clicked = pyqtSignal()
    mute_toggled = pyqtSignal()
    settings_clicked = pyqtSignal()
    close_requested = pyqtSignal()
    login_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(330)
        self._is_listening = False
        self._is_muted = False
        self._is_authenticated = False

        self._setup_ui()
        self._apply_styles()
        self.set_authenticated_state(False, None)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 12)
        main_layout.setSpacing(8)

        # 1. Barra de Título / Cabeçalho
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #f59e0b; font-size: 11px;")
        header_layout.addWidget(self.status_dot)

        self.title_label = QLabel("MascoteIA")
        self.title_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #f8fafc;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Botão Painel de Configurações (Mini Engrenagem)
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(24, 24)
        self.settings_btn.setToolTip("Abrir Painel de Customização e Abas")
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        header_layout.addWidget(self.settings_btn)

        # Botão de Mudo (TTS)
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setFixedSize(24, 24)
        self.mute_btn.setToolTip("Alternar Voz da IA (Mudo)")
        self.mute_btn.clicked.connect(self._on_mute_clicked)
        header_layout.addWidget(self.mute_btn)

        # Botão Fechar/Recolher balão
        self.hide_btn = QPushButton("✕")
        self.hide_btn.setFixedSize(24, 24)
        self.hide_btn.setToolTip("Recolher Janela de Texto")
        self.hide_btn.clicked.connect(self.close_requested.emit)
        header_layout.addWidget(self.hide_btn)

        main_layout.addLayout(header_layout)

        # 2. Painel de Bloqueio / Login Obrigatório do Google
        self.login_frame = QFrame()
        login_layout = QVBoxLayout(self.login_frame)
        login_layout.setContentsMargins(10, 10, 10, 10)
        login_layout.setSpacing(6)

        self.login_title = QLabel("🔑 Conectar Conta Google")
        self.login_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.login_title.setStyleSheet("color: #38bdf8;")
        login_layout.addWidget(self.login_title)

        self.login_desc = QLabel(
            "Clique no botão abaixo para entrar com o seu email Google e liberar seu assistente."
        )
        self.login_desc.setWordWrap(True)
        self.login_desc.setFont(QFont("Segoe UI", 8))
        self.login_desc.setStyleSheet("color: #cbd5e1;")
        login_layout.addWidget(self.login_desc)

        self.login_btn = QPushButton("🔑 Conectar Conta Google")
        self.login_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: 1px solid #3b82f6;
                border-radius: 8px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.login_btn.clicked.connect(self.login_requested.emit)
        login_layout.addWidget(self.login_btn)

        main_layout.addWidget(self.login_frame)

        # 3. Área de Mensagens (Histórico de Respostas)
        self.message_frame = QFrame()
        msg_layout = QVBoxLayout(self.message_frame)
        msg_layout.setContentsMargins(8, 8, 8, 8)
        msg_layout.setSpacing(4)

        self.user_label = QLabel("")
        self.user_label.setWordWrap(True)
        self.user_label.setFont(QFont("Segoe UI", 8))
        self.user_label.setStyleSheet("color: #94a3b8;")
        self.user_label.hide()
        msg_layout.addWidget(self.user_label)

        self.bot_label = QLabel("Olá! Clique no microfone ou digite seu comando abaixo.")
        self.bot_label.setWordWrap(True)
        self.bot_label.setFont(QFont("Segoe UI", 9))
        self.bot_label.setStyleSheet("color: #e2e8f0; line-height: 1.4;")
        msg_layout.addWidget(self.bot_label)

        main_layout.addWidget(self.message_frame)

        # 4. Barra de Entrada de Comandos (Texto + Microfone)
        self.input_container = QWidget()
        input_layout = QHBoxLayout(self.input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(6)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Pergunte algo ou dê um comando...")
        self.input_field.returnPressed.connect(self._on_submit)
        input_layout.addWidget(self.input_field)

        # Botão Microfone
        self.mic_btn = QPushButton("🎙️")
        self.mic_btn.setFixedSize(32, 32)
        self.mic_btn.setToolTip("Falar por Voz (Microfone)")
        self.mic_btn.clicked.connect(self.mic_clicked.emit)
        input_layout.addWidget(self.mic_btn)

        # Botão Enviar
        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(32, 32)
        self.send_btn.setToolTip("Enviar Mensagem")
        self.send_btn.clicked.connect(self._on_submit)
        input_layout.addWidget(self.send_btn)

        main_layout.addWidget(self.input_container)

    def _apply_styles(self):
        self.setStyleSheet("""
            SpeechBubble {
                background-color: rgba(9, 13, 22, 0.96);
                border: 1px solid rgba(71, 85, 105, 0.5);
                border-radius: 16px;
            }
            QFrame {
                background-color: rgba(15, 23, 42, 0.85);
                border-radius: 10px;
                border: 1px solid rgba(51, 65, 85, 0.4);
            }
            QLineEdit {
                background-color: #0b1329;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 7px 12px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
                background-color: #0f1c3f;
            }
            QLineEdit:disabled {
                background-color: rgba(15, 23, 42, 0.5);
                color: #64748b;
                border-color: #1e293b;
            }
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #475569;
            }
            QPushButton:disabled {
                opacity: 0.4;
                background-color: rgba(30, 41, 59, 0.3);
                color: #64748b;
            }
        """)

    def set_authenticated_state(self, is_auth: bool, user_info: dict = None):
        """Atualiza a interface conforme o estado de login Google."""
        self._is_authenticated = is_auth
        if is_auth:
            self.login_frame.hide()
            self.input_field.setEnabled(True)
            self.mic_btn.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.status_dot.setStyleSheet("color: #10b981; font-size: 11px;")

            user_name = (user_info or {}).get("name") or "Google"
            email = (user_info or {}).get("email") or ""
            short_email = f" • {email.split('@')[0]}" if email else ""
            self.title_label.setText(f"MascoteIA{short_email}")
            self.bot_label.setText(f"Olá, {user_name}! Como posso ajudar você hoje?")
        else:
            self.login_frame.show()
            self.input_field.setEnabled(False)
            self.mic_btn.setEnabled(False)
            self.send_btn.setEnabled(False)
            self.status_dot.setStyleSheet("color: #f59e0b; font-size: 11px;")
            self.title_label.setText("MascoteIA (Login Necessário)")
            self.bot_label.setText("Autenticação Google obrigatória. Clique no botão de login acima.")

    def _on_submit(self):
        if not self._is_authenticated:
            self.login_requested.emit()
            return

        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.display_interaction(user_text=text, bot_text="Processando...")
            self.text_submitted.emit(text)

    def _on_mute_clicked(self):
        self._is_muted = not self._is_muted
        self.mute_btn.setText("🔇" if self._is_muted else "🔊")
        self.mute_toggled.emit()

    def set_listening_state(self, is_listening: bool):
        """Atualiza a aparência do balão quando o microfone está gravando."""
        self._is_listening = is_listening
        if is_listening:
            self.mic_btn.setStyleSheet("background-color: #f59e0b; border-color: #fbbf24;")
            self.status_dot.setStyleSheet("color: #f59e0b; font-size: 11px;")
            self.display_interaction(user_text="Gravando áudio...", bot_text="Ouvindo pelo microfone...")
        else:
            self.mic_btn.setStyleSheet("")
            color = "#10b981" if self._is_authenticated else "#f59e0b"
            self.status_dot.setStyleSheet(f"color: {color}; font-size: 11px;")

    def display_interaction(self, user_text: str = "", bot_text: str = ""):
        """Exibe o diálogo de interação."""
        if user_text:
            self.user_label.setText(f"👤 Você: {user_text}")
            self.user_label.show()
        else:
            self.user_label.hide()

        if bot_text:
            self.bot_label.setText(bot_text)
            self.bot_label.show()
