"""Основной процесс серверной части плагина Kandinsky

Файл содержит реализацию обработки запросов клиентской части плагина с использованием Flask.
"""

from flask import Flask, request

import uuid

from ModelProcess import ModelProcess
import multiprocessing
import queue

import base64
from array import array

app = Flask(__name__)

# очередь для отправки результата инференса основному процессу
queueM = multiprocessing.Queue(maxsize=1)
# очередь для получения данных для инференса от основного процесса
queueF = multiprocessing.Queue(maxsize=1)

# общая для процессов сервера переменная, предназанчена для фиксирования активности модели
modelIsInferencing = multiprocessing.Value('i', 0)
# общая для процессов сервера переменная, хранит прогресс модели
modelProgress = multiprocessing.Array('i', 3)

# основной эндпоинт сервера, через него клиент присылает данные для инференса
@app.route('/inpaint', methods=['POST'])
def inpainting_handle():
    global currentToken
    # проверяем, активна ли сейчас модель
    if modelIsInferencing.value == 0:
        queueMIsEmpty = queueM.empty()
        # проверяем, забран ли результат последнего инференса
        if queueMIsEmpty:
            plugin_request = request.json
            print("[FlaskProcess]: New request: ", plugin_request['prompt'])
            # обнуляем прогресс модели
            with modelProgress.get_lock():
                for i in range(3):
                    modelProgress[i] = 0
            queueF.put(('inpaint', plugin_request))
            with modelIsInferencing.get_lock():
                modelIsInferencing.value = True
            # генерируем токен и возращаем его пользователю
            currentToken = str(uuid.uuid4())
            return {
                'status': 'initiated',
                'token': currentToken
            }
        else:
            return { 'status': 'blocked' }
    else:
        return { 'status': 'inferencing' }

# эндпоинт, с помощью которого клиент получает прогресс инференса
@app.route('/progress', methods=['GET'])
def status_handle():
    global currentToken
    plugin_request = request.json
    flatModelProgress = [modelProgress[i] for i in range(3)]
    return {
        'status': "inferencing" if modelIsInferencing.value == 1 else "listening",
        'progress': flatModelProgress if plugin_request['token'] == currentToken else [0,0,0]
    }

# эндпоинт для получения результат инференса
@app.route('/result', methods=['GET'])
def result_handle():
    global currentToken
    plugin_request = request.json
    # токен совпадает с сохраненным на сервере?
    if plugin_request['token'] == currentToken:
        # модель неактивна?
        if modelIsInferencing.value == 0:
            try:
                modelResult = queueM.get(block=False)
                # функция для преобразования PIL Image в плоский массив в кодировке base64 
                def prepare(img):
                    pixels = list(img.getdata())
                    pixels = [y for x in map(lambda x: [*x, 255], pixels) for y in x]
                    return base64.b64encode(array('B', pixels)).decode('ascii')
                return {
                    'status': 'ready',
                    'images': [prepare(result_image) for result_image in modelResult['images']],
                    'width': modelResult['width'],
                    'height': modelResult['height']
                }
            except queue.Empty:
                return { 'status': 'empty' }
        else:
            return { 'status': 'inferencing' } 
    else:
        if modelIsInferencing.value == 0:
            return { 'status': 'listening' }
        else:
            return { 'status': 'inferencing' } 

# функция, вызывающаяся при старте текущего процесса
def on_app_start():
    global modelProcess
    global currentToken

    currentToken = None

    modelProcess = ModelProcess(
        queueM, queueF,
        modelIsInferencing, modelProgress)

    # старт вспомогательного процесса
    modelProcess.start()

if __name__ == '__main__':
    onAppStart()
    app.run(debug=True, use_reloader=False)