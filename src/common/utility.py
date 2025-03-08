from datetime import datetime, timezone, timedelta
import requests

class utility:
    GMT = timezone(timedelta(hours=0))

    # UNIX基準時間の取得（If-Modified-Sinceの形式）
    @classmethod
    def get_unix_begin_time(cls):
        dt = datetime(1970, 1, 1, 0, 0, 0, 0, cls.GMT)
        return cls.datetime_to_string(dt)
    
    @classmethod
    # 現在時刻の取得（If-Modified-Sinceの形式）
    def get_now(cls):
        dt = datetime.now(cls.GMT)
        return cls.datetime_to_string(dt)
    
    @classmethod
    # 文字列からIf-Modified-Sinceの形式に変換
    def datetime_to_string(cls, dt):
        return datetime.strftime(dt, '%a, %d %b %Y %I:%M:%S GMT')

    @classmethod
    # asyncのrequest.get
    async def requests_get(cls, url, headers):
        return requests.get(url, headers)
