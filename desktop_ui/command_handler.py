"""
Processador de Comandos Avançado do MascoteIA
Integra:
- Atalhos de Aplicativos do Windows (ShortcutManager)
- Controle e Reprodução do Spotify (SpotifyManager)
- Agenda e Lembretes Inteligentes (AgendaManager + Google Calendar)
- Personalidades e Tom de Resposta (PersonalityManager)
- Identificação Obrigatória do Usuário (User Name)
- IA Generativa e Conhecimento Autônomo com Autenticação Google
"""

import os
import re
import subprocess
import webbrowser
from datetime import datetime
from typing import Tuple

from config import Config
from services.token_manager import TokenManager
from services.google_calendar import GoogleCalendarService
from services.gemini_service import GeminiService
from desktop_ui.settings_manager import SettingsManager
from desktop_ui.personality_manager import PersonalityManager
from desktop_ui.shortcut_manager import ShortcutManager
from desktop_ui.spotify_manager import SpotifyManager
from desktop_ui.agenda_manager import AgendaManager


class CommandHandler:
    """Interpreta e executa comandos do usuário com personalidade e nome personalizados."""

    def __init__(self, settings_manager: SettingsManager = None, agenda_manager: AgendaManager = None):
        self.settings = settings_manager or SettingsManager()
        self.agenda = agenda_manager or AgendaManager(self.settings)

    def _get_user_and_personality(self) -> Tuple[str, str]:
        """Obtém o nome do usuário obrigatório e o ID da personalidade ativa."""
        user_name = self.settings.get_user_name()
        # Fallback para nome da conta Google se o usuário não alterou o padrão
        if user_name in ("Usuário", "", None):
            user_info = TokenManager.get_user_info() or {}
            google_name = user_info.get("name")
            if google_name:
                user_name = google_name.split()[0]  # Primeiro nome
                self.settings.set_user_name(user_name)
        personality_id = self.settings.get_personality()
        return user_name, personality_id

    def process(self, raw_input: str) -> Tuple[str, bool]:
        """
        Processa o comando e retorna (resposta_formatada_com_personalidade, deve_falar_via_tts).
        Exige autenticação Google ativa.
        """
        text = raw_input.strip()
        lower = text.lower()
        user_name, personality_id = self._get_user_and_personality()

        if not text:
            raw_reply = "Estou aqui aguardando suas ordens. No que posso te ajudar?"
            return PersonalityManager.format_response(personality_id, raw_reply, user_name), True

        # 1. Verifica autenticação Google obrigatória
        if not TokenManager.is_authenticated():
            raw_reply = (
                "Para interagir comigo, você precisa primeiro fazer login com a sua conta Google. "
                "Clique no botão de login para conectar."
            )
            return PersonalityManager.format_response(personality_id, raw_reply, user_name), True

        # 2. Atalhos de Aplicativos do Windows Cadastrados pelo Usuário
        shortcut_result = ShortcutManager.find_and_launch(text, self.settings)
        if shortcut_result:
            msg, success = shortcut_result
            return PersonalityManager.format_response(personality_id, msg, user_name), True

        # 3. Comandos do Spotify (Música, Playlist, Pausar, Próxima, Anterior)
        spotify_result = SpotifyManager.handle_command(text)
        if spotify_result:
            msg, success = spotify_result
            return PersonalityManager.format_response(personality_id, msg, user_name), True

        # 4. Comandos de Agenda e Lembretes Locais / Google
        if any(w in lower for w in ["minha agenda", "meus lembretes", "o que tenho hoje", "ver agenda", "listar compromissos"]):
            # Compromissos locais cadastrados
            local_events = self.agenda.get_all_appointments()
            upcoming_local = [e for e in local_events if e.get("datetime", "") >= datetime.now().strftime("%Y-%m-%d %H:%M")]
            
            agenda_lines = []
            if upcoming_local:
                agenda_lines.append(f"Seus lembretes cadastrados ({len(upcoming_local)}):")
                for item in upcoming_local[:4]:
                    agenda_lines.append(f"• {item['datetime'][11:16]} - {item['title']}")

            # Consulta Google Calendar se conectado
            credentials = TokenManager.get_credentials()
            if credentials:
                try:
                    events = GoogleCalendarService.list_upcoming_events(credentials, max_results=3)
                    if events:
                        agenda_lines.append(f"Google Agenda ({len(events)}):")
                        for ev in events:
                            time_str = ev["start"].split("T")[-1][:5] if "T" in ev["start"] else ev["start"]
                            agenda_lines.append(f"• {time_str} - {ev['summary']}")
                except Exception:
                    pass

            if agenda_lines:
                raw_reply = "\n".join(agenda_lines)
            else:
                raw_reply = "Sua agenda está livre! Não encontrei nenhum compromisso agendado para as próximas horas."
            return PersonalityManager.format_response(personality_id, raw_reply, user_name), True

        # 5. Adicionar Compromisso Rápido via Voz ("lembre-me de [algo] às [hh:mm]")
        reminder_match = re.search(r"(?:lembre-me de|lembrar de|agendar|novo compromisso)\s+(.+?)(?:\s+(?:às|as|em)\s+(\d{1,2}(?::\d{2})?))?$", lower)
        if reminder_match and ("lembre" in lower or "agendar" in lower):
            desc = reminder_match.group(1).strip()
            time_part = reminder_match.group(2)
            today = datetime.now().strftime("%Y-%m-%d")
            time_str = f"{int(time_part):02d}:00" if time_part and ":" not in time_part else (time_part or "18:00")
            dt_str = f"{today} {time_str}"

            item = self.agenda.add_appointment(
                title=desc.capitalize(),
                datetime_str=dt_str,
                notify=True,
                frequency="10m",
                description="Criado via comando de voz/texto"
            )
            raw_reply = f"Lembrete agendado para hoje às {time_str}: '{desc.capitalize()}'."
            return PersonalityManager.format_response(personality_id, raw_reply, user_name), True

        # 6. Comandos Básicos de Horário e Data
        if any(w in lower for w in ["que horas são", "horas", "horário atual"]):
            now = datetime.now().strftime("%H:%M")
            raw_reply = f"Agora são exatamente {now}."
            return PersonalityManager.format_response(personality_id, raw_reply, user_name), True

        if any(w in lower for w in ["que dia é hoje", "qual a data", "data de hoje", "dia da semana"]):
            hoje = datetime.now().strftime("%d/%m/%Y")
            dias_semana = [
                "Segunda-feira", "Terça-feira", "Quarta-feira",
                "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"
            ]
            dia_str = dias_semana[datetime.now().weekday()]
            raw_reply = f"Hoje é {dia_str}, dia {hoje}."
            return PersonalityManager.format_response(personality_id, raw_reply, user_name), True

        # 7. Aplicativos Padrão do Windows
        if any(w in lower for w in ["calculadora", "abrir calculadora"]):
            try:
                subprocess.Popen("calc.exe")
                raw_reply = "Abrindo a Calculadora para você."
                return PersonalityManager.format_response(personality_id, raw_reply, user_name), True
            except Exception as e:
                return f"Não foi possível abrir a calculadora: {e}", False

        if any(w in lower for w in ["bloco de notas", "notepad", "abrir notas"]):
            try:
                subprocess.Popen("notepad.exe")
                raw_reply = "Abrindo o Bloco de Notas."
                return PersonalityManager.format_response(personality_id, raw_reply, user_name), True
            except Exception as e:
                return f"Falha ao abrir bloco de notas: {e}", False

        if any(w in lower for w in ["abrir navegador", "abrir google"]):
            webbrowser.open("https://www.google.com")
            raw_reply = "Abrindo o Google no seu navegador."
            return PersonalityManager.format_response(personality_id, raw_reply, user_name), True

        if any(w in lower for w in ["abrir youtube", "youtube"]):
            webbrowser.open("https://www.youtube.com")
            raw_reply = "Abrindo o YouTube."
            return PersonalityManager.format_response(personality_id, raw_reply, user_name), True

        # 8. Painel Web
        if any(w in lower for w in ["painel web", "abrir painel", "servidor"]):
            url = Config.BASE_URL
            webbrowser.open(url)
            raw_reply = f"Abrindo o Painel Web em {url}."
            return PersonalityManager.format_response(personality_id, raw_reply, user_name), True

        # 9. Consultas e IA (Gemini Pro com personalidade e nome do usuário)
        try:
            p_info = PersonalityManager.get_personality_data(personality_id)
            tone_name = p_info["name"]
            tone_desc = p_info["desc"]

            sys_inst = (
                f"Você é o MascoteIA, assistente virtual pessoal de {user_name}. "
                f"Sua personalidade ativa é '{tone_name}' ({tone_desc}). "
                f"IMPORTANTE: Você DEVE chamar o usuário pelo nome '{user_name}' na resposta, "
                f"e responder fielmente mantendo o estilo e tom da personalidade '{tone_name}' em Português do Brasil. "
                "Nunca quebre o personagem e mantenha respostas diretas e bem-humoradas quando couber."
            )
            result = GeminiService.generate_response(prompt=text, system_instruction=sys_inst)
            ai_text = result.get("text", "Comando processado com sucesso.")

            # Garante que o nome do usuário está presente na resposta
            if user_name.lower() not in ai_text.lower():
                ai_text = PersonalityManager.format_response(personality_id, ai_text, user_name)

            return ai_text, True

        except Exception as e:
            fallback_reply = f"Tive uma pequena oscilação na resposta, mas estou aqui com você!"
            return PersonalityManager.format_response(personality_id, fallback_reply, user_name), True
