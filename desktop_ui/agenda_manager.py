"""
Gerenciador de Agenda e Lembretes Inteligentes do MascoteIA
Monitora compromissos cadastrados e dispara alertas visuais e de voz ativa:
"Ei [Seu Nome], não esqueça do seu compromisso: [Título]"
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from desktop_ui.settings_manager import SettingsManager


class AgendaManager(QObject):
    """Monitora ativamente a agenda e dispara alertas periódicos conforme a frequência."""

    reminder_triggered = pyqtSignal(dict)

    def __init__(self, parent_or_settings=None, settings_manager=None):
        if isinstance(parent_or_settings, QObject):
            super().__init__(parent_or_settings)
            self.settings = settings_manager or SettingsManager()
        elif isinstance(parent_or_settings, SettingsManager):
            super().__init__(None)
            self.settings = parent_or_settings
        else:
            super().__init__(None)
            self.settings = settings_manager or SettingsManager()

        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_reminders)
        self.check_timer.start(10000)  # Verifica a cada 10 segundos

    def stop_monitoring(self):
        """Para o timer de verificação da agenda."""
        self.check_timer.stop()

    def get_all_appointments(self) -> List[Dict[str, Any]]:
        return self.settings.get_agenda()

    def add_appointment(
        self, title: str, datetime_str: str, notify: bool = True, frequency: str = "10m", description: str = ""
    ) -> Dict[str, Any]:
        return self.settings.add_agenda_item(
            title=title,
            datetime_str=datetime_str,
            notify=notify,
            frequency=frequency,
            description=description,
        )

    def check_reminders(self):
        """Varre os compromissos cadastrados e verifica se algum atingiu o horário de aviso."""
        now = datetime.now()
        agenda = self.settings.get_agenda()

        for item in agenda:
            if not item.get("notify", True):
                continue

            dt_str = item.get("datetime")
            if not dt_str:
                continue

            try:
                # Suporta tanto ISO format (2026-11-05T15:00) quanto espaço (2026-11-05 15:00)
                clean_dt = dt_str.replace("T", " ")
                item_dt = datetime.strptime(clean_dt[:16], "%Y-%m-%d %H:%M")
            except Exception:
                continue

            freq = item.get("frequency", "10m")
            last_alert_str = item.get("last_alert")
            try:
                last_alert_dt = datetime.fromisoformat(last_alert_str) if last_alert_str else None
            except Exception:
                last_alert_dt = None

            # Calcula antecedência conforme a frequência selecionada
            if freq == "10m":
                lead_time = timedelta(minutes=10)
                repeat_delta = timedelta(minutes=10)
            elif freq == "1h":
                lead_time = timedelta(hours=1)
                repeat_delta = timedelta(hours=1)
            elif freq == "2h":
                lead_time = timedelta(hours=2)
                repeat_delta = timedelta(hours=2)
            elif freq == "1d":
                lead_time = timedelta(days=1)
                repeat_delta = timedelta(days=1)
            elif freq == "2d":
                lead_time = timedelta(days=2)
                repeat_delta = timedelta(days=2)
            else:  # padrão 10 minutos
                lead_time = timedelta(minutes=10)
                repeat_delta = timedelta(minutes=10)

            alert_time = item_dt - lead_time

            # Se o momento de alertar já chegou e ainda está na janela válida
            if now >= alert_time:
                should_alert = False

                if last_alert_dt is None:
                    should_alert = True
                elif repeat_delta and (now - last_alert_dt) >= repeat_delta:
                    # Se ainda não passou do evento em mais de 1 hora
                    if now <= (item_dt + timedelta(hours=1)):
                        should_alert = True

                if should_alert:
                    # Atualiza timestamp de último alerta no JSON
                    self.settings.update_agenda_item(item.get("id"), {"last_alert": now.isoformat()})
                    self.reminder_triggered.emit(item)
