import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'


def get_calendar_service():
    """Authenticate and return Google Calendar service."""
    creds = None

    # Load existing token
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # Refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)


def add_event_to_calendar(event: dict) -> str:
    """
    Add an event to Google Calendar.
    Returns the link to the created event.
    """
    service = get_calendar_service()

    calendar_event = {
        'summary': event['summary'],
        'start': {
            'dateTime': event['start_datetime'].isoformat(),
            'timeZone': 'Asia/Jerusalem',
        },
        'end': {
            'dateTime': event['end_datetime'].isoformat(),
            'timeZone': 'Asia/Jerusalem',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 30},
            ],
        },
    }

    # Add guest if provided
    if event.get('guest_email'):
        calendar_event['attendees'] = [
            {'email': event['guest_email']}
        ]

    created_event = service.events().insert(
        calendarId='primary',
        body=calendar_event,
        sendUpdates='all'
    ).execute()

    return created_event.get('htmlLink', '')
