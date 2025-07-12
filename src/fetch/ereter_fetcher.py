from common.utility import utility
from bs4 import BeautifulSoup
import os
import re
import asyncio

class ereter_data:
    # ファイルの場所
    _FILE_PATH = './dist/ereter'
    # ファイル名
    _FILES = {
        'list':'songs_list.json',
        'dict':'songs_dict.json',
        'last_modified': 'last_modified.txt'
    }
    # データ取得先
    _URLS= {
        'songs':'http://ereter.net/iidxsongs/analytics/combined/'
    }

    _VALUE_TITLE = ['ec_diff', 'hc_diff', 'exh_diff']

    def __init__(self, logging):
        self._logging = logging
        self._lastmodified_header = utility.init_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))
    
    # 難易度表取得
    async def update(self, textage_data):
        res = await utility.requests_get(self._URLS['songs'], self._lastmodified_header)
        if res.status_code == 200:
            # 200 OKの場合
            # htmlから情報を抽出
            soup = BeautifulSoup(res.read().decode('utf-8'), 'html.parser')
            tables = soup.find_all("table", class_="condensed")
            dct = self._table_json(tables[0], textage_data)
            # listとdictに成形
            lst = []
            for id in dct.keys():
                for difficulty in dct[id].keys():
                    elm = {
                        'id': int(id),
                        'difficulty': difficulty
                    }
                    for i in range(len(self._VALUE_TITLE)):
                        elm[self._VALUE_TITLE[i]] = dct[id][difficulty][self._VALUE_TITLE[i]]
                    lst.append(elm)
            # ファイルへ保存
            await asyncio.gather(
                utility.save_to_file(lst, os.path.join(self._FILE_PATH, self._FILES['list'])),
                utility.save_to_file(dct, os.path.join(self._FILE_PATH, self._FILES['dict']))
            )
            utility.update_last_modified(os.path.join(self._FILE_PATH, self._FILES['last_modified']))
            self._logging.info('Success in loading ereter.')
        elif res.status_code == 304:
            # 304 Not Modifiedの場合
            self._logging.info('ereter was not modified.')
        else:
            # その他の場合
            self._logging.error('Failed to fetch ereter.')
    
    # HTMLのtableからJSONに変換する
    def _table_json(self, table, textage_data):
        result = {}
        rows = table.find_all('tr')
        for row in rows:
            id = -2
            difficulty = ''
            title = 'null'
            cols = row.find_all('td', attrs={'sort-value': False})
            for col in cols:
                a = col.find('a')
                if a:
                    difficulty = a.find('span').get_text(strip=True)
                    title = a.get_text(strip=True)[:-len(difficulty)]
                    id = textage_data.get_song_id(title)
                    difficulty = difficulty[1]
            if id == -1:
                self._logging.error('[erter]:'+ title)
            elif id >= 0:
                id_str = str(id)
                if not id_str in result:
                    result[id_str] = {}
                if not difficulty in result[id_str]:
                    result[id_str][difficulty]= {}
                cols = row.find_all('td', attrs={'sort-value': True})
                for i in range(len(cols)):
                    value = float(cols[i].find('span').get_text(strip=True)[1:])
                    result[id_str][difficulty][self._VALUE_TITLE[i]] = value
        return result

    # 難易度文字を含むタイトルから難易度文字を削除したタイトルと難易度を取得
    def _get_title_and_difficulty(self, title):
        for d in self._TITLE_DIFFICULTY['intitle']:
            if d[0] in title:
                return title.replace(d[0], ''), d[1]
        return title, self._TITLE_DIFFICULTY['none']