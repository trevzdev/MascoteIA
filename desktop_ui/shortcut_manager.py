"""
Gerenciador de Atalhos de Aplicativos e Arquivos do Windows
Suporta comandos flexíveis baseados em intenções e NLP leve:
Permite acionar por variações naturais como:
- "abra o [nome]"
- "iniciar [nome]"
- "roda o [nome]"
- "executa o [nome]"
- variações fonéticas e sinônimos (ex: "notepad" <-> "bloco de notas", "not pad")
- ou simplesmente dizer o apelido cadastrado
"""

import os
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from desktop_ui.settings_manager import SettingsManager

# Sinônimos comuns e variações de transcrição fonética no português do Brasil
COMMON_ALIASES: Dict[str, List[str]] = {
    "notepad": ["bloco de notas", "bloco notas", "not pad", "note pad", "notepade", "caderno de notas"],
    "calc": ["calculadora", "calculador"],
    "mspaint": ["paint", "desenho", "desenhar"],
    "cmd": ["prompt", "prompt de comando", "terminal"],
    "explorer": ["explorador de arquivos", "arquivos", "pastas", "meus arquivos"],
    "chrome": ["google chrome", "navegador", "internet"],
    "spotify": ["spotfy", "spotifai"],
}


def _normalize_text(text: str) -> str:
    """Normaliza texto removendo acentos e convertendo para minúsculas."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_str = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return ascii_str.lower().strip()


class ShortcutManager:
    """Localiza e executa atalhos customizados do Windows por reconhecimento flexível de intenções."""

    @classmethod
    def clean_shortcut_target(cls, text: str) -> str:
        """
        Limpa termos de preenchimento, saudações e verbos de ação para isolar o nome do atalho.
        Ex: 'Ei Davros, roda o notepad pra mim por favor' -> 'notepad'
        """
        if not text:
            return ""

        norm = _normalize_text(text)

        # 1. Remove saudações e wake words
        norm = re.sub(r"^(?:ei|eai|ola|oi|diga)?\s*(?:laranja|mano|davros|robo|mascote|assistente)?\s*,?\s*", "", norm).strip()

        # 2. Remove fillers do final da frase
        norm = re.sub(r"\s+(?:pra mim|para mim|por favor|por gentileza|ai|aí|agora|rapido|faz favor)[.?!]*$", "", norm).strip()

        # 3. Remove verbos de ação no início
        action_verbs = (
            r"^(?:abra|abrir|abre|iniciar|inicia|inicie|executar|execute|executa|"
            r"rodar|roda|rode|chamar|chama|ligar|liga|lancar|lança|start|launch|run)\s+"
        )
        norm = re.sub(action_verbs, "", norm).strip()

        # 4. Remove artigos e pronomes de ligação
        norm = re.sub(r"^(?:o|a|os|as|meu|minha|um|uma|o\s+app|o\s+programa|o\s+atalho|o\s+arquivo)\s+", "", norm).strip()

        return norm.strip("\"' .,!?-")

    @classmethod
    def _get_candidate_tokens(cls, trigger: str, path: str) -> Set[str]:
        """Gera conjunto de variações, sinônimos e nomes derivados do atalho."""
        candidates = set()
        norm_trig = _normalize_text(trigger)
        if norm_trig:
            candidates.add(norm_trig)
            candidates.add(norm_trig.replace(" ", ""))

        # Nome base do executável sem extensão (ex: 'notepad' de 'C:/.../notepad.exe')
        try:
            stem = _normalize_text(Path(path).stem)
            if stem:
                candidates.add(stem)
                candidates.add(stem.replace(" ", ""))
        except Exception:
            stem = ""

        # Expande com dicionário de sinônimos conhecidos
        for key, aliases in COMMON_ALIASES.items():
            key_norm = _normalize_text(key)
            aliases_norm = [_normalize_text(a) for a in aliases]
            all_group = [key_norm] + aliases_norm

            # Se qualquer termo do grupo combina com o trigger ou stem
            if norm_trig in all_group or stem in all_group:
                for a in all_group:
                    candidates.add(a)
                    candidates.add(a.replace(" ", ""))

        return candidates

    @classmethod
    def check_and_execute(cls, text: str, settings_manager=None) -> Optional[Tuple[str, bool]]:
        """
        Verifica se o comando do usuário é um pedido de abertura de atalho cadastrado
        utilizando busca flexível por intenções e palavras-chave.
        """
        if not text:
            return None

        mgr = settings_manager or SettingsManager
        shortcuts = mgr.get_shortcuts()
        if not shortcuts:
            return None

        clean_target = cls.clean_shortcut_target(text)
        clean_target_nospace = clean_target.replace(" ", "")
        norm_full = _normalize_text(text)

        action_keywords = [
            "abra", "abrir", "abre", "iniciar", "inicia", "inicie",
            "executar", "execute", "executa", "rodar", "roda", "rode",
            "chamar", "chama", "ligar", "liga", "start", "launch", "run"
        ]
        has_action = any(re.search(r"\b" + re.escape(a) + r"\b", norm_full) for a in action_keywords)
        is_short_command = len(norm_full.split()) <= 3

        for sc in shortcuts:
            trigger_raw = sc.get("trigger", "").strip()
            path = sc.get("path", "").strip()
            if not trigger_raw or not path:
                continue

            candidates = cls._get_candidate_tokens(trigger_raw, path)

            is_match = False

            # 1. Correspondência exata de qualquer variação/sinônimo
            if clean_target in candidates or clean_target_nospace in [c.replace(" ", "") for c in candidates]:
                is_match = True

            # 2. Correspondência por prefixo ou sufixo
            if not is_match:
                for cand in candidates:
                    if len(cand) >= 3:
                        if clean_target.startswith(cand) or clean_target.endswith(cand):
                            is_match = True
                            break

            # 3. Busca por palavra inteira na frase completa com intenção de abertura
            if not is_match and (has_action or is_short_command):
                for cand in candidates:
                    if len(cand) >= 3:
                        if re.search(r"\b" + re.escape(cand) + r"\b", norm_full):
                            is_match = True
                            break

            if is_match:
                success, msg = cls.launch_path(path, trigger_raw)
                return msg, success

        return None

    @classmethod
    def find_and_launch(cls, text: str, settings_manager=None) -> Optional[Tuple[str, bool]]:
        """Alias para check_and_execute."""
        return cls.check_and_execute(text, settings_manager=settings_manager)

    @classmethod
    def execute_shortcut(cls, shortcut_item: Dict[str, Any]) -> Tuple[str, bool]:
        """Executa um atalho individual diretamente."""
        path = shortcut_item.get("path", "")
        trigger = shortcut_item.get("trigger", "Atalho")
        success, msg = cls.launch_path(path, trigger)
        return msg, success

    @classmethod
    def launch_path(cls, path: str, trigger_name: str) -> Tuple[bool, str]:
        """Abre o arquivo ou programa cadastrado no sistema operacional Windows de forma confiável."""
        user_name = SettingsManager.get_user_name()
        try:
            clean_path = path.strip().strip('"\'')
            expanded = os.path.expandvars(os.path.expanduser(clean_path))
            norm = os.path.normpath(expanded)

            # 1. Executável existente (.exe, .bat, .cmd)
            if os.path.exists(norm):
                if norm.lower().endswith((".exe", ".bat", ".cmd", ".com")):
                    try:
                        subprocess.Popen([norm], shell=False)
                        return True, f"Abrindo {trigger_name} para você agora, {user_name}!"
                    except Exception:
                        pass
                # Documentos ou arquivos gerais
                try:
                    os.startfile(norm)
                    return True, f"Abrindo {trigger_name} para você agora, {user_name}!"
                except Exception:
                    pass

            # 2. Comando registrado no PATH do Windows (ex: 'notepad', 'calc', 'notepad.exe')
            try:
                subprocess.Popen([clean_path], shell=False)
                return True, f"Abrindo {trigger_name} para você agora, {user_name}!"
            except Exception:
                pass

            # 3. Fallback no shell do Windows com aspas
            try:
                subprocess.Popen(f'"{norm}"', shell=True)
                return True, f"Abrindo {trigger_name} para você agora, {user_name}!"
            except Exception:
                pass

            # 4. Fallback final via os.startfile
            try:
                os.startfile(norm)
                return True, f"Abrindo {trigger_name} para você agora, {user_name}!"
            except Exception as err:
                return False, f"Não foi possível abrir {trigger_name}: {err}"

        except Exception as e:
            return False, f"Não foi possível abrir {trigger_name}: {e}"
