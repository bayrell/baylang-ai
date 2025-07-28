import re, json, starlette, datetime
from pydantic import ValidationError

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return format_datetime(obj)
        return json.JSONEncoder.default(self, obj)

class JSONResponse(starlette.responses.JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            cls=JSONEncoder,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

def json_encode(obj, indent=2):
    return json.dumps(obj, indent=indent, cls=JSONEncoder, ensure_ascii=False)

def json_decode(content, default=None):
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        return default

def json_response(value, status_code=200):
    response = JSONResponse(value, status_code=status_code)
    return response

def parse_nested_content(form_data):
    
    """
    Parse nested form data
    """
    
    result = {}
    
    def create(keys, index):
        key = keys[index]
        if re.fullmatch(r"\d+", key):
            return []
        return {}
    
    def add(result, keys, value):
        for i, key in enumerate(keys[:-1]):
            
            if isinstance(result, dict):
                if not key in result:
                    result[key] = create(keys, i + 1)
            elif isinstance(result, list):
                key = int(key)
                if key >= len(result):
                    result.append(create(keys, i + 1))
            
            result = result[key]
        
        last_key = keys[-1]
        if isinstance(result, dict):
            result[last_key] = value
        elif isinstance(result, list):
            result.append(value)
    
    for key, value in form_data.multi_items():
        keys = re.findall(r"\w+", key)
        add(result, keys, value)
    return result

async def convert_request(request, dto):
    
    """
    Convert request to DTO
    """
    
    response = None
    data = await request.form()
    data = parse_nested_content(data)
    
    try:
        data = dto(**data)
    except ValidationError as e:
        response = json_response({
            "code": -1,
            "message": str(e)
        }, status_code=500)
    
    return response, data

def format_datetime(utc):
    """
    Форматирует дату
    """
    if utc is None:
        return None
    formatted_time = utc.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time

def get_datetime_from_utc(utc):
    """
    Получить дату из UTC
    """
    value = datetime.datetime.strptime(utc, "%Y-%m-%d %H:%M:%S").astimezone(datetime.timezone.utc)
    return value

def get_current_datetime():
    """
    Получить дату по UTC
    """
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    formatted_time = utc_now.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time


class Index:
    def __init__(self, key="id"):
        self.index = {}
        self.key = key
    
    def extend(self, items):
        for item in items:
            value = item[self.key]
            if not value in self.index:
                self.index[value] = []
            self.index[value].append(item)
    
    def getall(self, key):
        if not(key in self.index):
            return []
        return self.index[key]
    
    def get(self, key):
        result = self.getall(key)
        return result[0] if len(result) > 0 else None


class Helper:
    
    def json_encode(self, *args, **kwargs):
        return json_encode(*args, **kwargs)
    
    def json_decode(self, *args, **kwargs):
        return json_decode(*args, **kwargs)
    
    def json_response(self, *args, **kwargs):
        return json_response(*args, **kwargs)
    
    def format_datetime(self, *args, **kwargs):
        return format_datetime(*args, **kwargs)
    
    def get_datetime_from_utc(self, *args, **kwargs):
        return get_datetime_from_utc(*args, **kwargs)
    
    def get_current_datetime(self):
        return get_current_datetime()