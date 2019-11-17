import asyncio, re, datetime, time, random, mysql, os
from slaver_spider import SlaverSpider
from Format import time_now, net_check, sleep, store_trans, time_zone
from pyppeteer import errors
from settings import MODE, test_server, production_server, local_server, STORE_INFO, my_user
from pyquery import PyQuery as pq
from login import Login
from logger import get_logger
from smtp import mail

logger = get_logger("price_tb")


class PriceTaoBao():
    item_url = "https://item.taobao.com/item.htm?id="
    item_erp_url = "http://shai3c.com/weberp/Prices_tb.php?Full=1&LinkID="
    url = "https://item.publish.taobao.com/taobao/manager/render.htm?tab=all"
    item = {}
    prices = {}
    prop = {}
    promo_price = {}
    common = {}
    db_test = {'host': 'www.veatao.com', 'port': 3306, 'user': 'test', 'password': 'sz123456', 'db': 'test'}
    sql_test_server = None
    sql_element = None
    complete = 0
    operator = "爬虫维护"
    server = {"production_server": production_server,
              "test_server": test_server,
              "local_server": local_server}
    target_server = server['production_server']
    sn = None

    def __init__(self, ss, browser, page, fromStore):
        self.ss = ss
        self.browser = browser
        self.page = page
        self.fromStore = fromStore

        # pass

    def shop_id(self, fromStore):
        time.sleep(1)
        res = mysql.get_data(t="shop_info", l=1, cn=["shop_id"], c={"typeabbrev": fromStore, "shopindex": 0})
        # res = mysql.get_data(t="salestypes", l=1, cn=["shop_id"], c={"typeabbrev": fromStore})
        return res[0][0]

    async def get_page(self):
        net_check()
        await self.page.goto(self.url)  # 跳转到页面
        await self.next_page()

    async def intercept_request(self, req):
        """截取request请求"""
        await req.continue_()

    async def intercept_response(self, res):
        """截取response响应"""
        req = res.request
        # print(req.method)
        if req.method == "POST":
            try:
                a = await res.json()
            except Exception as e:
                pass
            else:
                try:
                    if a['data']['table']['dataSource']:
                        await self.parse(a['data']['table']['dataSource'])
                    else:
                        await self.parse("q")
                except Exception as e:
                    try:
                        if a['data']['value']['skuOuterIdTable']['dataSource']:
                            await self.parse_2(a['data']['value'])
                    except Exception as e:
                        pass

    async def parse(self, data):
        if data != "q":
            for i in range(len(data)):
                self.item = {}
                self.item = self.common.copy()
                self.item['stockid'] = re.search("编码:(.*)", data[i]['itemDesc']['desc'][1]['text']).group(1).upper()
                self.item['link_id'] = data[i]['itemId']
                self.item['attribute'] = ""
                self.item['flag'] = "update"
                self.item['typeabbrev'] = self.fromStore
                self.item['shop_id'] = self.shop_id(self.fromStore)
                self.item['SpiderDate'] = time_now()
                temp_des = data[i]['itemDesc']['desc'][0]['text']
                self.item['description'] = temp_des.replace("（", "(").replace("）", ")")
                self.item['price_tb'] = re.findall("(\d+.?\d*)", data[i]["managerPrice"]['currentPrice'])[0]
                self.item['promotionprice'] = self.promo_price.get(self.item['link_id'])
                # print(self.promo_price)

                sql = "select spe_link from prices_tb_fix where link_id='%s' and server='%s'" % (
                    self.item['link_id'], self.sn)
                spe_link_id = mysql.get_data(db=self.db_test, sql=sql, return_one=True)
                isMut = re.search("^MUT\D*", self.item['stockid'])

                if isMut or spe_link_id:
                    await self.page.setRequestInterception(True)
                    self.page.on('request', self.intercept_request)
                    self.page.on('response', self.intercept_response)
                    await asyncio.sleep(1)
                    net_check()
                    await self.page.click(".next-table-row td:nth-child(2) div.product-desc-hasImg span:nth-child(2) i")
                    await asyncio.sleep(1)
                    await self.page.keyboard.press('Escape')
                else:
                    # print(self.item)
                    if self.item['promotionprice'] is None:
                        mail("price_tb_error", self.fromStore + ":" + self.item['link_id'], ["946930866@qq.com"])
                        logger.error(
                            "error:" + self.fromStore + " : " + self.item['link_id'] + " and " +
                            mysql.concat(self.promo_price, "="))
                        self.complete = 2
                        break
                    condition = {
                        "stockid": self.item['stockid'],
                        "link_id": self.item['link_id'],
                        "shop_id": self.item['shop_id'],
                    }
                    res = mysql.get_data(t="prices_tb", l=1, cn=["id"], c=condition, db=self.target_server)
                    if res:
                        self.item['ratio'] = round(float(self.item['price_tb']) / float(res[0][0]), 2)
                        print(self.item)
                        mysql.update_data(t="prices_tb", set=self.item, c=condition, db=self.target_server)
                    else:
                        insert_item = self.item.copy()
                        insert_item["currabrev"] = "CNY"
                        insert_item["price_erp"] = 0
                        insert_item["operator"] = self.operator
                        insert_item["last_time"] = time_now()
                        if self.operator == "爬虫维护":
                            insert_item["flag"] = "create"
                        else:
                            insert_item['flag'] = "add"
                        insert_item["ratio"] = 1
                        insert_item["package_number"] = 1
                        insert_item["Checker"] = ""
                        insert_item["CheckDate"] = "0000-00-00 00:00:00"
                        print(insert_item)

                        with open("reports/report_" + self.fromStore + "_insert.txt", "a") as file:
                            file.writelines("物料编码：" + insert_item['stockid'] + " 与 商品ID：" +
                                            insert_item['link_id'] + " 为最新匹配，添加至ERP系统。\n" +
                                            self.item_url + insert_item['link_id'] + "\n" +
                                            self.item_erp_url + insert_item['link_id'] + "\n\n")

                        mysql.insert_data(t="prices_tb", d=insert_item, db=self.target_server)
                    result = mysql.get_data(t="prices_tb",
                                            cn=["*"],
                                            c={"link_id": self.item['link_id']},
                                            db=self.target_server,
                                            dict_result=True)

                    if len(result) > 1:
                        for r in result:
                            if r['stockid'] != self.item['stockid'] and r['flag'] != "del":
                                with open("reports/report_" + self.fromStore + "_delete.txt", "a") as file:
                                    file.writelines("物料编码：" + r['stockid'] + " 与 商品ID：" +
                                                    self.item['link_id'] + " 不匹配，已被爬虫从ERP系统中删除。\n" +
                                                    self.item_url + self.item['link_id'] + "\n" +
                                                    self.item_erp_url + self.item['link_id'] + "\n\n"
                                                    )

                                mysql.update_data(t="prices_tb", c={"id": r['id']}, db=self.target_server,
                                                  set={"flag": "del"})

                    self.complete = 1
        else:
            pass
            self.complete = 1

    async def parse_2(self, data):
        verify = []
        repeat_list = []
        for i in data['skuOuterIdTable']['dataSource']:
            self.item['stockid'] = i['skuOuterId']
            logger.info(self.item['stockid'])
            if not self.item['stockid']:
                continue
            else:
                if self.item['stockid'] not in verify:
                    verify.append(self.item['stockid'])
                else:
                    if self.item['stockid'] not in repeat_list:
                        repeat_list.append(self.item['stockid'])
            skuId = str(i['skuId'])
            temp_attr = self.prop.get(skuId)
            self.item['attribute'] = temp_attr.replace("（", "(").replace("）", ")")
            if not self.item['attribute']:
                self.item.pop('attribute')
            self.item['price_tb'] = self.prices.get(skuId)
            if self.promo_price:
                self.item["promotionprice"] = self.promo_price.get(skuId)
            else:
                self.item["promotionprice"] = 0

            condition = {
                "stockid": self.item['stockid'],
                "link_id": self.item['link_id'],
                "shop_id": self.item['shop_id'],
            }
            res = mysql.get_data(t="prices_tb", l=1, cn=["price_tb"], c=condition, db=self.target_server)
            if res:

                if res[0][0] == 0:
                    self.item['ratio'] = 1
                else:
                    self.item['ratio'] = round(float(self.item['price_tb']) / float(res[0][0]), 2)

                print(self.item)
                mysql.update_data(t="prices_tb", set=self.item, c=condition, db=self.target_server)
            else:
                insert_item = self.item.copy()
                insert_item["currabrev"] = "CNY"
                insert_item["price_erp"] = 0
                insert_item["operator"] = self.operator
                insert_item["last_time"] = time_now()
                if self.operator == "爬虫维护":
                    insert_item["flag"] = "create"
                else:
                    insert_item['flag'] = "add"
                insert_item["ratio"] = 1
                insert_item["package_number"] = 1
                insert_item["Checker"] = ""
                insert_item["CheckDate"] = "0000-00-00 00:00:00"
                print(insert_item)

                with open("reports/report_" + self.fromStore + "_insert.txt", "a") as file:
                    file.write(
                        "物料编码：" + insert_item['stockid'] + " 与商品ID：" +
                        insert_item['link_id'] + " 为最新匹配，添加至ERP系统。\n" +
                        self.item_url + insert_item['link_id'] + "\n" +
                        self.item_erp_url + insert_item['link_id'] + "\n\n")

                mysql.insert_data(t="prices_tb", d=insert_item, db=self.target_server)

        if repeat_list:
            with open("reports/report_" + self.fromStore + "_repeat.txt", "a") as file:
                file.write("店铺：" + store_trans(self.fromStore) + ",商品id:" +
                           self.item['link_id'] + " 重复编码\n" +
                           "重复编码:" + ",".join(repeat_list) + "\n" +
                           self.item_url + self.item['link_id'] + "\n\n"
                           )

        if not verify:
            with open("reports/report_" + self.fromStore + "_empty.txt", "a") as file:
                file.write("店铺：" + store_trans(self.fromStore) + ",商品id:" +
                           self.item['link_id'] + " 空编码\n" +
                           self.item_url + self.item['link_id'] + "\n\n")

        sql = """
        select id,stockid 
        from prices_tb 
        where link_id='%s' 
        and flag not in('del','XiaJia')
        """ % (self.item['link_id'])
        res_verify = mysql.get_data(sql=sql,
                                    db=self.target_server)

        for rv in res_verify:
            if rv[1] not in verify:
                with open("reports/report_" + self.fromStore + "_delete.txt", "a") as file:
                    file.write("物料编码：" + rv[1] + " 与 商品ID：" +
                               self.item['link_id'] + " 不匹配，已被爬虫从ERP系统中删除。\n" +
                               self.item_url + self.item['link_id'] + "\n" +
                               self.item_erp_url + self.item['link_id'] + "\n\n")

                mysql.update_data(t="prices_tb", c={"id": rv[0]}, db=self.target_server,
                                  set={"flag": "del", "operator": self.operator, "last_time": time_now()})

        self.complete = 1

    async def get_nc_frame(self, frames):
        for frame in frames:
            slider = await frame.J("#nc_1_n1z")
            if slider:
                return frame
        return None

    async def run(self):
        net_check()
        await self.page.goto(self.url)
        await asyncio.sleep(2)
        await self.page.waitForSelector("input[name='queryItemId']", timeout=0)
        frames = self.page.frames
        frame = await self.get_nc_frame(frames)

        if frame:
            logger.info("条形验证码")
            while True:
                await asyncio.sleep(1)
                await frame.hover("#nc_1_n1z")
                await self.page.mouse.down()
                await self.page.mouse.move(2000, 0, {'delay': random.randint(1000, 2000)})
                await self.page.mouse.up()
                try:
                    frame.waitForSelector(".nc-lang-cnt a", timeout=10000)
                    await asyncio.sleep(2)
                    await frame.click(".nc-lang-cnt a")
                except errors.TimeoutError:
                    await asyncio.sleep(1)
                    slider = await frame.J("#nc_1_n1z")
                    if not slider:
                        break
                except errors.PageError:
                    await asyncio.sleep(1)
                    slider = await frame.J("#nc_1_n1z")
                    if not slider:
                        break

        operator = ""
        if MODE == 2:
            operator = input(time_now() + " | 输入操作者名字:")
        if operator:
            self.operator = operator
        logger.info("当前操作者 ：" + self.operator)
        while True:
            a = await self.fix_data()
            if a == 1:
                break

    async def fix_data(self, link_id=None):
        # page = await self.browser.newPage()
        self.complete = 0
        self.prices = {}
        self.promo_price = {}
        await asyncio.sleep(2)
        await self.page.focus("input[name='queryItemId']")
        await self.page.keyboard.down("ShiftLeft")
        await self.page.keyboard.press("Home")
        await self.page.keyboard.down("ShiftLeft")
        await self.page.keyboard.press("Delete")
        server_name = 'production_server'
        self.sn = server_name
        if not link_id:
            if MODE == 1:
                link_id = "585308692855"
            elif MODE == 2:
                while True:
                    link_id = input(time_now() + " | 输入link_id：")
                    isMatch = re.match("^\d{10,20}$", link_id)
                    if isMatch:
                        break
            elif MODE == 3:
                sql = """
                SELECT link_id,updateTime,server,operator
                FROM prices_tb_fix 
                WHERE fromStore='%s' and isComplete=0
                ORDER BY flag LIMIT 1
                """ % (self.fromStore)
                res = mysql.get_data(sql=sql, db=self.db_test)
                if res:
                    self.target_server = self.server[res[0][2]]
                    link_id = res[0][0]
                    updateTime = res[0][1]
                    server_name = res[0][2]
                    self.sn = server_name
                    self.operator = res[0][3]
                else:
                    return 1

        logger.info(link_id)
        page = await self.browser.newPage()
        await page.setViewport({'width': 1600, 'height': 900})
        net_check()
        await page.goto("https://item.taobao.com/item.htm?id=" + link_id, timeout=0)
        await asyncio.sleep(3)
        error_page = await page.J(".error-notice-hd")  # 判断宝贝是否正常在售
        offline = await page.J("#J_detail_offline")  # 判断宝贝是否正常在售
        if error_page or offline:
            logger.info("商品已下架")
            mysql.update_data(t="prices_tb",
                              set={"flag": "XiaJia", "typeabbrev": self.fromStore},
                              c={"link_id": link_id},
                              db=self.target_server)
            # mysql.update_data(t="tb_order_detail_spider",
            #                   set={"link_id": link_id + "xiajia"},
            #                   c={"link_id": link_id},
            #                   db=self.target_server)
            mysql.update_data(db=self.db_test,
                              t="prices_tb_fix",
                              set={"isComplete": "2", "updateTime": time_now()},
                              c={"link_id": link_id, "server": server_name})
            await page.close()
            return
        else:
            while True:
                content = await page.content()
                # print(content)
                doc = pq(content)
                self.common['rates'] = doc.find("#J_RateCounter").text()
                self.common['sales'] = doc.find("#J_SellCounter").text()
                self.common['freight'] = doc.find("#J_WlServiceTitle").text()
                mat1 = re.match("\d+", self.common['sales'])
                mat2 = re.match("\d+", self.common['rates'])
                if mat1 and mat2:
                    break
            res = re.findall('";(.*?);".*?e":"(\d+\.\d+).*?d":"(\d+)"', content)  # 判断是否存在多属性
            if res:
                control = 1
                benefit_price = 0
                for r in res:
                    data_values = r[0].split(";")
                    prop = []
                    for data in data_values:
                        prop.append(doc.find("li[data-value='" + data + "'] span").text())

                    if control:
                        for data in data_values:
                            try:
                                await page.click('li[data-value="' + data + '"]')
                            except errors.PageError:
                                pass
                        content_p = await page.content()
                        promo_price = re.findall('<em id="J_PromoPriceNum".*?>(\d+\.?\d*)</em>', content_p)  # 判断是否存在优惠
                        if len(promo_price) == 1:
                            benefit_price = float(r[1]) - float(promo_price[0])
                            control = 0

                    self.prices[r[2]] = r[1]
                    prop.reverse()
                    self.prop[r[2]] = "-".join(prop)

                for r in res:
                    if benefit_price:
                        self.promo_price[r[2]] = round(float(r[1]) - benefit_price, 2)
            else:
                promo_price = re.findall('<em id="J_PromoPriceNum".*?>(\d+.*\d*)</em>', content)  # 判断是否存在优惠
                if promo_price:
                    self.promo_price[link_id] = promo_price[0]
                else:
                    self.promo_price[link_id] = 0
            # print(self.prices)
            # print(self.promo_price)

            await page.close()
            await self.page.type("input[name='queryItemId']", link_id)
            await self.page.setRequestInterception(True)
            self.page.on('request', self.intercept_request)
            self.page.on('response', self.intercept_response)
            await asyncio.sleep(1)
            net_check()
            await self.page.click(".filter-footer button:first-child")
            while True:
                await asyncio.sleep(1)
                if self.complete == 1:
                    res = mysql.get_data(db=self.db_test,
                                         t="prices_tb_fix",
                                         c={"link_id": link_id, "server": server_name})
                    if res:
                        mysql.update_data(db=self.db_test,
                                          t="prices_tb_fix",
                                          set={"isComplete": "1", "updateTime": time_now()},
                                          c={"link_id": link_id, "server": server_name})
                    break
                elif self.complete == 2:
                    mysql.update_data(db=self.db_test,
                                      t="prices_tb_fix",
                                      set={"spe_link": "1"},
                                      c={"link_id": link_id, "server": server_name})
                    break


def report_mail():
    trans = {
        "YJ": "玉佳电子",
        "YK": "玉佳企业店",
        "KY": "开源电子",
        "TB": "赛宝电子",
        "report": "报告",
        "insert.txt": "添加",
        "delete.txt": "删除",
        "empty.txt": "空编码",
        "repeat.txt": "重复编码",
    }

    filenames = os.listdir("reports")
    for file in filenames:
        txt = re.search("txt", file)
        if txt:
            with open("reports/" + file, "r") as file_obj:
                a = file_obj.read()
                if a:
                    x = file.split("_")
                    title = trans[x[1]] + trans[x[2]] + trans[x[0]]
                    content = a
                    mail_receiver = my_user.copy()
                    mail_receiver.append(STORE_INFO[x[1]]['manager_mail'])
                    mail(title, content, mail_receiver)
            with open("reports/" + file, "w") as file_obj:
                pass  # 清除文件内容

if __name__ == '__main__':
    ss = SlaverSpider()
    l = Login()
    loop = asyncio.get_event_loop()
    if MODE == 3:
        t = time_zone(["9:00", "14:00", "17:00"])
        t1 = t2 = t3 = 0
        while True:
            now = datetime.datetime.now()
            if t[0] < now < t[1] and t1 == 0:
                report_mail()
                t1, t2, t3 = 1, 0, 0
            elif t[1] < now < t[2] and t2 == 0:
                report_mail()
                t1, t2, t3 = 0, 1, 0
            elif now > t[2] and t3 == 0:
                report_mail()
                t1, t2, t3 = 0, 0, 1
            sql = """
            SELECT fromStore
            FROM prices_tb_fix WHERE isComplete='0'
            GROUP BY fromStore ORDER BY COUNT(link_id) DESC
            """
            ts = test_server.copy()
            ts['db'] = 'test'
            res = mysql.get_data(db=ts, sql=sql)
            if res:
                b, p, f = loop.run_until_complete(ss.login(**STORE_INFO[res[0][0]]))
                ptb = PriceTaoBao(ss, b, p, f)
                loop.run_until_complete(ptb.run())
                loop.run_until_complete(p.close())
                if len(res) == 1:
                    loop.run_until_complete(b.close())
                    ss.b = None
            else:
                sleep(10)
    else:
        b, p, f = loop.run_until_complete(l.login())
        ptb = PriceTaoBao(l, b, p, f)
        loop.run_until_complete(ptb.run())
