import asyncio, logging, random, pymysql, datetime, re, time
import numpy as np
from pyquery.pyquery import PyQuery as pq
from login import Login
from settings import SQL_SETTINGS, LOCAL_SQL_SETTINGS
from Format import time_now, status_format
from smtp import mail

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.WARNING)
handler = logging.FileHandler("log.txt")
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
console = logging.StreamHandler()
console.setLevel(logging.WARNING)
logger.addHandler(console)
logger.addHandler(handler)


class Spider():
    url = 'https://trade.taobao.com/trade/itemlist/list_sold_items.htm'
    base_url = 'https://trade.taobao.com'
    con = None
    cursor = None
    username = None
    password = None
    page = None
    fromStore = None
    browser = None

    def __init__(self):
        self.login = Login()
        loop = asyncio.get_event_loop()
        self.browser, self.page, self.fromStore = loop.run_until_complete(self.login.login())

    def connect_sql(self):
        self.con = pymysql.connect(**SQL_SETTINGS)
        # self.con = pymysql.connect(**LOCAL_SQL_SETTINGS)
        self.cursor = self.con.cursor()

    def sql_close(self):
        self.con.close()

    async def get_page(self):
        # 跳转至订单页面
        await self.page.goto(self.url)  # 跳转到订单页面
        await self.next_page(self.page, 1)

    async def intercept_request(self, req):
        """截取request请求"""
        if req.url == 'https://trade.taobao.com/trade/itemlist/asyncSold.htm?event_submit_do_query=1&_input_charset=utf8':
            a = re.search("pageNum=(\d+)", req.postData)
            if a:
                print("爬取第" + str(a.group(1) + "页成功！"))
        await req.continue_()

    async def intercept_response(self, res):
        """截取response响应"""
        if res.url == 'https://trade.taobao.com/trade/itemlist/asyncSold.htm?event_submit_do_query=1&_input_charset=utf8':
            a = await res.json()
            await self.parse(a['mainOrders'])

    async def next_page(self, page, i=1):
        """执行翻页"""
        await self.page.waitForSelector(".pagination-mod__show-more-page-button___txdoB", timeout=0)
        await self.page.click(".pagination-mod__show-more-page-button___txdoB")  # 显示全部页码
        await asyncio.sleep(3)
        for i in range(1, 21, 1):
            # 翻页并载数据包
            await page.setRequestInterception(True)
            page.on('request', self.intercept_request)
            page.on('response', self.intercept_response)
            await page.waitForSelector(".pagination-item-" + str(i) + " a", timeout=0)
            print("正面爬取第" + str(i) + "页" + time_now())
            await page.click(".pagination-item-" + str(i) + " a")
            while True:
                s = random.random()
                if s > 0.3:
                    await asyncio.sleep(s * 30)
                    break

    async def parse(self, mainOrders):
        """解析爬取内容信息"""
        for i in range(len(mainOrders)):
            order = {}  # 用于存储订单详细信息
            order['orderNo'] = mainOrders[i]["id"]
            order['createTime'] = mainOrders[i]['orderInfo']['createTime']
            order['buyerName'] = mainOrders[i]['buyer']['nick']
            flag = mainOrders[i]['extra']['sellerFlag']
            order['actualFee'] = mainOrders[i]['payInfo']['actualFee']
            order['deliverFee'] = re.search("\(含快递:￥(\d+.\d+)\)", mainOrders[i]['payInfo']['postType']).group(1)
            order['datailURL'] = "https:" + mainOrders[i]['statusInfo']['operations'][0]['url']
            order['orderStatus'] = mainOrders[i]['statusInfo']['text']
            order['fromStore'] = self.fromStore
            order['updateTime'] = time_now()
            if flag == 1:
                data_url = self.base_url + mainOrders[i]['operations'][0]['dataUrl']
                order['sellerFlag'] = await self.get_flag_text(data_url)
            try:
                order['isPhoneOrder'] = mainOrders[i]['payInfo']['icons'][0]['linkTitle']
            except KeyError:
                pass
            items = mainOrders[i]['subOrders']
            for j in range(len(items)):
                item = {}  # 用于存储售出商品详细信息
                item['orderNo'] = mainOrders[i]["id"]
                item['itemNo'] = str(j)
                item['goodsCode'] = items[j]['itemInfo']['extra'][0]['value']
                item['tbName'] = re.sub("(\s+)", " ", items[j]['itemInfo']['title']).strip()
                item['unitPrice'] = items[j]['priceInfo']['realTotal']
                item['sellNum'] = items[j]['quantity']
                item['orderStatus'] = order['orderStatus']
                try:
                    goodsAttributes = items[j]['itemInfo']['skuText']
                except KeyError:
                    pass
                else:
                    temp = []
                    for k in range(len(goodsAttributes)):
                        temp.append(goodsAttributes[k]['value'])
                    item['goodsAttribute'] = "-".join(temp)
                try:
                    refund = items[j]['operations']
                except KeyError:
                    pass
                else:
                    for x in range(len(refund)):
                        item['refundStatus'] = refund[x]['text']
                        item['isRefund'] = "1"
                self.save_in_sql(item=item, tableName='tb_order_detail_spider')
            self.save_in_sql(item=order, tableName='tb_order_spider')

    async def get_flag_text(self, data_url):
        page = await self.browser.newPage()
        await self.login.page_evaluate(page)  # 载入新的页面时，重新使用JS写入浏览器属性，用于反爬
        await page.goto(data_url)
        content = await page.content()
        await page.close()
        doc = pq(content)
        return re.search('"tip":"(.*?)"', doc("pre").text()).group(1)

    async def order_page(self):
        """爬取订单详情"""
        result = self.select_ndd()
        if result:
            # order = {}
            for url in result:
                order = {}
                page = await self.browser.newPage()
                # await self.login.page_evaluate(page)
                await page.goto(url[0])
                await page.waitForSelector("title")
                content = await page.content()
                doc = pq(content)
                orderNo = doc("span:contains('订单编号:') + span").text().split(" ")[0]
                refundItems = doc("#J_refundItem tr").items()
                if refundItems:
                    # item1 = {}
                    # item2 = {}
                    for item in refundItems:
                        item1 = {}
                        item2 = {}
                        item1["refundStatus"] = item.find("td.status").text().strip()
                        tbName = item.find("td.item-desc").text().strip().replace("&plusmn;", "±")
                        item2["tbName"] = re.sub("(\s+)", " ", tbName).strip()
                        item2["orderNo"] = orderNo
                        self.update_new(TABLENAME="tb_order_detail_spider", SET=item1, WHERE=item2)
                        logger.warning(
                            item2["orderNo"] + "," + item2["tbName"] + "退款订单入库成功,入库字段字段为" + "refundStatus" + "==>" +
                            item1[
                                "refundStatus"])
                order['payTime'] = " ".join(doc("span:contains('付款时间:') + span").text().split(" ")[0:2])
                order['tradeNo'] = doc("span:contains('支付宝交易号:')+span").text().split(" ")[0]
                receiverInfo = doc("span:contains('收货地址：') + span").text()
                try:
                    order['receiverName'] = receiverInfo.split("，")[0]
                    order['receiverPhone'] = receiverInfo.split("，")[1]
                    order['receiverAddress'] = "".join(receiverInfo.split("，")[2:])
                except Exception as e:
                    logger.error(e + "爬取买家信息有误，请手动查看" + orderNo)
                    break
                order['shippingMethod'] = doc("span:contains('运送方式：') + span").text()
                order['shippingCompany'] = doc("span:contains('物流公司名称：') + span").text()
                order['shippingNo'] = doc("span:contains('运单号：') + span").text()
                order['buyerComments'] = doc("dt:contains('买家留言：') + dd").text()
                coupon = doc("tr.order-item:first td:last-child").text().strip()
                order['couponPrice'] = "0"
                search_res = re.search("优惠.*?元", coupon)
                if not search_res:
                    search_res = re.search("省.*?元", coupon)
                if search_res:
                    order['couponPrice'] = "".join(re.findall("([0-9]+[.]*[0-9]*)", search_res.group()))
                    # print(order['couponPrice'])
                order['isDetaildown'] = '1'
                items = doc(".order-info-mod__order-info___2sjYJ tr").items()
                # item1 = {}
                # item2 = {}
                for i in items:
                    item1 = {}
                    item2 = {}
                    benefits = i.find(".promotion-mod__promotion___q71TJ").text()
                    if benefits:
                        tbName = i.find(".desc .name a").text().strip().replace("&plusmn;", "±")
                        item2["tbName"] = re.sub("(\s+)", " ", tbName).strip()
                        item2["orderNo"] = orderNo
                        unitBenefits = i.find(".promotion-mod__promotion___q71TJ").text()
                        item1["unitBenefits"] = str(
                            np.array(re.findall("([-]?[0-9]+[.]*[0-9]*)", unitBenefits)).astype(float).sum())
                        self.update_new(TABLENAME="tb_order_detail_spider", SET=item1, WHERE=item2)
                        logger.warning(
                            item2["orderNo"] + "," + item2["tbName"] + "更新入库成功,更新字段为" + "unitBenefits" + "==>" + item1[
                                "unitBenefits"])
                self.update_new(TABLENAME="tb_order_spider", SET=order, WHERE={"orderNo": orderNo})
                logger.warning(orderNo + "更新详情入库成功")
                await asyncio.sleep(5)
                await page.close()
                while True:
                    ss = random.random()
                    if ss > 0.3:
                        print(str(ss * 60) + "秒后开始爬取下一条")
                        await asyncio.sleep(ss * 60)
                        break

        else:
            print("没有可爬的详情")

    def save_in_sql(self, item, tableName):
        """
        写入数据库
        :param item: 需要被操作爬取到的数据
        :param tableName: 需要被操作的表名
        """
        # 下面三行是拼接SQL语句
        keys = ','.join(item.keys())
        values = ','.join(['%s'] * len(item))
        sql = "INSERT INTO %s (%s) VALUES (%s)" % (tableName, keys, values)
        if 'goodsCode' in item:
            item_new = {'goodsCode': item['goodsCode'], 'orderNo': item['orderNo'], 'itemNo': item['itemNo']}
            status = self.select(ITEM=item_new, TABLENAME=tableName)
            self.write_in_sql(STATUS=status, ITEM=item, TABLENAME=tableName, SQL=sql, ITEN_NEW=item_new)
        else:
            item_new = {'orderNo': item['orderNo']}
            status = self.select(ITEM=item_new, TABLENAME=tableName)
            self.write_in_sql(STATUS=status, ITEM=item, TABLENAME=tableName, SQL=sql, ITEN_NEW=item_new)

    def write_in_sql(self, STATUS, ITEM, TABLENAME, SQL, ITEN_NEW):
        """
        执行数据库写入
        :param STATUS: 从数据库查询订单的状态，如果不存在则为新的订单，如果存在则和爬取的状态对比，执行相应操作
        :param ITEM: 需要被操作的爬取到的数据，字典格式
        :param TABLENAME: 需要被操作的数据表的名
        :param SQL: 如果订单为新的订单时，需要使用的sql语句
        :param ITEN_NEW: 更新订单状态时所需的条件，字典格式
        """
        if STATUS:
            if STATUS != ITEM['orderStatus']:
                try:
                    self.update_new(TABLENAME=TABLENAME, WHERE=ITEN_NEW,
                                    SET=ITEM)
                except KeyError:
                    self.update_new(TABLENAME=TABLENAME, WHERE=ITEN_NEW,
                                    SET=ITEM)
                if 'goodsCode' in ITEM:
                    logger.warning(
                        "订单状态更新:" + ITEM['orderNo'] + " | 物料代码：" + ITEM['goodsCode'] + "|" + STATUS + '==>' + ITEM[
                            'orderStatus'])
                else:
                    logger.warning("订单状态更新:" + ITEM['orderNo'] + "|" + STATUS + '==>' + ITEM['orderStatus'])
            else:
                logger.info('订单已存在，不需要写入')
        else:
            try:
                self.cursor.execute(SQL, tuple(ITEM.values()))
                self.con.commit()
                logger.warning("新订单写入成功:" + ITEM['orderNo'] + ":" + ITEM['orderStatus'])
            except Exception as e:
                self.con.rollback()
                logger.error("写入数据库失败，失败原因：" + ITEM['orderNo'])
                logger.error(e)
                # mail("error report", "更新数据库失败，失败原因：" + ITEM['orderNo'] + e)

    def select(self, ITEM, TABLENAME):
        """
        查询数据库中订单状态
        :param ITEM: 查询的字段的条件
        :param TABLENAME: 需要查询的表名
        :return: 订单状态
        """
        conditions = self.concat(dictionary=ITEM, string=" AND ")
        sql = "select orderStatus from %s where %s" % (TABLENAME, conditions)
        self.cursor.execute(sql)
        result = self.cursor.fetchall()
        if result:
            return result[0][0]
        else:
            return None

    def select_ndd(self, orderNo=None):
        """查询数据库tb_order_spider表中，没有被爬取过订单详情的数据"""
        sql = "select datailURL from tb_order_spider where isDetaildown = 0 and fromStore = '%s'" % (self.fromStore)
        # print(sql)
        # sql = "SELECT datailURL FROM tb_order_spider WHERE orderNo = '531852160106225329'"
        self.cursor.execute(sql)
        result = self.cursor.fetchall()
        return result

    def update_new(self, TABLENAME, SET, WHERE):
        """
        执行更新数据库，并输出日志
        :param TABLENAME: 需要更新的表名
        :param SET: 需要更新的字段，字典格式
        :param WHERE: 需要更新字段的条件，字典格式
        :return: None
        """
        a = self.concat(SET, ",")
        b = self.concat(WHERE, " AND ")
        sql = "UPDATE %s SET %s WHERE %s" % (TABLENAME, a, b)
        try:
            self.cursor.execute(sql)
            self.con.commit()
        except Exception as e:
            self.con.rollback()
            logger.error("更新数据库失败，失败原因：" + WHERE['orderNo'])
            logger.error(e)
            mail("error report", "更新数据库失败，失败原因：" + WHERE['orderNo'] + e)

    def concat(self, dictionary, string):
        """
        拼装字典
        :param dictionary: 需要拼装的字典
        :param string: 拼装时所使用的连接的字符
        :return: key='value' string key='value' string key='value'...
        """
        list_key_value = []
        for k, v in dictionary.items():
            list_key_value.append(k + "=" + '\'' + v + '\'')
        conditions = string.join(list_key_value)
        return conditions


if __name__ == '__main__':
    spider = Spider()
    while True:
        print(spider.fromStore)
        print("starting spider")
        start_time = datetime.datetime.now()
        spider.connect_sql()
        loop = asyncio.get_event_loop()
        tasks = [spider.get_page(), spider.order_page()]
        loop.run_until_complete(asyncio.wait(tasks))
        # loop.run_until_complete(spider.get_page())
        # loop.run_until_complete(spider.order_page())
        loop.close()
        spider.sql_close()
        end_time = datetime.datetime.now()
        spending_time = end_time - start_time
        print(str(round(spending_time.seconds / 60, 2)) + "分钟完成一轮爬取")
        time.sleep(900)
