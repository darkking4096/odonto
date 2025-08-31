"""
Validadores de dados extraídos
"""
import logging
from datetime import datetime, date, time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DataValidator:
    """Valida e normaliza dados extraídos"""
    
    def __init__(self):
        # Lista de procedimentos válidos
        self.valid_procedures = [
            "limpeza",
            "consulta", 
            "avaliacao",
            "ortodontia",
            "restauracao",
            "canal",
            "extracao",
            "clareamento",
            "implante"
        ]
        
        # Janelas válidas
        self.valid_windows = ["manhã", "tarde", "noite"]
        
        # Horário de funcionamento (exemplo)
        self.opening_time = time(8, 0)   # 08:00
        self.closing_time = time(18, 0)  # 18:00
    
    def validate_all(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida todos os dados extraídos
        
        Args:
            data: Dicionário com dados extraídos
            
        Returns:
            Dict com apenas dados válidos
        """
        validated = {}
        
        # Validar nome
        if 'full_name' in data:
            name = self.validate_name(data['full_name'])
            if name:
                validated['full_name'] = name
        
        # Validar procedimento
        if 'procedure' in data:
            procedure = self.validate_procedure(data['procedure'])
            if procedure:
                validated['procedure'] = procedure
        
        # Validar data
        if 'desired_date' in data:
            date_value = self.validate_date(data['desired_date'])
            if date_value:
                validated['desired_date'] = date_value
        
        # Validar horário
        if 'desired_time' in data:
            time_value = self.validate_time(data['desired_time'])
            if time_value:
                validated['desired_time'] = time_value
        
        # Validar janela
        if 'desired_window' in data:
            window = self.validate_window(data['desired_window'])
            if window:
                validated['desired_window'] = window
        
        return validated
    
    def validate_name(self, name: str) -> Optional[str]:
        """
        Valida e normaliza nome
        
        Regras:
        - Mínimo 2 caracteres
        - Máximo 100 caracteres
        - Apenas letras e espaços
        - Capitalização adequada
        """
        if not name or not isinstance(name, str):
            return None
        
        # Limpar espaços extras
        name = ' '.join(name.split())
        
        # Verificar tamanho
        if len(name) < 2 or len(name) > 100:
            logger.warning(f"Nome inválido (tamanho): {name}")
            return None
        
        # Verificar caracteres (permite letras, espaços e acentos)
        if not all(c.isalpha() or c.isspace() for c in name.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ã','a').replace('õ','o').replace('â','a').replace('ê','e').replace('ô','o').replace('ç','c')):
            logger.warning(f"Nome contém caracteres inválidos: {name}")
            return None
        
        # Capitalizar adequadamente
        words = name.lower().split()
        # Preposições que não devem ser capitalizadas
        prepositions = ['de', 'da', 'do', 'dos', 'das', 'e']
        
        capitalized = []
        for i, word in enumerate(words):
            if i == 0 or word not in prepositions:
                capitalized.append(word.capitalize())
            else:
                capitalized.append(word)
        
        validated_name = ' '.join(capitalized)
        logger.info(f"Nome validado: {validated_name}")
        return validated_name
    
    def validate_procedure(self, procedure: str) -> Optional[str]:
        """
        Valida procedimento
        
        Args:
            procedure: Nome do procedimento
            
        Returns:
            str: Procedimento normalizado ou None
        """
        if not procedure or not isinstance(procedure, str):
            return None
        
        # Normalizar para lowercase
        procedure_lower = procedure.lower().strip()
        
        # Verificar se está na lista válida
        if procedure_lower in self.valid_procedures:
            logger.info(f"Procedimento válido: {procedure_lower}")
            return procedure_lower
        
        logger.warning(f"Procedimento inválido: {procedure}")
        return None
    
    def validate_date(self, date_value: Any) -> Optional[date]:
        """
        Valida data
        
        Regras:
        - Deve ser hoje ou no futuro
        - Máximo 90 dias no futuro
        """
        if not date_value:
            return None
        
        # Converter para date se necessário
        if isinstance(date_value, datetime):
            date_value = date_value.date()
        elif not isinstance(date_value, date):
            try:
                date_value = datetime.strptime(str(date_value), "%Y-%m-%d").date()
            except:
                logger.warning(f"Data em formato inválido: {date_value}")
                return None
        
        today = datetime.now().date()
        
        # Verificar se é no futuro (ou hoje)
        if date_value < today:
            logger.warning(f"Data no passado: {date_value}")
            return None
        
        # Verificar limite máximo (90 dias)
        max_date = today.replace(day=today.day, month=(today.month + 3) % 12 or 12)
        if date_value > max_date:
            logger.warning(f"Data muito distante: {date_value}")
            return None
        
        logger.info(f"Data válida: {date_value}")
        return date_value
    
    def validate_time(self, time_value: Any) -> Optional[time]:
        """
        Valida horário
        
        Regras:
        - Dentro do horário de funcionamento
        - Intervalos de 30 minutos
        """
        if not time_value:
            return None
        
        # Converter para time se necessário
        if not isinstance(time_value, time):
            try:
                if isinstance(time_value, str):
                    time_value = datetime.strptime(time_value, "%H:%M").time()
                else:
                    logger.warning(f"Horário em formato inválido: {time_value}")
                    return None
            except:
                logger.warning(f"Erro ao converter horário: {time_value}")
                return None
        
        # Verificar horário de funcionamento
        if time_value < self.opening_time or time_value >= self.closing_time:
            logger.warning(f"Horário fora do funcionamento: {time_value}")
            return None
        
        # Ajustar para intervalos de 30 minutos
        minute = time_value.minute
        if minute not in [0, 30]:
            # Arredondar para o próximo intervalo de 30 min
            if minute < 30:
                minute = 30
            else:
                minute = 0
                hour = time_value.hour + 1
                if hour >= self.closing_time.hour:
                    logger.warning(f"Horário ajustado excede funcionamento")
                    return None
                time_value = time(hour, minute)
            time_value = time(time_value.hour, minute)
        
        logger.info(f"Horário válido: {time_value}")
        return time_value
    
    def validate_window(self, window: str) -> Optional[str]:
        """
        Valida janela de horário
        
        Args:
            window: Janela (manhã, tarde, noite)
            
        Returns:
            str: Janela normalizada ou None
        """
        if not window or not isinstance(window, str):
            return None
        
        window_lower = window.lower().strip()
        
        if window_lower in self.valid_windows:
            logger.info(f"Janela válida: {window_lower}")
            return window_lower
        
        logger.warning(f"Janela inválida: {window}")
        return None