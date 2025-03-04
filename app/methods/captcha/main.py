from PIL import Image,ImageDraw,ImageFont,ImageFilter
import random
import string
import os
from io import BytesIO
import time


class CaptachaGenerator:
    def __init__(self):
        self.width = 160
        self.height = 60
        #验证码字符数
        self.char_length = 4
        #字体大小
        self.font_size = 35
        #干扰线条数
        self.n_line = 3
        #干扰带点个数
        self.n_points = 50

    def generate_text(self):
        """
        生成随机字符串
        :return:
        """
        source = string.digits + string.ascii_uppercase
        return ''.join(random.choices(source, k=self.char_length))

    def generate_colors(self):
        """
        生成随机颜色
        :return:
        """
        return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    def generate_captcha(self):
        """生成验证码图片"""
        #创建画布
        image = Image.new('RGB',(self.width,self.height),'white')
        #创建画笔图片""
        draw = ImageDraw.Draw(image)
        #加载字体
        font = ImageFont.truetype('arial.ttf',self.font_size)
        #生成验证码字符
        text = self.generate_text()

        #绘制文字
        for i in range(self.char_length):
            #随机生成字符颜色
            char_color = self.generate_colors()
            #计算每个字符的位置。
            x = 20 + i * (self.width  // self.char_length)
            y = random.randint(5,20) #随机上下位置

            #绘制字符

            draw.text((x,y),text[i],font=font,fill=char_color)
        #绘制干扰线
        for _ in range(self.n_line):
            #随机生成线条颜色
            line_color = self.generate_colors()
            #随机生成线条起点和终点
            start_x = random.randint(0,self.width)
            start_y = random.randint(0,self.height)
            end_x = random.randint(0,self.width)
            end_y = random.randint(0,self.height)
            #绘制线条
            draw.line((start_x,start_y,end_x,end_y),fill=line_color,width=2)
        #绘制干扰点
        for _ in range(self.n_points):
            #随机生成点颜色
            point_color = self.generate_colors()
            #随机生成点位置
            x = random.randint(0,self.width)
            y = random.randint(0,self.height)
            #绘制点
            draw.point((x,y),fill=point_color)
        #添加模糊
        image = image.filter(ImageFilter.BLUR)

        #创建一个字节流
        byte_io = BytesIO()
        image.save(byte_io,'png')
        return {
            "image": byte_io.getvalue(),
            "text": text,
            "created_at": time.time()
        }