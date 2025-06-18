import warnings

# Suppress deprecation warning from pkg_resources triggered inside pygame
warnings.filterwarnings("ignore", category=UserWarning, message="pkg_resources is deprecated*")


import flet as ft
import asyncio
from langchain_ollama import OllamaLLM
from langchain.schema import HumanMessage, AIMessage
import speech_recognition as sr
import edge_tts
import threading
import pygame
import uuid
import os
import random
import time
from datetime import datetime
from speech_recognition import WaitTimeoutError

llm=OllamaLLM(model="llama3:latest")
pygame.mixer.init()

class VoiceBot:
    def __init__(self, page, chat_list, wave_bars, status_text):
        self.page=page
        self.chat=chat_list
        self.wave_bars=wave_bars
        self.recognizer=sr.Recognizer()
        self.running=False
        self.status=status_text
        self.history=[]

    def listen_and_reply(self):
        loop=asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        with sr.Microphone() as source:
            self.recognizer.energy_threshold = 300
            self.recognizer.pause_threshold = 0.5
            # self.recognizer.adjust_for_ambient_noise(source)
            while self.running:
                self.animate_wave(True)
                try:
                    audio=self.recognizer.listen(source)
                    user_text=self.recognizer.recognize_google(audio)
                    self.animate_wave(False)
                    self.add_message("user", user_text)
                    self.history.append(HumanMessage(content=user_text))
                    reply=llm.invoke(self.history)
                    self.add_message("bot", reply)
                    self.history.append(AIMessage(content=reply))
                    loop.run_until_complete(self.speak(reply))
                    time.sleep(1.0)
                except sr.UnknownValueError:
                    self.animate_wave(False)
                    self.add_message("bot", "I didn't catch that. Please try again.")
                except sr.RequestError as e:
                    self.animate_wave(False)
                    self.add_message("bot", f"Speech recognition error: {str(e)}")
                except OSError as e:
                    self.animate_wave(False)
                    self.add_message("bot", f"Mic error: {str(e)}. Please wait a moment.")
                except Exception as e:
                    self.animate_wave(False)
                    self.add_message("bot", f"Unexpected Error: {str(e)}")
                finally:
                    self.animate_wave(False)

    def add_message(self, sender, text):
        is_user=sender=="user"
        now=datetime.now().strftime("%I:%M %p")
        avatar=ft.CircleAvatar(
            content=ft.Icon(
                ft.Icons.PERSON if is_user else ft.Icons.ASSISTANT,color="#DD1E88E5" if is_user else "#DDA04DD9",
size=22,shadows=[ft.BoxShadow(blur_radius=4, offset=ft.Offset(1, 1), color="#551E88E5" if is_user else "#55A04DD9")]),radius=16,
            bgcolor=ft.Colors.BLUE_400 if is_user else ft.Colors.GREY_300,)
        text_color=ft.Colors.WHITE if is_user else ft.Colors.BLACK87
        bg_color=ft.Colors.BLUE_600 if is_user else ft.Colors.GREY_300
        message_text=ft.Text(text, size=16, color=text_color, no_wrap=False)
        
        def copy_message_text(e):
            self.page.set_clipboard(text)
            self.status.value="✅ Message copied!"
            self.page.update()
        copy_btn=ft.IconButton(
            icon="content_copy_rounded",tooltip="Copy",on_click=copy_message_text,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
padding=0,bgcolor=ft.Colors.TRANSPARENT,icon_color=ft.Colors.WHITE70 if is_user else ft.Colors.BLACK45,),
width=24,height=24,)

        bubble=ft.Container(
            content=ft.Column([
                ft.Row([ft.Container(message_text, expand=True)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text(now, size=11, color=ft.Colors.WHITE70 if is_user else ft.Colors.BLACK54, italic=True),copy_btn],
                    alignment=ft.MainAxisAlignment.START if is_user else ft.MainAxisAlignment.END, spacing=8)]),
            bgcolor=bg_color,
            padding=ft.padding.symmetric(vertical=10, horizontal=16),
            border_radius=ft.border_radius.only(top_left=12, top_right=12,bottom_left=12 if is_user else 2,bottom_right=2 if is_user else 12,),
            shadow=ft.BoxShadow(color=ft.Colors.BLACK26, blur_radius=10, offset=ft.Offset(0, 4)),
            expand=True)

        row=ft.Row(
            controls=[bubble, avatar] if is_user else [avatar, bubble],
            alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START,spacing=4,expand=True)
        self.chat.controls.append(row)
        self.page.update()

    def on_resize(self, e):
        max_width=260
        window_width=self.page.window_width

        for row in self.chat.controls:
            bubble=None
            for c in row.controls:
                if isinstance(c, ft.Container):
                    bubble=c
                    break
            if bubble:
                new_width=min(max_width, max(window_width - 100, 100))
                bubble.width=new_widthS
        self.page.update()

    async def speak(self, text):
        try:
            filename=f"response_{uuid.uuid4().hex}.mp3"
            communicate=edge_tts.Communicate(text, "en-US-AriaNeural")
            await communicate.save(filename)
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)
            pygame.mixer.music.unload()
            os.remove(filename)
            pygame.mixer.init()
        except Exception as e:
            self.add_message("bot", "TTS Error: " + str(e))

    def start(self):
        self.running=True
        threading.Thread(target=self.listen_and_reply, daemon=True).start()

    def stop(self):
        self.running=False
        self.animate_wave(False)

    def animate_wave(self, state):
        if state:
            def animate():
                while self.running:
                    for bar in self.wave_bars:
                        bar.height=random.randint(20, 50)
                    self.page.update()
                    time.sleep(0.12)
            threading.Thread(target=animate, daemon=True).start()
        else:
            for bar in self.wave_bars:
                bar.height=20
            self.page.update()

def main(page: ft.Page):
    page.title="Voice Assistant"
    page.bgcolor="#202123"
    page.window_width=400
    page.window_height=700
    page.theme_mode=ft.ThemeMode.DARK
    page.padding=15
    header=ft.Text("AI Voice Chat", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)
    wave_bars=[
        ft.Container(width=6, height=20, bgcolor=ft.Colors.CYAN, border_radius=20)
        for _ in range(5)
    ]
    wave_bar_row=ft.Container(content=ft.Row(wave_bars, alignment=ft.MainAxisAlignment.CENTER, spacing=6),height=60,alignment=ft.alignment.center,)
    chat_column=ft.ListView(spacing=10, expand=True, auto_scroll=True)
    chat_area=ft.Container(chat_column, expand=True, bgcolor="#2b2d31", border_radius=10, padding=10)
    start_button=ft.ElevatedButton("Start", bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE)
    end_button=ft.ElevatedButton("End", bgcolor=ft.Colors.RED, color=ft.Colors.WHITE)
    status_text=ft.Text("", color=ft.Colors.WHITE70, italic=True)
    bot=VoiceBot(page, chat_column, wave_bars, status_text)
    page.on_resize=bot.on_resize
    start_button.on_click=lambda _: bot.start() if not bot.running else None
    end_button.on_click=lambda _: bot.stop()
    layout=ft.Column(
        controls=[ft.Container(header, alignment=ft.alignment.center, padding=10),chat_area,
            ft.Row([start_button, end_button], alignment=ft.MainAxisAlignment.CENTER, spacing=20),wave_bar_row,ft.Container(status_text, padding=5)],
            expand=True,alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    page.add(layout)


ft.app(target=main)
