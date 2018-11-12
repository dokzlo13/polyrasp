
import re
import json
import requests
from lxml import etree


TIMEOUT = 1.5

def parse_react_init(element):
    if element is None:
        return None
    data = element.text
    data = data.replace('\n', '')
    m = re.compile('    window.__INITIAL_STATE__ = (.*);').match(data)
    data = json.loads(m.groups()[0])
    return data

def collect_element_from_page(page, xpath, params=None, retries=5):
    while retries > 0:
        try:
            response = requests.get(page, params=params, timeout=TIMEOUT)
        except requests.Timeout:
            print('Request timeout for {0}'.format(page))
            retries -= 1
            # return None
        else:
            if not response.ok:
                return None
            page = etree.HTML(response.text)
            data = page.xpath(xpath)
            if len(data) > 0:
                return data[0]
    return None

def collect_json(page, xpath, params=None, retries=5):
    element = collect_element_from_page(page, xpath, params, retries)
    data = parse_react_init(element)
    return data

def collect_faculties():
    data = collect_json('http://ruz.spbstu.ru/', '/html/body/script[1]')
    if data:
        return data['faculties']['data']

def collect_groups(faculty_id):
    data = collect_json('http://ruz.spbstu.ru/faculty/{0}/groups'.format(faculty_id), '/html/body/script[1]')
    if data:
        return data['groups']['data'][str(faculty_id)]

def collect_rasp(faculty_id, group_id, params=None):
    data = collect_json('http://ruz.spbstu.ru/faculty/{0}/groups/{1}'.format(faculty_id, group_id),
                                        '/html/body/script[1]', params=params)
    # pprint(data)
    if data:
        return data['lessons']['data'][str(group_id)]

def get_teachers(query):
    data = collect_json('http://ruz.spbstu.ru/search/teacher?', '/html/body/script[1]', params={'q': query})
    if data:
        return data['searchTeacher']['data']

def get_teacher_rasp(teacher_id, params=None):
    teacher_id = str(teacher_id)
    data = collect_json('http://ruz.spbstu.ru/teachers/' + teacher_id, '/html/body/script[1]', params=params)
    if data:
        return data['teacherSchedule']['data'][teacher_id]
