import requests
import re
import os
from common.utility import utility
from common.manualdata_loader import manualdata_loader
import asyncio
import json
from logging import getLogger
import gzip

class textage_data:
    # ファイルの場所
    _FILE_PATH = './dist/textage'
    # ファイル名
    _OTHER_FILES = {
        'reverse-normalized-title': 'reverse-normalized-title.json',
        'normalized-title': 'normalized-title.json',
        'title': 'title.json',
        'reverse-textage-tag': 'reverse-textage-tag.json',
        'textage-tag': 'textage-tag.json',
        'last_modified': 'last_modified.json',
        'song-info':'song-info.json',
        'song-info-gz':'song-info.json.gz',
        'chart-info':'chart-info.json',
        'chart-info-gz':'chart-info.json.gz',
        'version': 'version.json',
        'all':'all.json',
        'all-gz':'all.json.gz',
        'debug': 'debug.txt'
    }
    # データ取得先
    _URLS={
        'titletbl': 'https://textage.cc/score/titletbl.js',
        'scrlist': 'https://textage.cc/score/scrlist.js',
        'datatbl': 'https://textage.cc/score/datatbl.js',
        'actbl': 'https://textage.cc/score/actbl.js'
    }
    # データ抽出のためのパターン
    _PATTERN_TBL = re.compile(r'tbl=((\[|{)(.|\s)*?(\]|}));')
    _PATTERN_TITLETBL_COMMENT = [
        re.compile(r"//'.*?\n"),
        re.compile(r'<br>'),
        re.compile(r'\t'),
        re.compile(r'<span.*?>'),
        re.compile(r'<\\/span>'),
        re.compile(r'\.fontcolor\(.*?\)')
    ]
    _PATTERN_OTHERTBL_COMMENT = [
        re.compile(r'//.*?\n'),
    ]
    _REPLACE_TITLETBL = [
        [re.compile(r':\[SS,'), ':[-1,'],
        [re.compile(r"'(.*?)'(.*?):(.*?)\[(.*?)\]"), r'"\1":[\4]']
    ]
    _REPLACE_ACTBL = [
        [re.compile(r'A'), '10'],
        [re.compile(r'B'), '11'],
        [re.compile(r'C'), '12'],
        [re.compile(r'D'), '13'],
        [re.compile(r'E'), '14'],
        [re.compile(r'F'), '15'],
        [re.compile(r"'(.*?)'(.*?):(.*?)\[(.*?)\]"), r'"\1":[\4]']
    ]
    _REPLACE_OTHERTBL = [
        [re.compile(r"'(.*?)'(.*?):(.*?)\[(.*?)\]"), r'"\1":[\4]']
    ]
    _BPM_SPLIT = '〜'

    # コンストラクタ
    def __init__(self, logging):
        # Loggingオブジェクトの引き継ぎ
        self._logging = logging
        self._isupdated = False
    
    # 初期化（非同期処理のためコンストラクタから分離）
    async def init(self):
        self._init_last_modified()
        await self._init_titletbl()

    # Last Modifiedの初期化
    def _init_last_modified(self):
        try:
            with open(os.path.join(self._FILE_PATH, self._OTHER_FILES['last_modified']), mode='r', encoding='utf_8') as f:
                last_modified = f.read()
                self._logging.debug('Load Last Modified: ' + last_modified)
                self._lastmodified_header ={
                    'If-Modified-Since': last_modified
                } 
        except:
            with open(os.path.join(self._FILE_PATH, self._OTHER_FILES['last_modified']), mode= "w", encoding='utf_8') as f:
                f.write(utility.get_unix_begin_time())
                self._logging.debug('Create Last Modified File.')
                self._lastmodified_header ={
                    'If-Modified-Since': utility.get_unix_begin_time()
                } 
        
    # titletbl空のデータ取得
    async def _init_titletbl(self):
        self._logging.debug('init titletbl')
        # ファイル読み込み
        results = await asyncio.gather(
            self._load_from_file('reverse-normalized-title'),
            self._load_from_file('reverse-textage-tag'),
            self._load_from_file('all'),
            self._load_from_file('normalized-title'),
            self._load_from_file('title'),
            self._load_from_file('textage-tag'),
            self._load_from_file('song-info'),
            self._load_from_file('chart-info')
        )
        self._reversed_normalized_title_dict = results[0]
        self._reverse_textage_tag_dict = results[1]
        self._all_dict = results[2]
        self._normalized_title_dict = results[3]
        self._title_dict = results[4]
        self._textage_tag_dict = results[5]
        self._song_info_dict = results[6]
        self._chart_info_dict = results[7]
        # Fetch
        results = await asyncio.gather(
            utility.requests_get(self._URLS['titletbl'], headers=self._lastmodified_header),
            utility.requests_get(self._URLS['actbl'], headers=self._lastmodified_header)
        )
        titletbl_res = results[0]
        actbl_res = results[1]
        # AC/INF収録情報を取得する
        if actbl_res.status_code == requests.codes.ok:
            # 200 OKの場合
            actblRaw = self._res_to_json(actbl_res, self._PATTERN_TBL, self._PATTERN_OTHERTBL_COMMENT, self._REPLACE_ACTBL)
            if actblRaw:
                self._logging.info('Success in loading actbl.')
                self._isupdated = True
            else:
                self._logging.error('Faild to find JSON from actbl.')
        elif actbl_res.status_code == requests.codes.not_modified:
            # 304 Not Modifiedの場合
            actblRaw = None
            self._logging.info('actbl was not modified.')
        else:
            # その他の場合
            actblRaw = None
            self._logging.error('Failed to fetch actbl.')

        # titletblのフェッチ結果に応じて登録処理を分ける
        if titletbl_res.status_code == requests.codes.ok:
            # 200 OKの場合
            tblRaw = self._res_to_json(titletbl_res, self._PATTERN_TBL, self._PATTERN_TITLETBL_COMMENT, self._REPLACE_TITLETBL)
            if tblRaw:
                self._isupdated = True
                # JSONの取得に成功したらデータを成形
                for key in tblRaw.keys():
                    # バージョンの取得（CSonlyを-1, 1stを0, Subを1にするよう変更）
                    if tblRaw[key][0] == -1:
                        version = 1
                    elif tblRaw[key][0] == 0:
                        version = -1
                    elif tblRaw[key][0] == 1:
                        version = 0
                    else:
                        version = tblRaw[key][0]
                    # その他情報の取得
                    id = tblRaw[key][1]
                    id_str = str(id)
                    genre = tblRaw[key][3]
                    artist = tblRaw[key][4]
                    # サブタイトルを持つ場合は結合
                    if len(tblRaw[key]) >= 7:
                        title = tblRaw[key][5] + tblRaw[key][6]
                    else:
                        title = tblRaw[key][5]
                    # タイトルの特殊文字置き換え
                    normalized_title = manualdata_loader.normalize_title(title)
                    # actblをフェッチしている場合はフェッチ結果からデータを抽出する
                    if actblRaw:
                        # actblに存在しないデータならばスキップ
                        if not key in actblRaw:
                            self._logging.debug(key +  ' is not found in actbl')
                            continue
                        in_ac = bool(actblRaw[key][0] & 1)
                        in_inf = bool(actblRaw[key][0] & 2)
                        level = {
                            'sp': [0]*5,
                            'dp': [0]*5
                        }
                        for i in range(5):
                            level['sp'][i] = actblRaw[key][i * 2 + 3]
                            level['dp'][i] = actblRaw[key][i * 2 + 13]
                    else:
                        if not id_str in self._chart_info_dict:
                            self._logging.debug(key +  ' is not found in actbl.')
                            continue
                        in_ac = self._chart_info_dict[id_str]['in_ac']
                        in_inf = self._chart_info_dict[id_str]['in_inf']
                        level = self._chart_info_dict[id_str]['level']
                    if '†LEGGENDARIA' in title:
                        self._logging.debug(key + ' is leggendaria.')
                        # †LEGGENDARIA用の曲情報はスキップする
                        continue
                    else:
                        # 曲名が衝突する場合、ACやINFに収録されている方を優先する
                        if normalized_title in self._reversed_normalized_title_dict and self._reversed_normalized_title_dict[normalized_title] != id:
                            the_priority = 0
                            other_priority = 0
                            other_id = self._reversed_normalized_title_dict[normalized_title]
                            other_key = self._textage_tag_dict[str(other_id)]
                            if in_ac:
                                the_priority += 2
                            if in_inf:
                                the_priority += 1
                            if self._chart_info_dict[str(other_id)]['in_ac']:
                                other_priority += 2
                            if self._chart_info_dict[str(other_id)]['in_inf']:
                                other_priority += 1
                            # 優先度比較
                            if the_priority > other_priority:
                                self._reversed_normalized_title_dict[normalized_title] = id
                                self._logging.debug(other_key + ' is same title with ' + key)
                            elif the_priority < other_priority:
                                self._logging.debug(key + ' is same title with ' + other_key)
                                continue
                            else:
                                # 優先度が同じ場合はidが大きい方を優先
                                if id > other_id:
                                    self._reversed_normalized_title_dict[normalized_title] = id
                                    self._logging.debug(other_key + ' is same title with ' + key)
                                else:
                                    self._logging.debug(key + ' is same title with ' + other_key)
                                    continue
                        else:
                            self._reversed_normalized_title_dict[normalized_title] = id
                        # その他データを成形して保持
                        self._reverse_textage_tag_dict[key] = id
                        self._normalized_title_dict[id_str] = normalized_title
                        self._title_dict[id_str] = title
                        self._textage_tag_dict[id_str] = key
                        if not id_str in self._song_info_dict:
                            self._song_info_dict[id_str] = {}
                        self._song_info_dict[id_str]['version'] = version
                        self._song_info_dict[id_str]['genre'] = genre
                        self._song_info_dict[id_str]['artist'] = artist
                        if not id_str in self._chart_info_dict:
                            self._chart_info_dict[id_str] = {}
                        self._chart_info_dict[id_str]['in_ac'] = in_ac
                        self._chart_info_dict[id_str]['in_ac'] = in_ac
                        self._chart_info_dict[id_str]['in_inf'] = in_inf
                        self._chart_info_dict[id_str]['level'] = level
                        if not id_str in self._all_dict:
                            self._all_dict[id_str] = {}
                        self._all_dict[id_str]['title'] = title
                        self._all_dict[id_str]['normalized_title'] = normalized_title
                        self._all_dict[id_str]['textage_tag'] = key
                        self._all_dict[id_str]['version'] = version
                        self._all_dict[id_str]['genre'] = genre
                        self._all_dict[id_str]['artist'] = artist
                        self._all_dict[id_str]['in_ac'] = in_ac
                        self._all_dict[id_str]['in_inf'] = in_inf
                        self._all_dict[id_str]['level'] = level
                self._logging.info('Success in loading titletbl.')
                return
            else:
                # レスポンスからJSONを取り出せない場合
                self._logging.error('Faild to find JSON from titletbl.')
        elif titletbl_res.status_code == requests.codes.not_modified:
            # 304 Not Modifiedの場合
            self._logging.info('Titletbl was not modified.')
        else:
            # その他の場合
            self._logging.error('Failed to fetch titletbl.')
        # titletblはフェッチ出来なかったがacttblフェッチした場合の処理
        if actblRaw:
            for key in self._reverse_textage_tag_dict.keys():
                # actblに存在しないデータならばスキップ
                if not key in actblRaw:
                    self._logging.debug(key +  'is not found in actbl')
                    continue
                in_ac = bool(actblRaw[key][0] & 1)
                in_inf = bool(actblRaw[key][0] & 2)
                level = {
                    'sp': [0] * 5,
                    'dp': [0]* 5 
                }
                for i in range(5):
                    level['sp'][i] = actblRaw[key][i * 2 + 3]
                    level['dp'][i] = actblRaw[key][i * 2 + 13]
                id = self._reverse_textage_tag_dict[key]
                id_str = str(id)
                if not id_str in self._chart_info_dict:
                    self._chart_info_dict[id_str] = {}
                self._chart_info_dict[id_str]['in_ac'] = in_ac
                self._chart_info_dict[id_str]['in_ac'] = in_ac
                self._chart_info_dict[id_str]['in_inf'] = in_inf
                self._chart_info_dict[id_str]['level'] = level
                if not id in self._all_dict:
                    self._all_dict[id_str] = {}
                self._all_dict[id_str]['in_ac'] = in_ac
                self._all_dict[id_str]['in_inf'] = in_inf
                self._all_dict[id_str]['level'] = level

    # scrlistの取得
    async def _fetch_scrlist(self):
        self._logging.debug('init scrtbl')
        res = await utility.requests_get(self._URLS['scrlist'], headers=self._lastmodified_header)
        if res.status_code == requests.codes.ok:
            # 200 OKの場合
            tblRaw = self._res_to_json(res, self._PATTERN_TBL, self._PATTERN_OTHERTBL_COMMENT,self._REPLACE_OTHERTBL)
            if tblRaw:
                self._isupdated = True
                tblRaw[0] = tblRaw[1]
                tblRaw[1] = 'substream'
                self._version_dict = {
                    'version': tblRaw
                }
                self._logging.info('Success in loading scrlist.')
                return
        elif res.status_code == requests.codes.not_modified:
            # 304 Not Modifiedの場合
            self._logging.info('Scrtbl was not modified.')
        else:
            # その他の場合
            self._logging.error('Failed to fetch scrtbl.')
        self._version_dict = await self._load_from_file('version')

    # datatblの取得
    async def _fetch_datatbl(self):
        self._logging.debug('init datatbl')
        res = await utility.requests_get(self._URLS['datatbl'], headers=self._lastmodified_header)
        if res.status_code == requests.codes.ok:
            # 200 OKの場合
            tblRaw = self._res_to_json(res, self._PATTERN_TBL, self._PATTERN_OTHERTBL_COMMENT, self._REPLACE_OTHERTBL)
            if tblRaw:
                self._isupdated = True
                # JSONの取得に成功したらデータを成形
                for key in tblRaw.keys():
                    # titletblに存在しないtagならばスキップ
                    if not key in self._reverse_textage_tag_dict:
                        continue
                    id = self._reverse_textage_tag_dict[key]
                    id_str = str(id)
                    # BPMを取得
                    bpm = tblRaw[key][11]
                    if self._BPM_SPLIT in bpm:
                        bpms = bpm.split(self._BPM_SPLIT)
                        bpm = [ int(bpms[0]), int(bpms[1]) ]
                    else:
                        bpm = int(bpm)
                    bpm = manualdata_loader.get_bpm(id, bpm)
                    # ノーツ数を取得
                    notes = {
                        'sp': [0] * 5,
                        'dp': [0]* 5 
                    }
                    for i in range(5):
                        notes['sp'][i] = tblRaw[key][i + 1]
                        notes['dp'][i] = tblRaw[key][i + 6]
                    self._chart_info_dict[id_str]['bpm'] = bpm
                    self._chart_info_dict[id_str]['notes'] = notes
                    self._all_dict[id_str]['bpm'] = bpm
                    self._all_dict[id_str]['notes'] = notes
                self._logging.info('Success in loading datatbl.')
        elif res.status_code == requests.codes.not_modified:
            # 304 Not Modifiedの場合
            self._logging.info('Datatbl was not modified.')
        else:
            # その他の場合
            self._logging.error('Failed to fetch datatbl.')
    
    # ファイルからロード
    async def _load_from_file(self, file_id):
        try:
            with open(os.path.join(self._FILE_PATH, self._OTHER_FILES[file_id]), mode='r', encoding='utf_8') as f:
                return json.loads(f.read())
        except:
            self._logging.error('Failed to load JSON from file:' + os.path.join(self._FILE_PATH, self._OTHER_FILES[file_id]))
            return {}
        
    # dictをJSONファイルとして出力する
    async def _save_to_file(self, data, file_id):
        try:
            with open(os.path.join(self._FILE_PATH, self._OTHER_FILES[file_id]), mode='w', encoding='utf_8') as f:
                f.write(json.dumps(data, ensure_ascii=False, indent='\t', sort_keys=True, separators=(',', ': ')))
        except Exception as e:
            self._logging.error('Failed to save file:' + os.path.join(self._FILE_PATH, self._OTHER_FILES[file_id]))
            raise e

    # dictをJSONファイルとして出力する
    async def _save_to_file_gz(self, data, file_id):
        try:
            with open(os.path.join(self._FILE_PATH, self._OTHER_FILES[file_id]), mode='wb') as f:
                text = json.dumps(data)
                f.write(gzip.compress(bytes(text, 'utf_8')))
        except Exception as e:
            self._logging.error('Failed to save file:' + os.path.join(self._FILE_PATH, self._OTHER_FILES[file_id]))
            raise e
        
    # Last Modifiedの更新
    def _update_last_modified(self):
        with open(os.path.join(self._FILE_PATH, self._OTHER_FILES['last_modified']), mode= "w", encoding='utf_8') as f:
            now = utility.get_now()
            f.write(now)
            self._logging.debug('Update Last Modified File: ' + str(utility.get_now()))
    
    # レスポンス(Javascript)からデータを抽出
    def _res_to_json(self, res, tbl_pattern, comment_pattern, replace_list):
        # JSONとなっているテーブルを抽出
        res.encoding = "shift_jis"
        match = tbl_pattern.findall(res.text)
        text = match[0][0]
        # レスポンスからJSONとして抽出
        # コメント等余計なものを置き換え
        for pattern in comment_pattern:
            text = pattern.sub('', text)
        # 置き換えリストの文字を置き換え
        for r in replace_list:
            text = r[0].sub(r[1], text)
        result = json.loads(text)
        # ダミーがある場合は削除
        if '__dmy__' in result:
            del result['__dmy__']
        return result
        #except Exception as e:
        #    self._logging.error('Faild to find JSON from response.')
        #    self._logging.error(str(e))
        #    return {}
    
    # 情報のアップデート
    async def update(self):
        await asyncio.gather(
            self._fetch_scrlist(),
            self._fetch_datatbl()
        )
        # ファイルに保存
        await asyncio.gather(
            self._save_to_file(self._reversed_normalized_title_dict, 'reverse-normalized-title'),
            self._save_to_file(self._reverse_textage_tag_dict, 'reverse-textage-tag'),
            self._save_to_file(self._normalized_title_dict, 'normalized-title'),
            self._save_to_file(self._title_dict, 'title'),
            self._save_to_file(self._textage_tag_dict, 'textage-tag'),
            self._save_to_file(self._song_info_dict, 'song-info'),
            self._save_to_file_gz(self._song_info_dict, 'song-info-gz'),
            self._save_to_file(self._chart_info_dict, 'chart-info'),
            self._save_to_file_gz(self._chart_info_dict, 'chart-info-gz'),
            self._save_to_file(self._version_dict, 'version'),
            self._save_to_file(self._all_dict, 'all'),
            self._save_to_file_gz(self._all_dict, 'all-gz')
        )
        if self._isupdated:
            self._update_last_modified()
        else:
            self._logging.info('No Change.')

    # 曲名からidを取得する
    def get_song_id(self, title):
        title = manualdata_loader.normalize_title(title)
        if title in self._reversed_normalized_title_dict:
            return self._reversed_normalized_title_dict[title]
        else:
            self._logging.error(title + ' is not found.')
            return -1
        
            

