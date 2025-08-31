"""
Extratores de dados das mensagens
"""
import re
import logging
from datetime import datetime, timedelta, time
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class DataExtractor:
    """Extrai dados estruturados das mensagens"""
    
    def __init__(self):
        # Palavras-chave para procedimentos
        self.procedures_map = {
            "limpeza": ["limpeza", "limpar", "profilaxia"],
            "consulta": ["consulta", "consultar", "avaliação inicial"],
            "avaliacao": ["avaliação", "avaliar", "checkup", "check-up", "exame"],
            "ortodontia": ["ortodontia", "aparelho", "ortodôntico", "brackets"],
            "restauracao": ["restauração", "restaurar", "obturação", "cárie"],
            "canal": ["canal", "endodontia", "tratamento de canal"],
            "extracao": ["extração", "extrair", "arrancar", "tirar dente"],
            "clareamento": ["clareamento", "clarear", "branqueamento"],
            "implante": ["implante", "implantar", "prótese"]
        }
        
        # Mapeamento de dias relativos
        self.relative_days = {
            "hoje": 0,
            "amanhã": 1,
            "amanha": 1,
            "depois de amanhã": 2,
            "depois de amanha": 2
        }
        
        # Dias da semana
        self.weekdays = {
            "segunda": 0, "segunda-feira": 0, "seg": 0,
            "terça": 1, "terca": 1, "terça-feira": 1, "ter": 1,
            "quarta": 2, "quarta-feira": 2, "qua": 2,
            "quinta": 3, "quinta-feira": 3, "qui": 3,
            "sexta": 4, "sexta-feira": 4, "sex": 4,
            "sábado": 5, "sabado": 5, "sab": 5,
            "domingo": 6, "dom": 6
        }
        
        # Janelas de horário
        self.time_windows = {
            "manhã": "manhã",
            "manha": "manhã",
            "de manhã": "manhã",
            "pela manhã": "manhã",
            "tarde": "tarde",
            "de tarde": "tarde",
            "à tarde": "tarde",
            "a tarde": "tarde",
            "noite": "noite",
            "de noite": "noite",
            "à noite": "noite",
            "a noite": "noite"
        }
    
    def extract_all(self, text: str) -> Dict[str, Any]:
        """
        Extrai todos os dados possíveis da mensagem
        
        Args:
            text: Texto da mensagem
            
        Returns:
            Dict com dados extraídos
        """
        result = {}
        
        # Extrair nome
        name = self.extract_name(text)
        if name:
            result['full_name'] = name
        
        # Extrair procedimento
        procedure = self.extract_procedure(text)
        if procedure:
            result['procedure'] = procedure
        
        # Extrair data
        date = self.extract_date(text)
        if date:
            result['desired_date'] = date
        
        # Extrair horário
        time_value = self.extract_time(text)
        if time_value:
            result['desired_time'] = time_value
        
        # Extrair janela de horário
        window = self.extract_time_window(text)
        if window:
            result['desired_window'] = window
        
        return result
    
    def extract_name(self, text: str) -> Optional[str]:
        """
        Extrai nome da mensagem
        
        Padrões:
        - "sou o/a [Nome]"
        - "meu nome é [Nome]"
        - "me chamo [Nome]"
        - "[Nome] aqui"
        """
        text_lower = text.lower()
        
        # Padrões de identificação
        patterns = [
            r"(?:sou o|sou a|sou)\s+([A-Za-zÀ-ÿ\s]+)",
            r"(?:meu nome é|me chamo)\s+([A-Za-zÀ-ÿ\s]+)",
            r"(?:é o|é a)\s+([A-Za-zÀ-ÿ\s]+)\s+(?:aqui|falando)",
            r"^([A-Za-zÀ-ÿ]+)\s+(?:aqui|falando)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Limpar e capitalizar
                name = ' '.join(word.capitalize() for word in name.split())
                # Validar tamanho mínimo
                if len(name) >= 2 and len(name) <= 100:
                    logger.info(f"Nome extraído: {name}")
                    return name
        
        return None
    
    def extract_procedure(self, text: str) -> Optional[str]:
        """
        Extrai tipo de procedimento da mensagem
        
        Returns:
            str: Procedimento normalizado ou None
        """
        text_lower = text.lower()
        
        for procedure, keywords in self.procedures_map.items():
            for keyword in keywords:
                if keyword in text_lower:
                    logger.info(f"Procedimento extraído: {procedure}")
                    return procedure
        
        return None
    
    def extract_date(self, text: str) -> Optional[datetime]:
        """
        Extrai data da mensagem
        
        Formatos suportados:
        - Datas relativas: hoje, amanhã
        - Dias da semana: segunda, terça
        - Datas específicas: 15/03, 15/3
        """
        text_lower = text.lower()
        today = datetime.now().date()
        
        # Verificar datas relativas
        for relative, days in self.relative_days.items():
            if relative in text_lower:
                target_date = today + timedelta(days=days)
                logger.info(f"Data relativa extraída: {target_date}")
                return target_date
        
        # Verificar dias da semana
        for day_name, day_num in self.weekdays.items():
            if day_name in text_lower:
                # Calcular próxima ocorrência do dia
                days_ahead = day_num - today.weekday()
                if days_ahead <= 0:  # Dia já passou esta semana
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
                logger.info(f"Dia da semana extraído: {target_date}")
                return target_date
        
        # Verificar datas específicas (dd/mm ou dd/mm/yyyy)
        date_pattern = r'\b(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?\b'
        match = re.search(date_pattern, text)
        if match:
            day = int(match.group(1))
            month = int(match.group(2))
            year = match.group(3)
            
            if year:
                year = int(year)
                if year < 100:  # Ano com 2 dígitos
                    year += 2000
            else:
                year = today.year
                # Se a data já passou este ano, assumir próximo ano
                test_date = datetime(year, month, day).date()
                if test_date < today:
                    year += 1
            
            try:
                target_date = datetime(year, month, day).date()
                if target_date >= today:  # Só aceitar datas futuras
                    logger.info(f"Data específica extraída: {target_date}")
                    return target_date
            except ValueError:
                pass  # Data inválida
        
        return None
    
    def extract_time(self, text: str) -> Optional[time]:
        """
        Extrai horário específico da mensagem
        
        Formatos:
        - 14h, 14:00, 14:30
        - 2h da tarde (converte para 14:00)
        - meio-dia (12:00)
        """
        text_lower = text.lower()
        
        # Horários especiais
        if "meio-dia" in text_lower or "meio dia" in text_lower:
            return time(12, 0)
        
        # Padrão de horário (14h, 14:00, 14h30)
        time_pattern = r'\b(\d{1,2})(?:h|:)(\d{0,2})\b'
        match = re.search(time_pattern, text)
        
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            
            # Ajustar AM/PM baseado no contexto
            if "tarde" in text_lower and hour < 12:
                hour += 12
            elif "noite" in text_lower and hour < 12:
                hour += 12
            
            # Validar horário
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                extracted_time = time(hour, minute)
                logger.info(f"Horário extraído: {extracted_time}")
                return extracted_time
        
        return None
    
    def extract_time_window(self, text: str) -> Optional[str]:
        """
        Extrai janela de horário (manhã, tarde, noite)
        
        Returns:
            str: Janela normalizada ou None
        """
        text_lower = text.lower()
        
        for pattern, window in self.time_windows.items():
            if pattern in text_lower:
                logger.info(f"Janela de horário extraída: {window}")
                return window
        
        return None