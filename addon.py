import sys
import urllib
import urllib2
import urlparse
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import feedparser
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from t0mm0.common.net import Net
net = Net()
import cookielib
import settings
import re

__selfpath__   = xbmcaddon.Addon(id='plugin.video.highspots_tv').getAddonInfo('path')
lastNum = re.compile(r'(?:[^\d]*(\d+)[^\d]*)+')
addon = xbmcaddon.Addon()
_pluginId = 'plugin.video.highspots_tv'
pluginhandle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])
cookie_jar = settings.cookie_jar()
USER = settings.username()
PW = settings.user_password()


def parameters_string_to_dict(parameters):
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = paramSplits[1]
    return paramDict


def translation(id):
    return addon.getLocalizedString(id).encode('utf-8')


def gethtmlfromurl(param):  # Returns the html of the provided URL using stored cookies
    net.set_cookies(cookie_jar)
    html = net.http_GET(param).content
    net.save_cookies(cookie_jar)
    return html


def playvideo(param): # Gets the stream from the selected video and plays it
    try:
        stream = gethighspotsstreamurl(param)
        listitem = xbmcgui.ListItem(path=stream)
        xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)
    except:
        xbmcgui.Dialog().ok('Highspots.TV', 'Highspots.TV subscribers you will need to purchase access to view this event.')

def gethighspotsstreamurl(param): # Returns the stream URL from Highspots.TV for the link passed to the function
    link = gethtmlfromurl(param)
    soup = BeautifulSoup(link)
    streams = soup.findAll('video')
    stream = streams[-1]['src']
    return stream


def login(): # Attempts to log in to Highspots.TV with the username and password the user supplies in the addon's settings
    header_dict = {}
    header_dict['Accept'] = '	text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    header_dict['Host'] = 'highspots.tv'
    header_dict['Referer'] = 'http://highspots.tv/wp-login.php?loggedout=true'
    header_dict['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.10240'
    header_dict['Accept-Encoding'] = 'gzip, deflate'
    header_dict['Connection'] = 'keep-alive'
    form_data = ({'log' : USER, 'pwd' : PW, 'wp-submit' : 'Log+In', 'redirect_to' : 'http%3A%2F%2Fhighspots.tv%2Fwp-admin%2F', 'testcookie' : '1'})
    net.set_cookies(cookie_jar)
    login = net.http_POST('http://highspots.tv/wp-login.php', form_data=form_data, headers=header_dict).content
    net.save_cookies(cookie_jar)


def getfeed(param): # Gets the RSS feed passed and creates video links for each result, then adds a Search option
    try:
        html = gethtmlfromurl(param)
        feed = feedparser.parse(html)

        for item in feed['items']:
            try:
                u = sys.argv[0]+"?url="+urllib.quote_plus(item.link)
                xbmcplugin.setContent(pluginhandle, 'episodes')
                name = item.title
                base, id = item.id.split('=')
                thumb = 'http://highspots.tv/wp-content/thumbnails/{0}.jpg'.format(id)
                liz = xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=thumb)
                decodedString = BeautifulStoneSoup(item.description, convertEntities=BeautifulStoneSoup.ALL_ENTITIES).contents[0]
                liz.setInfo(type="Video", infoLabels={"Title": item.title, "Plot": decodedString})
                liz.setProperty('IsPlayable', 'true')
                addLink(name, item.link, 'playvideo' ,thumb, decodedString)
            except:
                pass
        try:
            if param.find('paged') == -1:
                nextUrl = param + '?paged=2'
            else:
                nextUrl = increment(param)
            print('nextURL:: ' + str(nextUrl))
            addDir('Next Page >>', nextUrl, 'category')
        except:
            pass
        xbmcplugin.endOfDirectory(pluginhandle)
        xbmc.executebuiltin('Container.SetViewMode(%d)' % 504)
    except urllib2.HTTPError:
        xbmc.executebuiltin("XBMC.Notification(Highspots.TV, There are no more results for this category, '5000', %s)" % ( __selfpath__ + '/icon.png'))


def increment(s): # Function that looks at the last sequence of number(s) in a string and increments it by 1
    m = lastNum.search(s)
    if m:
        next = str(int(m.group(1))+1)
        start, end = m.span(1)
        s = s[:max(end-len(next), start)] + next + s[end:]
    return s


def searchquery(): # Searches Highspots.TV for the user's query then lists the results from the parsed RSS
    keyboard = xbmc.Keyboard('', translation(30017))
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        search_string = urllib.quote_plus(keyboard.getText().replace(" ", "+"))
        queryurl = 'http://highspots.tv/search/{0}/feed/rss2/'.format(search_string)
        getfeed(queryurl)


def addLink(name, url, mode, iconimage, desc, length="", date="", nr=""): # Creates playable links for the videos listed
    u = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok = True
    liz = xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo(type="Video", infoLabels={"Title": name, "Plot": desc, "Aired": date, "Episode": nr})
    if length:
        liz.addStreamInfo('video', {'duration': int(length)})
    liz.setProperty('IsPlayable', 'true')
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz)
    return ok



def addDir(name, url, mode, iconimage='', plot=''): # Creates a directory list
    u = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo(type="Video", infoLabels={ "Title": name, "plot": plot})
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
    return ok


def listCategories(): # The default view for the addon.  Lists all of the available top level RSS feeds on Highspots.TV.  Adds a search option.
    addDir('Free Videos', 'http://highspots.tv/category/video/free-videos/feed/', 'category')
    addDir('Matches', 'http://highspots.tv/category/video/wrestling-matches/feed/', 'category')
    addDir('Originals', 'http://highspots.tv/category/video/highspots-originals/feed/', 'category')
    addDir('Shoot Interviews', 'http://highspots.tv/category/video/shoot-interviews/feed/', 'category')
    addDir('Features', 'http://highspots.tv/category/video/features/feed/', 'category')
    addDir('Female Wrestling', 'http://highspots.tv/category/video/female-wrestling/feed/', 'category')
    addDir('Premium', 'http://highspots.tv/category/video/premium/feed/', 'category')
    addDir('iPPV', 'http://highspots.tv/category/video/ippv/feed/', 'category')
    addDir('Search', '', 'search')
    xbmcplugin.endOfDirectory(pluginhandle)

params = parameters_string_to_dict(sys.argv[2])
mode = urllib.unquote_plus(params.get('mode', ''))
url = urllib.unquote_plus(params.get('url', ''))
type = urllib.unquote_plus(params.get('type', ''))
name = urllib.unquote_plus(params.get('name', ''))

if mode == 'category':
    getfeed(url)
elif mode == 'playvideo':
    link = args.get('url')[0] # Gets the URL out of the query string to pass to playvideo
    playvideo(link)
elif mode == 'search':
    searchquery()
else:
    try:
        login()
    except:
        pass
    listCategories()