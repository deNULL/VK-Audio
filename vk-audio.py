#!/usr/bin/env python
import json, getpass, sys, os, urllib, urllib2, time, curses, re, locale

locale.setlocale(locale.LC_ALL, '')

# Authenticate as iOS app

if os.path.isfile('vk-auth.json'):
  auth = json.load(open('vk-auth.json', 'r'))
else:
  username = raw_input('Enter your VK login (phone or email): ')
  password = getpass.getpass('Enter your VK password: ')

  request = {
    'client_id': 3140623,
    'client_secret': 'VeWdmVclDCtn6ihuP1nt',
    'grant_type': 'password',
    'username': username,
    'password': password,
    '2fa_supported': 1,
  }

  try:
    auth = json.loads(urllib2.urlopen('https://api.vk.com/oauth/token', urllib.urlencode(request)).read())
  except urllib2.HTTPError, error:
    auth = json.loads(error.read())

  if auth['error'] == 'need_validation':
    request['code'] = raw_input('Enter the code you received in SMS: ')
    try:
      auth = json.loads(urllib2.urlopen('https://api.vk.com/oauth/token', urllib.urlencode(request)).read())
    except urllib2.HTTPError, error:
      auth = json.loads(error.read())

  if 'error' in auth:
    print 'Unknown error: ' + auth['error'] + ', quitting'
    sys.exit()

  json.dump(auth, open('vk-auth.json', 'w'))

if not 'access_token' in auth:
  print 'access_token is missing, quitting'
  sys.exit()

# Now auth['access_token'] should contain valid unlimited oauth token

screen = curses.initscr()
curses.noecho()
curses.cbreak()
curses.start_color()
curses.curs_set(1)
screen.keypad(1)
(scrh, scrw) = screen.getmaxyx()

curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
style0 = curses.A_NORMAL
style1 = curses.color_pair(1) | curses.A_BOLD

lists = [
  { 'title': '> My Music:', 'subtitle': 'Leave empty to show all your audios. Enter any text to search it.' }, # , <TAB> to cycle through albums
  { 'title': '> Search for:', 'subtitle': 'Enter any text to search all VK music.' },
  { 'title': '> User/community:', 'subtitle': 'Positive ID for users, negative for communities, or any short name.' },
  { 'title': '> URL:', 'subtitle': 'Link to a user\'s or community\'s audio list.' },
  { 'title': 'Exit', 'subtitle': 'Terminate this script. Or just use Ctrl+C if something goes wrong.' }
]

while True:
  screen.clear()

  oldindex = -1
  index = 0
  key = None
  query = ''
  while key != ord('\n'):
    screen.addstr(2, 2, 'Select an audio list to choose from:', curses.A_UNDERLINE)
    row = 5
    selrow = 5
    for i, item in enumerate(lists):
      screen.move(row, 2)
      screen.clrtoeol()
      screen.addstr(row, 2, item['title'], style1 if i == index else curses.A_BOLD)

      if i == index:
        selrow = row
        screen.addstr(row, 2 + len(item['title']) + 1, query, curses.A_NORMAL)
        screen.move(row + 1, 2)
        screen.clrtoeol()
        screen.move(row + 2, 2)
        screen.clrtoeol()
        screen.addstr(row + 1, 2, item['subtitle'], curses.A_NORMAL)

        row += 3
      else:
        row += 1

    screen.move(selrow, 2 + len(lists[index]['title']) + 1 + len(query))
    screen.border(0)
    screen.refresh()

    oldindex = index
    key = screen.getch()
    if key == 258: # down arrow
      index = index + 1 if (index < len(lists) - 1) else 0
      query = ''
    elif key == 259: # up arrow
      index = index - 1 if (index > 0) else (len(lists) - 1)
      query = ''
    elif key == curses.KEY_BACKSPACE or key == 0x7f:
      query = query[:-1]
    elif index != 4 and key != ord('\n'):
      query = query + chr(key)

    curses.curs_set(0 if index == 4 else 1)

  curses.curs_set(1)
  if index == 4:
    curses.endwin()
    print 'Goodbye!'
    sys.exit()

  request = {
    'v': '5.37',
    'access_token': auth['access_token']
  }

  audio = None
  try:
    if index == 0:
      if query != '':
        request['count'] = 300
        request['q'] = query
        request['search_own'] = 1
        request['sort'] = 2
        audio = json.loads(urllib2.urlopen('https://api.vk.com/method/audio.search', urllib.urlencode(request)).read())
      else:
        request['count'] = 6000
        audio = json.loads(urllib2.urlopen('https://api.vk.com/method/audio.get', urllib.urlencode(request)).read())
    elif index == 1:
      if query != '':
        request['count'] = 300
        request['q'] = query
        request['sort'] = 2
        audio = json.loads(urllib2.urlopen('https://api.vk.com/method/audio.search', urllib.urlencode(request)).read())
      else:
        request['count'] = 1000
        audio = json.loads(urllib2.urlopen('https://api.vk.com/method/audio.getPopular', urllib.urlencode(request)).read())
    elif index == 2:
      request['count'] = 6000
      try:
        request['owner_id'] = int(query)
      except:
        request['screen_name'] = query
        info = json.loads(urllib2.urlopen('https://api.vk.com/method/utils.resolveScreenName', urllib.urlencode(request)).read())
        if ('response' in info) and ('type' in info['response']) and (info['response']['type'] == 'user' or info['response']['type'] == 'group'):
          request['owner_id'] = info['response']['object_id'] if info['response']['type'] == 'user' else -info['response']['object_id']

      if 'owner_id' in request:
        audio = json.loads(urllib2.urlopen('https://api.vk.com/method/audio.get', urllib.urlencode(request)).read())
    elif index == 3:
      m = re.search("vk\\.com/audios(-?[0-9]+)", query)
      if m:
        request['count'] = 6000
        request['owner_id'] = m.group(1)
        audio = json.loads(urllib2.urlopen('https://api.vk.com/method/audio.get', urllib.urlencode(request)).read())
  except urllib2.HTTPError, error:
    curses.endwin()
    print 'Oops, error: {}'.format(error.read())
    sys.exit()

  if not audio:
    continue

  screen.clear()

  if 'response' in audio:
    if 'items' in audio['response']:
      items = audio['response']['items']

      selected = []
      for item in items:
        selected.append(False)

      oldindex = -1
      index = 0
      key = None
      query = ''
      typing = False

      findex = None
      block_sz = 8192

      while key != 27:
        row = 10
        selrow = 10
        offset = 0
        if findex != None and findex + 10 >= scrh - 1:
          offset = findex - scrh + 12
        elif index + 10 >= scrh - 1:
          offset = index - scrh + 12

        for i, item in enumerate(items):
          idx = i + offset
          song = items[idx]
          screen.move(row, 0)
          screen.clrtoeol()
          ind = '[' + str(idx + 1) + ']'
          if selected[idx]:
            screen.addstr(row, 2, u'\u2713'.encode('utf-8'))
          screen.addstr(row, 11 - len(ind), ind, style1 if idx == findex or (findex == None and idx == index) else curses.A_BOLD)
          screen.addstr(row, 12, song['artist'].encode('utf-8'));
          screen.addstr(row, 50, song['title'].encode('utf-8'));

          if 'fsize' in song:
            status = r'%3.2f%%' % (song['loaded'] * 100. / song['fsize'])
            progr = song['loaded'] * 30 / song['fsize']
            if song['loaded'] < 1024:
              loaded = str(song['loaded']) + ' b'
            elif song['loaded'] < 1024*1024:
              loaded = r'%3.2f Kb' % (song['loaded'] / 1024.)
            else:
              loaded = r'%3.2f Mb' % (song['loaded'] / (1024.*1024.))
            if song['loaded'] == -1:
              progr = 'ERROR'
            status = '[' + ' ' * (7 - len(status)) + status + '] [' + u'\u2588' * progr + ' ' * (30 - progr) + '] ' + loaded
            screen.addstr(row, 120, status.encode('utf-8'))

          row += 1
          if row >= scrh - 1:
            break

        selcount = 0
        for i, item in enumerate(items):
          if selected[i]:
            selcount += 1

        title = 'Select (or type in) audio(s) to download:'
        screen.move(2, 2)
        screen.clrtoeol()
        screen.addstr(2, 2, title, curses.A_UNDERLINE)
        screen.addstr(2, 2 + len(title) + 1, query, curses.A_NORMAL)
        screen.addstr(3, 3, 'Arrows + Space', curses.A_BOLD)
        screen.addstr(3, 24, 'Select audios to download')
        screen.addstr(4, 3, '1,2,5', curses.A_BOLD)
        screen.addstr(4, 24, 'Download first, second and fifth audio')
        screen.addstr(5, 3, '2-12,13-20', curses.A_BOLD)
        screen.addstr(5, 24, 'Download ranges of audios')
        screen.addstr(6, 3, '*', curses.A_BOLD)
        screen.addstr(6, 24, 'Download everything/nothing')
        screen.addstr(7, 3, 'Esc', curses.A_BOLD)
        screen.addstr(7, 24, 'Back')
        screen.addstr(9, 2, str(len(items)) + ' audios, ' + str(selcount) + ' selected:', curses.A_UNDERLINE)
        screen.border(0)
        screen.move(2, 2 + len(title) + 1 + len(query))

        screen.refresh()

        if findex != None:
          if f != None:
            buf = u.read(block_sz)
          else:
            buf = False

          if buf:
            items[findex]['loaded'] += len(buf)
            f.write(buf)
          else:
            if f != None:
              selected[findex] = False
              f.close()
              findex = findex + 1

            while findex < len(items) and not selected[findex]:
              findex = findex + 1
            if findex == len(items):
              findex = None
            else:
              try:
                if not os.path.exists('audio'):
                  os.makedirs('audio')
                fname = (items[findex]['artist'] + ' - ' + items[findex]['title'] + '.mp3')
                fname = 'audio/' + fname.replace('/', '').replace('\\', '').replace(':', '').replace('@', '')
                f = open(fname.encode('utf-8'), 'wb')
              except:
                items[findex]['fsize'] = -1
                items[findex]['loaded'] = 0
                f = None
                findex = findex + 1

              if f != None:
                try:
                  u = urllib2.urlopen(items[findex]['url'])
                  items[findex]['fsize'] = int(u.info().getheaders("Content-Length")[0])
                  items[findex]['loaded'] = 0
                except:
                  f = None
          continue

        oldindex = index
        key = screen.getch()
        if key == 258: # down arrow
          index = index + 1 if (index < len(items) - 1) else 0
        elif key == 259: # up arrow
          index = index - 1 if (index > 0) else (len(items) - 1)
        elif key == 339:
          index = max(0, index - (scrh - 11))
        elif key == 338:
          index = min(len(items) - 1, index + (scrh - 11))
        elif key == 32:
          selected[index] = not selected[index]
          typing = False
        elif key == 42: # '*'
          selcount = 0
          for i, item in enumerate(items):
            if selected[i]:
              selcount += 1
          for i, item in enumerate(items):
            selected[i] = selcount < len(items)
          typing = False
        elif key == ord('\n'):
          selcount = 0
          for i, item in enumerate(items):
            if selected[i]:
              selcount += 1
          if selcount == 0:
            selected[index] = True

          f = None
          findex = 0
        elif key == curses.KEY_BACKSPACE or key == 0x7f:
          query = query[:-1]
          typing = True
        elif (key >= ord('0') and key <= ord('9')) or key == ord('-') or key == ord(','):
          query = query + chr(key)
          typing = True
        elif key == ord('q'):
          curses.endwin()
          print 'Goodbye!'
          sys.exit()

        if not typing:
          selcount = 0
          for i, item in enumerate(items):
            if selected[i]:
              selcount += 1
          if selcount == len(items):
            query = '*'
          else:
            query = ''
            st = 0
            while st < len(items):
              en = st
              if selected[st]:
                while en + 1 < len(items) and selected[en + 1]:
                  en = en + 1
                if query != '':
                  query = query + ','
                if st < en:
                  query = query + str(st + 1) + '-' + str(en + 1)
                else:
                  query = query + str(st + 1)
              st = en + 1
        else:
          try:
            nselected = []
            for i, item in enumerate(items):
              nselected.append(query == '*')
            if query != '' and query != '*':
              ranges = query.split(',')
              for rng in ranges:
                pair = rng.split('-')
                if len(pair) > 1:
                  for i in range(min(max(0, int(pair[0]) - 1), len(items) - 1), min(max(0, int(pair[1]) - 1), len(items) - 1) + 1):
                    nselected[i] = True
                else:
                  nselected[min(max(0, int(pair[0]) - 1), len(items) - 1)] = True
            selected = nselected
          except:
            pass