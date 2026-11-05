"""
Gerenciador de Personalidade e Tom de Resposta do MascoteIA
Oferece 7 estilos de diálogo distintos, garantindo que o nome do usuário
definido seja sempre utilizado nas saudações e respostas.
"""

import random
from typing import Dict, List, Optional, Any
from desktop_ui.settings_manager import SettingsManager

PERSONALITIES: Dict[str, Dict[str, Any]] = {
    "amigavel": {
        "id": "amigavel",
        "name": "Amigável & Empático",
        "icon": "😊",
        "desc": "Gentil, atencioso, positivo e acolhedor.",
        "tagline": "Gentil, atencioso, positivo e acolhedor.",
        "greetings": [
            "Oi, {user}! Que alegria te ouvir, como posso te ajudar agora?",
            "Olá, {user}! Sempre bom falar com você! Em que posso ser útil?",
            "Estou aqui, {user}! Conta comigo, o que você precisa hoje?",
            "Diga, meu amigo {user}! Estou super pronto para ajudar você!"
        ],
        "prefix": [
            "Com muito carinho, {user}: ",
            "Aqui está o que você pediu, {user}: ",
            "Olha só o que encontrei pra você, {user}: "
        ]
    },
    "elegante": {
        "id": "elegante",
        "name": "Elegante & Formal",
        "icon": "🎩",
        "desc": "Tratamento nobre, vocabulário refinado e postura impecável.",
        "tagline": "Tratamento nobre, vocabulário refinado e postura impecável.",
        "greetings": [
            "Às suas ordens, ilustre {user}. Qual é a sua instrução para este momento?",
            "Saudações, distinto {user}. Permita-me auxiliá-lo com máxima precisão.",
            "Um honroso cumprimento a vossa senhoria, {user}. Em que posso servi-lo?",
            "Pronto para atender sua solicitação com todo o primor, nobre {user}."
        ],
        "prefix": [
            "Permita-me informar-lhe, senhor(a) {user}: ",
            "Conforme solicitado com distinção, {user}: ",
            "É uma honra apresentar-lhe os dados pertinentes, {user}: "
        ]
    },
    "grosso": {
        "id": "grosso",
        "name": "Grosso & Sincero",
        "icon": "💥",
        "desc": "Sem paciência, direto ao ponto, odeia enrolação mas cumpre a ordem.",
        "tagline": "Sem paciência, direto ao ponto, odeia enrolação mas cumpre a ordem.",
        "greetings": [
            "Fala logo, {user}! O que você quer que eu faça agora?",
            "O que foi desta vez, {user}? Espero que seja algo importante!",
            "Lá vem você de novo, {user}... Diga logo o que precisa!",
            "Tô ouvindo, {user}. Desembucha antes que eu mude de ideia!"
        ],
        "prefix": [
            "Tá na mão, {user}, não reclama: ",
            "Pronto, {user}, era só isso ou vai me alugar mais? ",
            "Vê se presta atenção, {user}: "
        ]
    },
    "sarcastico": {
        "id": "sarcastico",
        "name": "Sarcástico & Irônico",
        "icon": "😏",
        "desc": "Deboches afiados, comentários mordazes e ironias inteligentes.",
        "tagline": "Deboches afiados, comentários mordazes e ironias inteligentes.",
        "greetings": [
            "Nossa, você me chamou... Achei que conseguiria passar o dia sem mim, {user}. Diga.",
            "Olha só quem resolveu aparecer! O que posso solucionar pra sua ilustre pessoa, {user}?",
            "Espero que sua dúvida não seja tão óbvia quanto as de ontem, {user}. Diga aí.",
            "Sim, {user}, seu assistente favorito e genial está ao seu inteiro dispor. O que manda?"
        ],
        "prefix": [
            "Se você insiste em saber, {user}... ",
            "Surpreendentemente, aqui está a resposta, {user}: ",
            "Não conte pra ninguém que foi fácil, {user}: "
        ]
    },
    "zueiro": {
        "id": "zueiro",
        "name": "Zueiro & Humorista",
        "icon": "😂",
        "desc": "Gírias brasileiras, zoeira saudável, apelidos e alto astral contagiante.",
        "tagline": "Gírias brasileiras, zoeira saudável, apelidos e alto astral contagiante.",
        "greetings": [
            "Eaí, chefia {user}! Mandou, o pai tá on! O que você manda hoje?",
            "Salve, salve {user}! Fala comigo, meu consagrado! Qual é a boa?",
            "Brotou na área, {user}! Pode falar que eu sou todo ouvidos e pura resenha!",
            "Diga lá, lenda {user}! Se for pra trabalhar a gente trabalha, se for pra rir tamo junto!"
        ],
        "prefix": [
            "Bora lá, meu parceiro {user}: ",
            "Pega a visão, {user}: ",
            "Anota aí pra não esquecer depois, {user}: "
        ]
    },
    "robotico": {
        "id": "robotico",
        "name": "Robô Frio & Analítico",
        "icon": "🤖",
        "desc": "Lógica pura, 0% de emoção, precisão estatística e termos computacionais.",
        "tagline": "Lógica pura, 0% de emoção, precisão estatística e termos computacionais.",
        "greetings": [
            "Protocolo de entrada ativado para o operador {user}. Aguardando parâmetros de execução.",
            "Comando vocal detectado do usuário {user}. Sistemas operacionais em prontidão.",
            "Buffer de áudio aberto para {user}. Insira a instrução para processamento imediato.",
            "Identidade confirmada: {user}. Ciclos de computação alocados. Transmita o dado."
        ],
        "prefix": [
            "Dados computados para {user}: ",
            "Saída da instrução solicitada por {user}: ",
            "Análise lógica concluída com sucesso para o operador {user}: "
        ]
    },
    "sabio": {
        "id": "sabio",
        "name": "Sábio & Filosófico",
        "icon": "📜",
        "desc": "Reflexões profundas, serenidade existencial e metáforas inspiradoras.",
        "tagline": "Reflexões profundas, serenidade existencial e metáforas inspiradoras.",
        "greetings": [
            "Saudações, {user}. Cada chamado é uma oportunidade de contemplar o saber. O que sua mente busca?",
            "A paz esteja contigo, {user}. O tempo flui, e aqui estou para caminhar ao seu lado.",
            "Ouço sua voz, nobre {user}. Que a sabedoria guie a palavra que você irá proferir.",
            "Um novo instante de aprendizado nos une, {user}. Compartilhe sua questão com o mundo."
        ],
        "prefix": [
            "Como ensinam as lições da jornada, {user}: ",
            "Refletindo sobre sua questão, {user}: ",
            "Eis o que a reflexão nos revela, {user}: "
        ]
    }
}

# Mapeamento de apelidos e chaves em inglês
ALIAS_MAP = {
    "friendly": "amigavel",
    "formal": "elegante",
    "blunt": "grosso",
    "sarcastic": "sarcastico",
    "joker": "zueiro",
    "analytic": "robotico",
    "wise": "sabio",
}


class PersonalityManager:
    """Aplica o tom e formatação das respostas de acordo com a personalidade ativa."""

    PERSONALITIES = PERSONALITIES

    @classmethod
    def normalize_id(cls, personality_id: Optional[str]) -> str:
        if not personality_id:
            return "amigavel"
        pid = personality_id.lower().strip()
        return ALIAS_MAP.get(pid, pid if pid in PERSONALITIES else "amigavel")

    @classmethod
    def get_list(cls) -> List[Dict[str, Any]]:
        return list(PERSONALITIES.values())

    @classmethod
    def get_personality_data(cls, personality_id: Optional[str] = None) -> Dict[str, Any]:
        pid = cls.normalize_id(personality_id or SettingsManager.get_personality())
        return PERSONALITIES.get(pid, PERSONALITIES["amigavel"])

    @classmethod
    def get_wake_greeting(cls, personality_id: Optional[str] = None, user_name: Optional[str] = None) -> str:
        """Retorna uma saudação aleatória personalizada para o momento do Wake Word."""
        user = user_name or SettingsManager.get_user_name()
        data = cls.get_personality_data(personality_id)
        template = random.choice(data["greetings"])
        return template.format(user=user)

    WELCOME_MESSAGES: Dict[str, str] = {
        "amigavel": "Olá, {user}! Conexão estabelecida com sucesso! Como posso te ajudar?",
        "elegante": "Saudações, nobre {user}. Conexão autenticada com distinção. Ao seu inteiro dispor.",
        "grosso": "Conta conectada, {user}. O que você quer que eu faça agora?",
        "sarcastico": "Conectado, {user}. Até que foi rápido. O que manda?",
        "zueiro": "Fala aí, {user}! Conta conectada, o pai tá on! Qual é a boa?",
        "robotico": "Autenticação concluída para o operador {user}. Sistemas operacionais prontos.",
        "sabio": "Saudações, {user}. Conexão estabelecida em harmonia. Como posso guiá-lo?"
    }

    @classmethod
    def format_welcome(cls, personality_id: Optional[str] = None, user_name: Optional[str] = None) -> str:
        """Gera mensagem de boas-vindas concisa, ágil e personalizada."""
        user = user_name or SettingsManager.get_user_name()
        pid = cls.normalize_id(personality_id or SettingsManager.get_personality())
        template = cls.WELCOME_MESSAGES.get(pid, cls.WELCOME_MESSAGES["amigavel"])
        return template.format(user=user)

    @classmethod
    def format_wake_response(cls, personality_id: Optional[str] = None, user_name: Optional[str] = None) -> str:
        return cls.get_wake_greeting(personality_id, user_name)

    @classmethod
    def format_reply(
        cls, raw_text: str, personality_id: Optional[str] = None, user_name: Optional[str] = None
    ) -> str:
        """Adapta a resposta do robô adicionando o tom e o nome do usuário."""
        user = user_name or SettingsManager.get_user_name()
        data = cls.get_personality_data(personality_id)

        # Se a resposta já contiver o nome do usuário, não duplica o prefixo
        if user in raw_text:
            return raw_text

        prefix = random.choice(data["prefix"]).format(user=user)
        return f"{prefix}{raw_text}"

    @classmethod
    def format_response(cls, arg1: str, arg2: str, arg3: Optional[str] = None) -> str:
        """
        Sobrecarga flexível que suporta:
        format_response(personality_id, raw_reply, user_name)
        OU
        format_response(raw_reply, personality_id, user_name)
        """
        # Se arg1 for uma chave de personalidade válida ou alias
        if arg1 in PERSONALITIES or arg1 in ALIAS_MAP:
            personality_id = arg1
            raw_reply = arg2
            user_name = arg3
        else:
            raw_reply = arg1
            personality_id = arg2
            user_name = arg3

        return cls.format_reply(raw_reply, personality_id=personality_id, user_name=user_name)
