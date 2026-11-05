"""
Gerenciador de Integração e Controle Nativo do Spotify (Windows)
Suporta comandos flexíveis por voz e texto baseados em intenções e NLP leve.
Resolve faixas online para URIs oficiais diretas (spotify:track:..., spotify:playlist:...)
e dispara a reprodução imediata no aplicativo desktop nativo instalado no Windows,
com foco de janela e início automático sem tocar a música anterior do buffer.
"""

import ctypes
import json
import os
import re
import subprocess
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
import webbrowser
from typing import Optional, Tuple


def _normalize_text(text: str) -> str:
    """Normaliza texto removendo acentos e convertendo para minúsculas."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_str = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return ascii_str.lower().strip()


class SpotifyManager:
    """Gerencia a automação e controle do Spotify via protocolo nativo e teclas multimídia."""

    # Códigos virtuais de tecla multimídia e de controle no Windows
    VK_RETURN = 0x0D
    VK_SPACE = 0x20
    VK_MEDIA_NEXT_TRACK = 0xB0
    VK_MEDIA_PREV_TRACK = 0xB1
    VK_MEDIA_STOP = 0xB2
    VK_MEDIA_PLAY_PAUSE = 0xB3
    KEYEVENTF_KEYUP = 0x0002

    @classmethod
    def _send_key(cls, vk_code: int):
        """Envia um evento de pressionar e soltar tecla no Windows."""
        try:
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, cls.KEYEVENTF_KEYUP, 0)
            return True
        except Exception:
            return False

    @classmethod
    def play_pause(cls) -> Tuple[str, bool]:
        """Alterna entre reproduzir e pausar a música atual."""
        if cls._send_key(cls.VK_MEDIA_PLAY_PAUSE):
            return "Reprodução do Spotify alternada (Play/Pause).", True
        return "Não foi possível alternar a reprodução do Spotify.", False

    @classmethod
    def next_track(cls) -> Tuple[str, bool]:
        """Avança para a próxima música."""
        if cls._send_key(cls.VK_MEDIA_NEXT_TRACK):
            return "Avançando para a próxima faixa no Spotify.", True
        return "Não foi possível avançar a faixa.", False

    @classmethod
    def prev_track(cls) -> Tuple[str, bool]:
        """Retorna para a música anterior."""
        if cls._send_key(cls.VK_MEDIA_PREV_TRACK):
            return "Voltando para a faixa anterior no Spotify.", True
        return "Não foi possível voltar a faixa.", False

    @classmethod
    def resolve_spotify_uri(cls, query: str, is_playlist: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve o nome da música ou playlist para sua URI oficial direta (spotify:track:ID ou spotify:playlist:ID)
        utilizando a API pública do Spotify (token anônimo oficial do web player).
        Retorna (uri, nome_completo_para_exibição) ou (None, None).
        """
        if not query or query.startswith("spotify:"):
            return query, None

        try:
            # 1. Obtém token de sessão anônimo oficial do Spotify Web Player
            token_url = "https://open.spotify.com/get_access_token?reason=transport&productType=web_player"
            req_token = urllib.request.Request(
                token_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req_token, timeout=3) as resp:
                token_data = json.loads(resp.read().decode("utf-8"))
                access_token = token_data.get("accessToken")

            if not access_token:
                return None, None

            # 2. Busca o item no catálogo oficial
            q_type = "playlist" if is_playlist else "track"
            clean_q = urllib.parse.quote(query.strip())
            search_url = f"https://api.spotify.com/v1/search?q={clean_q}&type={q_type}&limit=1"
            req_search = urllib.request.Request(
                search_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req_search, timeout=3) as s_resp:
                s_data = json.loads(s_resp.read().decode("utf-8"))
                if is_playlist:
                    items = s_data.get("playlists", {}).get("items", [])
                else:
                    items = s_data.get("tracks", {}).get("items", [])

                if items and items[0].get("uri"):
                    found_uri = items[0]["uri"]
                    found_name = items[0].get("name", query)
                    artists = items[0].get("artists", [])
                    artist_name = artists[0].get("name") if artists else ""
                    display_name = f"{found_name} ({artist_name})" if artist_name else found_name
                    return found_uri, display_name

        except Exception as e:
            # Silencioso se não houver internet ou se houver restrição
            pass

        return None, None

    @classmethod
    def play_query(cls, query: str, is_playlist: bool = False) -> Tuple[str, bool]:
        """
        Abre e inicia a reprodução da música ou playlist informada no Spotify nativo.
        Garante que a faixa nova seja selecionada e iniciada, evitando tocar faixas antigas em buffer.
        """
        clean_query = query.strip()
        if not clean_query:
            return "Por favor, informe o nome da música ou playlist que deseja tocar.", False

        target_type = "a playlist" if is_playlist else "a música"
        display_name = clean_query

        # 1. Se o usuário já passou um URI do Spotify completo (ex: spotify:track:...)
        if clean_query.startswith("spotify:"):
            spotify_uri = clean_query
        else:
            # 2. Resolve online a URI exata da música (spotify:track:[ID]) para não abrir apenas busca
            resolved_uri, resolved_name = cls.resolve_spotify_uri(clean_query, is_playlist=is_playlist)
            if resolved_uri:
                spotify_uri = resolved_uri
                display_name = resolved_name or clean_query
            else:
                # Fallback: URI de busca nativa
                encoded = urllib.parse.quote(clean_query)
                spotify_uri = f"spotify:search:{encoded}"

        # 3. Dispara no Windows para o aplicativo nativo oficial
        executed_natively = False
        try:
            os.startfile(spotify_uri)
            executed_natively = True
        except Exception:
            try:
                subprocess.Popen(f'start "" "{spotify_uri}"', shell=True)
                executed_natively = True
            except Exception:
                executed_natively = False

        if executed_natively:
            # Automação de Início Imediato da Nova Faixa:
            # Traz o Spotify para o foco e executa a faixa específica
            def activate_and_play():
                time.sleep(1.0)
                try:
                    hwnd = ctypes.windll.user32.FindWindowW("SpotifyMainWindow", None)
                    if hwnd:
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                        time.sleep(0.2)

                    if "track" in spotify_uri:
                        # Faixa específica carregada: envia Play para iniciar a nova faixa
                        cls._send_key(cls.VK_MEDIA_PLAY_PAUSE)
                    else:
                        # Na tela de busca, envia ENTER para tocar o primeiro resultado da lista!
                        cls._send_key(cls.VK_RETURN)
                except Exception:
                    cls._send_key(cls.VK_MEDIA_PLAY_PAUSE)

            threading.Thread(target=activate_and_play, daemon=True).start()
            return f"Abrindo e reproduzindo {target_type} '{display_name}' no aplicativo Spotify!", True

        # 4. Fallback Seguro para o Spotify Web Player caso o app desktop não esteja instalado
        try:
            encoded = urllib.parse.quote(clean_query)
            web_url = f"https://open.spotify.com/search/{encoded}"
            webbrowser.open(web_url)
            return f"Abrindo {target_type} '{clean_query}' no Spotify Web...", True
        except Exception as e:
            return f"Não foi possível iniciar o Spotify: {e}", False

    @classmethod
    def extract_search_entity(cls, text: str) -> Tuple[Optional[str], bool]:
        """
        NLP leve e remoção de stopwords para extrair limpo o nome da música ou playlist.
        Trata frases naturais como:
        'Ei Laranja, coloca aquela música Labareda de fogo pra mim' -> 'Labareda de fogo'
        'reproduzir a playlist Rock Nacional' -> 'Rock Nacional' (is_playlist=True)
        'solta o som de Queen' -> 'Queen'
        """
        if not text:
            return None, False

        norm = _normalize_text(text)
        is_playlist = "playlist" in norm

        # Remove saudações e wake words do início
        cleaned = re.sub(
            r"^(?:ei|eai|ola|oi)?\s*(?:laranja|mano|robo|mascote|assistente)?\s*,?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        # Remove fillers do final da frase ("pra mim", "por favor", "no spotify", etc.)
        cleaned = re.sub(
            r"\s+(?:pra mim|para mim|por favor|por gentileza|no spotify|aqui|agora|faz favor)[.?!]*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        # Remove sinônimos de ação no início
        action_pattern = (
            r"^(?:toque|tocar|toca|coloque|coloca|coloquem|reproduza|reproduzir|ouvir|ouca|ouça|"
            r"curtir|curte|solta|solte|bota|bote|play|iniciar|inicie|poe|põe)\s+"
        )
        cleaned = re.sub(action_pattern, "", cleaned, flags=re.IGNORECASE).strip()

        # Remove descritores de entidade após a ação ("aquela música", "o som", "a playlist", etc.)
        entity_descriptors = (
            r"^(?:aquela\s+musica|aquela\s+música|aquele\s+som|a\s+musica|a\s+música|o\s+som|"
            r"uma\s+musica|uma\s+música|um\s+som|aquela\s+cancao|aquela\s+canção|a\s+cancao|a\s+canção|"
            r"aquela\s+playlist|a\s+playlist|minha\s+playlist|a\s+faixa|aquela\s+faixa)\s+"
        )
        cleaned = re.sub(entity_descriptors, "", cleaned, flags=re.IGNORECASE).strip()

        # Remove preposições residuais de ligação ("de", "do", "da", "chamada", "chamado")
        cleaned = re.sub(r"^(?:de|do|da|chamada|chamado)\s+", "", cleaned, flags=re.IGNORECASE).strip()

        # Remove menções soltas a "no spotify"
        cleaned = re.sub(r"\bno spotify\b", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = cleaned.strip("\"' .,!?-")

        if len(cleaned) >= 2:
            return cleaned, is_playlist

        return None, is_playlist

    @classmethod
    def handle_command(cls, text: str) -> Optional[Tuple[str, bool]]:
        """
        Reconhecimento flexível de comandos e intenções do Spotify (NLP leve).
        Identifica ações como tocar, pausar, avançar, retroceder e extrai a faixa de forma inteligente.
        """
        if not text:
            return None

        norm = _normalize_text(text)

        # 1. Comandos de Pausa (Pause / Stop)
        pause_keywords = ["pausar", "pause", "pausa", "parar musica", "parar o som", "para a musica", "pare o som", "stop no spotify"]
        if any(w in norm for w in pause_keywords):
            return cls.play_pause()

        # 2. Comandos de Retomada (Play / Resume)
        resume_keywords = ["despausar", "despause", "retomar", "continuar musica", "dar play", "play no spotify", "continue a musica"]
        if any(w in norm for w in resume_keywords):
            return cls.play_pause()

        # 3. Avançar Faixa (Next Track)
        next_keywords = ["proxima musica", "proxima faixa", "avancar musica", "avanca musica", "passar musica", "passa musica", "pular musica", "pule a musica", "next track"]
        if any(w in norm for w in next_keywords):
            return cls.next_track()

        # 4. Voltar Faixa (Previous Track)
        prev_keywords = ["musica anterior", "faixa anterior", "voltar musica", "volta musica", "volte a musica", "previous track"]
        if any(w in norm for w in prev_keywords):
            return cls.prev_track()

        # 5. Intenções de Tocar / Reproduzir / Ouvir / Curtir Música ou Playlist
        play_actions = [
            "tocar", "toca", "toque", "coloca", "coloque", "ouvir", "ouca", "ouça",
            "reproduzir", "reproduza", "curtir", "curte", "solta", "solte", "bota", "bote",
            "play", "poe", "põe"
        ]

        has_play_intent = any(re.search(r"\b" + re.escape(w) + r"\b", norm) for w in play_actions)
        has_spotify_keyword = "spotify" in norm

        if has_play_intent or has_spotify_keyword:
            entity, is_playlist = cls.extract_search_entity(text)
            if entity:
                return cls.play_query(entity, is_playlist=is_playlist)
            elif has_spotify_keyword and ("abrir" in norm or "iniciar" in norm):
                try:
                    os.startfile("spotify:")
                    return "Abrindo o aplicativo Spotify para você!", True
                except Exception:
                    webbrowser.open("https://open.spotify.com")
                    return "Abrindo o Spotify Web...", True

        return None
