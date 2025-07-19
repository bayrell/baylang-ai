import json, starlette
from datetime import datetime, timezone

class JSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        self.helper = kwargs["helper"]
        del kwargs["helper"]
        json.JSONEncoder.__init__(self, *args, **kwargs)
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return self.helper.format_datetime(obj)
        return json.JSONEncoder.default(self, obj)

class JSONResponse(starlette.responses.JSONResponse):
    def __init__(self, *args, **kwargs):
        self.helper = kwargs["helper"]
        del kwargs["helper"]
        super().__init__(*args, **kwargs)
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            helper=self.helper,
            cls=JSONEncoder,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

class Helper:
    
    def json_encode(self, obj, indent=2):
        return json.dumps(obj, indent=indent, cls=JSONEncoder, ensure_ascii=False, helper=self)
    
    def json_response(self, value):
        response = JSONResponse(value, helper=self)
        return response
    
    def format_datetime(self, utc):
        """
        Форматирует дату
        """
        if utc is None:
            return None
        formatted_time = utc.strftime("%Y-%m-%d %H:%M:%S")
        return formatted_time
    
    
    def get_datetime_from_utc(self, utc):
        """
        Получить дату из UTC
        """
        value = datetime.datetime.strptime(utc, "%Y-%m-%d %H:%M:%S").astimezone(datetime.timezone.utc)
        return value
    
    
    def get_current_datetime(self):
        """
        Получить дату по UTC
        """
        utc_now = datetime.now(timezone.utc)
        formatted_time = utc_now.strftime("%Y-%m-%d %H:%M:%S")
        return formatted_time