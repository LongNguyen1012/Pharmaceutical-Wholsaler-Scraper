"""
Created on Thu Jul 21 23:54:20 2016

@author: Long Nguyen
"""
import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
import gc, re
from bs4 import BeautifulSoup
import multiprocessing, os
from os import listdir
from string import ascii_lowercase
from collections import defaultdict
from multiprocessing.managers import BaseManager, DictProxy
from multiprocessing import Process, Manager
import csv
import urllib
from selenium.common.exceptions import ElementNotVisibleException
import sys
import datetime


class MyManager(BaseManager):
    pass


MyManager.register('defaultdict', defaultdict, DictProxy)

def GetCredential():
#    input_data = []
#    with open('credential.csv', 'rb') as (in_file):
#        csv_reader = csv.reader(in_file)
#        for line in csv_reader:
#            input_data.append(line[1])
#
#    user_name = input_data[0]
#    pass_word = input_data[1]
    user_name = '006716'
    pass_word = 'Medcare1'
    return (
     user_name, pass_word)


def MakeEmptyFolder(folder):
    path = os.getcwd() + '\\{}'.format(folder)
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def CreateMasterFile():
    path = MakeEmptyFolder('RDC')
    file_list = listdir(path)
    out_file = path + '\\master.csv'
    with open(out_file, 'wb') as master_file:
        master_file.write('Name,Vendor,Price,UPC\n')
        for f in file_list:
            in_file = path + '\\' + f
            with open(in_file) as infile:
                first_line = True
                for line in infile:
                    if first_line:
                        first_line = False
                    else:
                        master_file.write(line)


def InitialScraper(scrape_list, session_log):
    user_name, pass_word = GetCredential()
    url = 'https://rdc.rdcdrug.com/BrowseBy?by=12'
    chromepath = os.getcwd() + '\\chrome\\chromedriver.exe'
    driver = webdriver.Chrome(chromepath)
    error = True
    while error:
        try:
            driver.get(url)
            print 'about to look for element'
            element = WebDriverWait(driver, 10).until(lambda driver: driver.find_element_by_id('exampleInputEmail1') and driver.find_element_by_id('exampleInputPassword1'))
        except:
            error = True
        else:
            error = False

    print 'Found'
    current_url = driver.command_executor._url
    session_id = driver.session_id
    session_log[current_url] = session_id
    username = driver.find_element_by_id('exampleInputEmail1')
    username.send_keys(user_name)
    password = driver.find_element_by_id('exampleInputPassword1')
    password.send_keys(pass_word)
    driver.find_element_by_class_name('btn-block').click()
    time.sleep(2)
    print 'Getting page source'
    page_source = driver.page_source
    print 'Getting page source complete'
    print 'Scraping'
    soup = BeautifulSoup(page_source)
    del page_source
    gc.collect()
    div_tags = soup.findAll('div',{'class': 'categoryGroup'})
#    total_dict = {}
    for div in div_tags:
        a_tags = div.findAll('a')
        for a in a_tags:
            data_category = a['data-category']
            data_string = urllib.quote(str(a['data-description'])).replace("+","%20")
            scrape_url = 'https://rdc.rdcdrug.com/ProductSearch?q={}%7C{}&by=12'.format(data_category, data_string)
            scrape_list.append(scrape_url)
            #############################
#            span_num = int(str(a.find('span').text).strip("(").strip(")").strip(" "))
#            total_dict[scrape_url] = span_num
    print 'Success...'
    driver.close()


def NumberMap(total):
    temp = {}
    if total >= 10:
        length = (total - (total % 10))/10
        for i in range(length):
            temp[i] = 10
        if (total % 10) != 0:
            temp[i+1] = total % 10
    else:
        temp[0] = total
    return temp


def GetLength(tags):
    count = 0
    for row in tags:
        count += 1
    return count


def MainScraper(scrape_list, log_list, session_log, process_id):
    user_name, pass_word = GetCredential()
    url = 'https://rdc.rdcdrug.com/'
    chromepath = os.getcwd() + '\\chrome\\chromedriver.exe'
    driver = webdriver.Chrome(chromepath)
    error = True
    while error:
        try:
            driver.get(url)
            print 'about to look for element'
            element = WebDriverWait(driver, 10).until(lambda driver: driver.find_element_by_id('exampleInputEmail1') and driver.find_element_by_id('exampleInputPassword1'))
        except:
            error = True
        else:
            error = False

    print 'Found'
    current_url = driver.command_executor._url
    session_id = driver.session_id
    session_log[current_url] = session_id
    username = driver.find_element_by_id('exampleInputEmail1')
    username.send_keys(user_name)
    password = driver.find_element_by_id('exampleInputPassword1')
    password.send_keys(pass_word)
    driver.find_element_by_class_name('btn-block').click()
    time.sleep(4)
    for scrape_link in scrape_list:
        driver.get(scrape_link)
        filepath = MakeEmptyFolder('RDC')
        filename = '{}\\process_{}.csv'.format(filepath, process_id)
        count = 0
        with open(filename, 'a') as outfile:
            error_count = 0
            while True:
                time.sleep(5)
                print 'Getting page source'
                page_source = driver.page_source
                print 'Getting page source complete'
                print 'Scraping'
                soup = BeautifulSoup(page_source)
                del page_source
                gc.collect()
                div_tags = soup.findAll('div',{'class': 'data-cont'})
                tags_len = GetLength(div_tags)
                if tags_len > 0:
                    break
                else:
                    error_count += 1
                    if error_count == 50:
                        break
                    driver.refresh()
            for row in div_tags:
                product_name, vendor, price, upc = ExtractData(row)
                out_row = '"%s",%s,%s,%s\n' % (product_name, vendor, price, upc)
                outfile.write(out_row)
                count += 1
            while True:
                try:
                    pagination = driver.find_element_by_css_selector('a[ng-click="nextPage()"]')
                    pagination.click()
                except ElementNotVisibleException as ex:
                    break
                else:
                    error_count = 0
                    while True:
                        time.sleep(5)
                        page_source = driver.page_source
                        soup = BeautifulSoup(page_source)
                        del page_source
                        gc.collect()
                        div_tags = soup.findAll('div',{'class': 'data-cont'})
                        tags_len = GetLength(div_tags)
                        if tags_len > 0:
                            break
                        else:
                            error_count += 1
                            if error_count == 50:
                                break
                            driver.refresh()
                    for row in div_tags:
                        product_name, vendor, price, upc = ExtractData(row)
                        out_row = '"%s",%s,%s,%s\n' % (product_name, vendor, price, upc)
                        outfile.write(out_row)
                        count += 1
#        filepath = MakeEmptyFolder('total')
#        filename = '{}\\total_{}.csv'.format(filepath, process_id)
#        with open(filename,'a') as outfile:
#            original = total_dict[scrape_link]
#            out_row = '"%s",%s,%s\n' % (scrape_link, original, count)
#            outfile.write(out_row)
        log_list.append(scrape_link)
    driver.close()


def ExtractData(row):
    a_tag = row.find('a',{'class':'ng-binding'})
    product_name = str(a_tag.text)
    print 'Getting ', product_name
    p_tags = row.findAll('p')
    vendor = str(p_tags[4].text).strip('RDC #: ')
    upc = str(p_tags[6].text).strip('UPC #: ')
    price = str(p_tags[8].findAll('span')[2].text)
    print 'Success...'
    
    return product_name, vendor, price, upc


def BuildSchedule(scrape_map_list):
    n = int(len(scrape_map_list)) / 6
    count = 0
    total_count = 0
    schedule = []
    temp = []
    for key in scrape_map_list:
        count += 1
        total_count += 1
        temp.append(key)
        if count == n or total_count == len(scrape_map_list):
            schedule.append(temp)
            temp = []
            count = 0

    return schedule


if __name__ == '__main__':
    try:
        start_time = time.time()
        multiprocessing.freeze_support()
        manager = Manager()
        log_list = manager.list()
        remaining_list = []
        session_log = manager.dict()
        jobs = []
        scrape_list = []
        InitialScraper(scrape_list, session_log)
        schedule = BuildSchedule(scrape_list)
        i = 0
        
    #    MainScraper(scrape_list, log_list, session_log, i, total_dict)
            
        filepath = MakeEmptyFolder('RDC')
        file_list = listdir(filepath)
        for f in file_list:
            file_name = filepath + '\\' + f
            os.remove(file_name)
            
    #    filepath_total = MakeEmptyFolder('total')
    #    file_list = listdir(filepath_total)
    #    for f in file_list:
    #        file_name_total = filepath_total + '\\' + f
    #        os.remove(file_name_total)
            
        for scrape_list in schedule:
            filename = '{}\\process_{}.csv'.format(filepath, i)
            with open(filename,'w') as outfile:
                outfile.write('Name,Vendor,Price,UPC\n')
    #        filename_total = '{}\\total_{}.csv'.format(filepath_total, i)
    #        with open(filename_total,'w') as outfile:
    #            outfile.write('URL,Original,Actual\n')
            p = Process(target=MainScraper, args=(scrape_list, log_list, session_log, i))
            p.start()
            print 'Starting main process'
            jobs.append(p)
            time.sleep(10)
            i += 1
    
        while True:
            print 'Checking is_alive main'
            if not any((j.is_alive() for j in jobs)):
                break
            else:
                for j in jobs:
                    if not j.is_alive():
                        print 'Detect unresponding main'
                        jobs.pop(jobs.index(j))
                        j.terminate()
    
            time.sleep(5)
    
        for j in jobs:
            print 'Joining main process'
            j.join()
    
        for c in scrape_list:
            if c not in log_list:
                remaining_list.append(c)
    
        print 'Remaining list....', remaining_list
        while len(remaining_list) != 0:
            print 'Closing windows initial.....'
            for current_url in session_log.keys():
                session_id = session_log[current_url]
                try:
                    driver = webdriver.Remote(command_executor=current_url, desired_capabilities={})
                    driver.session_id = session_id
                    driver.close()
                except:
                    continue
    
            session_log = manager.dict()
            print 'Rerun.........'
            schedule = BuildSchedule(remaining_list)
            log_list = manager.list()
            jobs = []
            i = 0
            for scrape_list in schedule:
                p = Process(target=MainScraper, args=(scrape_list, log_list, session_log, i))
                print 'Starting rerun process.....'
                p.start()
                jobs.append(p)
                time.sleep(10)
    
            while True:
                print 'Checking is_alive for rerun process.......'
                if not any((j.is_alive() for j in jobs)):
                    break
                else:
                    for j in jobs:
                        if not j.is_alive():
                            print 'Detect unresponding'
                            jobs.pop(jobs.index(j))
                            j.terminate()
    
                time.sleep(5)
    
            for j in jobs:
                print 'Joining rerun process........'
                j.join()
                
        CreateMasterFile()
        print '--- %s seconds ---' % (time.time() - start_time)
        raw_input()
        
    except Exception as ex:
        print 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
        print ex
        raw_input()
    
