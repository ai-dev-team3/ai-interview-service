import logging
import requests
import json
import os


logger = logging.getLogger(__name__)

class ClovaSpeechClient:
    # Clova Speech invoke URL (앱 등록 시 발급받은 Invoke URL)
    invoke_url = os.getenv("CLOVA_SPEECH_API_URL")
    # Clova Speech secret key (앱 등록 시 발급받은 Secret Key)
    secret = os.getenv("CLOVA_API_KEY")

    def req_url(self, url, completion, callback=None, userdata=None, forbiddens=None, boostings=None, wordAlignment=True, fullText=True, diarization=None, sed=None):
        request_body = {
            'url': url,
            'language': 'ko-KR',
            'completion': completion,
            'callback': callback,
            'userdata': userdata,
            'wordAlignment': wordAlignment,
            'fullText': fullText,
            'forbiddens': forbiddens,
            'boostings': boostings,
            'diarization': diarization,
            'sed': sed,
        }
        headers = {
            'Accept': 'application/json;UTF-8',
            'Content-Type': 'application/json;UTF-8',
            'X-CLOVASPEECH-API-KEY': self.secret
        }
        return requests.post(headers=headers,
                             url=self.invoke_url + '/recognizer/url',
                             data=json.dumps(request_body).encode('UTF-8'))

    def req_object_storage(self, data_key, completion, callback=None, userdata=None, forbiddens=None, boostings=None,
                           wordAlignment=True, fullText=True, diarization=None, sed=None):
        request_body = {
            'dataKey': data_key,
            'language': 'ko-KR',
            'completion': completion,
            'callback': callback,
            'userdata': userdata,
            'wordAlignment': wordAlignment,
            'fullText': fullText,
            'forbiddens': forbiddens,
            'boostings': boostings,
            'diarization': diarization,
            'sed': sed,
        }
        headers = {
            'Accept': 'application/json;UTF-8',
            'Content-Type': 'application/json;UTF-8',
            'X-CLOVASPEECH-API-KEY': self.secret
        }
        return requests.post(headers=headers,
                             url=self.invoke_url + '/recognizer/object-storage',
                             data=json.dumps(request_body).encode('UTF-8'))

    def req_upload(self, file, completion, callback=None, userdata=None, forbiddens=None, boostings=None,
                   wordAlignment=True, fullText=True, diarization=None, sed=None):
        request_body = {
            'language': 'ko-KR',
            'completion': completion,
            'callback': callback,
            'userdata': userdata,
            'wordAlignment': wordAlignment,
            'fullText': fullText,
            'forbiddens': forbiddens,
            'boostings': boostings,
            'diarization': diarization,
            'sed': sed,
            'noiseFiltering': False 
        }
        headers = {
            'Accept': 'application/json;UTF-8',
            'X-CLOVASPEECH-API-KEY': self.secret
        }
        logger.debug("Clova 요청 바디: %s", json.dumps(request_body, ensure_ascii=False))
        files = {
            'media': open(file, 'rb'),
            'params': (None, json.dumps(request_body, ensure_ascii=False).encode('UTF-8'), 'application/json')
        }
        response = requests.post(headers=headers, url=self.invoke_url + '/recognizer/upload', files=files)
        return response
    
    def get_full_text_from_upload(self, file, completion='sync', diarization=None):
        response = self.req_upload(file=file, completion=completion, diarization=diarization)
        try:
            data = response.json()
            segments = data.get("segments", [])

            for seg in segments:
                logger.debug("원문 text: %s", seg.get('text'))
                logger.debug("편집 textEdited: %s", seg.get('textEdited'))

            full_text = " ".join(seg.get("text", "") for seg in segments)
            return full_text, data
        except Exception as e:
            logger.exception("Clova STT 오류 발생")
            return ""

if __name__ == '__main__':
    # res = ClovaSpeechClient().req_url(url='http://example.com/media.mp3', completion='sync')
    # res = ClovaSpeechClient().req_object_storage(data_key='data/media.mp3', completion='sync')
    re, data = ClovaSpeechClient().get_full_text_from_upload(file=r'C:\Users\UserK\AppData\Local\Temp\tmp63ci_9kv.wav', completion='sync')
    print(re)
    print(data)