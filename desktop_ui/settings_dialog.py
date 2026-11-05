"""
Painel de Customização Avançado e Abas do MascoteIA
Acessado pela mini engrenagem flutuante (⚙).
Abas:
1. Customização Visual do Robô (Modular, Encaixe Perfeito, Cores e 5 Skins Heróicas)
2. Nome, Ativação por Voz (Wake Word), Voz (3M + 3F) e Personalidade (7 Estilos)
3. Atalhos de Aplicativos do Windows (.exe, .msc, .txt, .csv, etc.)
4. Agenda e Lembretes Inteligentes com Notificação e Alerta Ativo
"""

from datetime import datetime, date, time
from typing import Dict, Any

from PyQt6.QtCore import Qt, QPointF, pyqtSignal, QDate, QTime
from PyQt6.QtGui import QColor, QFont, QPainter, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QCheckBox,
    QColorDialog,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QScrollArea,
    QMessageBox,
    QListView,
)

from desktop_ui.settings_manager import SettingsManager
from desktop_ui.personality_manager import PersonalityManager
from desktop_ui.modular_mascot import ModularMascotPainter, SKINS
from desktop_ui.tts_engine import TTSEngine
from desktop_ui.shortcut_manager import ShortcutManager
from desktop_ui.agenda_manager import AgendaManager


class ModularPreviewWidget(QWidget):
    """Widget de visualização em tempo real do robô na Aba 1."""

    def __init__(self, config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 150)
        self.config = dict(config)

    def set_config(self, new_config: Dict[str, Any]):
        self.config = dict(new_config)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fundo do preview com grid sutil
        painter.fillRect(self.rect(), QColor("#090d16"))
        painter.setPen(QColor("#1e293b"))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)

        cx = self.width() / 2.0
        cy = self.height() / 2.0 + 4.0

        ModularMascotPainter.paint_robot(
            painter=painter,
            center=QPointF(cx, cy),
            config=self.config,
            state_str="idle",
            amplitude=0.0,
            is_blinking=False,
            look_offset=QPointF(0, 0),
            pulse_radius=0.0,
            tick=1.0,
        )


class SettingsDialog(QDialog):
    """Diálogo de configurações tabuladas do MascoteIA."""

    settings_saved = pyqtSignal()

    def __init__(self, settings_manager: SettingsManager, tts_engine: TTSEngine = None, parent=None):
        super().__init__(parent)
        self.settings = settings_manager
        self.tts = tts_engine
        self.setWindowTitle("Configurações do MascoteIA")
        self.setFixedSize(720, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        # Cópia temporária da configuração visual para preview
        self.current_visual = self.settings.get_visual_config()

        self._setup_ui()
        self._apply_styles()
        self._load_current_values()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Cabeçalho do Diálogo
        header = QHBoxLayout()
        icon_label = QLabel("⚙️")
        icon_label.setFont(QFont("Segoe UI", 16))
        header.addWidget(icon_label)

        title_label = QLabel("Central de Customização e Automação")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #f8fafc;")
        header.addWidget(title_label)
        header.addStretch()
        main_layout.addLayout(header)

        # Abas Principais
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_tab_visual(), "🎨 Visual e Skins")
        self.tabs.addTab(self._build_tab_voice_personality(), "🎙️ Voz e Personalidade")
        self.tabs.addTab(self._build_tab_shortcuts(), "⚡ Atalhos do Windows")
        self.tabs.addTab(self._build_tab_agenda(), "📅 Agenda e Lembretes")
        main_layout.addWidget(self.tabs)

        # Barra Inferior com Botões de Ação
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("💾 Salvar Alterações")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.clicked.connect(self._save_all_settings)
        bottom_layout.addWidget(self.btn_save)

        main_layout.addLayout(bottom_layout)

    # =========================================================================
    # ABA 1: Customização Visual do Robô
    # =========================================================================
    def _build_tab_visual(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        # Coluna Esquerda: Preview ao Vivo
        left_box = QVBoxLayout()
        preview_title = QLabel("Visualização em Tempo Real")
        preview_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        preview_title.setStyleSheet("color: #38bdf8;")
        left_box.addWidget(preview_title)

        self.preview = ModularPreviewWidget(self.current_visual, self)
        left_box.addWidget(self.preview)

        # Botão de Reset para Padrão
        btn_reset_visual = QPushButton("Restaurar Padrão")
        btn_reset_visual.clicked.connect(self._reset_visual_defaults)
        left_box.addWidget(btn_reset_visual)
        left_box.addStretch()
        layout.addLayout(left_box)

        # Coluna Direita: Controles Modulares em Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll_content = QWidget()
        controls = QVBoxLayout(scroll_content)
        controls.setSpacing(12)

        # 1. Temas Heroicos / Lendários (Skins Perfeitas)
        skin_header = QLabel("🌟 Temas Heróicos / Lendários (Skins Prontas)")
        skin_header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        skin_header.setStyleSheet("color: #f59e0b;")
        controls.addWidget(skin_header)

        skins_grid = QGridLayout()
        skins_data = [
            ("iron_armor", "🔴 Armadura de Ferro"),
            ("patriot", "🔵 Patriota"),
            ("spider", "🕷️ Aranha"),
            ("thunder_god", "⚡ Deus do Trovão"),
            ("night_vigilante", "🦇 Vigilante Noturno"),
        ]
        col = 0
        row = 0
        for skin_id, label in skins_data:
            btn_skin = QPushButton(label)
            btn_skin.setToolTip(SKINS[skin_id]["description"])
            btn_skin.clicked.connect(lambda _, s=skin_id: self._apply_heroic_skin(s))
            skins_grid.addWidget(btn_skin, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1
        controls.addLayout(skins_grid)

        controls.addWidget(self._make_separator())

        # 2. Peças Modulares (Encaixe Perfeito)
        modular_title = QLabel("🧩 Peças Modulares com Encaixe Milimétrico")
        modular_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        modular_title.setStyleSheet("color: #38bdf8;")
        controls.addWidget(modular_title)

        form_grid = QGridLayout()
        form_grid.setSpacing(8)

        # Chassi
        form_grid.addWidget(QLabel("Corpo / Chassi:"), 0, 0)
        self.combo_chassis = QComboBox()
        self._setup_combobox(self.combo_chassis)
        self.combo_chassis.addItems(["Clássico Moderno (classic)", "Cyberpunk Angular (cyber)", "Orbe Esférico (orb)", "Mecha Blindado (mecha)"])
        self.combo_chassis.currentIndexChanged.connect(self._on_visual_changed)
        form_grid.addWidget(self.combo_chassis, 0, 1)

        # Olhos / Visores
        form_grid.addWidget(QLabel("Olhos / Visor:"), 1, 0)
        self.combo_eyes = QComboBox()
        self._setup_combobox(self.combo_eyes)
        self.combo_eyes.addItems(["Cápsulas Digitais (capsule)", "Visor Panorâmico (visor)", "Olhos Felizes (happy)", "Cyber Dots (dots)", "Aranha Tática (spider)"])
        self.combo_eyes.currentIndexChanged.connect(self._on_visual_changed)
        form_grid.addWidget(self.combo_eyes, 1, 1)

        # Boca / Grelha
        form_grid.addWidget(QLabel("Boca / Grelha:"), 2, 0)
        self.combo_mouth = QComboBox()
        self._setup_combobox(self.combo_mouth)
        self.combo_mouth.addItems(["Onda Sonora Equalizador (wave)", "Grelha Acústica (grille)", "Sorriso LED (smile)", "Linha Laser (laser)"])
        self.combo_mouth.currentIndexChanged.connect(self._on_visual_changed)
        form_grid.addWidget(self.combo_mouth, 2, 1)

        # Acessórios
        form_grid.addWidget(QLabel("Acessório / Capacete:"), 3, 0)
        self.combo_acc = QComboBox()
        self._setup_combobox(self.combo_acc)
        self.combo_acc.addItems(["Antena com LED (antenna)", "Crista de Ferro (iron_crest)", "Espinhos Cibernéticos (spikes)", "Chifres Noturnos (bat_horns)", "Chifres Vikings (viking_horns)", "Nenhum (none)"])
        self.combo_acc.currentIndexChanged.connect(self._on_visual_changed)
        form_grid.addWidget(self.combo_acc, 3, 1)

        controls.addLayout(form_grid)

        controls.addWidget(self._make_separator())

        # 3. Cores Livres e Paletas
        colors_title = QLabel("🎨 Cores da Carcaça, Detalhes e LEDs")
        colors_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        colors_title.setStyleSheet("color: #38bdf8;")
        controls.addWidget(colors_title)

        colors_layout = QHBoxLayout()

        self.btn_col_body = QPushButton("Carcaça")
        self.btn_col_body.clicked.connect(lambda: self._pick_color("body_color"))
        colors_layout.addWidget(self.btn_col_body)

        self.btn_col_detail = QPushButton("Detalhes")
        self.btn_col_detail.clicked.connect(lambda: self._pick_color("detail_color"))
        colors_layout.addWidget(self.btn_col_detail)

        self.btn_col_led = QPushButton("LEDs")
        self.btn_col_led.clicked.connect(lambda: self._pick_color("led_color"))
        colors_layout.addWidget(self.btn_col_led)

        controls.addLayout(colors_layout)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        return widget

    # =========================================================================
    # ABA 2: Nome, Wake Word, Voz e Personalidade
    # =========================================================================
    def _build_tab_voice_personality(self) -> QWidget:
        widget = QWidget()
        scroll = QScrollArea(widget)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 1. Identificação do Usuário e Nome do Robô
        id_title = QLabel("👤 Identificação e Nomes")
        id_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        id_title.setStyleSheet("color: #38bdf8;")
        layout.addWidget(id_title)

        names_grid = QGridLayout()
        names_grid.addWidget(QLabel("Seu Nome (Como o robô deve te chamar):"), 0, 0)
        self.input_user_name = QLineEdit()
        self.input_user_name.setPlaceholderText("Ex: Everton, Mariana, Chefe...")
        names_grid.addWidget(self.input_user_name, 0, 1)

        names_grid.addWidget(QLabel("Nome do Robô / Assistente:"), 1, 0)
        self.input_robot_name = QLineEdit()
        self.input_robot_name.setPlaceholderText("Ex: Laranja, Jarvis, Sexta-Feira...")
        names_grid.addWidget(self.input_robot_name, 1, 1)
        layout.addLayout(names_grid)

        # 2. Ativação Contínua por Voz (Wake Word)
        self.chk_wake_word = QCheckBox("Habilitar escuta contínua de frase de ativação (Ex: 'Ei Laranja' ou 'Eai Laranja')")
        self.chk_wake_word.setStyleSheet("color: #cbd5e1; font-weight: bold;")
        layout.addWidget(self.chk_wake_word)

        layout.addWidget(self._make_separator())

        # 3. Seleção de Voz do Robô (Text-to-Speech) - Exatamente 6 Vozes (3M + 3F)
        voice_title = QLabel("🎙️ Seleção de Voz (Exatamente 3 Masculinas e 3 Femininas)")
        voice_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        voice_title.setStyleSheet("color: #38bdf8;")
        layout.addWidget(voice_title)

        voice_layout = QHBoxLayout()
        self.combo_voice = QComboBox()
        self._setup_combobox(self.combo_voice)
        for v_id, v_info in TTSEngine.VOICES.items():
            gender_icon = "👨" if v_info["gender"] == "male" else "👩"
            self.combo_voice.addItem(f"{gender_icon} {v_info['name']} - {v_info['desc']}", v_id)
        voice_layout.addWidget(self.combo_voice, stretch=3)

        self.btn_test_voice = QPushButton("🔊 Testar Voz")
        self.btn_test_voice.clicked.connect(self._test_voice)
        voice_layout.addWidget(self.btn_test_voice, stretch=1)
        layout.addLayout(voice_layout)

        layout.addWidget(self._make_separator())

        # 4. Personalidade e Tom de Resposta (7 Estilos)
        pers_title = QLabel("🧠 Personalidade e Tom de Resposta (7 Estilos)")
        pers_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        pers_title.setStyleSheet("color: #38bdf8;")
        layout.addWidget(pers_title)

        self.combo_personality = QComboBox()
        self._setup_combobox(self.combo_personality)
        for p_id, p_info in PersonalityManager.PERSONALITIES.items():
            self.combo_personality.addItem(f"{p_info['name']} - {p_info['desc']}", p_id)
        self.combo_personality.currentIndexChanged.connect(self._on_personality_changed)
        layout.addWidget(self.combo_personality)

        # Caixa de Exemplo da Personalidade
        self.pers_preview_box = QLabel("")
        self.pers_preview_box.setWordWrap(True)
        self.pers_preview_box.setStyleSheet("""
            background-color: rgba(30, 41, 59, 0.7);
            border: 1px solid #475569;
            border-radius: 8px;
            padding: 10px;
            color: #93c5fd;
            font-style: italic;
        """)
        layout.addWidget(self.pers_preview_box)

        layout.addStretch()
        scroll.setWidget(scroll_content)
        scroll_layout = QVBoxLayout(widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.addWidget(scroll)
        return widget

    # =========================================================================
    # ABA 3: Atalhos de Aplicativos do Windows
    # =========================================================================
    def _build_tab_shortcuts(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        desc = QLabel(
            "Cadastre arquivos e executáveis do Windows (.exe, .msc, .txt, .csv, etc.) com nomes de gatilho personalizados. "
            "Exemplo: cadastre um executável e chame de 'Abacate' -> você pode dizer 'Abra o Abacate'."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8;")
        layout.addWidget(desc)

        # Tabela de Atalhos
        self.table_shortcuts = QTableWidget(0, 2)
        self.table_shortcuts.setHorizontalHeaderLabels(["Gatilho (Nome Chamado)", "Caminho do Arquivo"])
        self.table_shortcuts.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_shortcuts.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_shortcuts.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table_shortcuts)

        # Formulário para Adicionar Novo Atalho
        form = QGridLayout()
        form.addWidget(QLabel("Nome do Gatilho:"), 0, 0)
        self.input_shortcut_trigger = QLineEdit()
        self.input_shortcut_trigger.setPlaceholderText("Ex: Abacate, Relatório, Código...")
        form.addWidget(self.input_shortcut_trigger, 0, 1)

        form.addWidget(QLabel("Caminho do Arquivo:"), 1, 0)
        path_box = QHBoxLayout()
        self.input_shortcut_path = QLineEdit()
        self.input_shortcut_path.setPlaceholderText("Caminho completo do arquivo (.exe, .msc, .txt, .csv)...")
        path_box.addWidget(self.input_shortcut_path)

        btn_browse = QPushButton("📁 Procurar...")
        btn_browse.clicked.connect(self._browse_shortcut_file)
        path_box.addWidget(btn_browse)
        form.addLayout(path_box, 1, 1)

        layout.addLayout(form)

        # Botões de Ação na Tabela
        btn_row = QHBoxLayout()
        self.btn_add_shortcut = QPushButton("➕ Cadastrar Atalho")
        self.btn_add_shortcut.clicked.connect(self._add_shortcut)
        btn_row.addWidget(self.btn_add_shortcut)

        self.btn_test_shortcut = QPushButton("▶ Testar Execução")
        self.btn_test_shortcut.clicked.connect(self._test_selected_shortcut)
        btn_row.addWidget(self.btn_test_shortcut)

        self.btn_remove_shortcut = QPushButton("🗑️ Remover Selecionado")
        self.btn_remove_shortcut.clicked.connect(self._remove_selected_shortcut)
        btn_row.addWidget(self.btn_remove_shortcut)

        layout.addLayout(btn_row)
        return widget

    # =========================================================================
    # ABA 4: Agenda e Lembretes Inteligentes
    # =========================================================================
    def _build_tab_agenda(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        desc = QLabel(
            "Cadastre compromissos e tarefas com notificações sonoras ativas. "
            "Quando expirar, o robô notificará visualmente e falará em voz alta: "
            "'Ei [Seu Nome], não esqueça do seu compromisso: [Título]'."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8;")
        layout.addWidget(desc)

        # Tabela de Compromissos
        self.table_agenda = QTableWidget(0, 4)
        self.table_agenda.setHorizontalHeaderLabels(["Título", "Data & Hora", "Notificar", "Antecedência"])
        self.table_agenda.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_agenda.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_agenda.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_agenda.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_agenda.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table_agenda)

        # Formulário de Novo Compromisso
        form = QGridLayout()
        form.addWidget(QLabel("Título do Compromisso:"), 0, 0)
        self.input_agenda_title = QLineEdit()
        self.input_agenda_title.setPlaceholderText("Ex: Reunião com Diretoria, Tomar Remédio...")
        form.addWidget(self.input_agenda_title, 0, 1)

        form.addWidget(QLabel("Data e Horário:"), 1, 0)
        dt_box = QHBoxLayout()
        self.input_agenda_date = QLineEdit()
        self.input_agenda_date.setText(datetime.now().strftime("%Y-%m-%d"))
        self.input_agenda_date.setPlaceholderText("AAAA-MM-DD")
        dt_box.addWidget(self.input_agenda_date)

        self.input_agenda_time = QLineEdit()
        self.input_agenda_time.setText((datetime.now()).strftime("%H:%M"))
        self.input_agenda_time.setPlaceholderText("HH:MM")
        dt_box.addWidget(self.input_agenda_time)
        form.addLayout(dt_box, 1, 1)

        form.addWidget(QLabel("Notificação Ativa:"), 2, 0)
        notify_box = QHBoxLayout()
        self.chk_agenda_notify = QCheckBox("Ativar Alerta Falado pelo Robô")
        self.chk_agenda_notify.setChecked(True)
        notify_box.addWidget(self.chk_agenda_notify)

        self.combo_agenda_freq = QComboBox()
        self._setup_combobox(self.combo_agenda_freq)
        self.combo_agenda_freq.addItem("10 minutos antes (10m)", "10m")
        self.combo_agenda_freq.addItem("1 hora antes (1h)", "1h")
        self.combo_agenda_freq.addItem("2 horas antes (2h)", "2h")
        self.combo_agenda_freq.addItem("1 dia antes (1d)", "1d")
        self.combo_agenda_freq.addItem("2 dias antes (2d)", "2d")
        notify_box.addWidget(self.combo_agenda_freq)
        form.addLayout(notify_box, 2, 1)

        layout.addLayout(form)

        # Botões de Ação da Agenda
        btn_row = QHBoxLayout()
        self.btn_add_agenda = QPushButton("➕ Cadastrar Compromisso")
        self.btn_add_agenda.clicked.connect(self._add_agenda_item)
        btn_row.addWidget(self.btn_add_agenda)

        self.btn_test_reminder = QPushButton("🔔 Testar Alerta do Robô")
        self.btn_test_reminder.clicked.connect(self._test_robot_alert)
        btn_row.addWidget(self.btn_test_reminder)

        self.btn_remove_agenda = QPushButton("🗑️ Excluir Selecionado")
        self.btn_remove_agenda.clicked.connect(self._remove_selected_agenda)
        btn_row.addWidget(self.btn_remove_agenda)

        layout.addLayout(btn_row)
        return widget

    def _make_separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: rgba(51, 65, 85, 0.6); margin: 6px 0;")
        return line

    def _setup_combobox(self, combo: QComboBox):
        """Configura QListView interno para garantir 100% de contraste e legibilidade nas opções suspensas."""
        view = QListView()
        view.setStyleSheet("""
            QListView {
                background-color: #0b1329;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
                outline: none;
            }
            QListView::item {
                min-height: 28px;
                padding: 6px 12px;
                color: #f8fafc;
                background-color: #0b1329;
                border-radius: 6px;
                margin: 1px 0px;
            }
            QListView::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QListView::item:hover {
                background-color: #1e293b;
                color: #38bdf8;
            }
        """)
        combo.setView(view)

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #090d16;
                color: #f8fafc;
            }
            QTabWidget::pane {
                border: 1px solid rgba(71, 85, 105, 0.4);
                background-color: rgba(15, 23, 42, 0.95);
                border-radius: 12px;
            }
            QTabBar::tab {
                background-color: rgba(15, 23, 42, 0.7);
                color: #94a3b8;
                padding: 9px 18px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 3px;
                font-weight: 600;
                font-size: 11px;
                border: 1px solid transparent;
            }
            QTabBar::tab:selected {
                background-color: rgba(30, 41, 59, 0.95);
                color: #38bdf8;
                font-weight: bold;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-bottom: none;
            }
            QTabBar::tab:hover:!selected {
                background-color: rgba(30, 41, 59, 0.5);
                color: #cbd5e1;
            }
            QLabel {
                color: #e2e8f0;
                font-size: 11px;
            }
            QLineEdit, QComboBox {
                background-color: #0b1329;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 7px 12px;
                font-size: 11px;
                min-height: 22px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #38bdf8;
                background-color: #0f1c3f;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                border-left: 1px solid #1e293b;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                background-color: #0b1329;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #94a3b8;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background-color: #0b1329;
                color: #f8fafc;
                selection-background-color: #0284c7;
                selection-color: #ffffff;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                min-height: 28px;
                padding: 6px 12px;
                color: #f8fafc;
                background-color: #0b1329;
                border-radius: 6px;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #1e293b;
                color: #38bdf8;
            }
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 7px 16px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #475569;
            }
            QPushButton#primaryBtn {
                background-color: #0284c7;
                border: 1px solid #38bdf8;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton#primaryBtn:hover {
                background-color: #0369a1;
                border-color: #7dd3fc;
            }
            QTableWidget {
                background-color: #0b1329;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                gridline-color: #1e293b;
            }
            QTableWidget::item {
                padding: 4px 8px;
            }
            QTableWidget::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #151f38;
                color: #94a3b8;
                padding: 6px;
                border: 1px solid #1e293b;
                font-weight: bold;
                font-size: 11px;
            }
            QScrollBar:vertical {
                background: #090d16;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #475569;
            }
        """)

    # =========================================================================
    # Lógica de Carregamento e Eventos
    # =========================================================================
    def _load_current_values(self):
        """Carrega os valores salvos no SettingsManager para os campos da tela."""
        # 1. Visual
        vis = self.current_visual
        chassis_map = {"classic": 0, "cyber": 1, "orb": 2, "mecha": 3}
        self.combo_chassis.setCurrentIndex(chassis_map.get(vis.get("chassis"), 0))

        eyes_map = {"capsule": 0, "visor": 1, "happy": 2, "dots": 3, "spider": 4}
        self.combo_eyes.setCurrentIndex(eyes_map.get(vis.get("eyes"), 0))

        mouth_map = {"wave": 0, "grille": 1, "smile": 2, "laser": 3}
        self.combo_mouth.setCurrentIndex(mouth_map.get(vis.get("mouth"), 0))

        acc_map = {"antenna": 0, "iron_crest": 1, "spikes": 2, "bat_horns": 3, "viking_horns": 4, "none": 5}
        self.combo_acc.setCurrentIndex(acc_map.get(vis.get("accessory"), 0))

        # 2. Nomes, Wake Word, Voz e Personalidade
        self.input_user_name.setText(self.settings.get_user_name())
        self.input_robot_name.setText(self.settings.get_robot_name())
        self.chk_wake_word.setChecked(self.settings.is_wake_word_enabled())

        voice_id = self.settings.get_voice()
        idx_voice = self.combo_voice.findData(voice_id)
        if idx_voice >= 0:
            self.combo_voice.setCurrentIndex(idx_voice)

        pers_id = self.settings.get_personality()
        idx_pers = self.combo_personality.findData(pers_id)
        if idx_pers >= 0:
            self.combo_personality.setCurrentIndex(idx_pers)
        self._on_personality_changed()

        # 3. Atalhos
        self._refresh_shortcuts_table()

        # 4. Agenda
        self._refresh_agenda_table()

    def _on_visual_changed(self):
        """Atualiza a configuração visual conforme combos e atualiza o preview."""
        chassis_keys = ["classic", "cyber", "orb", "mecha"]
        eyes_keys = ["capsule", "visor", "happy", "dots", "spider"]
        mouth_keys = ["wave", "grille", "smile", "laser"]
        acc_keys = ["antenna", "iron_crest", "spikes", "bat_horns", "viking_horns", "none"]

        self.current_visual["chassis"] = chassis_keys[self.combo_chassis.currentIndex()]
        self.current_visual["eyes"] = eyes_keys[self.combo_eyes.currentIndex()]
        self.current_visual["mouth"] = mouth_keys[self.combo_mouth.currentIndex()]
        self.current_visual["accessory"] = acc_keys[self.combo_acc.currentIndex()]

        self.preview.set_config(self.current_visual)

    def _apply_heroic_skin(self, skin_id: str):
        """Aplica uma das 5 skins heróicas lendárias perfeitamente."""
        skin_data = SKINS.get(skin_id)
        if not skin_data:
            return

        self.current_visual["skin"] = skin_id
        if "chassis" in skin_data:
            self.current_visual["chassis"] = skin_data["chassis"]
        if "eyes" in skin_data:
            self.current_visual["eyes"] = skin_data["eyes"]
        if "mouth" in skin_data:
            self.current_visual["mouth"] = skin_data["mouth"]
        if "accessory" in skin_data:
            self.current_visual["accessory"] = skin_data["accessory"]
        if "body_color" in skin_data:
            self.current_visual["body_color"] = skin_data["body_color"]
        if "detail_color" in skin_data:
            self.current_visual["detail_color"] = skin_data["detail_color"]
        if "led_color" in skin_data:
            self.current_visual["led_color"] = skin_data["led_color"]

        self._load_current_values()
        self.preview.set_config(self.current_visual)

    def _pick_color(self, target_key: str):
        """Abre seletor nativo de cor."""
        curr = QColor(self.current_visual.get(target_key, "#0ea5e9"))
        chosen = QColorDialog.getColor(curr, self, "Escolha uma Cor")
        if chosen.isValid():
            self.current_visual[target_key] = chosen.name()
            self.preview.set_config(self.current_visual)

    def _reset_visual_defaults(self):
        """Restaura as peças e cores padrão."""
        self.current_visual = {
            "skin": "custom",
            "chassis": "classic",
            "eyes": "capsule",
            "mouth": "wave",
            "accessory": "antenna",
            "body_color": "#1e293b",
            "detail_color": "#334155",
            "led_color": "#0ea5e9"
        }
        self._load_current_values()
        self.preview.set_config(self.current_visual)

    def _on_personality_changed(self):
        pers_id = self.combo_personality.currentData() or "friendly"
        user_name = self.input_user_name.text().strip() or "Everton"
        example_resp = PersonalityManager.format_response(
            pers_id,
            "Recebi o seu comando perfeitamente e estou pronto.",
            user_name
        )
        p_info = PersonalityManager.PERSONALITIES.get(pers_id, {})
        desc = p_info.get("desc", "")
        self.pers_preview_box.setText(f"★ Tom: {desc}\n\nExemplo de Fala:\n\"{example_resp}\"")

    def _test_voice(self):
        """Testa a voz selecionada com a personalidade atual."""
        if not self.tts:
            return
        voice_id = self.combo_voice.currentData()
        self.tts.set_voice(voice_id)
        user_name = self.input_user_name.text().strip() or "Everton"
        pers_id = self.combo_personality.currentData() or "friendly"
        test_msg = PersonalityManager.format_wake_response(pers_id, user_name)
        self.tts.speak(test_msg)

    # -------------------------------------------------------------------------
    # Métodos de Atalhos
    # -------------------------------------------------------------------------
    def _refresh_shortcuts_table(self):
        shortcuts = self.settings.get_shortcuts()
        self.table_shortcuts.setRowCount(len(shortcuts))
        for row, item in enumerate(shortcuts):
            self.table_shortcuts.setItem(row, 0, QTableWidgetItem(item.get("trigger", "")))
            self.table_shortcuts.setItem(row, 1, QTableWidgetItem(item.get("path", "")))

    def _browse_shortcut_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecione o Aplicativo ou Arquivo",
            "",
            "Arquivos Suportados (*.exe *.msc *.bat *.cmd *.txt *.csv *.pdf *.docx *.xlsx);;Todos os Arquivos (*.*)"
        )
        if file_path:
            self.input_shortcut_path.setText(file_path)
            if not self.input_shortcut_trigger.text().strip():
                # Sugere o nome do arquivo sem extensão como gatilho
                import os
                base = os.path.splitext(os.path.basename(file_path))[0]
                self.input_shortcut_trigger.setText(base.capitalize())

    def _add_shortcut(self):
        trigger = self.input_shortcut_trigger.text().strip()
        path = self.input_shortcut_path.text().strip()
        if not trigger or not path:
            QMessageBox.warning(self, "Aviso", "Preencha o nome do gatilho e o caminho do arquivo.")
            return

        self.settings.add_shortcut(trigger, path)
        self.input_shortcut_trigger.clear()
        self.input_shortcut_path.clear()
        self._refresh_shortcuts_table()

    def _test_selected_shortcut(self):
        curr_row = self.table_shortcuts.currentRow()
        if curr_row < 0:
            QMessageBox.information(self, "Aviso", "Selecione um atalho na tabela para testar.")
            return

        shortcuts = self.settings.get_shortcuts()
        if curr_row < len(shortcuts):
            item = shortcuts[curr_row]
            msg, ok = ShortcutManager.execute_shortcut(item)
            if ok:
                QMessageBox.information(self, "Sucesso", msg)
            else:
                QMessageBox.critical(self, "Erro", msg)

    def _remove_selected_shortcut(self):
        curr_row = self.table_shortcuts.currentRow()
        if curr_row < 0:
            return
        shortcuts = self.settings.get_shortcuts()
        if curr_row < len(shortcuts):
            item = shortcuts[curr_row]
            self.settings.remove_shortcut(item.get("id", ""))
            self._refresh_shortcuts_table()

    # -------------------------------------------------------------------------
    # Métodos de Agenda
    # -------------------------------------------------------------------------
    def _refresh_agenda_table(self):
        agenda_items = self.settings.get_agenda()
        self.table_agenda.setRowCount(len(agenda_items))
        for row, item in enumerate(agenda_items):
            self.table_agenda.setItem(row, 0, QTableWidgetItem(item.get("title", "")))
            self.table_agenda.setItem(row, 1, QTableWidgetItem(item.get("datetime", "")))
            notify_str = "Sim" if item.get("notify", True) else "Não"
            self.table_agenda.setItem(row, 2, QTableWidgetItem(notify_str))
            self.table_agenda.setItem(row, 3, QTableWidgetItem(item.get("frequency", "10m")))

    def _add_agenda_item(self):
        title = self.input_agenda_title.text().strip()
        date_str = self.input_agenda_date.text().strip()
        time_str = self.input_agenda_time.text().strip()
        if not title or not date_str or not time_str:
            QMessageBox.warning(self, "Aviso", "Informe título, data e horário do compromisso.")
            return

        dt_str = f"{date_str} {time_str}"
        freq = self.combo_agenda_freq.currentData() or "10m"
        notify = self.chk_agenda_notify.isChecked()

        self.settings.add_agenda_item(
            title=title,
            datetime_str=dt_str,
            notify=notify,
            frequency=freq,
            description="Cadastrado via painel de configurações"
        )
        self.input_agenda_title.clear()
        self._refresh_agenda_table()

    def _test_robot_alert(self):
        """Testa a frase ativa de notificação do robô."""
        user_name = self.input_user_name.text().strip() or "Everton"
        alert_phrase = f"Ei {user_name}, não esqueça do seu compromisso: Reunião Importante!"
        if self.tts:
            voice_id = self.combo_voice.currentData()
            self.tts.set_voice(voice_id)
            self.tts.speak(alert_phrase)
        QMessageBox.information(self, "Teste de Alerta Ativo", f"Alerta emitido pelo Mascote:\n\"{alert_phrase}\"")

    def _remove_selected_agenda(self):
        curr_row = self.table_agenda.currentRow()
        if curr_row < 0:
            return
        items = self.settings.get_agenda()
        if curr_row < len(items):
            item = items[curr_row]
            self.settings.remove_agenda_item(item.get("id", ""))
            self._refresh_agenda_table()

    # -------------------------------------------------------------------------
    # Salvar Tudo
    # -------------------------------------------------------------------------
    def _save_all_settings(self):
        """Persiste todas as abas no JSON do SettingsManager."""
        # Visual
        self.settings.update_visual(**self.current_visual)

        # Identificação e Voz
        user_name = self.input_user_name.text().strip() or "Everton"
        robot_name = self.input_robot_name.text().strip() or "Laranja"
        wake_enabled = self.chk_wake_word.isChecked()
        voice_id = self.combo_voice.currentData() or "pt-BR-AntonioNeural"
        pers_id = self.combo_personality.currentData() or "friendly"

        self.settings.set_user_name(user_name)
        self.settings.set_robot_name(robot_name)
        self.settings.set_wake_word_enabled(wake_enabled)
        self.settings.set_voice(voice_id)
        self.settings.set_personality(pers_id)

        if self.tts:
            self.tts.set_voice(voice_id)

        self.settings_saved.emit()
        self.accept()

