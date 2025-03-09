from datetime import datetime, timezone, timedelta
import requests
import os
import json
import gzip

class utility:
    # クラス変数
    GMT = timezone(timedelta(hours=0))
    _logging = None

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
    # Last Modifiedの初期化
    def init_last_modified(cls, file_path):
        try:
            with open(file_path, mode='r', encoding='utf_8') as f:
                last_modified = f.read()
                header = {
                    'If-Modified-Since': last_modified
                } 
        except:
            with open(file_path, mode= "w", encoding='utf_8') as f:
                f.write(cls.get_unix_begin_time())
                header = {
                    'If-Modified-Since': cls.get_unix_begin_time()
                } 
        return header
    
    @classmethod
    # Last Modifiedの更新
    def update_last_modified(self, file_path):
        with open(file_path, mode= "w", encoding='utf_8') as f:
            now = utility.get_now()
            f.write(now)

    @classmethod
    # ファイルからJSONをロード
    async def load_from_file(cls, file_path):
        try:
            with open(file_path, mode='r', encoding='utf_8') as f:
                return json.loads(f.read())
        except:
            if cls._logging:
                cls._logging.error('Failed to load JSON from file:' + file_path)
            return {}

    @classmethod    
    # pythonオブジェクトをJSONファイルとして出力する
    async def save_to_file(cls, data, file_path):
        try:
            with open(file_path, mode='w', encoding='utf_8') as f:
                f.write(json.dumps(data, ensure_ascii=False, indent='\t', sort_keys=True, separators=(',', ': ')))
        except Exception as e:
            if cls._logging:
                cls._logging.error('Failed to save file:' + file_path)
            else:
                raise e

    @classmethod
    # pythonオブジェクトをgz圧縮されたJSONファイルとして出力する
    async def save_to_file_gz(cls, data, file_path):
        try:
            with open(file_path, mode='wb') as f:
                text = json.dumps(data, ensure_ascii=False, indent='\t', sort_keys=True, separators=(',', ': '))
                f.write(gzip.compress(bytes(text, 'utf_8')))
        except Exception as e:
            if cls._logging:
                cls._logging.error('Failed to save file:' + file_path)
            else:
                raise e

    @classmethod
    # asyncのrequest.get
    async def requests_get(cls, url, headers):
        return requests.get(url, headers)
    
    # loggingのset
    @classmethod
    def set_logging(cls, logging):
        cls._logging = logging
