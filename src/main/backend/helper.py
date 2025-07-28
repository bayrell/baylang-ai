import json, starlette
from datetime import datetime, timezone

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
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

def json_response(value):
    response = JSONResponse(value)
    return response

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
    utc_now = datetime.now(timezone.utc)
    formatted_time = utc_now.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time


class Index:
    def __init__(self, key="id"):
        self.index = {}
    
    def extend(self, items):
        for item in items:
            value = item[key]
            if not value in self.index:
                self.index = []
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