from dotenv import load_dotenv
import json
from logging import getLogger, config
from fetch.textage_fetcher import textage_data

import re

replace_list = [
    [re.compile(r"'(.*?)'(.*?):(.*?)\[(.*?)\]"), r'"\1":[\4]']
]

comment_pattern = [
    re.compile(r'//.*?\n')
]

def main():
    # 検証環境の.envを読み込み
    load_dotenv()
    # logger設定の読み込み
    with open('./src/log_config.json', 'r') as f:
        log_conf = json.loads(f.read())
        config.dictConfig(log_conf)
    logger = getLogger('main')
    # logger = getLogger('debug')
    td = textage_data(logger)

    td.update()


if __name__ == '__main__':
    main()