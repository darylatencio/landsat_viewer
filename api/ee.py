import json
import os
import re
import requests
import tarfile
import tempfile
import threading
from calendar import monthrange
from data_manager import data_manager
from datetime import datetime
from urllib.parse import urljoin

#--------------------------------------------------------------------------------------------------
#+
#-
class landsat():

    apiKey = None
    dirWork = None
    name = 'landsat_ot_c2_l2'
    text_output = None # optional widget ID for writing text (e.g., landsat_viewer)
    threads = []
    tlb = None
    url = 'https://m2m.cr.usgs.gov/api/api/json/stable/'
    urlDownload = []

    def __init__(self, uName, token, 
                 cloud_cover=30.0, debug=False, lonlat=[54.199,38.499], month=11,
                 working_folder=None, year=2018):
        self.cc = cloud_cover
        self.debug = debug
        self.dirWork = os.path.join(os.path.join(tempfile.gettempdir(),'data'),'landsat') \
            if (working_folder == None) else working_folder
        if not os.path.exists(self.dirWork):
            os.mkdir(self.dirWork)
        self.ll = lonlat
        self.month = month
        self.session = requests.Session()
        self.year = year
        self.login(uName, token)
        return None

    def __str__(self):
        if self.apiKey:
            return f'EarthExplorer Landsat (API KEY: {self.apiKey})'
        else:
            return 'EarthExplorer (not logged in)'

    def download(self, url, use_threads=True):
        void, dirOut = self.is_valid_url(url)
        if not void:
            return None
        fileCurrent = os.listdir(dirOut)
        if (len(fileCurrent) != 0):
            self.print(f'output folder is not empty: {dirOut}')
            if (len(fileCurrent) == 1): # this may be a downloaded TAR file. try to extract its contents
                self.extract_tar(os.path.join(dirOut,fileCurrent[0]))
            return None
        if (use_threads == True):
            thread = threading.Thread(target=self.download_thread, args=(url,dirOut))
            self.threads.append(thread)
            thread.start()
        else:
            self.download_thread(url, dirOut)

    def download_all(self, url=None, use_threads=True):
        urlAll = self.urlDownload if (url == None) else url
        if (len(urlAll) == 0):
            return None
        for urlDownload in urlAll:
            self.download(urlDownload, use_threads=use_threads)
        for thread in self.threads:
            thread.join()

    def download_thread(self, url, output_folder=None):
        if (output_folder == None):
            void, output_folder = self.is_valid_url(url)
            if (void == False): # This shouldn't happen
                return None
        r = requests.get(url, stream=True)
        base = r.headers['Content-Disposition']
        ss = 'filename="'
        base = base[base.find(ss)+len(ss):len(base)-1]
        file = os.path.join(output_folder, base)
        with open(file, 'wb') as f:
            for data in r.iter_content(chunk_size=8192):
                f.write(data)
        self.extract_tar(file)
        return None

    def extract_tar(self, file):
        if (os.path.splitext(file)[1] != '.tar'):
            return None
        dir = os.path.dirname(file)
        try:
            tar = tarfile.open(file, 'r')
            print('extracting files...')
            regex = re.compile('_B.')
            for m in tar.getmembers():
                if (os.path.splitext(m.name)[1].lower() == '.tif'):
                    ms = regex.search(m.name)
                    if (ms != None):
                        if not os.path.exists(os.path.join(dir, m.name)):
                            print(f' {m.name}')
                            tar.extract(m, path=dir)
            tar.close()
        except:
            self.print(f'not a valid TAR file: {file}')
            return None

    def get_id_from_url(self, url):
        strSearch = 'product_id='
        pos = url.find(strSearch)
        if (pos == -1):
            return ''
        id = (url[pos+len(strSearch):].split('&'))[0]
        return id

    def get_working_folder(self):
        return self.dirWork

    def is_valid_url(self, url):
        id = self.get_id_from_url(url)
        if (len(id) == 0):
            self.print(f'invalid url {url}')
            return False, ''
        tok = id.split('_')
        dirOut = self.dirWork
        for subdir in [tok[2],tok[3]]:
            if not os.path.exists(dirOut):
                os.mkdir(dirOut)
            dirOut = os.path.join(dirOut,subdir)
        if not os.path.exists(dirOut):
            os.mkdir(dirOut)
        return True, dirOut

    def login(self, uName, token):
        self.print('logging in...')
        url = urljoin(self.url,'login-token')
        dLogin = {'username':uName, 'token':token}
        r = self.session.post(url, json.dumps(dLogin))
        j = r.json()
        if j.get('errCode') or j.get('errorCode'):
            if (self.debug):
                self.print(' failed to set API key')
            return None
        self.apiKey = j.get('data')

    def logout(self):
        self.print('logging out...')
        void, data = self.post('logout', None)
        self.session = requests.Session()
        self.apiKey = None

    def post(self, ep, dPost, header=None, quiet=None):
        url = urljoin(self.url,ep)
        r = self.session.post(url,json.dumps(dPost),headers=header)
        j = r.json()
        if (j.get('errorCode') != None):
            if (quiet != None):
                self.print(url+'\n '+j.get('errorMessage'))
            return (False, [])
        data = j.get('data')
        return (True, data)

    def print(self,s):
        if (self.text_output != None):
            t = self.text_output.toPlainText()
            t += '\n'+s
            n = t.count('\n')
            self.text_output.setText(t)
            qScroll = self.text_output.verticalScrollBar()
            qScroll.setValue(len(t))
            self.text_output.repaint()
        print(s)

    def query(self, cloud_cover=None, dataset_name=None, lonlat=None,
              max_return=None, month=None, year=None):
        if (self.apiKey == None):
            self.print('Not logged into USGS M2M')
            return None
        self.urlDownload = [] # clear any results from previous search
    # input parameters
        cc = self.cc if (cloud_cover == None) else cloud_cover
        ll = self.ll if (lonlat == None) else lonlat
        m = self.month if (month == None) else month
        name = self.name if (dataset_name == None) else dataset_name
        nMax = 20 if (max_return == None) else max_return
        y = self.year if (year == None) else year
        self.print(f'querying:\n location{ll}\n year:{y}\n month:{m}')
        dHeader = {'X-Auth-Token': self.apiKey}
        dSpatial = {'filterType':'mbr',
                    'lowerLeft':{'latitude' : ll[1], 'longitude' : ll[0]},
                    'upperRight':{ 'latitude' : ll[1], 'longitude' : ll[0]}}
        range = monthrange(y,m)
        dTemporal = {'start':str(y)+'-'+str(m)+'-01', 'end':str(y)+'-'+str(m)+'-'+str(range[1])}
        dPost = {'datasetName':name,
                'spatialFilter':dSpatial,
                'temporalFilter':dTemporal}
        void, data = self.post('dataset-search', dPost, header=dHeader)
        if not void:
            return None
        for dData in data:
            if (name != dData['datasetAlias']):
                self.print(' skipping')
                continue
            self.print(f'{dData["collectionName"]}')
            dPost = {'datasetName':name,
                        'maxResults':nMax,
                        'sceneFilter':{'spatialFilter':dSpatial,
                                       'acquisitionFilter':dTemporal},
                        'startingNumber':1}
            void, dScene = self.post('scene-search',dPost, header=dHeader)
            if not void:
                continue
            if (len(dScene) == 0):
                self.print(' no data found')
                continue
            if (dScene['recordsReturned'] == 0):
                self.print(' no records found')
                continue
            self.print('checking scenes...')
            scene = []
            for result in dScene['results']:
                self.print(' '+result['displayId'])
                if (result['cloudCover'] > cc):
                    self.print(f'  removing for cloud cover ({result["cloudCover"]}|{self.cc})')
                    continue
                scene.append(result['entityId'])
            if (len(scene) == 0):
                self.print('no scenes to download')
                continue
            dPost = {'datasetName':dData['datasetAlias'], 'entityIds':scene}
            void, option = self.post('download-options',dPost, header=dHeader)
            if not void:
                continue
        # download request
            download = []
            for dOption in option:
                if (dOption['available']):
                    download.append({'entityId' : dOption['entityId'],
                                    'productId' : dOption['id']})
            if not download:
                self.print('no files to download')
                continue
            nDownload = len(download)
            label = datetime.now().strftime("%Y%m%d_%H%M%S")
            dPost = {'downloads':download, 'label':label}
            void, dRequest = self.post('download-request', dPost, header=dHeader)
            if not void:
                continue
            if (dRequest['preparingDownloads'] == None) or (len(dRequest['preparingDownloads']) == 0):
            
                for dDownload in dRequest['availableDownloads']:
                    self.urlDownload.append(dDownload['url'])
            else:
                print('not implemented yet')
                continue

#--------------------------------------------------------------------------------------------------
#+
#-
def test_ee():
    print('testing EarthExplorer...')
    uName = ""
    token = ""
# query
    ll = [54.199,38.499]
    m = 11
    y = 2018
    oLandsat = landsat(uName, token, cloud_cover=50, debug=True, month=m, year=y)
    print(oLandsat)
    oLandsat.query()
    oLandsat.download_all(use_threads=False)
    oLandsat.logout()

#--------------------------------------------------------------------------------------------------
#+
#-
if (__name__ == '__main__'):
    test_ee()