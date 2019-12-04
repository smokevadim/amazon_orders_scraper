# -*- coding: utf-8 -*-
from os import path

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from vars import *
from datetime import datetime as dt
import time
import csv

CURRENT_DIR = path.dirname(path.realpath(__file__))
ver = '1.4'

if BROWSER == 'chrome':
    DRIVER = path.join(CURRENT_DIR, 'chromedriver.exe')
    options = webdriver.ChromeOptions()
    options.add_argument("--user-data-dir=chrome-data")
    # headless mode (without window)
    # options.add_argument('headless')
    # options.add_argument("--window-size=1920x1080")
    driver = webdriver.Chrome(DRIVER, options=options)
else:
    # DRIVER = path.join(CURRENT_DIR, 'geckodriver.exe')
    DRIVER = CURRENT_DIR
    options = webdriver.FirefoxOptions()
    driver = webdriver.Firefox(DRIVER, options=options)

order_list = []


def save_pic(driver):
    try:
        driver.save_screenshot(str(dt.now().strftime('%d-%m-%Y %H-%M-%S')) + '.png')
    except Exception as e:
        print('Can not write screenshot to file! ({})'.format(e))


def get_years(driver):
    driver.get(BASE_LINK +
               '/gp/your-account/order-history?ie=UTF8&digitalOrders=1&opt=ab&returnTo=&unifiedOrders=1&')
    _years = driver.find_elements_by_xpath('//form[@id="timePeriodForm"]/*/select[@name="orderFilter"]/option')

    if len(_years) == 0:
        print('Something go wrong (maybe site need to be authorized again?')
        return

    years = []
    for year in reversed(_years):
        if '20' in year.text:
            if int(year.text) >= int(START_YEAR):
                years.append(int(year.text))
    return years


def wait_for_user_auth():
    try:
        element_present = EC.presence_of_element_located((By.NAME, 'claimspicker'))
        WebDriverWait(driver, 60).until_not(element_present)
        element_present = EC.presence_of_element_located((By.XPATH, '//h1[text()="Überprüfung Ihrer Identität"]'))
        WebDriverWait(driver, 240).until_not(element_present)
    except Exception as e:
        print(e)
        save_pic(driver)


def make_login(driver):
    actions = ActionChains(driver)

    # login
    try:
        driver.find_element_by_xpath('//*[@id="nav-link-accountList"]').click()
        input_login = driver.find_element_by_xpath('//input[@name="email"]')
        actions.move_to_element(input_login).send_keys(ACC_LOGIN).perform()
        actions.reset_actions()
        driver.find_element_by_xpath('//input[@id="continue"]').click()
    except:
        print('no login')
        save_pic(driver)

    # password
    try:
        time.sleep(2)
        input_password = driver.find_element_by_xpath('//input[@name="password"]')
        try:
            actions.move_to_element(input_password).send_keys(ACC_PASSWORD).perform()
        except:
            driver.find_element_by_xpath('//input[@name="password"]').send_keys(ACC_PASSWORD)
        actions.reset_actions()
        driver.find_element_by_xpath('//input[@name="rememberMe"]').click()
        driver.find_element_by_xpath('//input[@id="signInSubmit"]').click()
    except:
        print('no pass')
        save_pic(driver)

    try:
        if 'Überprüfung erforderlich' in driver.find_element_by_xpath('//h1').text:
            wait_for_user_auth()
    except:
        pass

    try:
        if 'Wichtige Mitteilung!' in driver.find_element_by_xpath('//h4').text:
            # wait user captcha
            element_present = EC.presence_of_element_located((By.CLASS_NAME, 'a-alert-content'))
            WebDriverWait(driver, 60).until_not(element_present)
            try:
                if 'Überprüfung erforderlich' in driver.find_element_by_xpath('//h1').text:
                    wait_for_user_auth()
            except:
                pass
    except:
        pass


def check_telephone_auth():
    try:
        if 'Überprüfung erforderlich' in driver.find_element_by_xpath('//h1[text()="Überprüfung erforderlich"]').text:
            wait_for_user_auth()
    except:
        pass


def check_input_password():
    try:
        check_telephone_auth()
    except:
        pass
    try:
        check_captcha()
    except:
        pass
    try:
        driver.find_element_by_xpath('//input[@type="password"')
        make_login(driver)
    except:
        pass

    return


def check_captcha():
    try:
        driver.find_element_by_xpath('//h4[text()="Geben Sie die angezeigten Zeichen im Bild ein:"]')
        actions.send_keys(Keys.F5).perform()
        actions.reset_actions()
        driver.get(driver.current_url)
    except:
        pass
    return


def get_title(item):
    try:
        title = item.find('a').text.strip()
        return title
    except:
        pass


def get_price(item):
    try:
        price = item.find('span', class_='a-color-price').find('nobr').text.split(' ')[1].replace(',', '.')
        return price
    except:
        pass


def get_delivery_date(item):
    try:
        delivery_date = item.find('div', class_='a-row a-size-small').text.split(' ')[-1]
        day = int(delivery_date.split('.')[0])
        day = '{0:02}'.format(day)
        month = int(delivery_date.split('.')[1])
        year = int(delivery_date.split('.')[2])
        year = (year) if month > 1 else (year - 1)
        month = (month - 1) if month > 1 else 12
        month = '{0:02}'.format(month)

        return '{}.{}.{}'.format(day, month, year)
    except:
        pass


def get_ordering_date(order):
    try:
        ordering_date = order.find('div', class_='a-box-inner').find('div', class_='a-row a-size-base').find(
            'span').text.strip()
        return ordering_date
    except:
        pass


def get_delivery_status(order):
    try:
        delivery_status = order.find('div', class_='a-box shipment').find('div',
                                                                          class_='a-row shipment-top-row js-shipment-info-container').find_all(
            'span')[0].text.split().split('\n')
        return delivery_status
    except:
        return 'ok'


def save_to_csv(order_list, path_):
    try:
        res = []
        for i in order_list:
            if i not in res:
                res.append(dict((k, v.split('\n').encode('utf-8') if type(v) == 'str' else v) for k, v in i.items()))
        with open(path_, 'w', encoding='utf-8', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=order_list[0], delimiter=';')
            writer.writeheader()
            writer.writerows(res)
    except Exception as e:
        print('Can not write to file! ({})'.format(e))


def get_pages(year, page_year):
    try:
        # getting numbers of pages
        driver.get(page_year)
        actions = ActionChains(driver)
        check_input_password()
        # moving to end of page
        move_to_end_of_page(actions)
        # scraping orders:
        bs4 = BeautifulSoup(driver.page_source, 'html.parser')
        try:
            last_page = bs4.find('ul', class_='a-pagination').findAll('li', class_='a-normal')[-1].find('a').text
        except:
            print('No pages in ', year)
            return
        total_pages = []
        for index in range(1, int(last_page) + 1):
            page_url = BASE_LINK + '/gp/your-account/order-history/ref=ppx_yo_dt_b_pagination_1_{}?ie=UTF8&orderFilter=year-{}&search=&startIndex={}'.format(
                index,
                year,
                index * 10 - 10)
            total_pages.append(page_url)
            print('Adding page: ', page_url)
        time.sleep(2)
        return total_pages
    except Exception as e:
        print('Getting pages error: ', e)


def move_to_end_of_page(actions):
    end_found = False
    while end_found is False:
        actions.send_keys(Keys.PAGE_DOWN).perform()
        actions.reset_actions()
        try:
            EC.presence_of_element_located((By.XPATH, '//div[@class="navFooterBackToTop"]'))
            end_found = True
        except:
            pass


def scrape_page(url):
    #    global actions, bs4, order
    try:
        print('Scraping url: ', url)
        driver.get(url)
        actions = ActionChains(driver)
        check_input_password()

        # moving to end of page
        move_to_end_of_page(actions)

        # scraping orders:
        bs4 = BeautifulSoup(driver.page_source, 'html.parser')
        orders = bs4.find_all('div', class_='a-box-group a-spacing-base order')
        for order in orders:
            items = order.find_all('div', class_='a-fixed-left-grid-col a-col-right')
            for item in items:
                delivery_date = get_delivery_date(item)
                delivery_status = get_delivery_status(order)
                delivery_status = delivery_date if delivery_status == 'ok' else delivery_status
                order_list.append({
                    'title': get_title(item),
                    'price': get_price(item),
                    'delivery date': delivery_date,
                    'ordering date': get_ordering_date(order),
                    'delivery status': delivery_status
                })
    except:
        pass

    # waiting 2 seconds between requests
    time.sleep(2)


if __name__ == '__main__':
    try:
        print('Version: ', ver)
        driver.get(BASE_LINK)
        actions = ActionChains(driver)

        # make login
        check_input_password()
        try:
            if 'Hallo! Anmelden' in driver.find_element_by_xpath('//span[text()="Hallo! Anmelden"]').text:
                make_login(driver)
        except:
            pass

        # going to orders:
        years = get_years(driver)
        if years is None:
            raise Exception('No years in order list')
        for year in years:
            page_year = BASE_LINK + '/gp/your-account/order-history?opt=ab&digitalOrders=1&language=de_DE&unifiedOrders=1&returnTo=&orderFilter=year-{}&ie=UTF8'.format(str(year))
            # parsing pagination
            pages = get_pages(year, page_year)
            if pages is not None:
                for page in pages:
                    scrape_page(page)
            # no pagination (only one page)
            else:
                scrape_page(page_year)

        # output orders
        print(order_list)
        save_to_csv(order_list, 'amazon_orders.csv')
        print('All done!')
    except Exception as e:
        save_pic(driver)
        print('Something goes wrong: ({})'.format(e))

    driver.close()
