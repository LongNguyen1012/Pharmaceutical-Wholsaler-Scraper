# -*- coding: utf-8 -*-
"""
Created on Thu Jul 21 23:54:20 2016

@author: Long Nguyen
"""

import time
from selenium import webdriver # pip install selenium
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
import gc
import re
from bs4 import BeautifulSoup
import multiprocessing
import os
from os import listdir
from string import ascii_lowercase
from collections import defaultdict
from multiprocessing.managers import BaseManager, DictProxy
from multiprocessing import Process, Manager
import csv
from selenium.webdriver.support.ui import Select

# user_name = 'washingtonavepharmacy@live.com'
# pass_word = 'Acare#5100'

class MyManager(BaseManager):
    pass
    
MyManager.register('defaultdict', defaultdict, DictProxy)

def GetCredential():
    first_line = True
    with open("credential.csv","rb") as in_file:
        csv_reader = csv.reader(in_file)
        for line in csv_reader:
            if first_line:
                user_name = line[1]
                first_line = False
            else:
                pass_word = line[1]
    return user_name, pass_word
	
				
def MakeEmptyFolder():
    path = os.getcwd() + '\drug_folder'
    if not os.path.exists(path): 
        os.makedirs(path)
    return path
        

def CreateMasterFile():
    path = MakeEmptyFolder()
    file_list = listdir(path)    
    out_file = path + "\master.csv"
    with open(out_file, 'wb') as master_file:
        master_file.write("DOE#,Description,Price,On Hand,UPC\n")
        for f in file_list:
            in_file = path + "\\" + f
            with open(in_file) as infile:
                first_line = True
                for line in infile:
                    if first_line:
                        first_line = False
                    else:
                        if '"Over 200"' not in line:
                            master_file.write(line)


def SortList(description_list):
    out_list = []
    for c in description_list:
        out_list.append(c.strip('"'))   
    out_list.sort()
    return out_list
    
                            
def BuildMap(scrape_map, description_list):
    
    if len(description_list) > 200:
        description_list = SortList(description_list)
        index_level = 1
        for search_word in description_list:
            search_char = search_word[0] + search_word[index_level]
            scrape_map[search_char] += 1 # Store data to create scrape map
        all_under_200 = True
        for key in scrape_map.keys():
            if scrape_map[key] > 200:
                under_200 = False
                all_under_200 = all_under_200 and under_200
            else:
                under_200 = True
                all_under_200 = all_under_200 and under_200
        while not all_under_200:
            index_level += 1
            for key in scrape_map.keys():
                if scrape_map[key] > 200:
                    for k in range(len(description_list)):
                        search_word = description_list[k]
                        if search_word[:index_level] == key:
                            start_place = k
                            break
                    for k in range(start_place, start_place + scrape_map[key]):
                        search_word = description_list[k]
                        search_char = key + search_word[index_level]
                        scrape_map[search_char] += 1
                    scrape_map.pop(key, None)
            all_under_200 = True
            for key in scrape_map.keys():
                if scrape_map[key] > 200:
                    under_200 = False
                    all_under_200 = all_under_200 and under_200
                else:
                    under_200 = True
                    all_under_200 = all_under_200 and under_200
    else:
        search_char = description_list[0][0]
        scrape_map[search_char] = len(description_list)
    
    return scrape_map
    
    
def InitialScraper(string, scrape_map, log_list, session_log):

    user_name, pass_word = GetCredential()

    url = "http://vdhub.valuedrugco.com/DesktopDefault.aspx"
    chromepath = os.getcwd() + '\chrome\chromedriver.exe'
    driver = webdriver.Chrome(chromepath) 
    
    # Later include a scraper to get the number of items 
    error = True
    while error:
        try:
            driver.get(url)
            print "about to look for element"
            element = WebDriverWait(driver, 10).until(
                    lambda driver : ((driver.find_element_by_id("ctl00_email")) \
                                    and (driver.find_element_by_id("ctl00_password")))
            )
        except:
            error = True
        else: 
            error = False
            
    print "Found"    
        
    current_url = driver.command_executor._url
    session_id = driver.session_id
    session_log[current_url] = session_id
        
    username = driver.find_element_by_id("ctl00_email")
    username.send_keys(user_name)
 
    password = driver.find_element_by_id("ctl00_password")
    password.send_keys(pass_word)
    
    driver.find_element_by_id("ctl00_SigninBtn").click()
    time.sleep(2)
    
    try:
        driver.find_element_by_id("AccessibleTPsGrid_ctl05_lnkTPNumber").click()
        time.sleep(2)
    except:
        pass
     
    driver.get("http://vdhub.valuedrugco.com/DesktopDefault.aspx?tabindex=2&tabid=26")
    time.sleep(2) 
        
    driver.find_element_by_id("ctl00_lbtnAdvOptions").click()
    time.sleep(2) 
     
    select = Select(driver.find_element_by_name('ctl00$Field'))
    select.select_by_value('2')
    time.sleep(2) 
        
    firsttime = True
    
    for c in string: 
        print "Initial..." + str(c)
        success = False
        count = 0
        
        search = driver.find_element_by_id("ctl00_SearchString")
        search.send_keys(c)
        search.send_keys(Keys.ENTER)  
        
        # Check if the letter leads to a blank page
        while not success: #Assuming first trial not successful
            try:
                WebDriverWait(driver, 5).until(
                        lambda driver : driver.find_element_by_id("ctl00_ShowAll"))
            except:
                print "Refreshing..." + str(count)
                success = False
                count += 1
                driver.refresh()
            else:
                count = 0
                if firsttime:
                    while True:
                        print "First time...clicking"
                        driver.find_element_by_id("ctl00_ShowAll").click()
                        time.sleep(5)
                                              
                        page_source = driver.page_source
                        soup = BeautifulSoup(page_source)
                        
                        button = soup.find("a",{"id":"ctl00_ShowAll"})
                        if button.text != "Turn On Scrolling":
                            print "Button status is off"
                            firsttime = False
                            break
                    
                print "Getting page source"
                page_source = driver.page_source
                print "Getting page source complete"
                            
                print "Scraping"
                soup = BeautifulSoup(page_source)

                del page_source
                gc.collect()
                
                description_list = ExtractDescription(soup)
                
                scrape_map = BuildMap(scrape_map, description_list)
                
                del description_list[:]
                
                print "Success..."
                success = True
                log_list.append(c)
            
            finally:
                if count == 5:
                    log_list.append(c)
                    break
                
    driver.close()


def MainScraper(scrape_list, log_list, session_log):
    
    user_name, pass_word = GetCredential()

    url = "http://vdhub.valuedrugco.com/DesktopDefault.aspx"
    chromepath = os.getcwd() + '\chrome\chromedriver.exe'
    driver = webdriver.Chrome(chromepath) 
    
    # Later include a scraper to get the number of items 
    error = True
    while error:
        try:
            driver.get(url)
            print "about to look for element"
            element = WebDriverWait(driver, 10).until(
                    lambda driver : ((driver.find_element_by_id("ctl00_email")) \
                                    and (driver.find_element_by_id("ctl00_password")))
            )
        except:
            error = True
        else: 
            error = False
            
    print 'found'
    
    current_url = driver.command_executor._url
    session_id = driver.session_id
    session_log[current_url] = session_id
        
    username = driver.find_element_by_id("ctl00_email")
    username.send_keys(user_name)
 
    password = driver.find_element_by_id("ctl00_password")
    password.send_keys(pass_word)

    driver.find_element_by_id("ctl00_SigninBtn").click()
    time.sleep(2)
    
    try:
        driver.find_element_by_id("AccessibleTPsGrid_ctl05_lnkTPNumber").click()
        time.sleep(2)
    except:
        pass
     
    driver.get("http://vdhub.valuedrugco.com/DesktopDefault.aspx?tabindex=2&tabid=26")
    time.sleep(4) 
    
    driver.find_element_by_id("ctl00_lbtnAdvOptions").click()
    time.sleep(2) 
     
    select = Select(driver.find_element_by_name('ctl00$Field'))
    select.select_by_value('2')
    time.sleep(2) 
        
    firsttime = True
    
    for c in scrape_list:
 
        print "Main..." + str(c)
        success = False
        count = 0
            
        # Test to see if window is responsive
        search = driver.find_element_by_id("ctl00_SearchString")
        search.send_keys(c)
        search.send_keys(Keys.ENTER)  
    
        while not success: #Assuming first trial not successful
            try:
                WebDriverWait(driver, 100).until(
                        lambda driver : driver.find_element_by_id("ctl00_ShowAll"))
                
            except:
                print "Refreshing..." + str(count)
                success = False
                count += 1
                driver.refresh()
            else:                        
                if firsttime:
                    while True:
                        print "First time...clicking"
                        driver.find_element_by_id("ctl00_ShowAll").click()
                        time. sleep(5)
                    
                        page_source = driver.page_source
                        soup = BeautifulSoup(page_source)
                    
                        button = soup.find("a",{"id":"ctl00_ShowAll"})
                        if button.text != "Turn On Scrolling":
                            print "Button status is off"
                            firsttime = False
                            break
                    
                print "Found element"
                print "Getting page source"
                time.sleep(4)
                
                page_source = driver.page_source
                print "Getting page source complete"
                        
                print "Scraping"
                soup = BeautifulSoup(page_source)

                del page_source
                gc.collect()
                
                try:
                    doe_list, description_list, price_list, on_hand_list, upc_list = ExtractData(soup)
                except:
                    driver.find_element_by_id("ctl00_ShowAll").click()
            
                WriteToFile(c, doe_list, description_list, price_list, on_hand_list, upc_list)
                
                print "Success..."
                success = True
                log_list.append(c)
        
            finally:
                if count == 5:
                    log_list.append(c)
                    break

    driver.close()
    
    
def InitialWrite():
    
    path = MakeEmptyFolder()
    for c in ascii_lowercase:
        out_file = path + "\drug_" + c + ".csv"
        with open(out_file, 'wb') as csvfile: 
            csvfile.write("DOE#,Description,Price,On Hand,UPC\n")
            
    for n in range(0,10):
        out_file = path + "\drug_" + str(n) + ".csv"
        with open(out_file, 'wb') as csvfile: 
            csvfile.write("DOE#,Description,Price,On Hand,UPC\n")
            

def WriteToFile(c, doe_list, description_list, price_list, on_hand_list, upc_list):
    
    if str(c) not in "0123456789":
        path = MakeEmptyFolder()
        out_file = path + "\drug_" + c[0].lower() + ".csv"
        with open(out_file, 'ab') as csvfile:
    
            for i in range(len(doe_list)):
                if '"Over 200"' not in price_list[i]:
                    doe = doe_list[i]
                    description = description_list[i]
                    price = price_list[i]
                    on_hand = on_hand_list[i]
                    upc = upc_list[i]
                
                    row = '%s,%s,%s,%s,%s\n' % (doe, description, price, on_hand, upc)
                            
                    csvfile.write(row)
               
        del doe_list[:], description_list[:], price_list[:], on_hand_list[:], upc_list[:]
    
    else:
        path = MakeEmptyFolder()
        out_file = path + "\drug_" + str(c) + ".csv"
        with open(out_file, 'ab') as csvfile:
    
            for i in range(len(doe_list)):
                if '"Over 200"' not in price_list[i]:
                    doe = doe_list[i]
                    description = description_list[i]
                    price = price_list[i]
                    on_hand = on_hand_list[i]
                    upc = upc_list[i]
                
                    row = '%s,%s,%s,%s,%s\n' % (doe, description, price, on_hand, upc)
                            
                    csvfile.write(row)
               
        del doe_list[:], description_list[:], price_list[:], on_hand_list[:], upc_list[:]
    
 
def ExtractDescription(soup):
    description_list = []
    pattern = re.compile(r'^(?!.*fixedHeader).*$')
    table = soup.find("table", {"id":"ctl00_myDataGrid"})
    tr = table.findAll("tr", {"class":pattern})
    for r in tr:
            pattern = re.compile(r'lnkDesc')
            description = r.find("a",{"id":pattern})
            desc = str(description.text)
            if "," in desc:
                desc = '"' + str(description.text) + '"'
            description_list.append(desc)
    return description_list
    
    
def GetUPCColumnIndex():
    try:
        with open("upc_column_index.csv","rb") as infile:
            csv_reader = csv.reader(infile)
            for line in csv_reader:
                upc_index = line[0]
    except:
        upc_index = 29
    return upc_index


def ExtractData(soup):
    
    doe_list = []
    description_list = []
    price_list = []
    on_hand_list = []
    upc_list = []
    alloc_list = []
    print "Extracting"

    upc_index = GetUPCColumnIndex()
    pattern = re.compile(r'^(?!.*fixedHeader).*$')
    table = soup.find("table", {"id":"ctl00_myDataGrid"})
    tr = table.findAll("tr", {"class":pattern})
    for r in tr:
        try:
            pattern = re.compile(r'ItemCode')
            doe = r.find("a",{"id":pattern})
            doe_list.append(str(doe.text))
            
            pattern = re.compile(r'lnkDesc')
            description = r.find("a",{"id":pattern})
            desc = str(description.text)
            if '"' in desc:
                desc = desc.replace('"',"'")
                desc = '"' + desc + '"'
            if "," in desc:
                if '"' not in desc:
                    desc = '"' + desc + '"'
            description_list.append(desc)
            
            pattern = re.compile(r'InvoiceCost')
            price = r.find('span', {"id":pattern})
            current_price = '"' + str(price.text) + '"'
            price_list.append(current_price)
                
            pattern = re.compile(r'lblQuantityAvailable')
            on_hand = r.find('span', {"id":pattern})
            on_hand_list.append(str(on_hand.text))
            
            pattern = re.compile(r'lblAllocationQty')
            alloc_qty = r.find('span', {"id":pattern})
            alloc_list.append(str(alloc_qty.text))
			
            td = r.select("td")
            upc_list.append(str(td[upc_index].text))
        except:
            upc_list.append("")
    
    return doe_list, description_list, price_list, on_hand_list, upc_list


def BuildSchedule(scrape_map_list):
    n = int(len(scrape_map_list))/5    
    count = 0
    total_count = 0
    schedule = []
    temp = []
    for key in scrape_map_list:
        count += 1
        total_count += 1
        temp.append(key)
        if (count == n) or (total_count == len(scrape_map_list)):
            schedule.append(temp)
            temp = []
            count = 0
    return schedule
    
    
if __name__ == '__main__':
    
    start_time = time.time()
    
    multiprocessing.freeze_support()

    mgr = MyManager()
    mgr.start()
    manager = Manager()
    
    scrape_map = mgr.defaultdict(int)
    log_list = manager.list()
    remaining_list = []
    
    session_log = manager.dict()
    
    full_list = "0123456789abcdefghijklmnopqrstuvwxyz"
    schedule = ['0123456','789abcd','efghijk','lmnopqr','stuvwxyz']
    
    jobs = []
    for string in schedule:
        p = Process(target = InitialScraper, args = (string, scrape_map, log_list, session_log))
        p.start()
        print "Starting initial process"
        jobs.append(p)
        time.sleep(10)
        
    while True:
        print "Checking is_alive initial"
        if not any(j.is_alive() for j in jobs):
            break
        else:
            for j in jobs:
                if not j.is_alive():
                    print "Detect unresponding initial"
                    jobs.pop(jobs.index(j))
                    j.terminate()
        
        time.sleep(5)
            
    for j in jobs:
        print "Joining initial process"
        j.join()
        
    for c in full_list:
        if c not in log_list:
            remaining_list.append(c)
    print "Remaining initial list....", remaining_list
            
    while len(remaining_list) != 0:
        
        print "Closing windows initial....."
        for current_url in session_log.keys():
            session_id = session_log[current_url]
            try:
                driver = webdriver.Remote(command_executor=current_url,desired_capabilities={})
                driver.session_id = session_id
                driver.close()
            except:
                continue
            
        session_log = manager.dict()
            
        print "Rerun........."
        schedule = BuildSchedule(remaining_list)
        log_list = manager.list()
        jobs = []
        for string in schedule:
            p = Process(target = InitialScraper, args = (string, scrape_map, log_list, session_log))
            print "Starting rerun process....."
            p.start()
            jobs.append(p)
            time.sleep(10)
            
        while True:
            print "Checking is_alive for rerun process......."
            if not any(j.is_alive() for j in jobs):
                break
            else:
                for j in jobs:
                    if not j.is_alive():
                        print "Detect unresponding"
                        jobs.pop(jobs.index(j))
                        j.terminate()
            
            time.sleep(5)
            
        for j in jobs:
            print "Joining rerun process........"
            j.join()
    
    schedule = BuildSchedule(scrape_map.keys())
    path = MakeEmptyFolder()
    file_list = listdir(path)  
    for f in file_list:
        file_name = path + "\\" + f
        os.remove(file_name)
                
    InitialWrite()
    log_list = manager.list()

    jobs = []
    for scrape_list in schedule:
        p = Process(target = MainScraper, args = (scrape_list, log_list, session_log))
        print "Starting main process....."
        p.start()
        jobs.append(p)
        time.sleep(10)
        
    while True:
        print "Checking is_alive main"
        if not any(j.is_alive() for j in jobs):
            break
        else:
            for j in jobs:
                if not j.is_alive():
                    print "Detect unresponding main"
                    jobs.pop(jobs.index(j))
                    j.terminate()
        
        time.sleep(5)
        
    for j in jobs:
        print "Joining main process....."
        j.join()
        
    remaining_list = []
    for c in scrape_map.keys():
        if c not in log_list:
            remaining_list.append(c)
            
    print "Remaining main list....", remaining_list
            
    while len(remaining_list) != 0:
        
        print "Closing windows main....."
        for current_url in session_log.keys():
            try:
                session_id = session_log[current_url]
                driver = webdriver.Remote(command_executor=current_url,desired_capabilities={})
                driver.session_id = session_id
                driver.close()
            except:
                continue
            
        print "Doing rerun for main scrape....."
        schedule = BuildSchedule(remaining_list)
        log_list = manager.list()
        jobs = []
        for scrape_list in schedule:
            p = Process(target = MainScraper, args = (scrape_list, log_list, session_log))
            print "Starting rerun for main scrape....."
            p.start()
            jobs.append(p)
            time.sleep(10)
            print "rerun for main scrape complete"
            
        while True:
            print "Checking unresponding for rerun main scrape...."
            if not any(j.is_alive() for j in jobs):
                break
            else:
                for j in jobs:
                    if not j.is_alive():
                        print "Detect unresponding main"
                        jobs.pop(jobs.index(j))
                        j.terminate()
            
            time.sleep(5)
            
        for j in jobs:
            print "Joining rerun for main scrape....."
            j.join()
    
    CreateMasterFile()

    print("--- %s seconds ---" % (time.time() - start_time))
    
    raw_input()
        
