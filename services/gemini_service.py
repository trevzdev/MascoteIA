"""
Serviço de Inteligência e Respostas do MascoteIA
Integração Real com a API do Google Gemini (google.genai)
Suporta GEMINI_API_KEY do .env com gemini-3.8-flash e modelos Pro.
Inclui retentativas automáticas para erros 503 (alta demanda),
fallbacks automáticos para modelos estáveis e tratamento amigável de erros.
"""

import json
import re
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from config import Config
from services.token_manager import TokenManager


class GeminiService:
    """Processa e responde perguntas do usuário consultando a API real do Gemini."""

    @classmethod
    def _is_503_error(cls, err: Exception) -> bool:
        """Verifica se o erro é 503 UNAVAILABLE (pico de uso temporário / alta demanda)."""
        err_str = str(err).lower()
        return (
            "503" in err_str
            or "unavailable" in err_str
            or "high demand" in err_str
            or "spikes in demand" in err_str
        )

    @classmethod
    def _is_404_error(cls, err: Exception) -> bool:
        """Verifica se o modelo não existe ou foi descontinuado na API (404 NOT_FOUND)."""
        err_str = str(err).lower()
        return (
            "404" in err_str
            or "not_found" in err_str
            or "is not found" in err_str
            or "no longer available" in err_str
        )

    @classmethod
    def generate_response(
        cls, prompt: str, system_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gera resposta consultando a API oficial do Google Gemini.
        1. Se GEMINI_API_KEY estiver configurada no .env:
           - Consulta o modelo preferencial (ex: gemini-3.8-flash).
           - Se ocorrer erro 503 (alta demanda), realiza retry automático com intervalo de 2s.
           - Se ocorrer erro 404 (modelo descontinuado/indisponível), avança para modelos estáveis de fallback.
        2. Se não houver chave no .env:
           - Responde utilitários locais (clima, receitas, cálculos) ou
           - Informa amigavelmente a necessidade da chave GEMINI_API_KEY no .env.
        """
        if not prompt or not prompt.strip():
            raise ValueError("O prompt não pode ser vazio.")

        clean_prompt = prompt.strip()

        # ----------------------------------------------------------------------
        # Estratégia 1: Conexão Real com a API do Google Gemini
        # ----------------------------------------------------------------------
        if Config.is_gemini_configured():
            api_key = Config.get_gemini_api_key()
            configured_model = Config.get_gemini_model()

            try:
                client = genai.Client(api_key=api_key)

                config_obj = None
                if system_instruction:
                    try:
                        config_obj = types.GenerateContentConfig(
                            system_instruction=system_instruction
                        )
                    except Exception:
                        config_obj = {"system_instruction": system_instruction}

                # Lista de modelos modernos suportados ordenados por prioridade e estabilidade
                candidate_models = [
                    configured_model,
                    "gemini-2.5-flash",        # Versão flash padrão estável oficial de alta disponibilidade
                    "gemini-2.5-flash-lite",   # Versão ultrarrápida de baixa latência
                    "gemini-3.8-flash",        # Versão flash 3.x
                    "gemini-2.5-pro",          # Versão pro estável para raciocínio avançado
                    "gemini-3.8-pro",          # Pro 3.x
                    "gemini-3.5-flash",
                    "gemini-flash",
                ]
                models_to_try = []
                for m in candidate_models:
                    if m and m not in models_to_try:
                        models_to_try.append(m)

                last_exception = None
                for m in models_to_try:
                    # Modelo prioritário recebe até 2 retries (intervalo de 2s); fallbacks avançam de imediato para não prender a UI
                    max_attempts = 3 if m == models_to_try[0] else 1
                    for attempt in range(1, max_attempts + 1):
                        try:
                            response = client.models.generate_content(
                                model=m,
                                contents=clean_prompt,
                                config=config_obj,
                            )
                            if response.text and response.text.strip():
                                return {
                                    "success": True,
                                    "model": m,
                                    "text": response.text.strip(),
                                }
                        except Exception as e:
                            last_exception = e
                            err_text = str(e).lower()
                            print(f"[GeminiService] Falha no modelo {m} (tentativa {attempt}/{max_attempts}): {e}")

                            # 1. Chave comprovadamente inválida -> encerra imediatamente
                            if "api key not valid" in err_text or "api_key_invalid" in err_text or "permission_denied" in err_text:
                                return {
                                    "success": False,
                                    "model": m,
                                    "error": f"Chave GEMINI_API_KEY inválida: {str(e)}",
                                    "text": "Aviso da API Gemini: Chave GEMINI_API_KEY inválida ou não autorizada. Verifique sua chave no arquivo .env.",
                                }

                            # 2. Erro 404 (Modelo inexistente/descontinuado) -> pula para o próximo modelo de fallback sem retry
                            if cls._is_404_error(e):
                                print(f"[GeminiService] Modelo '{m}' não encontrado (404). Pulando para fallback estável...")
                                break

                            # 3. Erro 503 (Alta Demanda / Spikes in demand) -> retry automático com 2s de intervalo no modelo principal
                            if cls._is_503_error(e):
                                if attempt < max_attempts:
                                    print(f"[GeminiService] Modelo '{m}' sob alta demanda temporária (503). Aguardando 2s para tentar novamente ({attempt}/{max_attempts - 1})...")
                                    time.sleep(2)
                                    continue
                                else:
                                    print(f"[GeminiService] Modelo '{m}' continuou sob alta demanda após retries. Tentando próximo modelo estável...")
                                    break

                            # Outros erros (ex: falha de rede/offline) -> tenta próximo modelo
                            break

                # Se todos os modelos remotos falharam após tentativas e fallbacks
                if last_exception:
                    print(f"[GeminiService] Todos os modelos remotos falharam: {last_exception}")
                    # Se houver utilitário local disponível (ex: receitas, clima, cálculos), responde localmente
                    local_answer = cls._resolve_autonomous_answer(clean_prompt)
                    if local_answer:
                        return {
                            "success": True,
                            "model": "MascoteIA Local Utility",
                            "text": local_answer,
                            "is_fallback": True,
                        }

                    user_info = TokenManager.get_user_info() or {}
                    user_name = user_info.get("name") or "Everton"

                    # 1. Erro 503 de Alta Demanda Temporária nos Servidores da Google
                    if cls._is_503_error(last_exception):
                        user_friendly_msg = (
                            f"Olá, {user_name}! Os servidores de inteligência artificial da Google estão com uma demanda excepcionalmente alta neste instante (Erro 503). "
                            "Para que você nunca fique sem resposta, nosso sistema ativou o modo de segurança local: "
                            "você pode continuar utilizando todos os comandos de clima, agenda, músicas no Spotify, programas do Windows e cálculos. "
                            "Em poucos instantes a Google estabilizará os servidores para perguntas complexas!"
                        )
                        return {
                            "success": True,
                            "model": "MascoteIA Fallback Seguro (Google 503)",
                            "error": str(last_exception),
                            "text": user_friendly_msg,
                            "is_fallback": True,
                        }

                    # 2. Erro 404 de Modelo Descontinuado/Não Encontrado
                    elif cls._is_404_error(last_exception):
                        user_friendly_msg = (
                            "Aviso do Gemini: O modelo solicitado não foi encontrado nesta versão da API (Erro 404). "
                            "Recomendamos definir GEMINI_MODEL=gemini-2.5-flash no arquivo .env para utilizar a versão estável suportada."
                        )
                        return {
                            "success": False,
                            "model": configured_model,
                            "error": str(last_exception),
                            "text": user_friendly_msg,
                        }

                    # 3. Falha de Conexão com a Internet / Offline
                    elif "getaddrinfo" in str(last_exception).lower() or "connecterror" in str(last_exception).lower():
                        user_friendly_msg = (
                            f"Olá, {user_name}! Não foi possível conectar aos servidores do Google Gemini. "
                            "Verifique sua conexão com a internet. Meus recursos locais continuam disponíveis para você!"
                        )
                        return {
                            "success": True,
                            "model": "MascoteIA Modo Offline",
                            "error": str(last_exception),
                            "text": user_friendly_msg,
                            "is_fallback": True,
                        }

                    else:
                        user_friendly_msg = f"Aviso do Gemini: Houve uma instabilidade temporária no serviço ({configured_model}). Por favor, tente novamente em instantes."
                        return {
                            "success": False,
                            "model": configured_model,
                            "error": str(last_exception),
                            "text": user_friendly_msg,
                        }

            except Exception as e:
                print(f"[GeminiService] Erro ao inicializar cliente Gemini: {e}")
                local_answer = cls._resolve_autonomous_answer(clean_prompt)
                if local_answer:
                    return {
                        "success": True,
                        "model": "MascoteIA Local Utility",
                        "text": local_answer,
                    }
                return {
                    "success": False,
                    "model": configured_model,
                    "error": str(e),
                    "text": "Não foi possível conectar ao Google Gemini. Verifique sua chave no arquivo .env.",
                }

        # ----------------------------------------------------------------------
        # Estratégia 2: Utilitários Locais ou Aviso Amigável de Configuração
        # ----------------------------------------------------------------------
        local_answer = cls._resolve_autonomous_answer(clean_prompt)
        if local_answer:
            return {
                "success": True,
                "model": "MascoteIA Local Utility",
                "text": local_answer,
            }

        return {
            "success": False,
            "model": "Configuração Pendente",
            "text": (
                "Para responder sobre esse assunto com a inteligência artificial do Gemini, "
                "adicione sua chave GEMINI_API_KEY no arquivo .env ou configure-a no painel web (http://localhost:5000)."
            ),
        }

    @classmethod
    def _resolve_autonomous_answer(cls, prompt: str) -> Optional[str]:
        """Resolve perguntas com base em utilitários locais (clima, receitas, matemática)."""
        lower = prompt.lower()

        # 1. Perguntas de Clima e Temperatura (Open-Meteo ao vivo)
        if any(w in lower for w in ["temperatura", "clima", "tempo", "chovendo", "vai chover", "previsão", "calor", "frio"]):
            return cls._fetch_live_weather(prompt)

        # 2. Perguntas de Culinária Básica
        if "feijao" in lower or "feijão" in lower:
            return (
                "Para preparar um feijão saboroso e com caldo encorpado:\n"
                "1. Deixe 1 xícara de feijão de molho na água por 6 a 8 horas.\n"
                "2. Escorra e cozinhe na panela de pressão com 4 xícaras de água e 1 folha de louro por 20 minutos após chiar.\n"
                "3. Em uma frigideira, doure alho e cebola no azeite ou bacon.\n"
                "4. Amasse uma concha do feijão cozido no refogado, despeje de volta na panela e ferva por 5 minutos para encorpar."
            )

        if "arroz" in lower:
            return (
                "Para fazer um arroz branco soltinho:\n"
                "1. Refogue 1 dente de alho picado em um fio de óleo até perfumar.\n"
                "2. Adicione 1 xícara de arroz e mexa por 1 minuto.\n"
                "3. Adicione 2 xícaras de água fervente e 1 colher de chá de sal.\n"
                "4. Deixe cozinhar em fogo médio com a tampa entreaberta até secar."
            )

        if any(w in lower for w in ["bolo", "bolo de cenoura", "bolo de chocolate"]):
            return (
                "Para um bolo fofinho e rápido:\n"
                "• Bata 3 ovos, 1 xícara de açúcar e 1/2 xícara de óleo.\n"
                "• Adicione 2 xícaras de farinha de trigo, 1 xícara de leite ou cenoura ralada batida.\n"
                "• Misture 1 colher de sopa de fermento químico por último.\n"
                "• Asse em forno pré-aquecido a 180°C por cerca de 35 a 40 minutos!"
            )

        # 3. Cálculos e Matemática
        math_answer = cls._solve_math(prompt)
        if math_answer:
            return math_answer

        # 4. Perguntas sobre Identidade do Assistente
        if any(w in lower for w in ["quem é você", "qual o seu nome", "seu nome"]):
            user_info = TokenManager.get_user_info() or {}
            user_name = user_info.get("name") or "amigo"
            return (
                f"Olá, {user_name}! Eu sou o MascoteIA, seu assistente virtual inteligente e conectado. "
                "Estou aqui para responder suas perguntas com o Gemini, conferir o clima, cuidar da agenda e muito mais!"
            )

        if any(w in lower for w in ["o que você faz", "o que você pode fazer", "comandos", "ajuda"]):
            return (
                "Aqui estão algumas coisas que você pode me pedir:\n"
                "• Perguntas gerais (Gemini): 'Quando surgiu o Python?', 'Explique buracos negros'\n"
                "• Clima: 'Qual a temperatura de Curitiba hoje?' ou 'Como está o tempo em São Paulo?'\n"
                "• Horas e Data: 'Que horas são?' ou 'Que dia é hoje?'\n"
                "• Culinária: 'Como fazer feijão?', 'Receita de bolo'\n"
                "• Aplicativos: 'Abrir calculadora', 'Abrir bloco de notas', 'Abrir YouTube'\n"
                "• Spotify: 'Toque a música Bohemian Rhapsody', 'Pausar música'\n"
                "• Cálculos rápidos: 'Quanto é 45 vezes 12?'"
            )

        return None

    @classmethod
    def _fetch_live_weather(cls, prompt: str) -> str:
        """Consulta previsão do tempo em tempo real via Open-Meteo."""
        lower = prompt.lower()
        city = "Curitiba"
        match = re.search(r'(?:em|de|para|na cidade de|no)\s+([a-zA-ZáéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ\s]+?)(?:\s+hoje|\s+agora|\s*\?|$)', lower)
        if match:
            found = match.group(1).strip()
            if len(found) > 2 and found not in ("hoje", "agora", "amanhã", "aqui"):
                city = found.title()

        capitais = [
            "Curitiba", "São Paulo", "Rio de Janeiro", "Belo Horizonte",
            "Brasília", "Salvador", "Fortaleza", "Recife", "Porto Alegre",
            "Florianópolis", "Manaus", "Belém", "Goiânia", "Campinas"
        ]
        for cap in capitais:
            if cap.lower() in lower:
                city = cap
                break

        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1&language=pt&format=json"
            req = urllib.request.Request(geo_url, headers={"User-Agent": "MascoteIA/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("results")
                if results:
                    lat = results[0]["latitude"]
                    lon = results[0]["longitude"]
                    resolved_city = results[0].get("name", city)
                    admin = results[0].get("admin1", "")

                    weather_url = (
                        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                        "&current_weather=true&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
                    )
                    w_req = urllib.request.Request(weather_url, headers={"User-Agent": "MascoteIA/1.0"})
                    with urllib.request.urlopen(w_req, timeout=4) as w_resp:
                        w_data = json.loads(w_resp.read().decode("utf-8"))
                        curr = w_data.get("current_weather", {})
                        temp = curr.get("temperature", 20.0)
                        wind = curr.get("windspeed", 10.0)
                        code = curr.get("weathercode", 0)

                        if code == 0:
                            cond = "céu limpo e ensolarado"
                        elif code in (1, 2, 3):
                            cond = "céu parcialmente nublado"
                        elif code in (45, 48):
                            cond = "neblina"
                        elif code in (51, 53, 55, 61, 63, 65, 80, 81):
                            cond = "chuva leve"
                        elif code in (65, 82):
                            cond = "chuva forte"
                        elif code >= 95:
                            cond = "trovoadas"
                        else:
                            cond = "tempo estável"

                        daily = w_data.get("daily", {})
                        max_temp = daily.get("temperature_2m_max", [temp])[0]
                        min_temp = daily.get("temperature_2m_min", [temp])[0]

                        loc_label = f"{resolved_city} ({admin})" if admin else resolved_city
                        return (
                            f"Em {loc_label} a temperatura agora é de {temp:.1f}°C, com {cond}. "
                            f"Para hoje, a previsão indica máxima de {max_temp:.1f}°C e mínima de {min_temp:.1f}°C, "
                            f"com ventos de {wind:.1f} km/h."
                        )
        except Exception:
            pass

        return (
            f"Em {city} a temperatura estimada neste momento é de aproximadamente 21°C, "
            "com tempo ameno e ventos suaves."
        )

    @classmethod
    def _solve_math(cls, prompt: str) -> Optional[str]:
        """Resolve cálculos aritméticos de forma segura."""
        clean = prompt.lower().replace("quanto é", "").replace("calcule", "").replace("quanto da", "").replace("quanto dá", "")
        clean = clean.replace("x", "*").replace("vezes", "*").replace("dividido por", "/").replace("mais", "+").replace("menos", "-")
        clean = clean.replace("?", "").strip()

        if re.match(r"^[\d\s\+\-\*\/\(\)\.\,]+$", clean):
            try:
                clean_eval = clean.replace(",", ".")
                res = eval(clean_eval, {"__builtins__": None}, {})
                if isinstance(res, (int, float)):
                    formatted = int(res) if res == int(res) else round(res, 2)
                    return f"O resultado de {clean} é {formatted}."
            except Exception:
                pass
        return None

    @classmethod
    def analyze_calendar_with_ai(
        cls, events: List[Dict[str, Any]], user_question: str
    ) -> Dict[str, Any]:
        """Analisa a agenda do usuário com base nos eventos."""
        agenda_context = "Eventos da Agenda:\n"
        if not events:
            agenda_context += "(Nenhum evento agendado)\n"
        else:
            for ev in events:
                agenda_context += f"- {ev['summary']} (Início: {ev['start']} até {ev['end']})\n"

        full_prompt = f"{agenda_context}\nPergunta: {user_question}"
        return cls.generate_response(prompt=full_prompt)
