from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '/etc/secrets/credentials.json')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv('GOOGLE_SHEET_ID')

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

service = build('sheets', 'v4', credentials=credentials)
sheet = service.spreadsheets()

def read_range(range_name):
    print(f"Reading range: {range_name} from Spreadsheet ID: {SPREADSHEET_ID}")
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
    values = result.get('values', [])
    print(f"Values read: {values}")
    return values

def write_range(range_name, values):
    body = {'values': values}
    result = sheet.values().update(
        spreadsheetId=SPREADSHEET_ID, range=range_name,
        valueInputOption='RAW', body=body).execute()
    return result
