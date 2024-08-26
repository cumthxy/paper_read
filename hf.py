# -*- coding: utf-8 -*-
"""
@file    : hf.py
@date    : 2024-07-11
@author  : leafw
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re 
import conf
import os
import shutil
from openai import OpenAI
import subprocess

from dotenv import load_dotenv

load_dotenv()
api_key=os.environ.get("OPENAI_API_KEY")

base_url = 'https://huggingface.co'
openai_base_url = "https://api.deepseek.com"
model_name = "deepseek-chat"
client = OpenAI(api_key=api_key, base_url=openai_base_url)
prompt= conf.en_zh

def chat(message):
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": message},
        ],
    )
    print(response)
    return response.choices[0].message.content
    
def extract_yy_text(text):
    # 使用正则表达式匹配 "### 意译" 后面的文本
    pattern = r'### 意译\s*(```)?(.+?)(```)?(?=###|\Z)'
    match = re.search(pattern, text, re.DOTALL)

    if match:
        # 提取匹配的文本，去除可能存在的 ``` 符号
        extracted_text = match.group(2).strip()
        return extracted_text
    else:
        return "未找到意译部分"
    


class Article:
    def __init__(self, title, arxiv_link, abstract):
        self.title = title
        self.arxiv_link = arxiv_link
        self.abstract = abstract


def en_content(article: Article):
    return f"""
[{article.title}]({article.arxiv_link})
{article.abstract}
"""


def home_parse(url):
    """
    获取文章列表
    :return:
    """
    response = requests.get(url)
    html_content = response.text

    # 解析HTML内容
    soup = BeautifulSoup(html_content, 'html.parser')

    articles = soup.find_all('article')

    article_list = []
    for article in articles:
        title = article.find('h3').get_text(strip=True)
        link = article.find('a')['href']
        leading_nones = article.find_all('div', class_='leading-none')
        likes_div = None
        for item in leading_nones:
            if item.get('class') == ['leading-none']:
                likes_div = item
                break
        likes = int(likes_div.get_text(strip=True))
        if likes < 20:
            break
        print(f"Title: {title}")
        print(f"Link: {link}")
        print(f"Likes: {likes}")
        print("------")
        one = {'title': title, 'link': base_url + link, 'likes': likes}
        article_list.append(one)
    return article_list


def parse_article(url, title):
    response = requests.get(url)
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')

    article_content = soup.find('p', class_='text-gray-700 dark:text-gray-400')
    content = article_content.get_text(strip=True)
    arxiv_link = soup.find('a', class_='btn inline-flex h-9 items-center')['href']

    return Article(title, arxiv_link, content)


def weekly_get():
    # 获取当前日期
    today = datetime.today()
    # 计算当前周的周一日期
    start_of_week = today - timedelta(days=today.weekday())
    # 创建一个包含周一到周五日期的列表
    weekdays = [start_of_week + timedelta(days=i) for i in range(5)]
    return [day.strftime('%Y-%m-%d') for day in weekdays]



def weekly_paper(output_path=''):
    days = weekly_get()
    output_path = days[0].replace('-', '') + '_' + days[-1].replace('-', '') + '.md'
    # 这一份是防止翻译不太好或者其他问题先留存下
    en_articles_content = []
    with open(output_path, 'w') as en:
        for day in days:
            print(f'开始处理日期: {day}')
            url = base_url + '/papers?date=' + day
            article_list = home_parse(url)
            print(f'{day} 主页解析完毕')
            for item in article_list:
                print(f'解析文章{item["title"]}开始')
                article = parse_article(item['link'], item['title'])
                content = en_content(article)
                en_articles_content.append({"en_title":article.title,"en_content":content})
            print(f'日期 {day} 处理结束')
    print('英文输出完毕')
    with open(output_path, 'w') as f:
        for each in en_articles_content:
            en_article = each['en_content']
            en_title = each['en_title']
            print(en_title)
            zh_article = extract_yy_text(chat(en_article))
            result =  f"""
## {en_title}
{zh_article}
"""
            f.write(result + '\n\n')
            
            
if __name__ =="__main__":
    #1.移动之前存在的 md到年月文件夹中。
    date = datetime.now()
    year_str = date.strftime('%Y')
    month_str = date.strftime('%Y%m')
    paper_dir = "paper/{}/{}".format(year_str,month_str)
    if not os.path.exists(paper_dir):
        os.makedirs(paper_dir)
    for item in os.listdir("."):
        if item.endswith('.md'):     
            shutil.move(item, paper_dir)
    weekly_paper()
    cmd1 = "git add ."
    cmd2 = "git commit -m update"
    cmd3 = "git push"
    subprocess.getoutput(cmd1)
    subprocess.getoutput(cmd2)
    subprocess.getoutput(cmd3)
