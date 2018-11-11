
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

def collect_element_from_page(page, xpath, params=None):
    try:
        response = requests.get(page, params=params, timeout=TIMEOUT)
    except requests.Timeout:
        print('request timeout for {0}'.format(page))
        return None
    else:
        if not response.ok:
            return None
        page = etree.HTML(response.text)
        data = page.xpath(xpath)
        if len(data) > 0:
            return data[0]

def collect_faculties():
    element = collect_element_from_page('http://ruz.spbstu.ru/', '/html/body/script[1]')
    data = parse_react_init(element)
    if data:
        return data['faculties']['data']

def collect_groups(faculty_id):
    element = collect_element_from_page('http://ruz.spbstu.ru/faculty/{0}/groups'.format(faculty_id), '/html/body/script[1]')
    data = parse_react_init(element)
    if data:
        return data['groups']['data'][str(faculty_id)]

def collect_rasp(faculty_id, group_id, params=None):
    element = collect_element_from_page('http://ruz.spbstu.ru/faculty/{0}/groups/{1}'.format(faculty_id, group_id),
                                        '/html/body/script[1]', params=params)
    data = parse_react_init(element)
    # pprint(data)
    if data:
        return data['lessons']['data'][str(group_id)]

def get_teachers(query):
    element = collect_element_from_page('http://ruz.spbstu.ru/search/teacher?', '/html/body/script[1]', params={'q': query})
    data = parse_react_init(element)
    if data:
        return data['searchTeacher']['data']

def get_teacher_rasp(teacher_id, params=None):
    teacher_id = str(teacher_id)
    element = collect_element_from_page('http://ruz.spbstu.ru/teachers/' + teacher_id, '/html/body/script[1]', params=params)
    data = parse_react_init(element)
    if data:
        return data['teacherSchedule']['data'][teacher_id]
