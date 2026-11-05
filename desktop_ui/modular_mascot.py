"""
Renderizador Modular do Mascote Robô (SVGs Estruturados e QPainter)
Implementa o Sistema de Encaixe Perfeito com coordenadas relativas e slots de ancoragem:
- Chassis / Corpos (Classic, Cyber, Orb, Mecha)
- Olhos / Visores (Capsule, Visor, Happy, Cyber Dots, Spider)
- Bocas / Grelhas (Sound Wave, Tech Grille, LED Smile, Laser Line)
- Acessórios / Capacetes (Antenna, Iron Crest, Spikes, Bat Horns, Viking Horns, None)
- Temas Heroicos / Lendários (Armadura de Ferro, Patriota, Aranha, Deus do Trovão, Vigilante Noturno)
"""

import math
from typing import Dict, Any, Tuple
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QBrush,
    QPen,
    QRadialGradient,
    QLinearGradient,
    QPainterPath,
)

# Definição das Skins Lendárias
SKINS: Dict[str, Dict[str, Any]] = {
    "custom": {
        "name": "Customizado",
        "description": "Suas próprias escolhas de peças e cores livres."
    },
    "iron_armor": {
        "name": "Armadura de Ferro",
        "chassis": "mecha",
        "eyes": "visor",
        "mouth": "laser",
        "accessory": "iron_crest",
        "body_color": "#8b0000",
        "detail_color": "#eab308",
        "led_color": "#06b6d4",
        "description": "Inspirado no gênio bilionário com armadura dourada e reator arc ciano."
    },
    "patriot": {
        "name": "Patriota",
        "chassis": "classic",
        "eyes": "capsule",
        "mouth": "grille",
        "accessory": "iron_crest",
        "body_color": "#1e3a8a",
        "detail_color": "#dc2626",
        "led_color": "#f8fafc",
        "description": "Azul cobalto, detalhes rubro e branco com postura heróica impecável."
    },
    "spider": {
        "name": "Aranha",
        "chassis": "cyber",
        "eyes": "spider",
        "mouth": "wave",
        "accessory": "none",
        "body_color": "#991b1b",
        "detail_color": "#1e1b4b",
        "led_color": "#ffffff",
        "description": "Vermelho teia com olhos angulares multi-ópticos brancos de alta precisão."
    },
    "thunder_god": {
        "name": "Deus do Trovão",
        "chassis": "mecha",
        "eyes": "capsule",
        "mouth": "wave",
        "accessory": "viking_horns",
        "body_color": "#475569",
        "detail_color": "#d97706",
        "led_color": "#38bdf8",
        "description": "Aço de Asgard, chifres alados reluzentes e descargas de relâmpago azul celeste."
    },
    "night_vigilante": {
        "name": "Vigilante Noturno",
        "chassis": "cyber",
        "eyes": "visor",
        "mouth": "grille",
        "accessory": "bat_horns",
        "body_color": "#09090b",
        "detail_color": "#27272a",
        "led_color": "#eab308",
        "description": "Preto stealth fosco, chifres táticos pontiagudos e visor âmbar vigilante."
    }
}


class ModularMascotPainter:
    """Calcula e desenha cada camada modular garantindo encaixe milimétrico."""

    @classmethod
    def paint_robot(
        cls,
        painter: QPainter,
        center: QPointF,
        config: Dict[str, Any],
        state_str: str = "idle",
        amplitude: float = 0.0,
        is_blinking: bool = False,
        look_offset: QPointF = QPointF(0, 0),
        pulse_radius: float = 0.0,
        tick: float = 0.0,
    ):
        """
        Desenha a composição modular completa respeitando a hierarquia de camadas:
        1. Anéis de Energia de Fundo
        2. Acessórios Traseiros (Chifres/Asas/Antena)
        3. Carcaça / Chassi Principal
        4. Orelhas / Fones Laterais
        5. Visor / Tela dos Olhos
        6. Olhos e Boca nos Slots Milimétricos
        7. Acessórios Frontais / Cristas
        """
        cx = center.x()
        cy = center.y()

        chassis_type = config.get("chassis", "classic")
        eyes_type = config.get("eyes", "capsule")
        mouth_type = config.get("mouth", "wave")
        accessory_type = config.get("accessory", "antenna")

        body_col = QColor(config.get("body_color", "#1e293b"))
        detail_col = QColor(config.get("detail_color", "#334155"))
        led_col = QColor(config.get("led_color", "#0ea5e9"))

        # Modulação de cor conforme estado emocional
        if state_str == "listening":
            active_glow = QColor("#f59e0b")  # Âmbar
        elif state_str == "thinking":
            active_glow = QColor("#a855f7")  # Roxo
        elif state_str == "speaking":
            active_glow = QColor("#10b981")  # Verde
        elif state_str == "error":
            active_glow = QColor("#ef4444")  # Vermelho
        else:
            active_glow = led_col

        # -------------------------------------------------------------
        # 1. Anéis Sonoros / Pulsos de Energia
        # -------------------------------------------------------------
        if state_str in ("listening", "speaking"):
            dyn = amplitude * 22.0
            rad = 48.0 + pulse_radius + dyn
            ring_col = QColor(active_glow)
            alpha = max(0, int(150 * (1.0 - (pulse_radius / 24.0))))
            ring_col.setAlpha(alpha)
            painter.setPen(QPen(ring_col, 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, rad, rad * 0.9)

        # -------------------------------------------------------------
        # 2. Definição dos Slots de Encaixe com base no Chassi
        # -------------------------------------------------------------
        # Cada chassi retorna seus pontos de ancoragem e dimensões relativas fixas
        slots = cls._get_chassis_slots(chassis_type, cx, cy)

        # -------------------------------------------------------------
        # 3. Acessório de Topo / Traseiro
        # -------------------------------------------------------------
        cls._draw_accessory(painter, slots["top_anchor"], accessory_type, detail_col, active_glow, tick)

        # -------------------------------------------------------------
        # 4. Orelhas / Fones Laterais
        # -------------------------------------------------------------
        cls._draw_ears(painter, slots["left_ear"], slots["right_ear"], detail_col, active_glow)

        # -------------------------------------------------------------
        # 5. Chassi / Carcaça Metálica Principal
        # -------------------------------------------------------------
        cls._draw_chassis(painter, slots["chassis_rect"], chassis_type, body_col, detail_col)

        # -------------------------------------------------------------
        # 6. Visor OLED Centralizado no Slot de Olhos
        # -------------------------------------------------------------
        screen_rect = slots["screen_rect"]
        painter.setBrush(QBrush(QColor("#030712")))  # Preto ultra-profundo
        painter.setPen(QPen(detail_col, 1.5))
        painter.drawRoundedRect(screen_rect, 12, 12)

        # Brilho de Vidro Superior
        glass_rect = QRectF(screen_rect.x(), screen_rect.y(), screen_rect.width(), screen_rect.height() * 0.4)
        painter.setBrush(QBrush(QColor(255, 255, 255, 18)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(glass_rect, 10, 10)

        # -------------------------------------------------------------
        # 7. Olhos Encaixados no Slot de Visão
        # -------------------------------------------------------------
        eye_center = QPointF(slots["eye_center"].x() + look_offset.x(), slots["eye_center"].y() + look_offset.y())
        cls._draw_eyes(
            painter, eye_center, slots["eye_box"], eyes_type, active_glow, is_blinking, state_str, tick
        )

        # -------------------------------------------------------------
        # 8. Boca Encaixada no Slot de Fala
        # -------------------------------------------------------------
        mouth_center = slots["mouth_center"]
        cls._draw_mouth(
            painter, mouth_center, slots["mouth_box"], mouth_type, active_glow, state_str, amplitude, tick
        )

    @classmethod
    def _get_chassis_slots(cls, chassis_type: str, cx: float, cy: float) -> Dict[str, Any]:
        """Calcula a geometria dos slots percentuais com ancoragem estrita."""
        if chassis_type == "cyber":
            w, h = 94.0, 78.0
            rect = QRectF(cx - w / 2, cy - h / 2, w, h)
            return {
                "chassis_rect": rect,
                "screen_rect": QRectF(cx - 36, cy - 24, 72, 34),
                "eye_center": QPointF(cx, cy - 8),
                "eye_box": QRectF(cx - 32, cy - 20, 64, 24),
                "mouth_center": QPointF(cx, cy + 22),
                "mouth_box": QRectF(cx - 24, cy + 14, 48, 16),
                "top_anchor": QPointF(cx, cy - 39),
                "left_ear": QPointF(cx - 48, cy),
                "right_ear": QPointF(cx + 48, cy),
            }
        elif chassis_type == "orb":
            w, h = 88.0, 88.0
            rect = QRectF(cx - w / 2, cy - h / 2, w, h)
            return {
                "chassis_rect": rect,
                "screen_rect": QRectF(cx - 33, cy - 23, 66, 32),
                "eye_center": QPointF(cx, cy - 8),
                "eye_box": QRectF(cx - 28, cy - 18, 56, 22),
                "mouth_center": QPointF(cx, cy + 20),
                "mouth_box": QRectF(cx - 20, cy + 14, 40, 14),
                "top_anchor": QPointF(cx, cy - 44),
                "left_ear": QPointF(cx - 44, cy),
                "right_ear": QPointF(cx + 44, cy),
            }
        elif chassis_type == "mecha":
            w, h = 96.0, 82.0
            rect = QRectF(cx - w / 2, cy - h / 2, w, h)
            return {
                "chassis_rect": rect,
                "screen_rect": QRectF(cx - 35, cy - 26, 70, 36),
                "eye_center": QPointF(cx, cy - 9),
                "eye_box": QRectF(cx - 30, cy - 21, 60, 24),
                "mouth_center": QPointF(cx, cy + 23),
                "mouth_box": QRectF(cx - 22, cy + 15, 44, 16),
                "top_anchor": QPointF(cx, cy - 41),
                "left_ear": QPointF(cx - 49, cy),
                "right_ear": QPointF(cx + 49, cy),
            }
        else:  # classic
            w, h = 90.0, 76.0
            rect = QRectF(cx - w / 2, cy - h / 2, w, h)
            return {
                "chassis_rect": rect,
                "screen_rect": QRectF(cx - 34, cy - 24, 68, 34),
                "eye_center": QPointF(cx, cy - 8),
                "eye_box": QRectF(cx - 28, cy - 19, 56, 22),
                "mouth_center": QPointF(cx, cy + 21),
                "mouth_box": QRectF(cx - 22, cy + 14, 44, 15),
                "top_anchor": QPointF(cx, cy - 38),
                "left_ear": QPointF(cx - 46, cy),
                "right_ear": QPointF(cx + 46, cy),
            }

    @classmethod
    def _draw_chassis(cls, painter: QPainter, rect: QRectF, chassis_type: str, body_col: QColor, detail_col: QColor):
        """Renderiza a carcaça do chassi selecionado com gradientes metálicos."""
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, body_col.lighter(125))
        grad.setColorAt(0.6, body_col)
        grad.setColorAt(1.0, body_col.darker(140))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(detail_col, 2.0))

        if chassis_type == "cyber":
            # Formato sextavado angular
            path = QPainterPath()
            w, h = rect.width(), rect.height()
            x, y = rect.x(), rect.y()
            path.moveTo(x + 18, y)
            path.lineTo(x + w - 18, y)
            path.lineTo(x + w, y + 26)
            path.lineTo(x + w - 10, y + h)
            path.lineTo(x + 10, y + h)
            path.lineTo(x, y + 26)
            path.closeSubpath()
            painter.drawPath(path)
        elif chassis_type == "orb":
            # Formato circular duto aerodinâmico
            painter.drawEllipse(rect)
        elif chassis_type == "mecha":
            # Blindagem reforçada com queixeira tática
            path = QPainterPath()
            w, h = rect.width(), rect.height()
            x, y = rect.x(), rect.y()
            path.moveTo(x + 12, y)
            path.lineTo(x + w - 12, y)
            path.lineTo(x + w, y + 24)
            path.lineTo(x + w - 8, y + h - 14)
            path.lineTo(x + w / 2, y + h)
            path.lineTo(x + 8, y + h - 14)
            path.lineTo(x, y + 24)
            path.closeSubpath()
            painter.drawPath(path)
        else:  # classic
            painter.drawRoundedRect(rect, 24, 24)

    @classmethod
    def _draw_ears(cls, painter: QPainter, left_pt: QPointF, right_pt: QPointF, detail_col: QColor, led_col: QColor):
        """Desenha os fones auditivos laterais."""
        ear_w, ear_h = 8.0, 24.0
        for pt, side in ((left_pt, -1), (right_pt, 1)):
            ear_rect = QRectF(pt.x() - ear_w / 2, pt.y() - ear_h / 2, ear_w, ear_h)
            painter.setBrush(QBrush(detail_col))
            painter.setPen(QPen(detail_col.darker(130), 1.5))
            painter.drawRoundedRect(ear_rect, 4, 4)

            # LED central na orelha
            painter.setBrush(QBrush(led_col))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(pt, 2.5, 2.5)

    @classmethod
    def _draw_accessory(
        cls, painter: QPainter, anchor: QPointF, acc_type: str, detail_col: QColor, led_col: QColor, tick: float
    ):
        """Renderiza os acessórios do topo da cabeça ancorados milimetricamente."""
        if acc_type == "antenna":
            # Haste
            top_pt = QPointF(anchor.x(), anchor.y() - 18)
            painter.setPen(QPen(detail_col, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(anchor, top_pt)

            # Esfera iluminada
            glow_grad = QRadialGradient(top_pt, 8.0)
            glow_grad.setColorAt(0.0, QColor(255, 255, 255, 240))
            glow_grad.setColorAt(0.5, led_col)
            glow_grad.setColorAt(1.0, QColor(led_col.red(), led_col.green(), led_col.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow_grad))
            painter.drawEllipse(top_pt, 8.0, 8.0)

        elif acc_type == "iron_crest":
            # Crista aero-estilizada do Homem de Ferro
            path = QPainterPath()
            path.moveTo(anchor.x() - 14, anchor.y() + 4)
            path.lineTo(anchor.x() - 4, anchor.y() - 16)
            path.lineTo(anchor.x(), anchor.y() - 20)
            path.lineTo(anchor.x() + 4, anchor.y() - 16)
            path.lineTo(anchor.x() + 14, anchor.y() + 4)
            path.closeSubpath()
            painter.setBrush(QBrush(detail_col))
            painter.setPen(QPen(detail_col.lighter(130), 1.5))
            painter.drawPath(path)

            # Linha de LED central
            painter.setPen(QPen(led_col, 2.0))
            painter.drawLine(QPointF(anchor.x(), anchor.y() + 2), QPointF(anchor.x(), anchor.y() - 16))

        elif acc_type == "spikes":
            # Espinhos / Aletas duplas
            for side in (-1, 1):
                path = QPainterPath()
                base_x = anchor.x() + (side * 18)
                path.moveTo(base_x - (side * 6), anchor.y() + 2)
                path.lineTo(base_x + (side * 14), anchor.y() - 18)
                path.lineTo(base_x + (side * 2), anchor.y() - 10)
                path.closeSubpath()
                painter.setBrush(QBrush(detail_col))
                painter.setPen(QPen(detail_col.lighter(120), 1.5))
                painter.drawPath(path)

        elif acc_type == "bat_horns":
            # Orelhas afiadas do Vigilante Noturno (Batman)
            for side in (-1, 1):
                path = QPainterPath()
                bx = anchor.x() + (side * 24)
                path.moveTo(bx - (side * 8), anchor.y() + 6)
                path.lineTo(bx + (side * 10), anchor.y() - 24)
                path.lineTo(bx + (side * 2), anchor.y() + 2)
                path.closeSubpath()
                painter.setBrush(QBrush(detail_col))
                painter.setPen(QPen(detail_col.darker(140), 1.5))
                painter.drawPath(path)

        elif acc_type == "viking_horns":
            # Chifres Alados Nórdicos (Thor)
            for side in (-1, 1):
                path = QPainterPath()
                bx = anchor.x() + (side * 20)
                path.moveTo(bx, anchor.y() + 4)
                path.cubicTo(
                    bx + (side * 22), anchor.y() - 6,
                    bx + (side * 30), anchor.y() - 26,
                    bx + (side * 18), anchor.y() - 32
                )
                path.cubicTo(
                    bx + (side * 24), anchor.y() - 20,
                    bx + (side * 14), anchor.y() - 12,
                    bx - (side * 4), anchor.y() + 2
                )
                path.closeSubpath()
                painter.setBrush(QBrush(detail_col))
                painter.setPen(QPen(detail_col.lighter(140), 1.5))
                painter.drawPath(path)

    @classmethod
    def _draw_eyes(
        cls,
        painter: QPainter,
        eye_center: QPointF,
        box: QRectF,
        eyes_type: str,
        led_col: QColor,
        is_blinking: bool,
        state_str: str,
        tick: float
    ):
        """Desenha os olhos dentro do slot de visão."""
        cx = eye_center.x()
        cy = eye_center.y()
        spacing = box.width() * 0.28

        if is_blinking:
            # Olho fechado em linha reta
            painter.setPen(QPen(led_col, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(cx - spacing - 7, cy), QPointF(cx - spacing + 7, cy))
            painter.drawLine(QPointF(cx + spacing - 7, cy), QPointF(cx + spacing + 7, cy))
            return

        if state_str == "speaking":
            # Olhos felizes em arco (^ ^)
            painter.setPen(QPen(led_col, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for ex in (cx - spacing, cx + spacing):
                path = QPainterPath()
                path.moveTo(ex - 7, cy + 3)
                path.quadTo(ex, cy - 7, ex + 7, cy + 3)
                painter.drawPath(path)
            return

        if eyes_type == "visor":
            # Visor contínuo horizontal
            visor_w = box.width() * 0.86
            visor_h = 10.0
            visor_rect = QRectF(cx - visor_w / 2, cy - visor_h / 2, visor_w, visor_h)
            painter.setBrush(QBrush(led_col))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(visor_rect, 5, 5)

            # Feixe laser percorrendo o visor
            sweep_x = cx + math.sin(tick * 3.5) * (visor_w * 0.35)
            painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
            painter.drawEllipse(QPointF(sweep_x, cy), 3.5, 3.5)

        elif eyes_type == "spider":
            # Olhos angulares de aranha (estilo Spider-Man)
            for side in (-1, 1):
                path = QPainterPath()
                ex = cx + (side * spacing)
                path.moveTo(ex - (side * 10), cy - 6)
                path.lineTo(ex + (side * 12), cy - 3)
                path.lineTo(ex + (side * 4), cy + 7)
                path.lineTo(ex - (side * 8), cy + 4)
                path.closeSubpath()
                painter.setBrush(QBrush(led_col))
                painter.setPen(QPen(QColor(255, 255, 255), 1.5))
                painter.drawPath(path)

        elif eyes_type == "cyber_dots":
            # Matriz de pontos digitais 3x3
            dot_rad = 2.0
            for side in (-1, 1):
                base_x = cx + (side * spacing)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        px = base_x + (dx * 5.0)
                        py = cy + (dy * 5.0)
                        painter.setBrush(QBrush(led_col))
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawEllipse(QPointF(px, py), dot_rad, dot_rad)

        elif eyes_type == "happy":
            # Olhos permanentemente expressivos (^ ^)
            painter.setPen(QPen(led_col, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for ex in (cx - spacing, cx + spacing):
                path = QPainterPath()
                path.moveTo(ex - 7, cy + 3)
                path.quadTo(ex, cy - 7, ex + 7, cy + 3)
                painter.drawPath(path)

        else:  # capsule (padrão)
            for ex in (cx - spacing, cx + spacing):
                painter.setBrush(QBrush(led_col))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(QRectF(ex - 6, cy - 8, 12, 16), 6, 6)

                # Ponto de reflexo pupilar branco
                painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
                painter.drawEllipse(QPointF(ex - 1.5, cy - 3.5), 2.2, 2.2)

    @classmethod
    def _draw_mouth(
        cls,
        painter: QPainter,
        mouth_center: QPointF,
        box: QRectF,
        mouth_type: str,
        led_col: QColor,
        state_str: str,
        amplitude: float,
        tick: float
    ):
        """Desenha a boca/equalizador no slot inferior."""
        cx = mouth_center.x()
        cy = mouth_center.y()

        if mouth_type == "grille":
            # Grelha de alto-falante horizontal
            painter.setPen(QPen(led_col, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for i in range(-2, 3):
                dy = cy + (i * 3.0)
                span = 14.0 - abs(i) * 3.0
                painter.drawLine(QPointF(cx - span, dy), QPointF(cx + span, dy))

        elif mouth_type == "smile":
            # Sorriso em arco suave
            path = QPainterPath()
            path.moveTo(cx - 12, cy - 2)
            path.quadTo(cx, cy + 6, cx + 12, cy - 2)
            painter.setPen(QPen(led_col, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        elif mouth_type == "laser":
            # Linha laser horizontal minimalista
            w = 26.0 + (amplitude * 14.0 if state_str in ("speaking", "listening") else 0.0)
            painter.setPen(QPen(led_col, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(cx - w / 2, cy), QPointF(cx + w / 2, cy))

        else:  # wave (onda de áudio padrão)
            painter.setPen(QPen(led_col, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            bar_count = 5
            step = 5.0
            for i in range(-2, 3):
                bx = cx + (i * step)
                if state_str == "speaking":
                    bar_h = 3.0 + math.sin(tick * 5.0 + abs(i) * 1.5) * 6.0
                elif state_str == "listening":
                    bar_h = 2.0 + (amplitude * 10.0) * math.sin(abs(i) + 1)
                else:
                    bar_h = 2.0 + math.sin(tick * 1.8 + abs(i)) * 1.5
                painter.drawLine(QPointF(bx, cy - bar_h), QPointF(bx, cy + bar_h))

