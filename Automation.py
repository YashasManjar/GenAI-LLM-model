from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_transformers import BeautifulSoupTransformer
from langchain_aws import ChatBedrock
from schema import schemas
import sys
import json
import re
from db_connection import DbConnection
from constants import STATE_NAME_STATE_CODE_LIST, state_key_and_id, prompt_func
from google.oauth2 import service_account
import gspread
from datetime import date
from nameparser import HumanName
from dateutil.parser import parse


def clean_text(text):
    text = re.sub(r'\n', '', text)
    text = re.sub(r'[,\s]+', ' ', text)

    return text.strip()
#To load attorney dsui from file
def load_attorney_list(filename='attorney_list.txt'):
    with open(filename, 'r') as file:
        return [line.strip() for line in file if line.strip()]

class SheetHandler:
    def __init__(self, state):
        self.state = state

    def add_headers(self, worksheet):
        header = ['data_source_unique_id', 'mis_matched_datapoint', 'value in source', 'value_in_DB']
        worksheet.insert_row(header, 1)
        return worksheet

    def create_or_open_spreadsheet(self):
        ''' If the spreadsheet already exists, create a new worksheet in that and update the values. Else create new wrokseet'''

        gsheet_credentials = service_account.Credentials.from_service_account_file('google_sheet_credentials.json')
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_scope = gsheet_credentials.with_scopes(scope)
        client = gspread.authorize(creds_scope)

        folder_id = '1d6QYO060UU4J21kAhdaYmbwPcDhzc-_J'
        spreadsheet_title = f'{self.state}_mismatches'

        try:
            spreadsheet = client.open(spreadsheet_title, folder_id)
            worksheet_count = len(spreadsheet.worksheets())
            try:
                last_updated_sheet = spreadsheet.worksheet(f"{date.today().isoformat()}_Sheet{worksheet_count}")
                last_updated_sheet_values = last_updated_sheet.get_all_values()
                if len(last_updated_sheet_values) < 2:
                    worksheet = last_updated_sheet
                else:
                    new_worksheet_title = f"{date.today().isoformat()}_Sheet{worksheet_count + 1}"
                    worksheet = spreadsheet.add_worksheet(title=new_worksheet_title, rows=1000, cols=26)
                    worksheet = self.add_headers(worksheet)
            except gspread.exceptions.WorksheetNotFound:
                new_worksheet_title = f"{date.today().isoformat()}_Sheet{worksheet_count + 1}"
                worksheet = spreadsheet.add_worksheet(title=new_worksheet_title, rows=1000, cols=26)
                worksheet = self.add_headers(worksheet)
        
        except gspread.SpreadsheetNotFound:
            spreadsheet = client.create(spreadsheet_title, folder_id)
            worksheet = spreadsheet.worksheet("Sheet1")
            worksheet.update_title(f"{date.today().isoformat()}_Sheet1")
            worksheet = self.add_headers(worksheet)
        return worksheet


class DataExtractor:
    def __init__(self, state, state_id, bar_num):
        self.state = state
        self.state_id = state_id
        self.bar_num = bar_num

    def get_attorney_data(self):
        cur = DbConnection.connection_to_abe_db()
        bar_num = self.bar_num

        cur.execute(
            f"select data_source_unique_id, bar_number, admitted_date, up.unresolved_parameter_name as status, county, inactivation_date from attorney_info inf inner join unresolved_parameter up on up.id = inf.status_id and mst_state_id = {state_id} and data_source_unique_id = '{bar_num}'")
        attorney_data = cur.fetchone()
        DB_response = {
            'bar_number': attorney_data['bar_number'],
            'status': attorney_data['status'].upper(),
            'admitted_date': attorney_data['admitted_date'],
            'county': attorney_data['county'].upper() if attorney_data['county'] else None,
            'inactivation_date': attorney_data['inactivation_date']
        }

        cur.execute(
            f"select phone, lower(unresolved_parameter_name) as unresolved_parameter_name from attorney_phone ph inner join attorney_info inf on inf.id = ph.attorney_id inner join unresolved_parameter un on un.id = phone_type_id where mst_state_id = {state_id} and data_source_unique_id = '{bar_num}' and ph.is_active = True")
        db_phone = cur.fetchall()
        DB_phone = {}
        if db_phone:
            for row in db_phone:
                DB_phone['phone' if row['unresolved_parameter_name'] == 'default' or row['unresolved_parameter_name'] == 'phone number' else row['unresolved_parameter_name']] = row['phone']
        phone_ele = ['phone', 'fax', 'cell']
        for ele in phone_ele:
            if ele not in DB_phone.keys():
                DB_phone.update({ele: None})
        DB_response.update(DB_phone)

        cur.execute(
            f"select lf.law_firm from attorney_lawfirm lf inner join attorney_info inf on inf.id = lf.attorney_id where mst_state_id = {state_id} and data_source_unique_id = '{bar_num}' and lf.is_active = True")
        db_lawfirm = cur.fetchone()
        DB_response['law_firm'] = clean_text(db_lawfirm['law_firm'].upper()) if db_lawfirm else None

        cur.execute(
            f"select mail.email from attorney_email mail inner join attorney_info inf on inf.id = mail.attorney_id where mst_state_id = {state_id} and data_source_unique_id = '{bar_num}' and mail.is_active = True")
        db_email = cur.fetchone()
        DB_response['email'] = db_email['email'].upper() if db_email else None

        DB_response = {key: None if value == '' or value is None else (value.upper() if not isinstance(value, date) else value) for key, value in DB_response.items()}

        cur.execute(
            f"select unresolved_parameter_name||'_address' as unresolved_parameter_name, ful.complete_address, street_address_1, street_address_2 , city, state_name , state_code , country_name , country_code , zip, zip_4 from attorney_full_address ful inner join attorney_info inf on inf.id  = ful.attorney_id  left join attorney_address add on add.full_address_id = ful.id inner join unresolved_parameter un on un.id = ful.address_type_id where add.is_active = True and mst_state_id = {state_id} and data_source_unique_id = '{bar_num}'")
        db_address = cur.fetchall()
        DB_address = {}
        for add in db_address:
            if add['street_address_1']:
                add['unresolved_parameter_name'] = 'office_address' if add['unresolved_parameter_name'] == 'not classified_address' else add['unresolved_parameter_name']
                DB_address[add['unresolved_parameter_name']] = {
                    'complete_address': clean_text(add['complete_address']),
                    'street_address': clean_text(add['street_address_1'].upper() + ', ' + add['street_address_2'].upper()) if add['street_address_2'] else clean_text(add['street_address_1'].upper()),
                    'city': add['city'],
                    'state_name': add['state_name'],
                    'state_code': add['state_code'],
                    'country_name': add['country_name'],
                    'country_code': add['country_code'],
                    'zip': add['zip'],
                    'zip4': add['zip_4']
                }
                DB_address[add['unresolved_parameter_name']] = {key: None if value == '' or value is None else value.upper() for key, value in DB_address[add['unresolved_parameter_name']].items()}
                DB_response[add['unresolved_parameter_name']] = DB_address[add['unresolved_parameter_name']]

        db_attorney_name = {}
        cur.execute(
            f"select nm.raw_name, nm.name, prefix, first_name, middle_name, last_name, suffix  from attorney_name nm inner join attorney_info inf on inf.id = nm.attorney_id where mst_state_id = {state_id} and data_source_unique_id = '{bar_num}' and nm.is_active = True")
        db_name = cur.fetchone()
        if db_name:
            db_attorney_name['name'] = db_name['name'].upper()
            db_attorney_name['prefix'] = db_name['prefix'].upper() if db_name['prefix'] else None
            db_attorney_name['first_name'] = db_name['first_name'].upper()
            db_attorney_name['middle_name'] = db_name['middle_name'].upper() if db_name['middle_name'] else None
            db_attorney_name['last_name'] = db_name['last_name'].upper()
            db_attorney_name['suffix'] = db_name['suffix'].upper() if db_name['suffix'] else None

        db_attorney_name = {key: None if value == '' or value is None else value.upper() for key, value in db_attorney_name.items()}
        DB_response['name'] = db_attorney_name

        db_custom_data = {}
        cur.execute(
            f"select additional_info->0 from attorney_custom cst inner join attorney_info inf on inf.id = cst.attorney_id where mst_state_id = {state_id} and data_source_unique_id = '{bar_num}'")
        db_custom_data = cur.fetchone()
        if db_custom_data:
            # for key, val in db_custom_data.items():
            #     DB_response[key] = val
            for key, val in dict(db_custom_data)['?column?'].items():
                DB_response[key] = str(val).upper() if not (isinstance(val, list) or  isinstance(val, dict)) else val
        return DB_response

class getLLMResponse:
    def __init__(self, message, total_input_token, total_output_token):
        self.message = message
        self.total_input_token = total_input_token
        self.total_output_token = total_output_token
        self.response_regex = r"\[.+\][^\]]*$"

    def claude_request(self):
        chat = ChatBedrock(
            #model_id="anthropic.claude-3-haiku-20240307-v1:0",
            model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
            model_kwargs={"temperature": 0.1, 'max_tokens': 4096},
            region_name="us-east-1"
        )
        loop_count = 0
        source_response = None
        response = None

        while loop_count < 5:
            try:
                response = chat.invoke(messages)
                source_response = response.content.replace('\n', '')
                source_response = re.search(self.response_regex, source_response, re.IGNORECASE).group()
                source_response = source_response.replace('None', 'null')
                source_response = json.loads(re.sub(r'(?<![a-zA-Z0-9_])\'|\'(?![a-zA-Z0-9_])', '"', source_response))
                break
            except:
                print('inavlid response from claude')
                loop_count += 1 #loop_count = +1
        source_response = self.response_validation(source_response)
        print(source_response)
        if source_response:
            self.total_input_token = self.total_input_token + int(response.additional_kwargs['usage']['prompt_tokens'])
            self.total_output_token = self.total_output_token + int(response.additional_kwargs['usage']['completion_tokens'])
            print(response.additional_kwargs['usage']['prompt_tokens'],
                  response.additional_kwargs['usage']['completion_tokens'])
        return source_response, self.total_input_token, self.total_output_token

    def response_validation(self, source_response_list):
        # address validation
        validation_regex = re.compile('^(\s+)?no(t|ne)?\s?(street|address|city|state|any|country|given|available|data.*|listed|liested|info(rmation)?\\s?(provided)?|(on|in)\s?file)?|null reported(\s+)?$', re.IGNORECASE)
        validated_response = []
        address_types = ['office_address', 'mailing_address']
        for source_response in source_response_list:
            source_response = {key: (None if re.search(validation_regex, value) else value) if isinstance(value, str) else value for key, value in source_response.items()}
            if source_response['admitted_date']:
                source_response['admitted_date'] = parse(source_response['admitted_date']).date()
            for address_type in address_types:
                if address_type in source_response.keys() and source_response[address_type]:
                    if not source_response[address_type]['street_address']:
                        source_response[address_type] = {
                            'full_address': clean_text(source_response[address_type]['complete_address'])} if source_response[address_type]['complete_address'] else None
                    else:
                        source_response[address_type]['complete_address'] = clean_text(source_response[address_type]['complete_address'])
                        source_response[address_type]['street_address'] = clean_text(source_response[address_type]['street_address'])
                        if source_response[address_type]['state_name']:
                            for key, val in STATE_NAME_STATE_CODE_LIST.items():
                                if source_response[address_type]['state_name'].upper() == key or \
                                        source_response[address_type]['state_name'].upper() == val:
                                    source_response[address_type]['state_name'] = key
                                    source_response[address_type]['state_code'] = val
                                    source_response[address_type]['country_name'] = "UNITED STATES OF AMERICA"
                                    source_response[address_type]['country_code'] = 'US'
                                    break
            if source_response['law_firm']:
                source_response['law_firm'] = clean_text(source_response['law_firm'])

            # name splitting using name parser
            name = HumanName(source_response['name'])
            splitted_name = {
                'name': name.full_name,
                'prefix': name.title if name.title else None,
                'first_name': name.first,
                'middle_name': name.middle if name.middle else None,
                'last_name': name.last,
                'suffix': name.suffix if name.suffix else None
            }
            source_response['name'] = splitted_name
            print(source_response)
            validated_response.append(source_response)
        return validated_response

class MismatchAnalyzer:
    def __init__(self, source_response, DB_response, dsui):
        self.source_response = source_response
        self.DB_response = DB_response
        self.dsui = dsui

    def find_mismatches(self):
        mis_matches = []
        for key, source_value in self.source_response.items():
            if key in self.DB_response:
                if isinstance(source_value, dict):
                    for sub_key, sub_source_value in source_value.items():
                        source_value_upper = sub_source_value.upper() if isinstance(sub_source_value,
                                                                                    str) else sub_source_value
                        if source_value_upper != self.DB_response[key].get(sub_key):
                            mis_matches.append(
                                [self.dsui, sub_key, str(source_value_upper), str(self.DB_response[key].get(sub_key))])
                else:
                    source_value_upper = source_value.upper() if isinstance(source_value, str) else source_value
                    if source_value_upper != self.DB_response[key]:
                        mis_matches.append([self.dsui, key, str(source_value_upper), str(self.DB_response[key])])
            elif source_value:
                mis_matches.append([self.dsui, key, str(source_value), 'Key not found'])
        return mis_matches


breakpoint()#use python3 ABE_Automation.py State to run
state = sys.argv[1]
state_id = state_key_and_id[state]

cur = DbConnection.connection_to_abe_db()

cur.execute(
    f"select data_source_unique_id from attorney_info where mst_state_id = {state_id} and mst_bar_source_type_id =1 and extract('day' from admitted_date)::int > 12 limit 1")


# cur.execute(
#     f"select data_source_unique_id from attorney_info where mst_state_id = {state_id} and mst_bar_source_type_id =1 and updated_date >= '2025-02-11' limit 5")
# input_data = cur.fetchall()
# DSUI_list = [ele['data_source_unique_id'] for ele in input_data]
#DSUI_list = ['77738', '47420','87599','35802','42913'] 
DSUI_list = load_attorney_list()



# Load HTML
loader = AsyncHtmlLoader(
    [f"https://prod-databank-abe-webapp.unicourt.net:9879/admin/view_html/{state_id}/1/{ele}" for ele in DSUI_list])
htmls = loader.load()

schema = schemas[state]
total_input_token = 0
total_output_token = 0
attorney_chunk = 5
mis_matches = []

for i in range(0, len(htmls), attorney_chunk):
    html_chunks = htmls[i:i + attorney_chunk]
    dsui_chunks = DSUI_list[i:i + attorney_chunk]

    #Beautify it to reduce the input token count, if it doesn't remove the required values from HTML response
    if state in ['NV', 'LA', 'OR']:
        temp = []
        for ele in html_chunks:
            bs_transformer = BeautifulSoupTransformer()
            temp.append(bs_transformer.transform_documents([ele]))
        html_chunks = temp
    date_format= "%y%m%d"
    messages = prompt_func(html_chunks, schema, date_format)

    get_llm_response = getLLMResponse(messages, total_input_token, total_output_token)
    llm_response, total_input_token, total_output_token = get_llm_response.claude_request()

    for j in range(attorney_chunk):
    # for j in range(len(dsui_chunks)):    
        data_extractor = DataExtractor(state, state_id, dsui_chunks[j])
        DB_response = data_extractor.get_attorney_data()

        mismatch_analyzer = MismatchAnalyzer(llm_response[j], DB_response, dsui_chunks[j])
        mis_matches.append(mismatch_analyzer.find_mismatches())

sheet_handler = SheetHandler(state)
worksheet = sheet_handler.create_or_open_spreadsheet()

# for ele in mis_matches:
#     for ele2 in ele:
#         try:
#             worksheet.append_row(ele2)
#         except Exception as e:
#             print(f'error occured, {e}')

 # Flatten list of mismatches
flat_rows = [row for group in mis_matches for row in group]
try:
    worksheet.append_rows(flat_rows)
except Exception as e:
    print(f'Error during batch write: {e}')
          
print(mis_matches)

print(f"Total attorneys fetched: {len(DSUI_list)}")
print(f'average input token - {total_input_token / (len(htmls) / attorney_chunk)}')
print(f'average output token - {total_output_token / (len(htmls) / attorney_chunk)}')

print(f"Total input tokens: {total_input_token}")
print(f"Input tokens per attorney: {total_input_token / len(DSUI_list)}")
print(f"Total output tokens: {total_output_token}")
print(f"Output tokens per attorney: {total_output_token / len(DSUI_list)}")
