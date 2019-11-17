import shutil
from pyppeteer.launcher import CHROME_PROFILE_PATH

if __name__ == '__main__':
    shutil.rmtree(CHROME_PROFILE_PATH, True)

# nohup python3 -u main.py > main.log 2>&1 &
# tail -f mytest.log如果要实时查看日志文件使用命令
# 解决：直接在putty中输入exit退出即可
# nohup python3 -u competitor_price_spider.py > log/cps.log 2>&1 &
