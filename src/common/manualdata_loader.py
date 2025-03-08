from datetime import datetime, timezone, timedelta
import os
import json

class manualdata_loader:
    # ファイルの場所
    _FILE_PATH = './dist/manual'
    _FILE_NAMES = {
        'replace-characters': 'replace-characters.json',
        'special-bpm': 'special-bpm.json'
    }
    # クラス変数
    _TITLE_REPLACE_LIST = []
    _SPECIAL_BPM = []
    _isinitialized = False
    _logging = None

    # 特殊文字を置き換えたタイトルの取得
    @classmethod
    def normalize_title(cls, text):
        if not cls._isinitialized:
            cls._initialize()
        for l in cls._TITLE_REPLACE_LIST:
            text = text.replace(l[0], l[1])
        text = text.strip()
        return text

    # 難易度によってBPMが変わる曲のBPM取得
    @classmethod
    def get_bpm(cls, id, base_bpm):
        if not cls._isinitialized:
            cls._initialize()
        id_str = str(id)
        if id_str in cls._SPECIAL_BPM:
            bpm = {
                'sp': [base_bpm for i in range(5)],
                'dp': [base_bpm for i in range(5)]
            }
            if 'spb' in cls._SPECIAL_BPM[id_str]:
                bpm['sp'][0] = cls._SPECIAL_BPM[id_str]['spb']
            if 'spn' in cls._SPECIAL_BPM[id_str]:
                bpm['sp'][1] = cls._SPECIAL_BPM[id_str]['spn']
            if 'sph' in cls._SPECIAL_BPM[id_str]:
                bpm['sp'][2] = cls._SPECIAL_BPM[id_str]['sph']
            if 'spa' in cls._SPECIAL_BPM[id_str]:
                bpm['sp'][3] = cls._SPECIAL_BPM[id_str]['spa']
            if 'spl' in cls._SPECIAL_BPM[id_str]:
                bpm['sp'][4] = cls._SPECIAL_BPM[id_str]['spl']
            if 'dpb' in cls._SPECIAL_BPM[id_str]:
                bpm['dp'][0] = cls._SPECIAL_BPM[id_str]['dpb']
            if 'dpn' in cls._SPECIAL_BPM[id_str]:
                bpm['dp'][1] = cls._SPECIAL_BPM[id_str]['dpn']
            if 'dph' in cls._SPECIAL_BPM[id_str]:
                bpm['dp'][2] = cls._SPECIAL_BPM[id_str]['dph']
            if 'dpa' in cls._SPECIAL_BPM[id_str]:
                bpm['dp'][3] = cls._SPECIAL_BPM[id_str]['dpa']
            if 'dpl' in cls._SPECIAL_BPM[id_str]:
                bpm['dp'][4] = cls._SPECIAL_BPM[id_str]['dpl']
            return bpm
        else:
            return base_bpm
    
    # 初期化
    @classmethod
    def _initialize(cls):
        try:
            with open(os.path.join(cls._FILE_PATH, cls._FILE_NAMES['replace-characters']), mode='r', encoding='utf_8') as f:
                cls._TITLE_REPLACE_LIST = json.loads(f.read())
            with open(os.path.join(cls._FILE_PATH, cls._FILE_NAMES['special-bpm']), mode='r', encoding='utf_8') as f:
                cls._SPECIAL_BPM = json.loads(f.read())
            cls._isinitialized = True
        except:
            if cls._logging:
                cls._logging.error("Faild to load manual file.")
    
    # loggingのset
    @classmethod
    def set_logging(cls, logging):
        cls._logging = logging