import pygame
from pygame.locals import *

import time
import platform
from functools import partial

if platform.system() == 'Linux':
	import evdev
	from evdev import InputDevice, categorize, ecodes

from common.Config import Config
from common.Utilities import Utilities
from common.Button import Button
from common.TouchScreen import TouchScreen
from common.LanguageButton import LanguageButton
from common.Log import Log

CONFIG_FILENAME = 'assets/config/config.json'
LOG_FILE_PATH = 'timeline.log'

DOT_TEXT_COLOR = (252, 175, 138)
DOT_SELECTED_TEXT_COLOR = (0, 65, 40)
TEXT_COLOR = (0, 65, 40)

class Timeline:
	def __init__(self):
		Log.init(LOG_FILE_PATH)
		Log.getLogger().info('START')
		self.touchPos = (0,0)

	def start(self):
		self.buttons = []
		self.blitCursor = True

		self.config = Config(CONFIG_FILENAME)

		pygame.mixer.pre_init(44100, -16, 1, 512)
		pygame.init()
		pygame.mouse.set_visible(False)

		self.loadFonts()

		self.screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN)
		self.cursor = pygame.image.load('assets/images/cursor.png').convert_alpha()

		self.touchScreen = None
		if self.config.isTouch():
			print("Loading touch screen...")
			self.touchScreen = TouchScreen(self.config.getTouchDevicePartialName(), (self.config.getTouchScreenMaxX(), self.config.getTouchScreenMaxY()))

			if not self.touchScreen.setup():
				self.config.setTouch(False)

		self.background = pygame.image.load('assets/images/background.png').convert()

		self.dotImage = pygame.image.load('assets/images/dot-normal.png').convert_alpha()
		self.dotTappedImage = pygame.image.load('assets/images/dot-tapped.png').convert_alpha()
		self.dotSelectedImage = pygame.image.load('assets/images/dot-selected.png').convert_alpha()

		languageButtonImage = pygame.image.load('assets/images/language-button-normal.png').convert()
		languageButtonTappedImage = pygame.image.load('assets/images/language-button-tapped.png').convert()
		languageButtonSelectedImage = pygame.image.load('assets/images/language-button-selected.png').convert()

		self.languageButtons = []
		for i in range(len(self.config.getLanguages())):
			language = self.config.getLanguages()[i]
			languageFont = pygame.font.Font(language['fonts']['textFont']['filename'], language['fonts']['textFont']['size'])

			languageButton = LanguageButton(self.screen, Rect(i * 63 + 15, 1010, languageButtonImage.get_width(), languageButtonImage.get_height()), 
				languageButtonImage, languageButtonTappedImage, languageButtonSelectedImage, language['buttonText'], DOT_TEXT_COLOR, DOT_SELECTED_TEXT_COLOR, DOT_SELECTED_TEXT_COLOR, languageFont, partial(self.languageClicked, i))
			if language['prefix'] == self.config.languagePrefix:
				languageButton.visible = False

			self.languageButtons.append(languageButton)
			self.buttons.append(languageButton)

		self.dots = self.config.getDots()
		self.dotButtons = []

		for i in range(len(self.dots)):
			dot = self.dots[i]
			x = dot['x']
			y = dot['y']
			dotButton = Button(self.screen, Rect(x - self.dotImage.get_width() // 2, y - self.dotImage.get_height() // 2, self.dotImage.get_width(), self.dotImage.get_height()), 
				self.dotImage, self.dotTappedImage, str(i + 1), DOT_TEXT_COLOR, DOT_SELECTED_TEXT_COLOR, self.numbersFont, partial(self.dotClicked, i), 1.5)
			self.dotButtons.append(dotButton)
			self.buttons.append(dotButton)

		self.selectedDotIndex = 0
		self.loadDot()

		Log.getLogger().info('INIT')

		self.loop()

	def loadFonts(self):
		languageData = self.config.getLanguage()
		self.numbersFont = pygame.font.Font(languageData['fonts']['numbersFont']['filename'], languageData['fonts']['numbersFont']['size'])
		self.headerFont = pygame.font.Font(languageData['fonts']['headerFont']['filename'], languageData['fonts']['headerFont']['size'])
		self.textFont = pygame.font.Font(languageData['fonts']['textFont']['filename'], languageData['fonts']['textFont']['size'])
		self.smallTextFont = pygame.font.Font(languageData['fonts']['smallTextFont']['filename'], languageData['fonts']['smallTextFont']['size'])

	def dotClicked(self, index):
		Log.getLogger().info('DOT_CLICKED,' + str(index + 1))
		self.selectedDotIndex = index
		self.loadDot()

	def languageClicked(self, index):
		self.config.changeLanguage(index)
		Log.getLogger().info('LANGUAGE_CHANGED,' + self.config.languagePrefix)
		self.loadFonts()
		self.onLanguageChanged()
		self.loadDot()

	def onLanguageChanged(self):
		languages = self.config.getLanguages()
		for i in range(len(languages)):
			if i == self.config.languageIndex:
				self.languageButtons[i].visible = False
			else:
				self.languageButtons[i].visible = True

	def loadDot(self):
		dot = self.dots[self.selectedDotIndex]
		textFont = self.smallTextFont if dot.get('smallText', False) else self.textFont
		self.currTexts = Utilities.renderTextList(self.config, textFont, dot['textKey'], TEXT_COLOR)
		self.currHeader = self.headerFont.render(self.config.getText(dot['headerKey']), True, TEXT_COLOR)

		for i in range(len(self.dotButtons)):
			if i == self.selectedDotIndex:
				self.dotButtons[i].image = self.dotSelectedImage
				self.dotButtons[i].color = DOT_SELECTED_TEXT_COLOR
				self.dotButtons[i].createText(self.dotButtons[i].text, self.dotButtons[i].font)
			else:
				self.dotButtons[i].image = self.dotImage
				self.dotButtons[i].color = DOT_TEXT_COLOR
				self.dotButtons[i].createText(self.dotButtons[i].text, self.dotButtons[i].font)

	def onMouseDown(self, pos):
		for button in self.buttons:
			button.onMouseDown(pos)

	def onMouseUp(self, pos):
		for button in self.buttons:
			button.onMouseUp(pos)

	def onMouseMove(self, pos):
		pass

	def draw(self, dt):
		self.screen.blit(self.background, (0, 0))

		if self.config.isRtl():
			self.screen.blit(self.currHeader, (1788 - self.currHeader.get_width(), 895))
			Utilities.drawTextsOnRightX(self.screen, self.currTexts, (1788, 951), 40)
			dotX = 1857
		else:
			self.screen.blit(self.currHeader, (320, 895))
			Utilities.drawTextsOnLeftX(self.screen, self.currTexts, (320, 951), 40)
			dotX = 240

		self.screen.blit(self.dotSelectedImage, (dotX - self.dotSelectedImage.get_width() // 2, 911 - self.dotSelectedImage.get_height() // 2))
		selectedNumberTextBox = self.numbersFont.render(str(self.selectedDotIndex + 1), True, TEXT_COLOR)
		self.screen.blit(selectedNumberTextBox, (dotX - selectedNumberTextBox.get_width() // 2, 911 - selectedNumberTextBox.get_height() // 2))

		for button in self.buttons:
			button.draw()

	def loop(self):
		try:
			isGameRunning = True
			clock = pygame.time.Clock()
			lastTime = pygame.time.get_ticks()
			font = pygame.font.Font(None, 30)

			while isGameRunning:
				for event in pygame.event.get():
					if event.type == MOUSEBUTTONDOWN:
						if not self.config.isTouch():
							self.onMouseDown(event.pos)
					elif event.type == MOUSEBUTTONUP:
						if not self.config.isTouch():
							self.onMouseUp(event.pos)
					elif event.type == KEYDOWN:
						if event.key == K_ESCAPE:
							isGameRunning = False

				if self.config.isTouch():
					event = self.touchScreen.readUpDownEvent()
					while event is not None:
						if event['type'] == TouchScreen.DOWN_EVENT:
							self.onMouseDown(event['pos'])
						elif event['type'] == TouchScreen.UP_EVENT:
							self.onMouseUp(event['pos'])
						event = self.touchScreen.readUpDownEvent()

				if not self.config.isTouch():
					self.onMouseMove(pygame.mouse.get_pos())
				else:
					pos = self.touchScreen.getPosition()
					self.onMouseMove(pos)

				self.screen.fill([0,0,0])
				currTime = pygame.time.get_ticks()
				dt = currTime - lastTime
				lastTime = currTime

				self.draw(dt / 1000)

				if not self.config.isTouch() and self.blitCursor:
					self.screen.blit(self.cursor, (pygame.mouse.get_pos()))

				if self.config.showFPS():
					fps = font.render(str(int(clock.get_fps())), True, Color('white'))
					self.screen.blit(fps, (50, 50))

				pygame.display.flip()
				clock.tick(60)

			pygame.quit()
		except Exception as e:
			Log.getLogger().exception('ERROR,Error occured!')
if __name__ == '__main__':
	Timeline().start()
