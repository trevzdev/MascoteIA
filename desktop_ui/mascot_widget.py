"""
Widget do Mascote Robô Flutuante e Animado
Renderizado com o Sistema Modular de Encaixe Perfeito (ModularMascotPainter).
Suporta chassis, olhos, boca, acessórios, skins heróicas,
física de flutuação senoidal, piscadas de olhos e anéis de áudio responsivos.
"""

import math
import random
from enum import Enum
from typing import Dict, Any
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QCursor
from PyQt6.QtWidgets import QWidget

from desktop_ui.modular_mascot import ModularMascotPainter, SKINS
from desktop_ui.settings_manager import SettingsManager


class MascotState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


class MascotWidget(QWidget):
    """Widget que desenha o mascote modular e animado com física responsiva."""

    clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()

    def __init__(self, parent=None, size: int = 140, settings_manager: SettingsManager = None):
        super().__init__(parent)
        self.setFixedSize(size, size + 20)
        self.setMouseTracking(True)

        self.settings = settings_manager or SettingsManager()
        self.visual_config: Dict[str, Any] = self.settings.get_visual_config()

        self.state = MascotState.IDLE
        self.accent_color = QColor(self.visual_config.get("led_color", "#0ea5e9"))
        self.amplitude = 0.0  # Nível de áudio do microfone (0.0 a 1.0)

        # Variáveis de Animação
        self._tick = 0.0
        self._bob_y = 0.0
        self._is_blinking = False
        self._blink_counter = 0
        self._blink_interval = random.randint(80, 160)
        self._look_target = QPointF(0, 0)
        self._current_look = QPointF(0, 0)
        self._pulse_radius = 0.0

        # Timer de Animação (~60 FPS para máxima fluidez)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)
        self.anim_timer.start(16)

    def set_state(self, new_state: MascotState):
        """Altera o estado emocional/operacional do mascote."""
        self.state = new_state
        self.update()

    def set_amplitude(self, amp: float):
        """Atualiza a intensidade sonora do microfone para animar a fala."""
        self.amplitude = max(0.0, min(1.0, amp))
        self.update()

    def update_visual_config(self, new_config: Dict[str, Any]):
        """Aplica uma nova configuração de peças, cores ou skin heróica."""
        self.visual_config.update(new_config)
        self.update()

    def set_accent_color(self, color: QColor):
        """Atualiza a cor dos LEDs."""
        self.accent_color = color
        self.visual_config["led_color"] = color.name()
        self.settings.update_visual(led_color=color.name())
        self.update()

    def _update_animation(self):
        """Ciclo de atualização física e temporal das animações."""
        self._tick += 0.06

        # Flutuação senoidal (Hover suave)
        self._bob_y = math.sin(self._tick) * 5.0

        # Anel de pulso contínuo
        self._pulse_radius = (self._pulse_radius + 0.6) % 24.0

        # Lógica de Piscada Natural
        self._blink_counter += 1
        if not self._is_blinking and self._blink_counter >= self._blink_interval:
            self._is_blinking = True
            self._blink_counter = 0
        elif self._is_blinking and self._blink_counter >= 6:  # Dura ~120ms
            self._is_blinking = False
            self._blink_counter = 0
            self._blink_interval = random.randint(90, 180)

        # Suavização do movimento dos olhos
        self._current_look = QPointF(
            self._current_look.x() + (self._look_target.x() - self._current_look.x()) * 0.15,
            self._current_look.y() + (self._look_target.y() - self._current_look.y()) * 0.15,
        )

        self.update()

    def mouseMoveEvent(self, event):
        """Olha suavemente na direção do cursor do mouse e repassa arraste ao parent se clicado."""
        center = QPointF(self.width() / 2, self.height() / 2)
        dx = (event.position().x() - center.x()) / (self.width() / 2)
        dy = (event.position().y() - center.y()) / (self.height() / 2)
        self._look_target = QPointF(
            max(-1.0, min(1.0, dx)) * 4.0,
            max(-1.0, min(1.0, dy)) * 3.0,
        )
        if (event.buttons() & Qt.MouseButton.LeftButton) and self.parent():
            self.parent().mouseMoveEvent(event)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        """Retorna o olhar para o centro ao sair do widget."""
        self._look_target = QPointF(0, 0)
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position()
            if self.parent():
                self.parent().mousePressEvent(event)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if hasattr(self, "_press_pos") and self._press_pos is not None:
                dist = (event.position() - self._press_pos).manhattanLength()
                if dist < 6:
                    self.clicked.emit()
                self._press_pos = None
            if self.parent():
                self.parent().mouseReleaseEvent(event)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = (h / 2.0) + self._bob_y

        # Desenho modular completo com slots milimétricos (limpo, sem engrenagem na cabeça)
        ModularMascotPainter.paint_robot(
            painter=painter,
            center=QPointF(cx, cy),
            config=self.visual_config,
            state_str=self.state.value,
            amplitude=self.amplitude,
            is_blinking=self._is_blinking,
            look_offset=self._current_look,
            pulse_radius=self._pulse_radius,
            tick=self._tick,
        )
