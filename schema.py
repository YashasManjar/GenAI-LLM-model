schemas = {
  "CA": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "bar_number": {"type": "string"},
      "status": {"type": "string"},
      "admitted_date": {"type": "string", "format": "date"},
      "law_firm": {"type": "string"},
      "phone": {"type": "string"},
      "fax": {"type": "string"},
      "office_address": {
        "type": "object",
        "properties": {
          "complete_address": {"type": "string"},
          "street_address": {"type": "string"},
          "city": {"type": "string"},
          "state_code": {"type": "string"},
          "state_name": {"type": "string"},
          "country_code": {"type": "string"},
          "country_name": {"type": "string"},
          "zip": {"type": "string"},
          "zip4": {"type": "string"}
        }
      },
      "email": {"type": "string", "format": "email"},
      "website": {"type": "string", "format": "uri"},
      "cla_sections_list": {"type": "array", "format": "string"},
      "practice_area_list": {"type": "array", "format": "string"},
      "languages_spoken_list": {"type": "array", "format": "string"},
      "law_school": {"type": "string"},
      "disciplinary_history": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "date": {"type": "string"},
            "license_status": {"type": "string"},
            "discipline": {"type": "string"},
            "administrative_action": {"type": "string"}
          }
        }
      }
    },
    "required": ["name", "status", "bar_number"]
  }
