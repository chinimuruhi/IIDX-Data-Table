from common.utility import utility
from bs4 import BeautifulSoup
import os
import asyncio

class konami_data:
    # ファイルの場所
    _FILE_PATH = './dist/konami'
    # ファイル名
    _FILES = {
        'song_to_label':'song_to_label.json',
        'label_to_songs':'label_to_songs.json',
        'label': 'label.json',
        'last_modified': 'last_modified.txt'
    }
    # データ取得先
    _URLS= {
        'songs':'https://p.eagate.573.jp/game/infinitas/2/music/index.html'
    }
    _NORMAL_MUSIC_LIST = [
        'default',
        'djp',
        'bit',
    ]
    _PACK_MUSIC_LIST = 'pac'
    _LEGGENDARIA_MUSIC_LIST = 'leg'
    _PACK_PREFIX = 'beatmania IIDX INFINITAS '


    # コンストラクタ
    def __init__(self, logging):
        # Loggingオブジェクトの引き継ぎ
        self._logging = logging
        self._lastmodified_header = utility.init_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))
        self._labels = []
        self._labels_pack_index = 0
    
    # 曲一覧取得
    async def update(self, textage_data):
        res = await utility.requests_get(self._URLS['songs'], self._lastmodified_header)
        if res.status_code == 200:
            # 200 OKの場合
            # htmlから情報を抽出
            soup = BeautifulSoup(res.read().decode('utf-8'), 'html.parser')
            data = self._html_to_json(soup, textage_data)
            # データを成形
            song_to_label = {}
            label_to_songs = {}
            for id in data.keys():
                id_str = id
                label = data[id]['label']
                label_str = label
                if 'in_leggendaria' in data[id]:
                    in_leggendaria = data[id]['in_leggendaria']
                else:
                    in_leggendaria = False
                if not id_str in song_to_label:
                    song_to_label[id_str] = {}
                song_to_label[id_str]['label'] = label
                song_to_label[id_str]['in_leggendaria'] = in_leggendaria
                if not label_str in label_to_songs:
                    label_to_songs[label_str] = []
                label_to_songs[label_str].append(
                    {
                        'id': id,
                        'in_leggendaria': in_leggendaria
                    }
                )
            # ファイルへ保存
            await asyncio.gather(
                utility.save_to_file(song_to_label , os.path.join(self._FILE_PATH, self._FILES['song_to_label'])),
                utility.save_to_file(label_to_songs, os.path.join(self._FILE_PATH, self._FILES['label_to_songs'])),
                utility.save_to_file(self._labels, os.path.join(self._FILE_PATH, self._FILES['label']))
            )
            utility.update_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))
            self._logging.info('Success in loading konami.')
        elif res.status_code == 304:
            # 304 Not Modifiedの場合
            self._logging.info('konami was not modified.')
        else:
            # その他の場合
            self._logging.error('Failed to fetch konami.')

    # HTMLから曲情報を抽出する
    def _html_to_json(self, html, textage_data):
        music_list_divs = html.find_all('div', id='music-list')
        result = {}
        for music_list_div in music_list_divs:
            # 解禁種別を取得
            label = self._get_label(music_list_div)
            if label:
                if label == self._PACK_MUSIC_LIST:
                    # パック解禁の場合
                    elements = music_list_div.find_all(['div', 'table'])
                    label = ''
                    for element in elements:
                        if element.name == 'div':
                            label = element.find('strong').get_text(strip=True)
                            label = label.replace(self._PACK_PREFIX, '')
                        elif element.name == 'table':
                            songs = self._table_to_music_id_list(element, textage_data)
                            for id in songs:
                                if not id in result:
                                    result[id] = {}
                                result[id]['label'] = self._get_label_id(label, True)
                elif label == self._LEGGENDARIA_MUSIC_LIST:
                    # LEGGENDARIAの場合
                    songs = self._table_to_music_id_list(music_list_div.find('table'), textage_data)
                    for id in songs:
                        if not id in result:
                            result[id] = {}
                        result[id]['in_leggendaria'] = True
                else:
                    # その他の場合
                    songs = self._table_to_music_id_list(music_list_div.find('table'), textage_data)
                    for id in songs:
                        if not id in result:
                            result[id] = {}
                        result[id]['label'] = self._get_label_id(label, False)
        return result
        
    # music-listのdivから解禁種別を取得する
    def _get_label(self, music_list_div):
        # normal
        for label in self._NORMAL_MUSIC_LIST:
            cat_div = music_list_div.find('div', id=label)
            if cat_div:
                label_name = cat_div.find('strong').get_text(strip=True)
                return label_name
        # pack
        pack = music_list_div.find('div', id=self._PACK_MUSIC_LIST)
        if pack:
            return self._PACK_MUSIC_LIST
        # leg
        leg = music_list_div.find('div', id=self._LEGGENDARIA_MUSIC_LIST)
        if leg:
            return self._LEGGENDARIA_MUSIC_LIST
        return None


    # ラベル名からラベルidを取得する
    def _get_label_id(self, label, is_pack):
        if not label in self._labels:
            self._labels.insert(self._labels_pack_index, label)
            if not is_pack:
                self._labels_pack_index += 1
        return self._labels.index(label)

    
    # tableから曲のIDを抽出する
    def _table_to_music_id_list(self, table, textage_data):
        rows = table.find_all('tr')
        result = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) == 2:
                title = cols[0].get_text(strip=True)
                id = textage_data.get_song_id(title)
                if id == -1:
                    self._logging.error('[konami]:'+ title)
                result.append(id)
        return result