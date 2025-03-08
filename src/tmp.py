import requests
import urllib.request
import gzip
import gspread
import os

with open('./dist/iidx11.io.json', mode='w') as f:
    # spred_sheet取得
    gc = gspread.api_key(os.getenv('GOOGLE_SHEET_KEY'))
    # https://docs.google.com/spreadsheets/d/1e7gdUmBk3zUGSxVGC--8p6w2TIWMLBcLzOcmWoeOx6Y/edit?gid=1585306050#gid=1585306050
    sh = gc.open_by_key('1e7gdUmBk3zUGSxVGC--8p6w2TIWMLBcLzOcmWoeOx6Y')
    normal = sh.worksheet('ノーマルゲージ').get_all_values()
    hard = sh.worksheet('ハードゲージ').get_all_values()
    f.write(str(normal) + str(hard))

with open('./dist/iidx-sp12.github.io.json', mode='w') as f:
    r = requests.get('https://iidx-sp12.github.io/songs.json')
    f.write(r.text)

with open('./dist/bpim.msqkn310.workers.dev.json', mode='w') as f:
    r = requests.get('https://bpim.msqkn310.workers.dev/release')
    f.write(r.text)

with open('./dist/cpi.makecir.com.json', mode='w') as f:
    r = requests.get('https://cpi.makecir.com/scores')
    f.write(r.text)

with open('./dist/textage.cc.json', mode='w') as f:
    r = requests.get('https://textage.cc/score/titletbl.js')
    f.write(r.text)

with open('./dist/bm2dx.com.json', mode='w') as f:
    with urllib.request.urlopen('https://bm2dx.com/IIDX/notes_radar/notes_radar.json.gz') as res:
        dec = gzip.GzipFile(fileobj=res)
        f.write(dec.read().decode("utf-8"))

with open('./dist/zasa.sakura.ne.jp.json', mode='w') as f:
    r = requests.get('https://zasa.sakura.ne.jp/dp/run.php')
    f.write(r.text)


async def dev():
    results = await asyncio.gather(
        async1(), async2()
    )
    print(results)

async def async1():
    aaa()
    return 10

async def async2():
    return 20