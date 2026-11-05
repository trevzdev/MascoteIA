"""
Serviço de Integração com Google Calendar API
Permite listar e gerenciar compromissos de forma segura usando o token OAuth 2.0 do usuário.
Detecta e trata erros de escopos insuficientes (403) com mensagens claras de reautenticação.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleCalendarService:
    """Consome a API Google Calendar com credenciais delegadas pelo OAuth 2.0."""

    @staticmethod
    def get_calendar_service(credentials: Credentials):
        """Constrói o cliente de serviço oficial da Google Calendar v3."""
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)

    @classmethod
    def list_upcoming_events(
        cls, credentials: Credentials, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Lista os próximos eventos da agenda principal (primary) do usuário autenticado.
        Lança PermissionError se o token não tiver o escopo calendar/calendar.events aprovado.
        """
        try:
            service = cls.get_calendar_service(credentials)
            now = datetime.now(timezone.utc).isoformat()

            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            items = events_result.get("items", [])

            sanitized_events = []
            for item in items:
                start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
                end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
                sanitized_events.append(
                    {
                        "id": item.get("id"),
                        "summary": item.get("summary", "(Sem título)"),
                        "description": item.get("description", ""),
                        "start": start,
                        "end": end,
                        "htmlLink": item.get("htmlLink"),
                        "location": item.get("location", ""),
                    }
                )
            return sanitized_events

        except HttpError as error:
            status_code = error.resp.status if error.resp else 500
            error_details = ""
            try:
                error_content = json.loads(error.content.decode("utf-8"))
                error_details = error_content.get("error", {}).get("message", "")
            except Exception:
                error_details = str(error.reason)

            # Detecta erro 403 de escopo insuficiente
            if status_code == 403 and ("insufficient" in error_details.lower() or "scope" in error_details.lower()):
                raise PermissionError(
                    "Permissão insuficiente no Google Calendar: os escopos de agenda não foram concedidos no login anterior. "
                    "Faça login novamente para autorizar o acesso à sua agenda."
                )
            raise RuntimeError(f"Erro na API Google Calendar (Status {status_code}): {error_details or error.reason}")

    @classmethod
    def create_event(
        cls,
        credentials: Credentials,
        summary: str,
        start_time_iso: str,
        end_time_iso: str,
        description: str = "",
        location: str = "",
    ) -> Dict[str, Any]:
        """Cria um novo evento na agenda principal do usuário."""
        try:
            service = cls.get_calendar_service(credentials)
            event_body = {
                "summary": summary,
                "description": description,
                "location": location,
                "start": {"dateTime": start_time_iso},
                "end": {"dateTime": end_time_iso},
            }

            created_event = (
                service.events().insert(calendarId="primary", body=event_body).execute()
            )
            return {
                "id": created_event.get("id"),
                "summary": created_event.get("summary"),
                "htmlLink": created_event.get("htmlLink"),
                "status": "confirmed",
            }
        except HttpError as error:
            status_code = error.resp.status if error.resp else 500
            error_details = ""
            try:
                error_content = json.loads(error.content.decode("utf-8"))
                error_details = error_content.get("error", {}).get("message", "")
            except Exception:
                error_details = str(error.reason)

            if status_code == 403 and ("insufficient" in error_details.lower() or "scope" in error_details.lower()):
                raise PermissionError(
                    "Permissão insuficiente para criar eventos na sua conta Google. "
                    "Faça login novamente autorizando os escopos do Google Calendar."
                )
            raise RuntimeError(f"Falha ao agendar evento (Status {status_code}): {error_details or error.reason}")
