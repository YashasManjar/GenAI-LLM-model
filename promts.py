STATE_NAME_STATE_CODE_LIST = {'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR', 'CALIFORNIA': 'CA',
                              'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE', 'FLORIDA': 'FL', 'GEORGIA': 'GA',
                              'HAWAII': 'HI', 'IDAHO': 'ID', 'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA',
                              'KANSAS': 'KS', 'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME', 'MARYLAND': 'MD',
                              'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN', 'MISSISSIPPI': 'MS',
                              'MISSOURI': 'MO', 'MONTANA': 'MT', 'NEBRASKA': 'NE', 'NEVADA': 'NV', 'NEWHAMPSHIRE': 'NH',
                              'NEWJERSEY': 'NJ', 'NEWMEXICO': 'NM', 'NEWYORK': 'NY', 'NORTHCAROLINA': 'NC',
                              'NORTHDAKOTA': 'ND', 'OHIO': 'OH', 'OKLAHOMA': 'OK', 'OREGON': 'OR', 'PENNSYLVANIA': 'PA',
                              'RHODEISLAND': 'RI', 'SOUTHCAROLINA': 'SC', 'SOUTHDAKOTA': 'SD', 'TENNESSEE': 'TN',
                              'TEXAS': 'TX', 'UTAH': 'UT', 'VERMONT': 'VT', 'VIRGINIA': 'VA', 'WASHINGTON': 'WA',
                              'WASHINGTON D.C.': 'DC', 'WASHINGTON DC': 'DC', 'DISTRICTOFCOLUMBIA': 'DC',
                              'WESTVIRGINIA': 'WV', 'WISCONSIN': 'WI', 'WYOMING': 'WY'}

state_key_and_id = {"AL": 1, "AK": 2, "AZ": 3, "AR": 4, "CA": 5, "CO": 6, "CT": 7, "DE": 8, "FL": 9, "GA": 10, "HI": 11, "ID": 12, "IL": 13, "IN": 14, "IA": 15, "KS": 16, "KY": 17, "LA": 18, "ME": 19, "MD": 20, "MA": 21, "MI": 22, "MN": 23, "MS": 24, "MO": 25, "MT": 26, "NE": 27, "NV": 28, "NH": 29, "NJ": 30, "NM": 31, "NY": 32, "NC": 33, "ND": 34, "OH": 35, "OK": 36, "OR": 37, "PA": 38, "RI": 39, "SC": 40, "SD": 41, "TN": 42, "TX": 43, "UT": 44, "VT": 45, "VA": 46, "WA": 47, "DC": 48, "WV": 49, "WI": 50, "WY": 51, "OH2": 52}
def prompt_func(html, schema, date_format):
    messages = f'''
            **Your Task:**

                1. **Extract Attorney Data from the given HTML content -> {html}:** 
                - The given HTML content is a list of responses for each attorney 
                - from the given html, extract all attorney-related data and structure it according to the schema: {schema} seperately for each attorney.
                - The HTML has the attorney admitted to bar date in {date_format}, convert it to dd/mm/yyyy format. Ignore if already converted

            **Important Notes:**

            * Include only data visible to a regular user browsing the website. Don't extract hidden informations.
            * You have been wrong before, so do understand the data and check whether that can be mapped to any of the fields in schema, if it can be mapped then only map, otherwise leave the field value as null
            * Remember that all the fields from schema must be present in response, it can have null value if the value is not provided in html response.
            * Ensure an exact match with the displayed information. 
            * Avoid making assumptions or modifying the data in any way. Only parse the data which present in the HTML content.
            ** Very important point - If there are multiple email values, then select the only the inline email which is visible to user in frontend** 
            **Extract only the information from provided HTML data and don't assume anything.**
            **Don't include any unnecessary information, code or any note in the response. The response should be list of JSON items for each attorney data**
            * If any key has junk values such as N/A, NOT AVAILABLE, NONE, null etc or anything that is not actually a valid value for attorney information, remove them and make it null. if a list item has only such values, then make it empty list
        '''
    return messages
