"""
services/core/calendar/google_client.py
"""

import json
import os
from typing import Optional
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Escopos necessários para o Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarClient:
    """Cliente para interagir com Google Calendar API."""
    
    def __init__(self):
        """Inicializa o cliente do Google Calendar."""
        self.service = None
        self.auth_mode = os.getenv("GOOGLE_AUTH_MODE", "service_account")
        self.credentials_path = os.getenv("GOOGLE_CREDENTIALS_JSON", "/secrets/google-credentials.json")
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        
    def authenticate(self) -> None:
        """Autentica com o Google Calendar usando o método configurado."""
        if self.auth_mode == "service_account":
            self._authenticate_service_account()
        elif self.auth_mode == "oauth":
            self._authenticate_oauth()
        else:
            raise ValueError(f"Modo de autenticação inválido: {self.auth_mode}")
            
    def _authenticate_service_account(self) -> None:
        """Autentica usando Service Account (ASSUNÇÃO A - preferida)."""
        try:
            if not os.path.exists(self.credentials_path):
                raise FileNotFoundError(
                    f"Arquivo de credenciais não encontrado: {self.credentials_path}\n"
                    "Por favor, crie uma Service Account no Google Cloud Console e "
                    "baixe o JSON das credenciais."
                )
                
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=SCOPES
            )
            
            self.service = build('calendar', 'v3', credentials=credentials)
            
            # Testa o acesso ao calendário
            try:
                calendar = self.service.calendars().get(calendarId=self.calendar_id).execute()
                print(f"✅ Conectado ao calendário: {calendar.get('summary', self.calendar_id)}")
            except HttpError as e:
                if e.resp.status == 404:
                    raise ValueError(
                        f"Calendário não encontrado: {self.calendar_id}\n"
                        "Certifique-se de compartilhar o calendário com o email da Service Account "
                        "e dar permissão 'Fazer alterações'."
                    )
                raise
                
        except Exception as e:
            raise Exception(f"Erro na autenticação com Service Account: {str(e)}")
            
    def _authenticate_oauth(self) -> None:
        """Autentica usando OAuth (ASSUNÇÃO B - alternativa)."""
        creds = None
        token_path = "/secrets/token.json"
        
        # Token existente
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
        # Se não há credenciais válidas
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Arquivo OAuth não encontrado: {self.credentials_path}\n"
                        "Baixe o arquivo de credenciais OAuth do Google Cloud Console."
                    )
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                
            # Salva as credenciais para próximas execuções
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
                
        self.service = build('calendar', 'v3', credentials=creds)
        
    def get_service(self):
        """Retorna o serviço do Google Calendar, autenticando se necessário."""
        if not self.service:
            self.authenticate()
        return self.service
        
    def test_connection(self) -> bool:
        """Testa a conexão com o Google Calendar."""
        try:
            service = self.get_service()
            calendar = service.calendars().get(calendarId=self.calendar_id).execute()
            print(f"✅ Conexão OK - Calendário: {calendar.get('summary', 'Primary')}")
            return True
        except Exception as e:
            print(f"❌ Erro na conexão: {str(e)}")
            return False
            
            
# Singleton para reutilizar a mesma instância
_client_instance = None

def get_calendar_client() -> GoogleCalendarClient:
    """Retorna instância singleton do cliente do Google Calendar."""
    global _client_instance
    if _client_instance is None:
        _client_instance = GoogleCalendarClient()
    return _client_instance