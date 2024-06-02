"""Модифицированная модель Kandinsky 2.2

Файл содержит определение класса ModifiedKandinskyV22Inpaint.
Данный класс унаследован от Kandinsky2_2 и изменен для оптимизации памяти и
получения возможности фиксации прогресса инференса модели вовне (через callback'и)
"""

from kandinsky2 import Kandinsky2_2
import torch
from diffusers import KandinskyV22PriorPipeline, KandinskyV22InpaintPipeline
from transformers import CLIPVisionModelWithProjection
from diffusers.models import UNet2DConditionModel
from transformers import CLIPVisionModelWithProjection
from diffusers.models import UNet2DConditionModel

class ModifiedKandinskyV22Inpaint(Kandinsky2_2):
    """
    Модицированный класс Kandinsky2_2
    Аттрибуты оригинального класса не изменены
    """
    def __init__(
        self, 
        device
    ):
        self.device = device
        self.image_encoder = CLIPVisionModelWithProjection.from_pretrained('kandinsky-community/kandinsky-2-2-prior', subfolder='image_encoder').to(torch.float16).to(self.device)
        self.unet = UNet2DConditionModel.from_pretrained('kandinsky-community/kandinsky-2-2-decoder-inpaint', subfolder='unet').to(torch.float16).to(self.device)
        self.prior = KandinskyV22PriorPipeline.from_pretrained('kandinsky-community/kandinsky-2-2-prior', image_encoder=self.image_encoder, torch_dtype=torch.float16)
        self.prior = self.prior.to(self.device)
        self.prior.enable_sequential_cpu_offload()
        self.decoder = KandinskyV22InpaintPipeline.from_pretrained('kandinsky-community/kandinsky-2-2-decoder-inpaint', unet=self.unet, torch_dtype=torch.float16)
        self.decoder = self.decoder.to(self.device)
        self.decoder.enable_sequential_cpu_offload()

    def generate_inpainting(
        self,
        prompt,
        pil_img,
        img_mask,
        batch_size=1,
        decoder_steps=50,
        prior_steps=25,
        decoder_guidance_scale=4,
        prior_guidance_scale=4,
        h=512,
        w=512,
        negative_prior_prompt="",
        negative_decoder_prompt="",
        img_emb_callback=None,
        neg_emb_callback=None,
        decoder_callback=None
    ):
    """Генерирует inpainting

    Новые параметры
    ---------------
    img_emb_callback : function
        Функция, получающая прогресс формирования положительных эмбедингов
    neg_emb_callback : function
        Функция, получающая прогресс формирования отрицательных эмбедингов
    decoder_callback : function
        Функция, получающая прогресс работы U-net'a и декодера
    """
        
        img_emb = self.prior(
            prompt=prompt,
            num_inference_steps=prior_steps,
            num_images_per_prompt=batch_size,
            guidance_scale=prior_guidance_scale,
            negative_prompt=negative_prior_prompt,
            callback_on_step_end=img_emb_callback)

        negative_emb = self.prior(
            prompt=negative_prior_prompt,
            num_inference_steps=prior_steps,
            num_images_per_prompt=batch_size,
            guidance_scale=prior_guidance_scale,
            callback_on_step_end=neg_emb_callback)

        if negative_decoder_prompt == "":
            negative_emb = negative_emb.negative_image_embeds
        else:
            negative_emb = negative_emb.image_embeds

        images = self.decoder(
            image_embeds=img_emb.image_embeds, 
            negative_image_embeds=negative_emb,
            num_inference_steps=decoder_steps,
            height=h,
            width=w,
            guidance_scale=decoder_guidance_scale,
            image=pil_img,
            mask_image=img_mask,
            callback_on_step_end=decoder_callback).images

        return images