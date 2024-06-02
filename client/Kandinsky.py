#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Клиентская часть плагина Kandinsky

Файл содержит определение интерфейса плагина и логику работы с сервером
"""

from gimpfu import *
import gtk
import os

from array import array
import json
import base64

import time
import requests


class KandinskyWindow(gtk.Window):
  """
  Класс, описывающий графический интерфейс плагина

  Аттрибуты
  ---------
  image : gimp.Image
      Исходное изображение
  positive_prompt_textview : gtk.TextView
      Поле для ввода позитивного промта
  negative_prompt_textview : gtk.TextView
      Поле для ввода негативного промта
  decoder_steps_scale : gtk.HScale
      Ползунок с кол-вом итераций декодера
  prior_steps_scale : gtk.HScale
      Ползунок с кол-вом итераций энкодера
  cgs_scale_scale : gtk.HScale
      Ползунок со значением параметра CGS
  output_images_scale : gtk.HScale
      Ползунок с количеством генерируемых изображений
  server_host_entry : gtk.Entry
      Поле с хостом

  Методы
  ------
  close_window()
      Вызывается при закрытии окна
  set_gimp_rc_file()
      Получает и возвращает путь к RC-файлу, в котром описана текущая тема редактора
  get_textview_value(widget)
      Возвращает значение виджета типа TextView (текстовое поле)
  on_click(widget)
      Обработчик события pressed кнопки ok, определенной в конструкторе класса
  """
  def __init__(self, image, *args):

    self.image = image

    win = gtk.Window.__init__(self, *args)
    
    self.set_title("[Kandinsky 2.2] Inpaiting")
    self.set_size_request(820, 150)
    self.set_position(gtk.WIN_POS_MOUSE)

    # Начало определения интерфейса

    hbox2 = gtk.HBox(False, 3)

    # Первая вкладка

    scrolledwindow = gtk.ScrolledWindow()
    scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

    self.positive_prompt_textview = gtk.TextView()
    scrolledwindow.add(self.positive_prompt_textview)

    # Вторая вкладка

    scrolledwindow1 = gtk.ScrolledWindow()
    scrolledwindow1.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

    self.negative_prompt_textview = gtk.TextView()
    scrolledwindow1.add(self.negative_prompt_textview)

    # Третья вкладка

    table = gtk.Table(2, 4, True)

    label1 = gtk.Label('Decoder Steps')
    self.decoder_steps_scale = gtk.HScale()
    self.decoder_steps_scale.set_can_focus(False)
    self.decoder_steps_scale.set_range(0, 80)
    self.decoder_steps_scale.set_increments(10, 10)
    self.decoder_steps_scale.set_digits(0)
    self.decoder_steps_scale.set_value(20)

    table.attach(label1, 0, 1, 0, 1)
    table.attach(self.decoder_steps_scale, 1, 2, 0, 1)

    label2 = gtk.Label('Prior Steps')
    self.prior_steps_scale = gtk.HScale()
    self.prior_steps_scale.set_can_focus(False)
    self.prior_steps_scale.set_range(0, 80)
    self.prior_steps_scale.set_increments(10, 10)
    self.prior_steps_scale.set_digits(0)
    self.prior_steps_scale.set_value(20)

    table.attach(label2, 2, 3, 0, 1)
    table.attach(self.prior_steps_scale, 3, 4, 0, 1)

    label3 = gtk.Label('Guadance Scale')
    self.cgs_scale_scale = gtk.HScale()
    self.cgs_scale_scale.set_can_focus(False)
    self.cgs_scale_scale.set_range(0, 30)
    self.cgs_scale_scale.set_increments(2, 2)
    self.cgs_scale_scale.set_digits(0)
    self.cgs_scale_scale.set_value(4)

    table.attach(label3, 0, 1, 1, 2)
    table.attach(self.cgs_scale_scale, 1, 2, 1, 2)

    label4 = gtk.Label('Output images')
    self.output_images_scale = gtk.HScale()
    self.output_images_scale.set_can_focus(False)
    self.output_images_scale.set_range(1, 10)
    self.output_images_scale.set_increments(1, 1)
    self.output_images_scale.set_digits(0)
    self.output_images_scale.set_value(2)

    table.attach(label4, 2, 3, 1, 2)
    table.attach(self.output_images_scale, 3, 4, 1, 2)

    # Четвертая вкладка

    table1 = gtk.Table(2, 5, True)

    label5 = gtk.Label('Server host with port')
    self.server_host_entry = gtk.Entry()
    self.server_host_entry.set_text('http://127.0.0.1:5000')

    table1.attach(label5, 0, 2, 0, 1)
    table1.attach(self.server_host_entry, 2, 5, 0, 1)

    # Объединение всех вкладок в единый Notebook

    notebook = gtk.Notebook()
    notebook.set_can_focus(False)
    notebook.props.border_width = 0
    notebook.append_page(scrolledwindow, gtk.Label('Positive prompt'))
    notebook.append_page(scrolledwindow1, gtk.Label('Negative prompt'))
    notebook.append_page(table, gtk.Label('Generation parameters'))
    notebook.append_page(table1, gtk.Label('Plugin settings'))

    icon_location = os.getcwd() + "\\AppData\\Roaming\\GIMP\\2.10\\plug-ins\\KandinskyIcon.png"

    # Кнопка

    image = gtk.Image()
    image.set_from_file(icon_location)
    ok = gtk.Button()
    ok.set_can_focus(False)
    ok.add(image)
    ok.connect("pressed", self.on_click)
    ok.set_size_request(150, 150)

    hbox2.pack_start(notebook)
    hbox2.pack_start(ok, False, False)

    al = gtk.Alignment(0, 0, 1, 1)
    al.set_padding(3, 3, 3, 3)
    al.add(hbox2)

    self.add(al)

    self.connect("destroy", gtk.main_quit)

    self.set_gimp_rc_file()
    self.set_icon_from_file(icon_location)

    self.show_all()

    return win

  def close_window(self, widget):
    """Вызывается при закрытии окна
    """
    gtk.main_quit()

  def set_gimp_rc_file(self):
    """Получает и возвращает путь к RC-файлу, в котром описана текущая тема редактора
    """
    selected_theme = pdb.gimp_get_theme_dir()
    gtk.rc_set_default_files([selected_theme + '\\gtkrc'])
    self.current_setting=gtk.settings_get_default()
    gtk.rc_reparse_all_for_settings(self.current_setting,True)

  def get_textview_value(self, widget):
    """Возвращает значение виджета типа gtk.TextView (текстовое поле)

    Параметры
    ---------
    widget: gtk.TextView
        Объект типа gtk.TextView
    """
    buffer = widget.get_buffer()
    startIter, endIter = buffer.get_bounds()    
    text = buffer.get_text(startIter, endIter, False) 
    return text

  def on_click(self, widget):
    """Обработчик события pressed кнопки ok, определенной в конструкторе класса
    """

    # старт группы для отмены действия
    self.image.undo_group_start()

    # сохряняем выделение в отдельный канал
    channel = pdb.gimp_selection_save(self.image)

    # функция для получения массива пикселей из объета слоя изображения
    def get_bytes_from_layer(layer, startx, starty, width, height):
      srcRgn = layer.get_pixel_rgn(
        startx, starty, width, height, False, False)
      return array('B', srcRgn[startx:startx+width, starty:starty+height])

    # получаем самый верхний слой
    drawable = self.image.layers[0]
    drawable_position = drawable.offsets

    b_drawable = get_bytes_from_layer(drawable, 0, 0, drawable.width, drawable.height)
    b_channel = get_bytes_from_layer(channel, drawable_position[0], drawable_position[1], drawable.width, drawable.height)

    # делаем преобразование канала с одним отенком в rgb изображение
    rgb_mask = [[x, x, x] for x in b_channel]
    b_mask = array('B', [v for rgb in rgb_mask for v in rgb])

    decoder_steps = self.decoder_steps_scale.get_value()
    prior_steps = self.prior_steps_scale.get_value()
    cgs_scale = self.cgs_scale_scale.get_value()
    output_images = self.output_images_scale.get_value()

    request_json_data = {
      'mask': base64.b64encode(b_mask),
      'image': base64.b64encode(b_drawable),
      'has_alpha': drawable.has_alpha,
      'width': drawable.width,
      'height': drawable.height,
      'prompt': self.get_textview_value(self.positive_prompt_textview),
      'decoder_steps': int(decoder_steps),
      'prior_steps': int(prior_steps),
      'cgs_scale': int(cgs_scale),
      'image_number': int(output_images)
    }

    server_host = self.server_host_entry.get_text()

    r = requests.post('{}/inpaint'.format(server_host), json=request_json_data)

    text2img_endp_result = r.json()
    token = text2img_endp_result['token']

    status_endp_result = {'status': 'unknown'}
    if text2img_endp_result['status'] == 'initiated':
      while status_endp_result['status'] != 'listening':
        r = requests.get('{}/progress'.format(server_host), json={'token':token})
        status_endp_result = r.json()
        gimp.progress_update(sum(status_endp_result['progress']) / (decoder_steps + prior_steps * 2.))
        time.sleep(0.1)

    r = requests.get('{}/result'.format(server_host), json={'token':token})
    raw_response = r.json()

    pdb.gimp_progress_end()

    # снимаем выделение
    gimp.pdb.gimp_selection_none(self.image)

    new_layer_width = raw_response['width']
    new_layer_height = raw_response['height']

    # итерируемся по полученным от сервера изображениям
    for b64image in raw_response['images']:

      new_layer_data = base64.b64decode(b64image)

      new_layer = pdb.gimp_layer_new(
        self.image, new_layer_width, new_layer_height, RGBA_IMAGE, "KandinskyResult", 100, NORMAL_MODE)

      pdb.gimp_image_insert_layer(self.image, new_layer, None, -1)

      pdb.gimp_layer_set_offsets(new_layer, drawable_position[0], drawable_position[1])

      new_layer_pixel_rgn = new_layer.get_pixel_rgn(0, 0, new_layer_width, new_layer_height, True, True)

      new_layer_pixel_rgn[0:new_layer_width, 0:new_layer_height] = new_layer_data

      new_layer.flush()
      new_layer.merge_shadow(True)
      new_layer.update(0, 0, new_layer_width, new_layer_height)

    # обнавляем интерфейс с новыми слоями
    pdb.gimp_displays_flush()

    # конец группы для отмены действия
    self.image.undo_group_end()

# оснавная функция плагина
def start_kandinsky(image, layer):
  window = KandinskyWindow(image)
  gtk.main()

# регистрация функции плагина в PDB
register(
          "python-fu-kandinsky-inpainting-interactive", # Имя регистрируемой функции
          "Догенерация изображения на основе промта", # Информация о дополнении
          "Догенерация изображения на основе промта", # Короткое описание выполняемых скриптом действий
          "sinvec", # Информация об авторе
          "MIT", # Информация о копирайте 
          "2024", # Дата релиза
          "<Image>/Kandinsky/inpaint", # Название пункта меню, с помощью которого дополнение будет запускаться
          "*", # Типы изображений с которыми может работать дополнение
          [],
          [], # Список переменных которые вернет дополнение
          start_kandinsky) # Имя исходной функции и меню в которое будет помещён пункт запускающий дополнение

# запуск скрипта
main()