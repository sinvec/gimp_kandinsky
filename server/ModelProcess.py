"""Вспомогательный процесс сервеной части плагина Kandinsky

Файл содержит определение класса ModelProcess.
Экземпляр класса описывает вспомогательный процесс сервера, который отвечает за
работу с моделью: ее запуск и инференс. Процесс также "общается" с основным
процессом через очереди queueM и queueF и переменные modelIsInferencing и modelProgress.
"""

import multiprocessing
import queue

from PIL import Image
import base64

from ModifiedKandinskyV22Inpaint import ModifiedKandinskyV22Inpaint

class ModelProcess(multiprocessing.Process):
    """
    Класс, описывающий вспомогательный процесс сервера. Содержит экземпляр модели и запускает инференс.

    Аттрибуты
    ---------
    queueM : multiprocessing.Queue
        Очередь для отправки результата инференса основному процессу
    queueF : multiprocessing.Queue
        Очередь для получения данных для инференса от основного процесса
    modelIsInferencing : multiprocessing.Value
        Общая для процессов сервера переменная, предназанчена для фиксирования активности модели
    modelProgress : multiprocessing.Value
        Общая для процессов сервера переменная, хранит прогресс модели
    exit : multiprocessing.Event
        Вспомогательная переменная, предназначена для выхода из цикла в методе run
    model : ModifiedKandinskyV22Inpaint
        Экземпляр модели

    Методы
    ------
    decode_gimp_image(img, width, height, has_alpha=False)
        Преобразовывает бинарную строку в PIL Image
    inpainting(request)
        Запускает инференс модели
    init_model()
        Инициализирует экземпляр модели
    delete_model()
        Удаляет модель (освобождает память)
    run()
        Метод с основным циклом процесса
    stop()
        Выполняет заключительные действия при остановке процесса
    """

    def __init__(self, queueM, queueF, modelIsInferencing, modelProgress):
        """
        Параметры
        ---------
        queueM : multiprocessing.Queue
            Очередь для отправки результата инференса основному процессу
        queueF : multiprocessing.Queue
            Очередь для получения данных для инференса от основного процесса
        modelIsInferencing : multiprocessing.Value
            Общая для процессов сервера переменная, предназанчена для фиксирования активности модели
        modelProgress : multiprocessing.Value
            Общая для процессов сервера переменная, хранит прогресс модели
        """
        super().__init__()
        self.queueM = queueM
        self.queueF = queueF
        self.modelIsInferencing = modelIsInferencing
        self.modelProgress = modelProgress
        self.exit = multiprocessing.Event()

    def decode_gimp_image(self, img, width, height, has_alpha=False):
        """Выполняет преобразование бинарной строки в PIL Image

        Параметры
        ---------
        img : str
            Строка с изображением в base64. Внутрее представление - плоский массив
            троек или четверок байтов форматов RGB и RGBA.
        width : int
            Ширина изображения в пикселях
        height : int
            Высота изображения в пикселях
        has_alpha : bool
            Флаг пристутсвия в изображении альфа-канала
        """

        ibytes = base64.b64decode(img)
        # если в изображении есть альфа-канал, то удаляем каждый четвертый байт
        if has_alpha:
            list_ibytes = list(ibytes)
            del list_ibytes[3::4]
            return Image.frombytes('RGB', (width, height), bytes(list_ibytes))
        else:
            return Image.frombytes('RGB', (width, height), ibytes)

    def inpainting(self, request):
        """Запускает инференс модели
    
        Параметры
        ---------
        request : dict
            Словарь с данными для инференса
        """

        # декодируем бинарные строки с изображением и маской в PIL Image
        image, mask = (
            self.decode_gimp_image(request['image'], request['width'], request['height'], request['has_alpha']),
            self.decode_gimp_image(request['mask'], request['width'], request['height'])
        )

        print("[ModelProcess]: start inpainting inferencing")

        # определяем внутреннюю структуру callback'ов
        def create_pipe_callback(stage):
            def pipe_callback(pipe, step_index, timestep, callback_kwargs):
                with self.modelProgress.get_lock():
                    self.modelProgress[stage] = step_index + 1
                return callback_kwargs
            return pipe_callback

        # генерируем callback'и, 0, 1 и 2 - индексы стадий инференса
        pipe_callbacks = {
            "img_emb_callback": create_pipe_callback(0),
            "neg_emb_callback": create_pipe_callback(1),
            "decoder_callback": create_pipe_callback(2)
        }

        images = self.model.generate_inpainting(
            [request['prompt']] * request['image_number'],
            [image] * request['image_number'], 
            [mask] * request['image_number'],
            decoder_steps=request['decoder_steps'],
            prior_steps=request['prior_steps'],
            decoder_guidance_scale=request['cgs_scale'],
            prior_guidance_scale=request['cgs_scale'],
            h=request['height'],
            w=request['width'],
            negative_prior_prompt=[''] * request['image_number'],
            negative_decoder_prompt=[''] * request['image_number'],
            **pipe_callbacks)

        print("[ModelProcess]: end of inpainting inferencing")

        return {
            'images': images,
            'width': request['width'],
            'height': request['height']
        }

    def init_model(self):
        """Инициализирует модель ModifiedKandinskyV22Inpaint
        """
        self.model = ModifiedKandinskyV22Inpaint('cuda')
        print("[ModelProcess]: Model is initiated")

    def delete_model(self):
        """Удаляет модель
        """
        del self.model

    def run(self):
        """Метод с основным циклом процесса
        """
        print("[ModelProcess]: The Start of ModelProcess ...")

        self.init_model()

        while not self.exit.is_set():
            try:
                inferenceType, data = self.queueF.get(timeout=2)
                if inferenceType == 'inpaint':
                    with self.modelIsInferencing.get_lock():
                        self.modelIsInferencing.value = True
                    modelResult = self.inpainting(data)
                    self.queueM.put(modelResult)
                    with self.modelIsInferencing.get_lock():
                        self.modelIsInferencing.value = False
            except queue.Empty:
                print("[ModelProcess]: No inference requests ...")
            except KeyboardInterrupt:
                print("[ModelProcess]: Caught KeyboardInterrupt, terminating this process ...")
                self.stop()

        self.delete_model()

        print("[ModelProcess]: The End of ModelProcess ...")

    def stop(self):
        """Выполняет заключительные действия при остановке процесса
        """
        print("[ModelProcess]: Shutdown of the ModelProcess is initiated")
        # https://docs.python.org/3/library/multiprocessing.html#pipes-and-queues (warning)
        try:
            self.queueM.get(block=False)
        except:
            print("[ModelProcess]: queueM is empty")
        self.exit.set()