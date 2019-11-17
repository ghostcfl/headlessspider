import asyncio, random, time, re, json, mysql, datetime, shutil
from settings import dev, STORE_INFO, login_url, NEXT_ORDER_TIME as n_o_time, test_server
from pyppeteer.launcher import launch, CHROME_PROFILE_PATH
from pyppeteer import errors
from Verify import Verify
from Format import net_check, status_format, sleep


class SlaverSpider():
    b = None

    async def get_browser(self):
        self.b = await launch(dev)  # 启动pyppeteer 属于内存中实现交互的模拟器
        return self.b

    async def get_new_page(self):
        if not self.b:
            await self.get_browser()
        p = await self.b.newPage()
        await p.setViewport({"width": 800, "height": 600})
        return p

    async def login(self, page=None, **kwargs):
        # shutil.rmtree(CHROME_PROFILE_PATH, True)
        if not page:
            page = await self.get_new_page()

        while 1:
            try:
                net_check()
                await page.goto(login_url)
            except errors.PageError:
                pass
            except errors.TimeoutError:
                pass
            else:
                break
        while True:
            try:
                await page.waitForSelector(".forget-pwd.J_Quick2Static", visible=True, timeout=10000)
                await page.click(".forget-pwd.J_Quick2Static")
            except errors.TimeoutError:
                pass
            except errors.ElementHandleError:
                await page.reload()
                continue
            finally:
                try:
                    await page.type('#TPL_username_1', kwargs['username'], {'delay': self.input_time_random() - 50})
                    await page.type('#TPL_password_1', kwargs['password'], {'delay': self.input_time_random()})
                except errors.ElementHandleError:
                    await page.reload()
                else:
                    break

        net_check()
        # 检测页面是否有滑块。原理是检测页面元素。
        slider = await page.Jeval('#nocaptcha', 'node => node.style')  # 是否有滑块
        if slider:
            print("出现滑块情况判定")
            await self.mouse_slide(p=page)
            await page.click("#J_SubmitStatic")  # 调用page模拟点击登录按钮。
            time.sleep(2)
            await self.get_cookie(page)
        else:
            await page.click("#J_SubmitStatic")

        try:
            await page.waitForSelector("#container", timeout=10000)
        except errors.TimeoutError:
            print("超时需要手机验证！")
            frames = page.frames
            try:
                await frames[1].waitForSelector("button#J_GetCode", timeout=10000)
            except errors.TimeoutError:
                pass
            else:
                print("需要要手机验证码")
                test_server['db'] = "test"
                id = random.randint(0, 100)
                mysql.insert_data(db=test_server, t="phone_verify", d={"id": id})
                # frames = page.frames
                # await frames[1].click(".J_SendCodeBtn")
                verify_code = "0"
                while True:
                    net_check()
                    await frames[1].click("button#J_GetCode")
                    for i in range(120):
                        await asyncio.sleep(5)
                        res = mysql.get_data(db=test_server, cn=["verify_code"],
                                             t="phone_verify", c={"id": id}, )
                        verify_code = res[0][0]
                        if verify_code != "0":
                            mysql.delete_data(db=test_server, t="phone_verify", c={"id": id})
                            break
                    if verify_code != "0":
                        break

                await frames[1].type("input#J_Phone_Checkcode", verify_code, {"delay": self.input_time_random() - 50})
                # await frames[1].type(".J_SafeCode", a, {'delay': self.input_time_random() - 50})
                net_check()
                await frames[1].click("input#submitBtn")
                # await frames[1].click("#J_FooterSubmitBtn")
            net_check()
            await page.goto("https://myseller.taobao.com/home.htm")
        await page.waitForSelector("#container", timeout=30000)

        return self.b, page, kwargs['fromStore']

    async def get_cookie(self, page):
        """获取登录后cookie"""
        cookies_list = await page.cookies()
        cookies = ''
        for cookie in cookies_list:
            str_cookie = '{0}={1};'
            str_cookie = str_cookie.format(cookie.get('name'), cookie.get('value'))
            cookies += str_cookie
        return cookies

    async def mouse_slide(self, p=None):
        await asyncio.sleep(2)
        while True:
            print("出现滑块验证码")
            await asyncio.sleep(2)
            await p.hover('#nc_1_n1z')
            await p.mouse.down()
            await p.mouse.move(2000, 0, {'delay': random.randint(1000, 2000)})
            await p.mouse.up()
            try:
                p.waitForSelector(".nc-lang-cnt a", timeout=10000)
                await asyncio.sleep(2)
                await p.click(".nc-lang-cnt a")
            except errors.TimeoutError:
                break
            except errors.PageError:
                break

    def input_time_random(self):
        return random.randint(100, 151)

    async def run_link_spider(self):
        sql = """
        SELECT COUNT(a.id),fromStore FROM tb_order_detail_spider a
        JOIN tb_order_spider b ON a.`orderNo`=b.`orderNo`
        WHERE link_id="1" AND a.url IS NOT NULL
        GROUP BY fromStore
        ORDER BY COUNT(a.id) DESC
        """
        time.sleep(2)
        res = mysql.get_data(sql=sql)
        if res:
            b, p, f = await self.login(**STORE_INFO[res[0][1]])
            await self.link_spider(p, f)
        else:
            mysql.update_data(t="tb_order_spider", set={"isDetaildown": 0}, c={"isDetaildown": 2})
            # if self.b:
            #     await self.b.close()
            #     self.b = None
            await self.run_order_detail_spider()

    async def link_spider(self, p, f):
        test_server["db"] = "test"
        while True:
            sql = """
                SELECT a.id,url,goodsCode,a.orderNo FROM tb_order_detail_spider a
                JOIN tb_order_spider b ON a.`orderNo`=b.`orderNo`
                WHERE link_id="1" AND b.`fromStore`='%s' AND a.url IS NOT NULL
                ORDER BY b.createTime DESC
                LIMIT 1
                    """ % (f)
            url = "https://smf.taobao.com/promotionmonitor/orderPromotionQuery.htm?orderNo="
            results = mysql.get_data(sql=sql, dict_result=True)
            if not results:
                break
            orderno = results[0]['orderNo']
            url += orderno
            await p.goto(url)
            content = await p.content()
            data = re.findall(">(\{.*?\})<", content)
            order = json.loads(data[0])
            try:
                sub_orders = order["data"]["subOrderViewDTOs"]
            except KeyError:
                continue
            for so in sub_orders:
                order_no = so["orderNoStr"]
                link_id = so["itemId"]
                sql = "select goodsCode from tb_order_detail_spider where url like '%%%s%%'" % (order_no)
                print(sql)
                goodsCode = mysql.get_data(sql=sql, return_one=True)
                del sql
                sql = "update tb_order_detail_spider set link_id='%s' where url like '%%%s%%'" % (link_id, order_no)
                mysql.update_data(sql=sql)
                del sql
                sql = """
                SELECT SpiderDate
                FROM prices_tb
                WHERE link_id='%s'
                AND stockid='%s'
                AND flag NOT IN ('del','XiaJia')
                """ % (link_id, goodsCode)

                res = mysql.get_data(sql=sql)
                res_fix = mysql.get_data(db=test_server,
                                         dict_result=True,
                                         t='prices_tb_fix',
                                         c={"link_id": link_id,
                                            "server": "production_server"})
                if res:
                    spider_date = res[0][0]
                    days = 1
                    if spider_date != '0000-00-00 00:00:00':
                        days = (datetime.datetime.now() - spider_date).days
                    if spider_date == '0000-00-00 00:00:00' or days > 14:
                        if not res_fix:
                            mysql.insert_data(db=test_server,
                                              t="prices_tb_fix",
                                              d={"link_id": link_id, "fromStore": f, "flag": 1})
                        elif res_fix[0]["isComplete"] != 0:
                            mysql.update_data(db=test_server,
                                              t="prices_tb_fix",
                                              set={"isComplete": 0, "flag": 1},
                                              c={"link_id": link_id, "server": "production_server"})
                else:
                    if not res_fix:
                        mysql.insert_data(db=test_server,
                                          t="prices_tb_fix",
                                          d={"link_id": link_id, "fromStore": f, "flag": 0})
                    elif res_fix[0]["isComplete"] != 0:
                        mysql.update_data(db=test_server,
                                          t="prices_tb_fix",
                                          set={"flag": 0, "isComplete": 0},
                                          c={"link_id": link_id, "server": "production_server"})
            sleep(5)
        await p.close()
        await self.run_link_spider()

    async def run_order_detail_spider(self):
        sql = """
                SELECT COUNT(id),fromStore 
                FROM tb_order_spider 
                WHERE isDetaildown=0 
                GROUP BY fromStore 
                ORDER BY COUNT(id) DESC 
                LIMIT 1
                """
        res = mysql.get_data(sql=sql)
        if res:
            b, p, f = await self.login(**STORE_INFO[res[0][1]])
            await self.order_detail_spider(p, f)
        else:
            # if self.b:
            #     await self.b.close()
            #     self.b = None
            await self.run_link_spider()

    async def order_detail_spider(self, p, f):
        sql1 = """
        SELECT datailURL,a.orderNo FROM tb_order_spider a
        JOIN taobaoorders b ON a.orderNo = b.OrderNo
        WHERE  isDetaildown=0 AND fromStore='%s' AND b.Flag = 8
        ORDER BY createTime DESC;
        """ % (f)
        sql = """
            SELECT datailURL,orderNo FROM tb_order_spider 
            WHERE  isDetaildown=0 AND fromStore='%s' 
            ORDER BY createTime DESC
        """ % (f)
        results = mysql.get_data(sql=sql1, dict_result=True)
        if not results:
            results = mysql.get_data(sql=sql, dict_result=True)
        if results:
            for result in results:
                order = {}
                url = result['datailURL']
                try:
                    net_check()
                    await p.goto(url)
                except errors.TimeoutError:
                    continue
                slider = await p.J('#nocaptcha')
                if slider:
                    while True:
                        print("出现滑块验证码")
                        await asyncio.sleep(2)
                        await p.hover('#nc_1_n1z')
                        await p.mouse.down()
                        await p.mouse.move(2000, 0, {'delay': random.randint(1000, 2000)})
                        await p.mouse.up()
                        try:
                            p.waitForSelector(".nc-lang-cnt a", timeout=10000)
                            await asyncio.sleep(2)
                            await p.click(".nc-lang-cnt a")
                        except errors.TimeoutError:
                            break
                        except errors.PageError:
                            break
                try:
                    await p.waitForSelector('#detail-panel', timeout=30000)
                except Exception as e:
                    continue
                content = await p.content()
                a = re.search("var data = JSON.parse\('(.*)'\);", content).group(1)
                b = a.replace('\\\\\\"', '')
                data = b.replace('\\"', '"')
                m = json.loads(data)
                order['actualFee'] = m['mainOrder']['payInfo']['actualFee']['value']
                order['orderStatus'] = status_format(m['mainOrder']['statusInfo']['text'])
                if order['orderStatus'] == '等待买家付款':
                    order['isDetaildown'] = 2
                else:
                    order['isDetaildown'] = 1
                coupon = 0
                for k, v in m['mainOrder']['payInfo'].items():
                    if k == 'promotions':
                        promotions = m['mainOrder']['payInfo']['promotions']
                        for i in range(len(promotions)):
                            if 'prefix' and 'suffix' in promotions[i]:
                                coupon_temp = re.search("(\d+\.\d+)", promotions[i]['value'])
                                if coupon_temp:
                                    coupon += float(coupon_temp.group(1))
                order['couponPrice'] = round(coupon, 2)
                for k, v in m.items():
                    if k == 'buyMessage':
                        order['buyerComments'] = v
                orderNo = m['mainOrder']['id']
                order_info = m['mainOrder']['orderInfo']['lines'][1]['content']
                for i in range(len(order_info)):
                    if order_info[i]['value']['name'] == '支付宝交易号:':
                        try:
                            order['tradeNo'] = order_info[i]['value']['value']
                        except KeyError:
                            order['tradeNo'] = None
                    # elif order_info[i]['value']['name'] == '创建时间:':
                    #     order['createTime'] = order_info[i]['value']['value']
                    # elif order_info[i]['value']['name'] == '发货时间:':
                    #     order['shipTime'] = order_info[i]['value']['value']
                    elif order_info[i]['value']['name'] == '付款时间:':
                        order['payTime'] = order_info[i]['value']['value']
                ship_info = m['tabs']
                for i in range(len(ship_info)):
                    if ship_info[i]['id'] == 'logistics':
                        temp = ship_info[i]['content']
                        for k, v in temp.items():
                            if k == 'logisticsName':
                                order['shippingCompany'] = v
                            elif k == 'shipType':
                                order['shippingMethod'] = v
                            elif k == 'logisticsNum':
                                order['shippingNo'] = v
                            # elif k == 'logisticsUrl':
                            #     order['shipUrl'] = "https" + v
                            elif k == 'address':
                                rec_info = v
                                order['receiverName'] = rec_info.split("，")[0].replace(" ", "")
                                order['receiverPhone'] = rec_info.split("，")[1]
                                order['receiverAddress'] = "".join(rec_info.split("，")[2:])
                sub_orders = m['mainOrder']['subOrders']
                # mainOrder.subOrders[10].tradeStatus[0].content[0].value
                line_no = 0
                for i in range(len(sub_orders)):
                    if sub_orders[i]['tradeStatus'][0]['content'][0]['value'] == '已取消':
                        continue
                    item = {}
                    temp = 0
                    itemNo = line_no
                    line_no += 1
                    if sub_orders[i]['promotionInfo']:
                        for j in sub_orders[i]['promotionInfo']:
                            for x in j['content']:
                                for k, v in x.items():
                                    if k == 'value':
                                        p_list = re.findall("-?\d+\.\d+", v)
                                        if p_list:
                                            temp += float(p_list.pop())
                    item['unitBenefits'] = temp
                    mysql.update_data(t="tb_order_detail_spider", set=item, c={'orderNo': orderNo, 'itemNo': itemNo})
                mysql.update_data(t="tb_order_spider", set=order, c={'orderNo': orderNo})
                Verify()
                while True:
                    s = random.random()
                    if s > 0.9:
                        for i in range(int(s * n_o_time)):
                            await asyncio.sleep(1)
                            print(">", end="", flush=True)
                        print("")
                        break
        else:
            pass
        await p.close()
        await self.run_order_detail_spider()


if __name__ == '__main__':
    s = SlaverSpider()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(s.run_link_spider())
    # loop.run_until_complete(s.run_order_detail_spider())
"""
import pymysql
from settings import local_server

sql = "SELECT * FROM taobaoordersdetail order by Id"
con = pymysql.connect(**local_server)
cursor_dict = con.cursor(cursor=pymysql.cursors.DictCursor)
cursor_dict.execute(sql)
result = cursor_dict.fetchall()
temp = ""
item_no = 0
for r in result:
    orderNo = r['OrderNo']
    id = r['Id']

    if temp == orderNo:
        item_no += 1
    else:
        item_no = 0
        temp = orderNo
    print(orderNo, end=":")
    print(item_no)
    sql = "UPDATE taobaoorders SET ExtCode='%s' WHERE Id='%s'" % (item_no, id)
    try:
        cursor_dict.execute(sql)
    except Exception:
        con.rollback()
    else:
        con.commit()
con.close()
"""
