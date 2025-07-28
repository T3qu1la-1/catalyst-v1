from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import os
import math
import hashlib

class RelatorioPremium:
    def __init__(self, nome, id_user, time, url_search, quantidade):
        self.largura = 1600
        self.altura = 800
        self.fundo_escuro = (8, 18, 45)
        self.cor_texto = (245, 245, 255)
        self.cor_secundaria = (60, 95, 180)
        self.cor_destaque = (80, 190, 240)
        self.cor_icones = (120, 220, 255)
        self.margem = 70
        self.espacamento = 90
        self.nome = nome
        self.id_user = id_user
        self.time = time
        self.url_search = url_search
        self.quantidade = quantidade
        self.imagem = Image.new("RGB", (self.largura, self.altura), self.fundo_escuro)
        self.draw = ImageDraw.Draw(self.imagem)
        self.carregar_fontes()
        self.criar_icones()

    def gerar_hash(self):
     texto = f"{self.nome}{self.id_user}"
     return hashlib.md5(texto.encode()).hexdigest()[:8]

    def carregar_fontes(self):
        try:
            sizes = {'titulo': 38, 'subtitulo': 26, 'destaque': 42, 'normal': 32, 'secundario': 24}
            self.fontes = {name: ImageFont.load_default(size=size) for name, size in sizes.items()}
        except:
            self.fontes = {name: ImageFont.load_default() for name in sizes.keys()}

    def criar_icones(self):
        self.icones = {
            'user': self.criar_icone_redondo("👤", 60, self.cor_icones),
            'id': self.criar_icone_redondo("🆔", 60, (120, 220, 180)),
            'time': self.criar_icone_redondo("🕒", 60, (220, 180, 100)),
            'hash': self.criar_icone_redondo("🔑", 60, (200, 150, 240)),
            'web': self.criar_icone_redondo("🌐", 60, (100, 200, 240)),
            'qtd': self.criar_icone_redondo("🔢", 60, (150, 240, 150))
        }

    def criar_icone_redondo(self, emoji, tamanho, cor):
        img = Image.new("RGBA", (tamanho, tamanho))
        draw = ImageDraw.Draw(img)
        draw.ellipse((0, 0, tamanho, tamanho), fill=(*cor[:3], 30), outline=(*cor[:3], 150), width=3)
        bbox = draw.textbbox((0, 0), emoji, font=self.fontes['destaque'])
        w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw.text(((tamanho-w)//2, (tamanho-h)//2-5), emoji, font=self.fontes['destaque'], fill=(*cor[:3], 200))
        return img

    def criar_degradê(self):
        for x in range(self.largura):
            r = int(8 + 30 * (x/self.largura)**0.5)
            g = int(18 + 40 * (x/self.largura)**0.7)
            b = int(45 + 50 * (x/self.largura))
            self.draw.line([(x, 0), (x, self.altura)], fill=(r, g, b))
        for i in range(0, self.largura, 120):
            self.draw.line([(i, 0), (i, self.altura)], fill=(255, 255, 255, 15), width=1)
        for j in range(0, self.altura, 120):
            self.draw.line([(0, j), (self.largura, j)], fill=(255, 255, 255, 15), width=1)
        self.imagem = self.imagem.filter(ImageFilter.GaussianBlur(1.5))
        self.draw = ImageDraw.Draw(self.imagem)

    def criar_card(self):
        sombra = Image.new("RGBA", self.imagem.size, (0, 0, 0, 0))
        draw_sombra = ImageDraw.Draw(sombra)
        draw_sombra.rounded_rectangle(
            (self.margem+10, self.margem+10, self.largura-self.margem+10, self.altura-self.margem+10),
            radius=40, fill=(0, 0, 0, 80))
        sombra = sombra.filter(ImageFilter.GaussianBlur(15))
        card = Image.new("RGBA", self.imagem.size, (0, 0, 0, 0))
        draw_card = ImageDraw.Draw(card)
        draw_card.rounded_rectangle(
            (self.margem, self.margem, self.largura-self.margem, self.altura-self.margem),
            radius=40, fill=(*self.cor_secundaria[:3], 200), outline=(*self.cor_destaque[:3], 150), width=3)
        self.imagem = Image.alpha_composite(self.imagem.convert("RGBA"), sombra)
        self.imagem = Image.alpha_composite(self.imagem, card)
        self.draw = ImageDraw.Draw(self.imagem)

    def desenhar_logo(self):
        tamanho = 200
        x = self.largura - self.margem - tamanho//2 - 20
        y = self.margem + tamanho//2 + 20
        self.draw.ellipse((x-tamanho//2, y-tamanho//2, x+tamanho//2, y+tamanho//2), outline=(*self.cor_destaque[:3], 80), width=5)
        texto1 = "CATALYST"
        w1, h1 = self.draw.textbbox((0, 0), texto1, font=self.fontes['titulo'])[2:]
        self.draw.text((x-w1//2, y-h1-15), texto1, font=self.fontes['titulo'], fill=self.cor_destaque, stroke_width=2, stroke_fill=self.fundo_escuro)
        texto2 = "SERVER"
        w2, h2 = self.draw.textbbox((0, 0), texto2, font=self.fontes['subtitulo'])[2:]
        self.draw.text((x-w2//2, y+15), texto2, font=self.fontes['subtitulo'], fill=self.cor_texto, stroke_width=1, stroke_fill=self.fundo_escuro)

    def desenhar_conteudo(self):
        titulo = "CONFIRMACAO DE LOGIN"
        w, h = self.draw.textbbox((0, 0), titulo, font=self.fontes['titulo'])[2:]
        self.draw.text(((self.largura - w) // 2, self.margem + 20), titulo, font=self.fontes['titulo'], fi...