#!/usr/bin/env python 

import json
import urllib
import urllib2
import gtk
import logging
from subprocess import Popen, PIPE

LOGIN_URL = "https://www.strava.com/api/v2/authentication/login"
UPLOAD_URL = "http://www.strava.com/api/v2/upload"

class ConfigError(Exception): pass

class ProgressDialog():
    def __init__(self, text):
        self.progress = None
        self.text = text
    def __enter__(self):
        self.progress = Popen(["zenity", "--text", "Strava Upload", "--percentage=0", "--auto-close=True", "--pulsate=True", "--progress", "--no-cancel"], stdin=PIPE)
        self.progress.stdin.write('# %s\n' % self.text)
        return self

    def __exit__(self, type, value, traceback):
        self.progress.stdin.write('100\n')
        self.progress.stdin.close()
        self.progress.wait()

class StravaUpload:
    def __init__(self, parent = None, pytrainer_main = None, conf_dir = None, options = None):
        self.pytrainer_main = pytrainer_main
        self.conf_dir = conf_dir

        self.strava_token = "%s/.strava_token" % self.conf_dir
        self.strava_uploads = "%s/.strava_uploads" % self.conf_dir

        self.email = None
        self.password = None
        if options:
            self.email = options['stravauploademail']
            self.password = options['stravauploadpassword']
      
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    def get_web_data(self, url, values, text):
        with ProgressDialog(text) as p:
            data = urllib.urlencode(values)
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req)
            return json.loads(response.read())

    def login_token(self):
        token = None
        try:
            with open(self.strava_token) as f:
                token = f.readline()
        except:
            pass
        if token is None or token.strip() == '' :
            if self.email and self.password:
                values = { 'email' : self.email, 'password' : self.password }
                result = self.get_web_data(LOGIN_URL, values, "Validating user...")
                token = result['token']
            else:
                raise ConfigError, "Username or password missing"
            try:
                with open(self.strava_token, 'w') as f:
                    f.write(token)
            except:
                # didn't write token but that's ok, get another next time...
                pass
        return token 

    def find_upload(self, id):
        upload_id = None
        try:
            with open(self.strava_uploads) as f:
                for line in f:
                    upload = line.strip().split(',')
                    if upload[0] == str(id):
                       upload_id = upload[1]
                       break
        except IOError, e:
            logging.debug("Failed to read uploads file: %s" % e)
        return upload_id

    def store_upload_id(self, id, upload_id):
        try:
            with open(self.strava_uploads, 'a') as f:
                f.write('%s,%s\n' % (id, upload_id))
        except IOError, e:
            # log failure but continue...
            logging.debug("Failed to write upload id: %s" % e)

    def upload(self, token, gpx_file):
        gpx = None
        upload_id = 0
        try:
            with open(gpx_file) as f:
                gpx = f.read()
        except:
            pass
        if gpx is not None and gpx.strip() != '':
            values = { 'token': token, 'type': 'gpx', 'data': gpx }
            result = self.get_web_data(UPLOAD_URL, values, "Uploading record...")
            upload_id = result['upload_id']
        return upload_id

    def run(self, id, activity = None):
        logging.debug(">>")
        log = "Strava Upload "
        gpx_file = "%s/gpx/%s.gpx" % (self.conf_dir, id)
        try:
            logging.debug("Getting user token")
            user_token = self.login_token();
            if user_token is not None:
                logging.debug("Uploading GPX: %s" % gpx_file)
                upload_id = self.upload(user_token, gpx_file)
                if upload_id > 0:
                    self.store_upload_id(id, upload_id)
                    log = log + "success (upload: %s)!" % upload_id
                else:
                    log = log + "failed to upload!"
        except (ValueError, KeyError), e:
            log = log + ("JSON error: %s." % e)
        except ConfigError, e:
            log = log + ("config error: %s." % e)
        except Exception, e:
            log = log + "failed! %s" % e
        md = gtk.MessageDialog(self.pytrainer_main.windowmain.window1, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, log)
        md.set_title(_("Strava Upload"))
        md.set_modal(False)
        md.run()
        md.destroy()
        logging.debug(log)
        logging.debug("<<")
