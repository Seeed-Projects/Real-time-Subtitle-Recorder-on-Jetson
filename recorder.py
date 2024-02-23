import sys
import time

import webbrowser
import flask
from threading import Thread
from riva_asr import ASR

import riva.client
import riva.client.audio_io
import pyaudio


class Recorder:
    def __init__(self, riva_server="127.0.0.1:50051", input_device=None, sample_rate_hz=None):
        # WebUI
        self.webapp = flask.Flask(__name__)
        self.messages = ["hello"]  # Simulated database, used for storing messages

        @self.webapp.route('/')
        def index():
            return flask.render_template('chat.html', messages=self.messages)

        @self.webapp.route('/get_messages', methods=['GET'])
        def get_messages():
            # 返回消息列表的JSON表示
            return flask.jsonify(self.messages)

        self.webapp_thread = None

        # ASR
        if input_device is None:
            target_device = self.get_asr_devices_list()
            input_device = target_device['index']
            sample_rate_hz = int(target_device['defaultSampleRate'])
            print(f"{input_device}, {sample_rate_hz}")
        auth = riva.client.Auth(uri=riva_server)
        self.asr = ASR(auth, input_device, sample_rate_hz, callback=self.asr_callback)

        # Flags
        self.input_end_flag = True
        self.temp_sentences = ''

    def asr_callback(self, response):
        try:
            for result in response.results:
                if not result.alternatives:
                    continue
                transcript = result.alternatives[0].transcript

                if result.is_final:
                    print("## " + transcript)
                    print(f"Confidence:{result.alternatives[0].confidence:9.4f}" + "\n")
                    # if result.alternatives[0].confidence > 0.1:
                    #     self.messages[-1] = transcript
                    # else:
                    #     self.messages.pop()
                    self.messages[-1] = transcript
                    self.input_end_flag = True
                    self.temp_sentences = ''
                else:
                    print(">> " + transcript)
                    print(f"Stability：{result.stability:9.4f}" + "\n")

                    if self.input_end_flag:
                        self.input_end_flag = False
                        self.messages.append(transcript)
                    else:
                        if result.stability > 0.1 and transcript not in self.temp_sentences:
                            self.temp_sentences = transcript
                            self.messages[-1] = self.temp_sentences
                        else:
                            self.messages[-1] = self.temp_sentences + transcript
        finally:
            pass
    
    def run(self):
        def run_app():
            self.webapp.run()
        self.webapp_thread = Thread(target=run_app)
        self.webapp_thread.start()

        self.asr.start()
        Thread(target=self.open_browser).start()

        count = 0
        while True:
            count += 1
            time.sleep(1)
            print(self.messages)

    @staticmethod
    def open_browser():
        webbrowser.open_new('http://127.0.0.1:5000/')

    @staticmethod
    def get_asr_devices_list():
        target_device = None
        p = pyaudio.PyAudio()
        print("Input audio devices:")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] < 1:
                continue
            if 'USB' in info["name"]:
                target_device = info
            print(f"{info['index']}: {info['name']}")
        p.terminate()
        if target_device is None:
            print('No available input device found, please manually config an device.')
            sys.exit(0)
        else:
            return target_device


if __name__ == '__main__':
    re = Recorder()
    re.run()
