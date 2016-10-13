# -*- coding: UTF-8 -*-
# /*
# *      Copyright (C) 2015 bbaron
# *
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with this program; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# */

import re
import urllib
import urllib2
import cookielib
import xml.etree.ElementTree as ET
import sys
import json
import string
import util
import resolver
import xbmcplugin,xbmc,xbmcgui,util
from provider import ContentProvider, cached, ResolveException

reload(sys)
sys.setrecursionlimit(10000)
sys.setdefaultencoding('utf-8')

BASE_URL="http://stream-cinema.online"
MOVIES_BASE_URL = BASE_URL + "/json"
MOVIES_A_TO_Z_TYPE = "movies-a-z"

#util.info('--------------------------------------------------------')
#util.info(resolver.resolve('https://openload.co/embed/DeZ-s187KYg/33-720p-2744411.mp4'))
#util.info('--------------------------------------------------------')

class StreamCinemaContentProvider(ContentProvider):
    par = None

    def __init__(self, username=None, password=None, filter=None, reverse_eps=False):
        ContentProvider.__init__(self, name='czsklib', base_url=MOVIES_BASE_URL, username=username,
                                 password=password, filter=filter)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
        urllib2.install_opener(opener)
        self.reverse_eps = reverse_eps

    def capabilities(self):
        return ['resolve', 'categories', '!download']

    def categories(self):
        result = []
        for title, url in [
                ("Movies", MOVIES_BASE_URL + '/movies-a-z'), 
                ("Movies by quality", MOVIES_BASE_URL + '/list/quality'),
                ("Movies by genre", MOVIES_BASE_URL + '/list/genre'),
                ("Movies by people", MOVIES_BASE_URL + '/list/people'),
                ("Movies by year", MOVIES_BASE_URL + '/list/year'),
                ("Movies latest", MOVIES_BASE_URL + '/list/latest'),
                ]:
            item = self.dir_item(title=title, url=url)
            if title == 'Movies' or title == 'TV Shows' or title == 'Movies - Recently added':
                item['menu'] = {"[B][COLOR red]Add all to library[/COLOR][/B]": {
                    'action': 'add-all-to-library', 'title': title}}
            result.append(item)
        return result

    def a_to_z(self, url_type):
        result = []
        for letter in ['0-9', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'e', 'h', 'i', 'j', 'k', 'l', 'm',
                       'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']:
            item = self.dir_item(title=letter.upper())
            item['url'] = self.base_url + "/movie/letter/" + letter
            result.append(item)
        return result

    def list(self, url):
        xbmcplugin.setContent(int(sys.argv[1]), 'movies')
        
        util.debug("URL: %s" % (url))
        if MOVIES_A_TO_Z_TYPE in url:
            return self.a_to_z(MOVIES_A_TO_Z_TYPE)
        if "/letter/" in url:
            return self.list_by_letter(url)
        if "/list/" in url:
            return self.list_by_params(url)
        
        return [self.dir_item(title="I failed", url="fail")]

    def list_by_params(self, url):
        data = json.loads(self.get_data_cached(url))
        result = []
        for m in data:
            if m['typ'] != 'latest':
                item = self.dir_item(title=m['title'], url=url + '/' + m['url'])
                if m['pic'] != '':
                    item['img'] = "%s%s" % (BASE_URL, m['pic'])
            else:
                item = self._video_item(m)
                
            self._filter(result, item)
        #xbmc.executebuiltin("Container.SetViewMode(515)")
        return result
        
    def _video_item(self, m):
        item = self.video_item(url=MOVIES_BASE_URL + '/play/' + m['id'], img=m['poster'])
        for k in m.keys():
            if k != 'url':
                item[k] = m[k]
        year = m['release']
        if m['rating'] > 0:
            item['rating'] = float(m['rating']) / 10
        
        if int(year[:4]) > 0:
            item['title'] = m['name'] + ' (' + year[:4] + ')'
        else:
            item['title'] = m['name']
        item['genre'] = m['genres']
        item['year'] = year[:4]
        item['cast'] = m['cast'].split(', ')
        item['director'] = m['director']
        if m['mpaa'] != '':
            item['mpaa'] = m['mpaa']
        item['plot'] = m['description']
        item['originaltitle'] = m['name_orig']
        item['sorttitle'] = m['name_seo']
        item['studio'] = m['studio']
        
        if m['imdb'] != '':
            item['code'] = 'tt' + m['imdb']
        art = {}
        if m['fanart'] != '':
            art['fanart'] = m['fanart']
        item['art'] = art
        return item
    
    def get_data_cached(self, url):
        return util.request(url)

    def list_by_letter(self, url):
        result = []
        util.debug("Ideme na pismeno!")
        data = json.loads(self.get_data_cached(url))
        for m in data:
            util.debug(m)
            item = self._video_item(m)
            self._filter(result, item)
        util.debug(result)
        return result

    def resolve(self, item, captcha_cb=None, select_cb=None):
        data = json.loads(self.get_data_cached(item['url']))
        util.debug(select_cb)
        if len(data) < 1:
            raise ResolveException('Video is not available.')
        if len(data) == 1:
            return data[0]
        elif len(data) > 1 and select_cb:
            return select_cb(data)
