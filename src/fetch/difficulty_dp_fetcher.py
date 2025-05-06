from common.utility import utility
from bs4 import BeautifulSoup
import os
import asyncio
import requests
import re

class difficulty_dp_data:
    # ファイルの場所
    _FILE_PATH = './dist/difficulty/dp'
    # ファイル名
    _FILES = {
        'list':'songs_list.json',
        'dict':'songs_dict.json',
        'last_modified': 'last_modified.txt'
    }
    # データ取得先
    _URLS= {
        'songs':'https://zasa.sakura.ne.jp/dp/run.php'
    }
    # 正規表現パターン
    _PATTERN_DIFFICULTY = re.compile(r'[0-9]+.[0-9]+')
    _PATTERN_SNJID = re.compile(r'id=([0-9]+-[0-9]+-[0-9]+)')

    _DIFFICULTY_LIST = ['H', 'A', 'L']


    # コンストラクタ
    def __init__(self, logging):
        # Loggingオブジェクトの引き継ぎ
        self._logging = logging
        self._lastmodified_header = utility.init_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))
    
    # 曲一覧取得
    async def update(self, textage_data):
        res = await utility.requests_get(self._URLS['songs'], self._lastmodified_header)
        if res.status_code == requests.codes.ok:
            # 200 OKの場合
            # htmlから情報を抽出
            soup = BeautifulSoup(res.text, 'html.parser')
            dct = self._html_to_json(soup, textage_data)
            # データを成形
            lst = []
            for id in dct.keys():
                for difficulty in dct[id].keys():
                    lst.append({
                        'id': id,
                        'difficulty': difficulty,
                        'value': dct[id][difficulty]['value'],
                        'snj_id': dct[id][difficulty]['snj_id']
                    })
            # ファイルへ保存
            await asyncio.gather(
                utility.save_to_file(lst , os.path.join(self._FILE_PATH, self._FILES['list'])),
                utility.save_to_file(dct, os.path.join(self._FILE_PATH, self._FILES['dict']))
            )
            utility.update_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))
            self._logging.info('Success in loading ＳＮＪ＠ＫＭＺＳ.')
        elif res.status_code == requests.codes.not_modified:
            # 304 Not Modifiedの場合
            self._logging.info('ＳＮＪ＠ＫＭＺＳ was not modified.')
        else:
            # その他の場合
            self._logging.error('Failed to fetch ＳＮＪ＠ＫＭＺＳ.')


    # HTMLから曲情報を抽出する
    def _html_to_json(self, html, textage_data):
        table = html.find('table', class_="run")
        rows = table.find_all('tr')
        result = {}
        # tableからデータを抽出
        for row in rows:
            cols = row.find_all('td')
            if len(cols) == 4:
                title = cols[3].get_text(strip=True)
                id = textage_data.get_song_id(title)
                if id == -1:
                    self._logging.error('[dp]:'+ title)
                row_data = {}
                for i in range(3):
                    link = cols[i].find('a')
                    if not link:
                        continue
                    span = link.find('span')
                    m1 = self._PATTERN_DIFFICULTY.search(span.get_text(strip=True))
                    m2 = self._PATTERN_SNJID.findall(link.attrs['href'])
                    if m1 and m2:
                        value = float(m1.group())
                        snj_id = m2[0]
                        row_data[self._DIFFICULTY_LIST[i]] = {
                            'value': value,
                            'snj_id': snj_id
                        }
                result[id] = row_data
        return result


 