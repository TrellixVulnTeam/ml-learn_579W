#!/user/bin/env python
# -*- coding: utf-8 -*-
# @File  : instagram.py.py
# @Author: sl
# @Date  : 2021/10/9 - 下午8:52


import os
import re
import sys
import json
import time
import random
import requests
from hashlib import md5
from pyquery import PyQuery as pq

url_base = 'https://www.instagram.com/'
uri = 'https://www.instagram.com/graphql/query/?query_hash=a5164aed103f24b03e7b7747a2d94e3c&variables=%7B%22id%22%3A%22{user_id}%22%2C%22first%22%3A12%2C%22after%22%3A%22{cursor}%22%7D'


headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
    'cookie': 'ig_did=E9EC0473-1CD0-4C7C-AE33-E00E9CE7D839; mid=Xc6hVgAEAAEGjqTYGm7_rVdYqaSt; csrftoken=NGGjfuhYuvnxMrcIAezJ2SOBfUFow76V; sessionid=2287083670:qE8hwXyuIIel6v:0; ig_nrcb=1; ds_user_id=2287083670; fbm_124024574287414=base_domain=.instagram.com; shbid="4547\0542287083670\0541665314060:01f74e5e0a52569a7653fb161d4a55decca3254a0a969ec488586721b3465b69a01a9665"; shbts="1633778060\0542287083670\0541665314060:01f77e6dd172acb9300e0960b0b7d7cc95cd8ee03db24b30928020fc3bec4d48cbe99f41"; fbsr_124024574287414=CE7OmT4ItlNeRb5nBXfqE5KqKQcrERDVp_G8EYyR74o.eyJ1c2VyX2lkIjoiMTAwMDA3MDg5MjI4ODI4IiwiY29kZSI6IkFRRHpvRmNDcGZYMWU5NjJfcUdSZFZDRkVxckw0d2Y4MFJkSk84am5rdlNXV2VOX0NiWUpuNThZaExFWnFMUTJxZ3ZCQ1pndnh2Z3lHUXk3T1gxU1lHWlVQRDQwZVUyWXVsbldMVjVkVUpwRXpTTlJaVG9VRGd5bzkzUGMzRlZLbGc1SldobTNLMjRFT2NWSGpDZWYyT1d6d3VDbkZodXpXMjEwaTRDeHhlVk9nTkRZbFNwYTQwdVFtWEhaRm1yeVBPRV9sZTNSQkNRQjBWZ25sTVV4bkttVjBMRndzTUN3RmlhUEhXZW5ZMEpTSlVBenhnNDRrcHc2UVV5T0FjVEd0NEgtNEsya0xVWlNfdXQ2ZnY2d0paNnRMeElJRzdlUmU0Rkg5a1g5SlFIUFU2MEJ0SVhPSWJOSTVIc09FMTZGb19RNGI4dWZkSGNoVGNNLU4tMFF2VXhGIiwib2F1dGhfdG9rZW4iOiJFQUFCd3pMaXhuallCQU9zclB1OFdXNXRaQUt2ZUFGV3AwZENRMTFyejM3c2xZaFpCWkN4anFLcW15NHhPa010OVJYaFVFNzJpb2k2aDBYSEl0RHpNb3lieW9NSjI5TFJ2ZEwzVVZaQVpDdG5oYUpibnN3WVcxYUlFZEZkaDd3bnVQdHBaQlBXRjNyQVltTmo3b3hzMDl2WkFaQnliT0dHd0c5ektyUWtKWkNQSWlBbmJqak5qbFpCb3BJM0x2MERieERvWkJJWkQiLCJhbGdvcml0aG0iOiJITUFDLVNIQTI1NiIsImlzc3VlZF9hdCI6MTYzMzc4NDA3Nn0; rur="VLL\0542287083670\0541665320094:01f79caa5835c52399b1465917079dcb7f8ceb7ea2da13cd4604e411e77e9d5dca8f3e4c"'
}


def get_html(url):
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        else:
            print('请求网页源代码错误, 错误状态码：', response.status_code)
    except Exception as e:
        print(e)
        return None


def get_json(url):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print('请求网页json错误, 错误状态码：', response.status_code)
    except Exception as e:
        print(e)
        time.sleep(60 + float(random.randint(1, 4000))/100)
        return get_json(url)


def get_content(url):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.content
        else:
            print('请求照片二进制流错误, 错误状态码：', response.status_code)
    except Exception as e:
        print(e)
        return None


def get_urls(html):
    urls = []
    user_id = re.findall('"profilePage_([0-9]+)"', html, re.S)[0]
    print('user_id：' + user_id)
    doc = pq(html)
    items = doc('script[type="text/javascript"]').items()
    for item in items:
        if item.text().strip().startswith('window._sharedData'):
            js_data = json.loads(item.text()[21:-1], encoding='utf-8')
            edges = js_data["entry_data"]["ProfilePage"][0]["graphql"]["user"]["edge_owner_to_timeline_media"]["edges"]
            page_info = js_data["entry_data"]["ProfilePage"][0]["graphql"]["user"]["edge_owner_to_timeline_media"]['page_info']
            cursor = page_info['end_cursor']
            flag = page_info['has_next_page']
            for edge in edges:
                if edge['node']['display_url']:
                    display_url = edge['node']['display_url']
                    print(display_url)
                    urls.append(display_url)
            print(cursor, flag)
    while flag:
        url = uri.format(user_id=user_id, cursor=cursor)
        js_data = get_json(url)
        infos = js_data['data']['user']['edge_owner_to_timeline_media']['edges']
        cursor = js_data['data']['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']
        flag = js_data['data']['user']['edge_owner_to_timeline_media']['page_info']['has_next_page']
        for info in infos:
            if info['node']['is_video']:
                video_url = info['node']['video_url']
                if video_url:
                    print(video_url)
                    urls.append(video_url)
            else:
                if info['node']['display_url']:
                    display_url = info['node']['display_url']
                    print(display_url)
                    urls.append(display_url)
        print(cursor, flag)
        # time.sleep(4 + float(random.randint(1, 800))/200)    # if count > 2000, turn on
    return urls


def main(user):
    url = url_base + user + '/'
    html = get_html(url)
    urls = get_urls(html)
    dirpath = r'.\{0}'.format(user)
    if not os.path.exists(dirpath):
        os.mkdir(dirpath)
    for i in range(len(urls)):
        print('\n正在下载第{0}张： '.format(i) + urls[i], ' 还剩{0}张'.format(len(urls)-i-1))
        try:
            content = get_content(urls[i])
            endw = 'mp4' if r'mp4?_nc_ht=scontent' in urls[i] else 'jpg'
            file_path = r'.\{0}\{1}.{2}'.format(user, md5(content).hexdigest(), endw)
            if not os.path.exists(file_path):
                with open(file_path, 'wb') as f:
                    print('第{0}张下载完成： '.format(i) + urls[i])
                    f.write(content)
                    f.close()
            else:
                print('第{0}张照片已下载'.format(i))
        except Exception as e:
            print(e)
            print('这张图片or视频下载失败')


if __name__ == '__main__':
    # user_name = sys.argv[1]
    user_name = "syc_joycechu_"
    start = time.time()
    main(user_name)
    print('Complete!!!!!!!!!!')
    end = time.time()
    spend = end - start
    hour = spend // 3600
    minu = (spend - 3600 * hour) // 60
    sec = spend - 3600 * hour - 60 * minu
    print(f'一共花费了{hour}小时{minu}分钟{sec}秒')
