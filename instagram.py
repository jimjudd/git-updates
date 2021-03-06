import requests
import re
import json
import os.path
import time
import random
import logging
import sys
from PIL import Image
import datetime
from pprint import pprint
import pickle


def get_numbers_from_filename(filename):
    return re.search(r'\d+', filename).group(0)

# logger = logging.getLogger()
# handler = logging.StreamHandler(sys.stdout)
# formatter = logging.Formatter('%(levelname)-8s %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)
# logger.setLevel(logging.INFO)
# logging.getLogger("requests").setLevel(logging.WARNING)
# logging.getLogger("urllib3").setLevel(logging.WARNING)


insta_url = 'https://www.instagram.com/explore/tags/'

tags = [
    'lovestarbicyclebags',
    'lovestarraceclub'
]

tag_page = {}


def merge_two_dicts(x, y):
    '''Given two dicts, merge them into a new dict as a shallow copy.'''
    z = x.copy()
    z.update(y)
    return z


def convert_to_iso_time(epoch_time):
    dt = datetime.datetime.utcfromtimestamp(epoch_time)
    return dt.isoformat()


# resets directory and creates instagram json
def reset_dir(lsphotos_json, media_file_folder):
    for the_file in os.listdir(media_file_folder):
        file_path = os.path.join(media_file_folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
                # elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except Exception as e:
            print(e)
    instagram_dict = {
        "images": []
    }
    with open(lsphotos_json, 'w') as f:
        json.dump(instagram_dict, f, sort_keys=True)


# make images smaller
def resize_big_images(image_path):
    fname, file_extension = os.path.splitext(image_path)
    img = Image.open(image_path)
    max_size = 800
    original_size = max(img.size[0], img.size[1])
    if original_size >= max_size:
        if (img.size[0] < img.size[1]):
            resized_width = max_size
            resized_height = int(round((max_size / float(img.size[0])) * img.size[1]))
        else:
            resized_height = max_size
            resized_width = int(round((max_size / float(img.size[1])) * img.size[0]))
        img = img.resize((resized_width, resized_height), Image.ANTIALIAS)
        img.save(image_path, 'JPEG')
        logging.info('image resized')


# def create_thumbnail(lsphotos_json, media_file_folder):
#     f = open(lsphotos_json)
#     lsjson = json.loads(f.read())
#     size = 400, 400
#     for item in lsjson['images']:
#         if 'thumbnail_path' in item:
#             logging.debug('skipping ' + item['media_code'])
#         else:
#             path, big_picture = os.path.split(item['media_file_path'])
#             file_name, file_ext = os.path.splitext(big_picture)
#             thumbnail_name = file_name + '_smaill' + file_ext
#             thumbnail_path = os.path.join(media_file_folder, file_name + '_small' + file_ext)
#             media_file = os.path.join(media_file_folder, big_picture)
#             im = Image.open(media_file)
#             im.thumbnail(size)
#             im.save(thumbnail_path)
#             item['thumbnail_path'] = os.path.relpath(
#                 thumbnail_path, os.path.join(os.path.dirname(__file__), '..'))
#             with open(lsphotos_json, 'w') as fp:
#                 json.dump(lsjson, fp, sort_keys=True)
#             logging.info('created thumbnail for ' + item['media_code'])


# remove a specific instagram photo based on photo number
def remove_ig_photo(lsphotos_json, ignore_photo):
    with open(lsphotos_json, 'r') as j:
        js = json.loads(j.read())
    img = str(ignore_photo).zfill(6) + '.jpg'
    for item in js['images']:
        media_file_path = item['media_file_path'][-10:]
        if img == media_file_path:
            item['ignore'] = True
    with open(lsphotos_json, 'wb') as f:
        f.write(json.dumps(js))


def parse_json(lsphotos_json, tag_page_json, media_file_folder):
    for item, entry in enumerate(tag_page_json):
        dir_list = os.listdir(media_file_folder)
        max_list = []
        downloaded_photos = []
        for item in dir_list:
            if item[:5] == 'image':
                max_list.append(item)
        if not max_list:
            n = 1
        else:
            max_item = max(max_list)
            n = int(get_numbers_from_filename(max_item))
            n += 1
        with open(lsphotos_json, 'r') as fej:
            dp = json.loads(fej.read())
        for item in dp['images']:
            downloaded_photos.append(item['media_id'])
        media_id = entry['id']
        media_url = entry['display_src']
        media_caption = entry['caption']
        media_code = entry['code']
        media_date = convert_to_iso_time(int(entry['date']))
        media_utc_date = entry['date']
        media_file_name = 'image' + '%0.6d' % n + '.jpg'
        media_file_path = os.path.abspath(os.path.join(media_file_folder, media_file_name))
        if entry['is_video'] is False and media_id not in downloaded_photos:
            with open(media_file_path, 'wb') as handle:
                response = requests.get(media_url, stream=True)
                if not response.ok:
                    logging.error('couldn\'t download file: ' + media_id)
                for block in response.iter_content(1024):
                    handle.write(block)
            entry = {}
            media_index = n - 1
            entry['media_id'] = media_id
            entry['instagram_url'] = 'https://www.instagram.com/p/' + media_code
            entry['media_code'] = media_code
            entry['media_url'] = media_url
            entry['caption'] = media_caption
            entry['date'] = media_date
            entry['utc_date'] = media_utc_date
            entry['ignore'] = False
            entry['media_file_path'] = os.path.join('lsphotos', media_file_name)
            f = open(lsphotos_json, 'r')
            lsphotos_dict = json.loads(f.read())
            f.close()
            lsphotos_dict['images'].insert(media_index, entry)
            with open(lsphotos_json, 'w') as fp:
                json.dump(lsphotos_dict, fp, sort_keys=True)
            logging.info('photo added ' + media_id)
            resize_big_images(media_file_path)
            time.sleep(random.randint(1, 10))
        else:
            logging.debug('skipping photo ' + media_id)


def get_photo_info(lsphotos_json):
    f = open(lsphotos_json)
    lsjson = json.loads(f.read())
    for item in lsjson['images']:
        if 'owner' in item:
            logging.debug('skipping ' + item['media_code'])
        else:
            url = item['instagram_url']
            r = requests.get(url)
            text = r.text
            photo_json = json.loads(re.search(r"window._sharedData\s*=\s*(.*);", text).group(1))
            media = photo_json['entry_data']['PostPage'][0]['graphql']['shortcode_media']
            item['owner'] = {}
            item['owner']['id'] = media['owner']['id']
            item['owner']['username'] = media['owner']['username']
            item['owner']['owner_url'] = str('https://www.instagram.com/' + media['owner']['username'])
            if media['location'] is not None:
                item['location'] = {}
                item['location']['name'] = media['location']['name']
                item['location']['id'] = media['location']['id']
                item['location']['location_url'] = str('https://www.instagram.com/explore/locations/' + media['location']['id'])
            with open(lsphotos_json, 'w') as fp:
                json.dump(lsjson, fp, sort_keys=True)
            logging.info('updated photo info for ' + item['media_code'])
            time.sleep(random.randint(1, 10))


def get_json(lsphotos_json, url, tag, lsphotos_folder):
    # new_url = insta_url + tag
    r = requests.get(url)
    text = r.text
    insta_json = json.loads(re.search(r"window._sharedData\s*=\s*(.*);", text).group(1))
    top_posts = insta_json['entry_data']['TagPage'][0]['tag']['top_posts']['nodes']
    parse_json(lsphotos_json, top_posts, lsphotos_folder)
    tag_page = insta_json['entry_data']['TagPage'][0]['tag']['media']['nodes']
    parse_json(lsphotos_json, tag_page, lsphotos_folder)
    try:
        while insta_json['entry_data']['TagPage'][0]['tag']['media']['page_info']['has_next_page'] is True:
            cursor = insta_json['entry_data']['TagPage'][0]['tag']['media']['page_info']['end_cursor']
            new_url = insta_url + tag + '/?max_id=' + cursor
            return new_url
    except TypeError:
        logging.info('cannot go to next page: ' + url)
        pass


def rename_files(lsphotos_json, media_file_folder):
    dir_list = os.listdir(media_file_folder)
    max_list = []
    for item in dir_list:
        if item[:5] == 'image':
            max_list.append(item)
    if not max_list:
        n = 1
    else:
        max_item = max(max_list)
        n = int(get_numbers_from_filename(max_item))
        n += 1
    for filename in os.listdir(media_file_folder):
        fname, file_extension = os.path.splitext(filename)
        if file_extension == '.jpg' and fname[:5] != 'image':
            file_name = 'image' + '%0.6d' % n + file_extension
            os.rename(os.path.join(media_file_folder, filename), os.path.join(media_file_folder, file_name))
            ls_json = open(lsphotos_json)
            ls_json = json.loads(ls_json.read())
            ls_json[fname]['java_array_id'] = n - 1
            ls_json[fname]['media_file_path'] = os.path.relpath(
                os.path.join(media_file_folder, file_name), os.path.join(os.path.dirname(__file__), '..'))
            with open(lsphotos_json, 'w') as fp:
                json.dump(ls_json, fp, sort_keys=True)
            n += 1
            logging.info('photo renamed ' + fname + ' ' + file_name)

# reset_dir()
# for item in tags:
#     tagged_url = insta_url + item
#     while tagged_url:
#         tagged_url = get_json(tagged_url, item)
#         time.sleep(random.randint(1, 10))
#
# get_photo_info()
# create_thumbnail()
# create_html.reset_dir()
# create_html.iterate_json()
