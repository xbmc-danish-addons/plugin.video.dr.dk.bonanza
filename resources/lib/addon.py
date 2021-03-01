#
#      Copyright (C) 2014 Tommy Winther, termehansen

#
#  https://github.com/xbmc-danish-addons/plugin.video.drnu#
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
import os
import re
import sys
import urlparse
import requests
import requests_cache
from htmlentitydefs import name2codepoint
import buggalo

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import json

BASE_URL = 'http://www.dr.dk/bonanza/'
tr = xbmcaddon.Addon().getLocalizedString
addon_path = xbmcaddon.Addon().getAddonInfo('path')
addon_name = xbmcaddon.Addon().getAddonInfo('name')
ICON = os.path.join(addon_path, 'resources', 'icon.png')
FANART = os.path.join(addon_path, 'resources', 'fanart.jpg')
CACHE = os.path.join(addon_path, 'requests_cache')

def make_notice(object):
    xbmc.log(str(object), xbmc.LOGNOTICE )

class BonanzaException(Exception):
    pass


class Bonanza(object):
    def __init__(self, plugin_url, plugin_handle):
        self._plugin_url = plugin_url
        self._plugin_handle = plugin_handle

        #cache expires after: 86400=1 day   604800=7 days
        requests_cache.install_cache(CACHE, backend='sqlite', expire_after=86400 )
        requests_cache.remove_expired_responses()

    def search(self):
        make_notice('search')
        keyboard = xbmc.Keyboard('', tr(30001))
        keyboard.doModal()
        if keyboard.isConfirmed():
            html = self._downloadUrl('http://www.dr.dk/bonanza/sog?q=' + keyboard.getText().replace(' ', '+'))

            items = list()
            pattern = '<a.*?href="/bonanza/(serie/.*?)".*?' \
                      'data-src="(//asset\.dr\.dk/[^"]+)".*?' \
                      '<h3.*?>([^<]+)</h3>.*?<p>([^<]+)</p>'

            for m in re.finditer(pattern, html, re.DOTALL):
                url = BASE_URL + m.group(1)
                image = 'http:' + m.group(2)
                title = self._decodeHtmlEntities(m.group(3))
                description = self._decodeHtmlEntities(m.group(4))

                infoLabels = {
                    'title': title,
                    'plot': description,
                    'studio': addon_name}

                item = xbmcgui.ListItem(infoLabels['title'])
                item.setArt({'fanart': FANART, 'icon': image, 'thumb': image})
                item.setProperty('IsPlayable', 'true')
                item.setInfo('video', infoLabels)

                url = '?mode=play&url=' + url
                items.append((self._plugin_url + url, item, False))
            xbmcplugin.addDirectoryItems(self._plugin_handle, items)

            xbmcplugin.endOfDirectory(self._plugin_handle)

    def showCategories(self):
        items = list()
        html = self._downloadUrl(BASE_URL)

        item = xbmcgui.ListItem(tr(30001))
        item.setArt({'fanart': FANART, 'icon': ICON})
        xbmcplugin.addDirectoryItem(self._plugin_handle, self._plugin_url + '?mode=search', item, True)

        pattern = '<a href="(/bonanza/kategori/.*)">(.*)</a>'
        for m in re.finditer(pattern, html):
            path = m.group(1)
            title = m.group(2)

            item = xbmcgui.ListItem(title)
            item.setArt({'fanart': FANART, 'icon': ICON})
            item.setInfo('video', infoLabels={
                'title': title
            })
            url = self._plugin_url + '?mode=subcat&url=http://www.dr.dk' + path
            items.append((url, item, True))

        xbmcplugin.addDirectoryItems(self._plugin_handle, items)
        xbmcplugin.addSortMethod(self._plugin_handle, xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(self._plugin_handle)

    def showSubCategories(self, url):
        html = self._downloadUrl(url.replace(' ', '+'))
        self.addSubCategories(html)
        xbmcplugin.addSortMethod(self._plugin_handle, xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(self._plugin_handle)

    def showContent(self, url):
        html = self._downloadUrl(url)
        self.addContent(html)

        xbmcplugin.endOfDirectory(self._plugin_handle)

    def addSubCategories(self, html):
        pattern = '<a href="/bonanza/(serie/.*?)".*?' \
                  'data-src="(//asset\.dr\.dk/[^"]+)".*?' \
                  '<h3>([^<]+)</h3>.*?<p>([^<]+)</p>'
        for m in re.finditer(pattern, html, re.DOTALL):
            url = BASE_URL + m.group(1)
            image = 'http:' + m.group(2)
            title = self._decodeHtmlEntities(m.group(3))
            description = self._decodeHtmlEntities(m.group(4))

            item = xbmcgui.ListItem(title)
            item.setArt({'fanart': FANART, 'icon': image})
            item.setInfo('video', infoLabels={
                'title': title,
                'plot': description
            })
            url = self._plugin_url + '?mode=content&url=' + url
            xbmcplugin.addDirectoryItem(self._plugin_handle, url, item, True)

    def addContent(self, html):
        items = list()
        pattern = '<a href="/bonanza/(serie/.*?)".*?title="([^"]+)".*?' \
                  'data-src="(//asset\.dr\.dk/[^"]+)".*?' \
                  '<h3>([^<]+)</h3>'
        html = html.split('<div class="list-footer"></div>',1)[0]
        for m in re.finditer(pattern, html, re.DOTALL):
            url = BASE_URL + m.group(1)
            description = self._decodeHtmlEntities(m.group(2))
            image = 'http:' + m.group(3)
            title = self._decodeHtmlEntities(m.group(4))

            infoLabels = {
                'title': title,
                'plot': description,
                'studio': addon_name}

            item = xbmcgui.ListItem(infoLabels['title'])
            item.setArt({'fanart': FANART, 'icon': image, 'thumb': image})
            item.setProperty('IsPlayable', 'true')
            item.setInfo('video', infoLabels)

            url = '?mode=play&url=' + url
            items.append((self._plugin_url + url, item, False))
        xbmcplugin.addDirectoryItems(self._plugin_handle, items)


    def playContent(self, url):
        html = self._downloadUrl(url)
        pattern = '<source.*?src="([^"]+)"'
        m = re.search(pattern, html, re.DOTALL)
        if m is not None:
            item = xbmcgui.ListItem(path=m.group(1))
            xbmcplugin.setResolvedUrl(self._plugin_handle, True, item)
        else:
            xbmcplugin.setResolvedUrl(self._plugin_handle, False, xbmcgui.ListItem())

    def _downloadUrl(self, url):
        try:
            xbmc.log(url)
            u = requests.get(url)
            if u.status_code == 200:
                data = u.text
                u.close()
                return data
        except Exception as ex:
            raise BonanzaException(ex)

    def _decodeHtmlEntities(self, string):
        """Decodes the HTML entities found in the string and returns the modified string.

        Both decimal (&#000;) and hexadecimal (&x00;) are supported as well as HTML entities,
        such as &aelig;

        Keyword arguments:
        string -- the string with HTML entities

        """
        if type(string) not in [str, unicode]:
            return string

        def substituteEntity(match):
            ent = match.group(3)
            if match.group(1) == "#":
                # decoding by number
                if match.group(2) == '':
                    # number is in decimal
                    return unichr(int(ent))
            elif match.group(2) == 'x':
                # number is in hex
                return unichr(int('0x' + ent, 16))
            else:
                # they were using a name
                cp = name2codepoint.get(ent)
                if cp:
                    return unichr(cp)
                else:
                    return match.group()

        entity_re = re.compile(r'&(#?)(x?)(\w+);')
        return entity_re.subn(substituteEntity, string)[0]

    def showError(self, message):
        heading = buggalo.getRandomHeading()
        line1 = tr(30900)
        line2 = tr(30901)
        xbmcgui.Dialog().ok(heading, line1, line2, message)

    def route(self, query):
        try:
            PARAMS = dict(urlparse.parse_qsl(query[1:]))
            if 'mode' in PARAMS:
                if PARAMS['mode'] == 'subcat':
                    self.showSubCategories(PARAMS['url'])
                elif PARAMS['mode'] == 'content':
                    self.showContent(PARAMS['url'])
                elif PARAMS['mode'] == 'search':
                    self.search()
                elif PARAMS['mode'] == 'play':
                    self.playContent(PARAMS['url'])
            else:
                self.showCategories()

        except BonanzaException as ex:
            self.showError(str(ex))

        except Exception:
            buggalo.onExceptionRaised()

if __name__ == '__main__':
    ADDON = xbmcaddon.Addon()
    PATH = sys.argv[0]
    HANDLE = int(sys.argv[1])
    PARAMS = urlparse.parse_qs(sys.argv[2][1:])

    ICON = os.path.join(ADDON.getAddonInfo('path'), 'icon.png')
    FANART = os.path.join(ADDON.getAddonInfo('path'), 'fanart.jpg')

    CACHE_FILE = os.path.join(ADDON.getAddonInfo('path'), 'requests_cache')
    #cache expires after: 86400=1 day   604800=7 days
    requests_cache.install_cache(CACHE_FILE, backend='sqlite', expire_after=604800 )

    buggalo.SUBMIT_URL = 'http://tommy.winther.nu/exception/submit.php'
    b = Bonanza()
    try:
        if 'mode' in PARAMS:
            if PARAMS['mode'][0] == 'subcat':
                b.showSubCategories(PARAMS['url'][0])
            elif PARAMS['mode'][0] == 'content':
                b.showContent(PARAMS['url'][0])
            elif PARAMS['mode'][0] == 'search':
                b.search()
            elif PARAMS['mode'][0] == 'play':
                b.playContent(PARAMS['url'][0])
        else:
            b.showCategories()

    except BonanzaException as ex:
        b.showError(str(ex))

    except Exception:
        buggalo.onExceptionRaised()