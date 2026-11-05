"""
Gerenciador de Configurações e Persistência do MascoteIA
Armazena e carrega todas as preferências do usuário em JSON local (instance/mascot_settings.json):
- Identificação (Nome do Robô e Nome do Usuário)
- Ativação por Voz (Wake Word contínuo)
- Seleção de Voz TTS (3 Masculinas e 3 Femininas)
- Personalidade e Tom (7 estilos de diálogo)
- Customização Visual Modular (Chassi, Olhos, Bocas, Acessórios, Cores e Skins)
- Atalhos de Aplicativos do Windows
- Agenda e Lembretes Inteligentes
Suporta tanto chamadas de classe (SettingsManager.get_...) quanto chamadas de instância (self.settings.get_...).
"""

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from config import BASE_DIR

SETTINGS_FILE = Path(BASE_DIR) / "instance" / "mascot_settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "robot_name": "Davros",
    "user_name": "Everton",
    "wake_word_enabled": True,
    "voice_id": "male_1",
    "personality": "sarcastico",
    "visual": {
        "chassis": "mecha",
        "eyes": "capsule",
        "mouth": "wave",
        "accessory": "antenna",
        "body_color": "#991b1b",
        "detail_color": "#1e1b4b",
        "led_color": "#ffffff",
        "skin": "spider"
    },
    "shortcuts": [],
    "agenda": []
}


class SettingsManager:
    """Gerenciador unificado de persistência com suporte a métodos de classe e de instância."""

    _cached_settings: Optional[Dict[str, Any]] = None
    _cached_mtime: float = 0.0

    @classmethod
    def get_file_path(cls) -> Path:
        os.makedirs(SETTINGS_FILE.parent, exist_ok=True)
        return SETTINGS_FILE

    @classmethod
    def load(cls, force_reload: bool = False) -> Dict[str, Any]:
        """Carrega as configurações salvas, mesclando com os padrões para evitar chaves ausentes."""
        path = cls.get_file_path()
        if not path.exists():
            cls._cached_settings = json.loads(json.dumps(DEFAULT_SETTINGS))
            cls.save(cls._cached_settings)
            return cls._cached_settings

        try:
            mtime = path.stat().st_mtime
            if cls._cached_settings is not None and not force_reload and mtime == cls._cached_mtime:
                return cls._cached_settings

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = json.loads(json.dumps(DEFAULT_SETTINGS))
            cls._deep_merge(merged, data)
            cls._cached_settings = merged
            cls._cached_mtime = mtime
            return cls._cached_settings
        except Exception:
            if cls._cached_settings is not None:
                return cls._cached_settings
            cls._cached_settings = json.loads(json.dumps(DEFAULT_SETTINGS))
            return cls._cached_settings

    @classmethod
    def save(cls, settings: Dict[str, Any]) -> bool:
        """Salva as configurações atualizadas no arquivo JSON."""
        cls._cached_settings = settings
        path = cls.get_file_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            try:
                cls._cached_mtime = path.stat().st_mtime
            except Exception:
                pass
            return True
        except Exception:
            return False

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        settings = cls.load()
        return settings.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> bool:
        settings = cls.load()
        settings[key] = value
        return cls.save(settings)

    # --------------------------------------------------------------------------
    # Nomes e Identificação
    # --------------------------------------------------------------------------
    @classmethod
    def get_robot_name(cls) -> str:
        return cls.get("robot_name", "Laranja")

    @classmethod
    def set_robot_name(cls, name: str) -> bool:
        return cls.set("robot_name", name.strip() or "Laranja")

    @classmethod
    def get_user_name(cls) -> str:
        return cls.get("user_name", "Everton")

    @classmethod
    def set_user_name(cls, name: str) -> bool:
        return cls.set("user_name", name.strip() or "Everton")

    # --------------------------------------------------------------------------
    # Wake Word
    # --------------------------------------------------------------------------
    @classmethod
    def is_wake_word_enabled(cls) -> bool:
        return bool(cls.get("wake_word_enabled", True))

    @classmethod
    def set_wake_word_enabled(cls, enabled: bool) -> bool:
        return cls.set("wake_word_enabled", bool(enabled))

    # --------------------------------------------------------------------------
    # Voz e Personalidade
    # --------------------------------------------------------------------------
    @classmethod
    def get_voice(cls) -> str:
        return cls.get("voice_id", "pt-BR-AntonioNeural")

    @classmethod
    def get_voice_id(cls) -> str:
        return cls.get_voice()

    @classmethod
    def set_voice(cls, voice_id: str) -> bool:
        return cls.set("voice_id", voice_id)

    @classmethod
    def get_personality(cls) -> str:
        return cls.get("personality", "friendly")

    @classmethod
    def set_personality(cls, pers_id: str) -> bool:
        return cls.set("personality", pers_id)

    # --------------------------------------------------------------------------
    # Visual e Modular
    # --------------------------------------------------------------------------
    @classmethod
    def get_visual_config(cls) -> Dict[str, Any]:
        vis = cls.get("visual", DEFAULT_SETTINGS["visual"])
        merged = dict(DEFAULT_SETTINGS["visual"])
        merged.update(vis)
        return merged

    @classmethod
    def update_visual(cls, **kwargs) -> bool:
        settings = cls.load()
        if "visual" not in settings:
            settings["visual"] = dict(DEFAULT_SETTINGS["visual"])
        settings["visual"].update(kwargs)
        return cls.save(settings)

    # --------------------------------------------------------------------------
    # Atalhos do Windows
    # --------------------------------------------------------------------------
    @classmethod
    def get_shortcuts(cls) -> List[Dict[str, Any]]:
        return cls.get("shortcuts", [])

    @classmethod
    def add_shortcut(cls, trigger: str, path: str, description: str = "") -> Dict[str, Any]:
        settings = cls.load()
        if "shortcuts" not in settings:
            settings["shortcuts"] = []
        item = {
            "id": f"sc_{uuid.uuid4().hex[:8]}",
            "trigger": trigger.strip(),
            "path": path.strip(),
            "description": description.strip()
        }
        settings["shortcuts"].append(item)
        cls.save(settings)
        return item

    @classmethod
    def remove_shortcut(cls, shortcut_id: str) -> bool:
        settings = cls.load()
        before_len = len(settings.get("shortcuts", []))
        settings["shortcuts"] = [s for s in settings.get("shortcuts", []) if s.get("id") != shortcut_id]
        if len(settings["shortcuts"]) != before_len:
            cls.save(settings)
            return True
        return False

    # --------------------------------------------------------------------------
    # Agenda e Lembretes
    # --------------------------------------------------------------------------
    @classmethod
    def get_agenda(cls) -> List[Dict[str, Any]]:
        return cls.get("agenda", [])

    @classmethod
    def get_all_appointments(cls) -> List[Dict[str, Any]]:
        return cls.get_agenda()

    @classmethod
    def add_agenda_item(
        cls, title: str, datetime_str: str = "", dt_iso: str = "", description: str = "", notify: bool = True, frequency: str = "10m"
    ) -> Dict[str, Any]:
        dt = (datetime_str or dt_iso or "").strip()
        settings = cls.load()
        if "agenda" not in settings:
            settings["agenda"] = []
        item = {
            "id": f"ag_{uuid.uuid4().hex[:8]}",
            "title": title.strip(),
            "datetime": dt,
            "description": description.strip(),
            "notify": notify,
            "frequency": frequency,
            "alerted": False
        }
        settings["agenda"].append(item)
        cls.save(settings)
        return item

    @classmethod
    def add_appointment(cls, *args, **kwargs) -> Dict[str, Any]:
        return cls.add_agenda_item(*args, **kwargs)

    @classmethod
    def update_agenda_item(cls, item_id: str, updates: Dict[str, Any]) -> bool:
        settings = cls.load()
        for it in settings.get("agenda", []):
            if it.get("id") == item_id:
                it.update(updates)
                cls.save(settings)
                return True
        return False

    @classmethod
    def remove_agenda_item(cls, item_id: str) -> bool:
        settings = cls.load()
        before_len = len(settings.get("agenda", []))
        settings["agenda"] = [a for a in settings.get("agenda", []) if a.get("id") != item_id]
        if len(settings["agenda"]) != before_len:
            cls.save(settings)
            return True
        return False

    @staticmethod
    def _deep_merge(target: dict, source: dict):
        for k, v in source.items():
            if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                SettingsManager._deep_merge(target[k], v)
            else:
                target[k] = v
