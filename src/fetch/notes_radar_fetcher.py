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
        'last_modified': 'last_modified.txt',
        'category_genre': 'category/category.json',
        'category_sp_dict': 'category/sp_dict.json',
        'category_sp_list': 'category/sp_list.json',
        'category_dp_dict': 'category/dp_dict.json',
        'category_dp_list': 'category/dp_list.json'
    }
    # データ取得先
    _URLS= {
        'songs':'https://bm2dx.com/IIDX/notes_radar/notes_radar_data.json.gz'
    }
    # Skipする曲
    _SKIP_MID = [
        81502,
    ]

    # 新形式のキーとモードの対応
    _MODES = {
        'radar_sp': 'SP',
        'radar_dp': 'DP',
    }
    # 各行の値の列番号
    _VALUE_TYPES = {
        'NOTES': 4,
        'CHORD': 5,
        'PEAK': 6,
        'CHARGE': 7,
        'SCRATCH': 8,
        'SOFLAN': 9,
    }
    # カテゴリ(最大値のジャンル)の並び
    _CATEGORY_GENRES = [
        'CHARGE',
        'CHORD',
        'NOTES',
        'PEAK',
        'SCRATCH',
        'SOFLAN'
    ]
    # 難易度のindexと表記の対応
    _DIFFICULTIES = ['B', 'N', 'H', 'A', 'L']

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
            for key, mode in self._MODES.items():
                self._register_songlist(json_data[key], mode)
            sp_category_dict, sp_category_list = self._create_category(self._songs['SP'])
            dp_category_dict, dp_category_list = self._create_category(self._songs['DP'])
        # ファイルへ保存
            os.makedirs(os.path.join(self._FILE_PATH, 'category'), exist_ok=True)
            await asyncio.gather(
                utility.save_to_file(self._CATEGORY_GENRES, os.path.join(self._FILE_PATH, self._FILES['category_genre'])),
                utility.save_to_file(sp_category_dict, os.path.join(self._FILE_PATH, self._FILES['category_sp_dict'])),
                utility.save_to_file(sp_category_list, os.path.join(self._FILE_PATH, self._FILES['category_sp_list'])),
                utility.save_to_file(dp_category_dict, os.path.join(self._FILE_PATH, self._FILES['category_dp_dict'])),
                utility.save_to_file(dp_category_list, os.path.join(self._FILE_PATH, self._FILES['category_dp_list'])),
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
    # 各行: [mid, 難易度, レベル, ノーツ数, NOTES, CHORD, PEAK, CHARGE, SCRATCH, SOFLAN]
    def _register_songlist(self, raw_list, mode):
        if not mode in self._songs:
            self._songs[mode] = {}
        for song in raw_list:
            mid = song[0]
            difficulty = song[1]
            str_id = str(self._mids[mid])
            if not str_id in self._songs[mode]:
                self._songs[mode][str_id] = {'notes': [0] * 5}
                for value_type in self._VALUE_TYPES:
                    self._songs[mode][str_id][value_type] = [0.0] * 5
            for value_type, index in self._VALUE_TYPES.items():
                self._songs[mode][str_id][value_type][difficulty] = song[index]
            self._songs[mode][str_id]['notes'][difficulty] = song[3]

    # カテゴリ(ノーツレーダー値が最大のジャンル)の作成
    def _create_category(self, songs):
        category_dict = {}
        category_list = []
        for str_id, song in songs.items():
            # 曲が特定できないものはスキップ
            if str_id == '-1':
                continue
            for index, difficulty in enumerate(self._DIFFICULTIES):
                values = [song[genre][index] for genre in self._CATEGORY_GENRES]
                # 値が全て0の譜面はスキップ
                if max(values) <= 0:
                    continue
                # 同値の場合はcategory.jsonで先のジャンルを優先
                genre = values.index(max(values))
                if not str_id in category_dict:
                    category_dict[str_id] = {}
                category_dict[str_id][difficulty] = genre
                category_list.append({
                    'genre': genre,
                    'difficulty': difficulty,
                    'id': int(str_id)
                })
        return category_dict, category_list
