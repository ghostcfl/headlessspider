width, height = 1600, 900
login_url = "https://login.taobao.com/"
launch_setting = {
    'executablePath': '.\\chrome-win\\chrome.exe',
    'headless': True,
    'autoClose': True,
    'dumpio': True,
    'args': [f'--window-size={width},{height}',
             '--disable-infobars',
             '--no-sandbox',
             #'--proxy-server=127.0.0.1:1080',
             ],
    # 'userDataDir': './userdata/userdata',
}
launch_setting_dev = {
    'executablePath': '.\\chrome-win\\chrome.exe',
    'headless': False,
    'autoClose': False,
    'dumpio': True,
    'args': [f'--window-size={width},{height}', '--disable-infobars', '--no-sandbox'],
    # 'userDataDir': './userdata/userdata',
}

"""
SQL服务器密码与端口配置
"""
HOST = 'www.veatao.com'
PORT = 3306
USER = 'test'
PWD = 'sz123456'
DB = 'test'
SQL_SETTINGS = {
    'host': HOST,
    'port': PORT,
    'user': USER,
    'password': PWD,
    'db': DB,
}
"""
localhost Mysql配置
"""
HOST = 'localhost'
PORT = 3306
USER = 'root'
PWD = 'root'
DB = 'test'
LOCAL_SQL_SETTINGS = {
    'host': HOST,
    'port': PORT,
    'user': USER,
    'password': PWD,
    'db': DB,
}

"""
邮箱SMTP服务账号和密码
"""
my_sender = '946930866@qq.com'  # 发件人邮箱账号
my_pass = 'gzaxfeshkzsxbded'  # 发件人邮箱密码
my_user = [
    '946930866@qq.com', 'szjavali@qq.com', '104684637@qq.com', '2052489524@qq.com',
]  # 收件人邮箱账号

headers = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
    'Connection': 'keep-alive',
    'Content-Length': '443',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Host': 'trade.taobao.com',
    'Referer': 'https://trade.taobao.com/trade/itemlist/list_sold_items.htm',
    'TE': 'Trailers',
    'X-Requested-With': 'XMLHttpRequest',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3824.0 Safari/537.36',
}
form_data = {
    'auctionType': 0,
    'close': 0,
    'pageNum': 2,
    'pageSize': 15,
    'queryMore': 'false',
    'rxAuditFlag': 0,
    'rxElectronicAllFlag': 0,
    'rxElectronicAuditFlag': 0,
    'rxHasSendFlag': 0,
    'rxOldFlag': 0,
    'rxSendFlag': 0,
    'rxSuccessflag': 0,
    'rxWaitSendflag': 0,
    'tradeTag': 0,
    'useCheckcode': 'false',
    'useOrderInfo': 'false',
    'errorCheckcode': 'false',
    'action': 'itemlist/SoldQueryAction',
    'prePageNo': 3,
    'buyerNick': '',
    'dateBegin': 0,
    'dateEnd': 0,
    'logisticsService': '',
    'orderStatus': '',
    'queryOrder': 'desc',
    'rateStatus': '',
    'refund': '',
    'sellerNick': '',
    'tabCode': 'latest3Months',
}
postData = """
auctionType=0
&close=0
&pageNum=**************
&pageSize=15
&queryMore=false
&rxAuditFlag=0
&rxElectronicAllFlag=0
&rxElectronicAuditFlag=0
&rxHasSendFlag=0
&rxOldFlag=0
&rxSendFlag=0
&rxSuccessflag=0
&rxWaitSendflag=0
&tradeTag=0
&useCheckcode=false
&useOrderInfo=false
&errorCheckcode=false
&action=itemlist%2FSoldQueryAction
&prePageNo=**************
"""
