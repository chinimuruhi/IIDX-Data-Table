from dotenv import load_dotenv
import json
from logging import getLogger, config
from fetch.textage_fetcher import textage_data
from common.manualdata_loader import manualdata_loader

import asyncio

async def main():
    # 検証環境の.envを読み込み
    load_dotenv()
    # logger設定の読み込み
    with open('./src/log_config.json', 'r') as f:
        log_conf = json.loads(f.read())
        config.dictConfig(log_conf)
    logging = getLogger('main')
    # logger = getLogger('debug')
    manualdata_loader.set_logging(logging)
    # textage情報の更新
    td = textage_data(logging)
    await td.init()
    await td.update()


if __name__ == '__main__':
    asyncio.run(main())