from common.utility import utility
import os
import asyncio

class notes_radar_data:
    # ファイルの場所
    _FILE_PATH = './dist/notes_radar'
    # ファイル名
    _FILES = {
        'sp':'sp.json',
        'sp-gz':'sp.json.gz',
        'dp':'dp.json',
        'dp-gz': 'dp.json.gz',
        'last_modified': 'last_modified.txt'
    }
    # データ取得先
    _URLS= {
        'songs':'https://bm2dx.com/IIDX/notes_radar/notes_radar.json.gz'
    }
    # Skipする曲
    _SKIP_MID = [
        81502,
    ]

    # コンストラクタ
    def __init__(self, logging):
        # Loggingオブジェクトの引き継ぎ
        self._logging = logging
        self._lastmodified_header = utility.init_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))
        self._mids = {}
        self._songs = {}

    # 難易度表取得
    async def update(self, textage_data):
        res = await utility.requests_get(self._URLS['songs'], self._lastmodified_header)
        # 200 OKの場合
        if res.status_code == 200:
            json_data = utility.load_from_gz(res.read())
            self._register_mid(json_data['mid'], textage_data)
            for mode in json_data['notes_radar'].keys():
                for value_type in json_data['notes_radar'][mode].keys():
                    self._register_songlist(json_data['notes_radar'][mode][value_type], mode, value_type)
        # ファイルへ保存
            await asyncio.gather(
                utility.save_to_file(self._songs['SP'] , os.path.join(self._FILE_PATH, self._FILES['sp'])),
                utility.save_to_file_gz(self._songs['SP'] , os.path.join(self._FILE_PATH, self._FILES['sp-gz'])),
                utility.save_to_file(self._songs['DP'] , os.path.join(self._FILE_PATH, self._FILES['dp'])),
                utility.save_to_file_gz(self._songs['DP'] , os.path.join(self._FILE_PATH, self._FILES['dp-gz']))
            )
            utility.update_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))
            self._logging.info('Success in loading konami.')
        elif res.status_code == 304:
            # 304 Not Modifiedの場合
            self._logging.info('notes_radar was not modified.')
        else:
            # その他の場合
            self._logging.error('Failed to fetch notes_radar.')
    
    # midとidの対応の登録
    def _register_mid(self, mid_dict, textage_data):
        for mid in mid_dict.keys():
            if not textage_data.is_contain_song(mid_dict[mid]):
                if int(mid) in self._SKIP_MID:
                    continue
            id = textage_data.get_song_id(mid_dict[mid])
            if id == -1:
                self._logging.error('[notes_radar]:'+ mid_dict[mid])
            self._mids[mid] = id

    # 曲情報の登録
    def _register_songlist(self, raw_list, mode, value_type):
        if not mode in self._songs:
            self._songs[mode] = {}
        for song in raw_list:
            mid = song['mid']
            difficulty = song['difficult']
            id = self._mids[mid]
            str_id = str(id)
            if not str_id in self._songs[mode]:
                self._songs[mode][str_id] = {
                    'notes': [0] * 5
                }
            if not value_type in self._songs[mode][str_id]:
                self._songs[mode][str_id][value_type] = [0.0] * 5
            self._songs[mode][str_id][value_type][difficulty] = song['value']
            self._songs[mode][str_id]['notes'][difficulty] = song['note']
            