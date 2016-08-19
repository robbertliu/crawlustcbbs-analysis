#coding:utf-8
'''
date:2016-08-12
version:2.1
mysql table is ustcbbs.csjobsv2full： jobdate   url   title   content
improvement:加入url，方便日后单独对页面进行打开
            修复所有的处理流程上的漏洞
            使用requests库，修复中英文存储转换编码bug
result:已爬取到符合条件的页面，存储进相应表中
'''

import pymysql
import re
import requests
from urllib.request import urlretrieve
from PIL import Image
import subprocess
from bs4 import BeautifulSoup

database = 'ustcbbs'
conn = pymysql.connect(host='localhost', port=3306, user='root', passwd='0551', db=database, charset='utf8')
cur = conn.cursor()

def processImage(location):
    image = Image.open(location)

    image = image.point(lambda x: 0 if x < 143 else 255)
    newFilePath = 'raw-' + location
    image.save(newFilePath)

    imageName = newFilePath.split('.')[0]
    command = [r'C:\Program Files\Tesseract-OCR\tesseract.exe', newFilePath,  imageName, '-l', 'chi_sim']

    child = subprocess.Popen(command)
    child.wait()
    outputFile = open(imageName + '.txt', 'r', encoding='utf-8')
    content = outputFile.read().strip()
    #print('content in image:', content)
    outputFile.close()
    return content

def getCSlink(startLink):
    response = requests.get(startLink)
    html = response.text

    content = BeautifulSoup(html, 'html.parser')
    csLink = content.find('a', {'title': 'CS'}).attrs['href']
    return csLink

baseBoardLink = 'https://bbs.ustc.edu.cn/cgi/'
jobWords = ['校园招聘', '校招', '秋招', '内推', '招聘']
filterWords = ['实习']

def getLinks(startLink):
    csFullLink = baseBoardLink + startLink
    response = requests.get(csFullLink)
    html = response.text
    content = BeautifulSoup(html, 'html.parser')

    # 1step:assay the article link
    articleLinks = content.findAll('tr', {'class': 'new'})

    for articleTag in articleLinks:
        label = articleTag.find('a', {'class': 'label'}).get_text()

        #此链接中有工作标签
        if label:
            if '[工作]' == label:
                newLink = articleTag.find('a', {'class': 'o_title'}).attrs['href']
                assayArticle(newLink)
        else:
            #过滤掉回复的帖子
            reply = articleTag.find('a', {'class': 'title_re'})
            if not reply:
                title = articleTag.find('a', {'class': 'o_title'}).get_text()
                #过滤掉实习的帖子
                if '实习' in title:
                    #print('实习')
                    #全职bug消除：实习/全职
                    if '全职' in title:
                        newLink = articleTag.find('a', {'class':'o_title'}).attrs['href']
                        assayArticle(newLink)
                else:
                    #遍历工作帖子，如果找到了，则进行爬取和存储，否则，直接过滤
                    for word in jobWords:
                        if word in title:
                            newLink = articleTag.find('a', {'class':'o_title'}).attrs['href']
                            assayArticle(newLink)
                            break
    # 2step:get the next page
    try:
        nextPage = content.find('a', {'class': 'prev'}).attrs['href']
    #已经遍历结束，则会儿产生一个keyerror
    except KeyError:
        print('All pages crawl done!')
        return
    #遇到了其他的错误
    except Exception as e:
        print('Some errors raised in content.find!')
        print(e)
    getLinks(nextPage)

imageNum = 0

def assayArticle(link):
    global imageNum
    fullLink = baseBoardLink + link
    #print('fullLink in assayArticle:', fullLink)

    response = requests.get(fullLink)
    html = response.text
    bsobj = BeautifulSoup(html, 'html.parser')

    content = bsobj.find('div', {'class': 'post_text'}).get_text()
    lines = re.findall(re.compile('\n[^\n]*'), content)

    #分析title，date，content
    title = lines[1]
    print('title:', title)
    date = lines[2]
    times = re.findall(re.compile('\d+'), date)
    timestr = str(times[0]) + '-' + str(times[1]) + '-' + str(times[2]) + ' ' + str(times[3]) + ':' + str(times[4]) + ':' + str(times[5])
    #print('time:', timestr)
    startrow = 3
    comefrom = 'bbs.ustc.edu.cn'
    while startrow < len(lines):
        if re.search(comefrom, lines[startrow]):
            break
        else:
            startrow += 1
    content = lines[3:startrow]
    text = ''
    text = text.join(content)
    #print('text:', text)

    #如果有照片，开始分析照片
    images = bsobj.find('div', {'class': 'post_text'}).findAll('img')
    #print('images:', images)

    if images:
        imageContent = ''
        for image in images:
            imageHref = image.attrs['src']
            imageLink = baseBoardLink + imageHref
            #print('imageLink:', imageLink)
            try:
                urlretrieve(imageLink, 'image' + str(imageNum) + '.png')
            except Exception as e:
                print(e)
                print('image raised error!Ignore it!')
                print('fullLink in assayArticle:', fullLink)
                print('imageLink:', imageLink)
                break
            imageContent += processImage('image' + str(imageNum) + '.png')
            imageNum += 1
        else:
            #将照片分析出来的内容添加进正文内容中
            previousContent = bsobj.find('div', {'class': 'post_text'}).find('img').parent.previous_sibling.previous_sibling
            imageIndex = text.find(previousContent)
            imageIndex += len(previousContent)
            text = text[:imageIndex] + imageContent + text[imageIndex:]
            #print('alltext:', text)

    storeINdatabase(timestr, fullLink, title, text)

def storeINdatabase(timestr, url, title, text):
    cur.execute('select * from csjobsv2full where jobdate = %s', timestr)
    if cur.rowcount == 0:
        cur.execute('insert into csjobsv2full (jobdate,url,title,content) values(%s,%s,%s,%s)', (timestr, url, title, text))
        conn.commit()

def main(link):
    startPage = getCSlink(link)
    getLinks(startPage)

startLink = 'https://bbs.ustc.edu.cn/cgi/bbsindex'
main(startLink)

cur.close()
conn.close()

