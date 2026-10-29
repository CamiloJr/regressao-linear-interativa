"""Regressão linear interativa — material de apoio da Aula 6.

Interface inspirada no projeto fornecido "busca_grade.py": Pygame, paleta
escura, organização em painéis, botões, temporizador e execução por passos.
Os componentes Button, DelaySlider e enable_dpi_awareness foram adaptados
do projeto de exemplo. O modelo matemático está em modelo.py.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
import math
import sys
import time

try:
    import pygame
except ImportError as exc:
    print('Pygame não está instalado. Execute: python -m pip install -r requirements.txt')
    raise SystemExit(1) from exc

from modelo import DEFAULT_POINTS, MAX_POINTS, Trainer, evaluate, training_problem


PREFERRED_W, PREFERRED_H = 1600, 950
MIN_W, MIN_H = 1000, 700
FPS = 120
BG = (10, 10, 10)
PANEL = (18, 18, 20)
PLOT_BG = (12, 13, 16)
GRID = (59, 62, 69)
TEXT = (235, 235, 238)
DIM = (166, 170, 179)
BORDER = (70, 74, 83)
ACCENT = (42, 205, 210)
ORANGE = (245, 151, 61)
YELLOW = (247, 209, 92)
GREEN = (89, 205, 132)
PINK = (204, 154, 244)
ERROR = (255, 123, 117)
BUTTON = (42, 42, 48)
BUTTON_HOVER = (58, 58, 66)
BUTTON_ACTIVE = (40, 92, 105)


def clamp(value, low, high):
    return max(low, min(high, value))


def enable_dpi_awareness():
    """Adaptado do visualizador de busca anexado."""
    if sys.platform != 'win32':
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def number(value: float, precision: int = 5) -> str:
    """Exibição compacta; os cálculos conservam a precisão float completa."""
    if abs(value) < 1e-14:
        value = 0.0
    a = abs(value)
    if a and (a >= 1e7 or a < 1e-5):
        return f'{value:.4g}'
    return f'{value:.{precision}f}'.rstrip('0').rstrip('.') or '0'


def parse_number(text: str, label: str) -> float:
    try:
        value = float(text.strip().replace(',', '.'))
    except ValueError as exc:
        raise ValueError(f'{label}: informe um número válido.') from exc
    if not math.isfinite(value):
        raise ValueError(f'{label}: informe um número finito.')
    return value


def fit_text(font, text: str, width: int) -> str:
    if font.size(text)[0] <= width:
        return text
    while len(text) > 1 and font.size(text + '…')[0] > width:
        text = text[:-1]
    return text + '…'


def text_lines(font, text: str, width: int) -> list[str]:
    """Quebra por palavras para manter as explicações dentro do painel."""
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph:
            lines.append('')
            continue
        current = ''
        for word in paragraph.split(' '):
            trial = (current + ' ' + word).strip()
            if current and font.size(trial)[0] > width:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
    return lines


@dataclass
class Button:
    """Baseado no componente Button do exemplo anexado."""
    rect: pygame.Rect
    label: str
    key: str
    active: bool = False

    def draw(self, screen, font, small_font, mouse):
        hovered = self.rect.collidepoint(mouse)
        color = BUTTON_ACTIVE if self.active else BUTTON_HOVER if hovered else BUTTON
        pygame.draw.rect(screen, color, self.rect, border_radius=6)
        pygame.draw.rect(screen, BORDER, self.rect, width=1, border_radius=6)
        chosen = font if font.size(self.label)[0] <= self.rect.w-12 else small_font
        label = fit_text(chosen, self.label, self.rect.w-10)
        surf = chosen.render(label, True, TEXT)
        screen.blit(surf, surf.get_rect(center=self.rect.center))


@dataclass
class InputField:
    key: str
    text: str
    rect: pygame.Rect
    active: bool = False
    select_all: bool = False

    def draw(self, screen, font):
        pygame.draw.rect(screen, (8, 9, 11), self.rect, border_radius=5)
        pygame.draw.rect(screen, ACCENT if self.active else BORDER, self.rect,
                         width=2 if self.active else 1, border_radius=5)
        visible = self.text or ('_' if self.active else '')
        while font.size(visible)[0] > self.rect.w-10 and len(visible) > 1:
            visible = visible[1:]
        surf = font.render(visible, True, TEXT if self.text else DIM)
        screen.blit(surf, (self.rect.x+6, self.rect.centery-surf.get_height()//2))


class DelaySlider:
    """Adaptado do slider do projeto fornecido; intervalo em segundos."""
    def __init__(self, value: float = .5):
        self.rect = pygame.Rect(0, 0, 1, 10)
        self.value = value
        self.dragging = False

    def set_from_x(self, x: int):
        ratio = clamp((x-self.rect.left)/max(1, self.rect.width), 0.0, 1.0)
        self.value = round(.01 + ratio*(5.0-.01), 2)

    def draw(self, screen):
        pygame.draw.line(screen, GRID, self.rect.midleft, self.rect.midright, width=4)
        ratio = (self.value-.01)/(5.0-.01)
        knob_x = round(self.rect.left + ratio*self.rect.width)
        pygame.draw.line(screen, ACCENT, self.rect.midleft, (knob_x, self.rect.centery), width=4)
        pygame.draw.circle(screen, ACCENT, (knob_x, self.rect.centery), 7)


class RegressionApp:
    def __init__(self, window_size=None):
        enable_dpi_awareness()
        pygame.init()
        pygame.display.set_caption('Regressão Linear Interativa — Aula 6')
        if window_size is None:
            info = pygame.display.Info()
            window_size = (min(PREFERRED_W, max(MIN_W, int(info.current_w*.94))),
                           min(PREFERRED_H, max(MIN_H, int(info.current_h*.90))))
        self.screen = pygame.display.set_mode(window_size, pygame.RESIZABLE | pygame.DOUBLEBUF)
        self.clock = pygame.time.Clock()
        self.trainer = Trainer()
        self.delay = DelaySlider(.5)
        self.fields = {
            'x': InputField('x', '', pygame.Rect(0, 0, 1, 1)),
            'y': InputField('y', '', pygame.Rect(0, 0, 1, 1)),
            'rate': InputField('rate', '0.1', pygame.Rect(0, 0, 1, 1)),
            'target': InputField('target', '0.0001', pygame.Rect(0, 0, 1, 1)),
            'max_steps': InputField('max_steps', '5000', pygame.Rect(0, 0, 1, 1)),
            'delay': InputField('delay', '0.50', pygame.Rect(0, 0, 1, 1)),
        }
        self.buttons: dict[str, Button] = {}
        self.mode = None  # None, slow ou fast
        self.next_step_at = 0.0
        self.click_to_add = False
        self.math_scroll = 0
        self.math_scroll_max = 0
        self.status = 'Exemplo da apostila carregado. Execute um passo para começar.'
        self.status_color = DIM
        self.axis_bounds = None
        self.layout()
        self.recalculate_axes()

    def fonts(self):
        s = self.scale
        self.font = pygame.font.SysFont('segoeui,dejavusans,arial', max(13, round(16*s)))
        self.small = pygame.font.SysFont('segoeui,dejavusans,arial', max(11, round(13*s)))
        self.tiny = pygame.font.SysFont('segoeui,dejavusans,arial', max(10, round(12*s)))
        self.bold = pygame.font.SysFont('segoeui,dejavusans,arial', max(14, round(17*s)), bold=True)
        self.title = pygame.font.SysFont('segoeui,dejavusans,arial', max(21, round(27*s)), bold=True)
        self.mono = pygame.font.SysFont('consolas,dejavusansmono,monospace', max(12, round(14*s)))

    def layout(self):
        W, H = self.screen.get_size()
        self.scale = clamp(min(W/1500, H/900), .76, 1.18)
        self.fonts()
        s = self.scale
        margin, gap = max(10, round(14*s)), max(8, round(12*s))
        header_h, bottom_h = round(65*s), round(230*s)
        top, bottom = header_h, H-margin-bottom_h
        body_h = max(210, bottom-top-gap)
        inner_w = W-2*margin
        left_w = int((inner_w-gap)*.58)
        right_w = inner_w-gap-left_w
        data_h = max(145, int((body_h-gap)*.66))
        self.plot_card = pygame.Rect(margin, top, left_w, data_h)
        self.loss_card = pygame.Rect(margin, top+data_h+gap, left_w, max(100, body_h-data_h-gap))
        self.math_card = pygame.Rect(margin+left_w+gap, top, right_w, body_h)
        self.math_body = pygame.Rect(self.math_card.x+round(13*s), self.math_card.y+round(48*s),
                                     self.math_card.w-round(27*s), self.math_card.h-round(60*s))
        self.plot = pygame.Rect(self.plot_card.x+round(65*s), self.plot_card.y+round(58*s),
                                max(80, self.plot_card.w-round(83*s)),
                                max(70, self.plot_card.h-round(95*s)))
        self.loss_plot = pygame.Rect(self.loss_card.x+round(65*s), self.loss_card.y+round(46*s),
                                     max(80, self.loss_card.w-round(83*s)),
                                     max(50, self.loss_card.h-round(76*s)))
        # Três painéis de operação, como no projeto de referência.
        card_w = (inner_w-2*gap)//3
        self.points_card = pygame.Rect(margin, bottom, card_w, bottom_h)
        self.config_card = pygame.Rect(margin+card_w+gap, bottom, card_w, bottom_h)
        self.run_card = pygame.Rect(margin+2*(card_w+gap), bottom,
                                    inner_w-2*(card_w+gap), bottom_h)
        self.build_controls()

    def build_controls(self):
        s = self.scale
        pad, gap = round(14*s), max(5, round(7*s))
        row_h = max(25, round(31*s))
        self.buttons.clear()

        def add(key, label, x, y, w, h=row_h):
            self.buttons[key] = Button(pygame.Rect(round(x), round(y), max(20, round(w)), round(h)), label, key)

        p = self.points_card
        x0, available = p.x+pad, p.w-2*pad
        y = p.y+round(40*s)
        add_w = min(round(113*s), int(available*.30))
        label_w = round(18*s)
        field_w = max(38, (available-add_w-2*label_w-4*gap)//2)
        self.fields['x'].rect = pygame.Rect(x0+label_w, y, field_w, row_h)
        y_label = self.fields['x'].rect.right+gap
        self.fields['y'].rect = pygame.Rect(y_label+label_w, y, field_w, row_h)
        add('add', 'Adicionar', p.right-pad-add_w, y, add_w)
        self.x_label_pos, self.y_label_pos = (x0, y), (y_label, y)
        y2 = y+round(42*s)
        half = (available-gap)//2
        add('example', 'Exemplo da aula', x0, y2, half)
        add('undo_point', 'Remover último', x0+half+gap, y2, available-half-gap)
        y3 = y2+round(40*s)
        add('clear_points', 'Limpar pontos', x0, y3, half)
        add('plot_add', 'Adicionar no gráfico', x0+half+gap, y3, available-half-gap)

        p = self.config_card
        x0, available = p.x+pad, p.w-2*pad
        y = p.y+round(40*s)
        label_w = min(round(58*s), int(available*.17))
        field_w = max(45, (available-2*label_w-3*gap)//2)
        self.config_labels = {}
        self.config_labels['rate'] = (x0, y, 'Taxa η')
        self.fields['rate'].rect = pygame.Rect(x0+label_w, y, field_w, row_h)
        second = self.fields['rate'].rect.right+gap
        self.config_labels['target'] = (second, y, 'Alvo J')
        self.fields['target'].rect = pygame.Rect(second+label_w, y, field_w, row_h)
        y2 = y+round(42*s)
        self.config_labels['max_steps'] = (x0, y2, 'Limite')
        self.fields['max_steps'].rect = pygame.Rect(x0+label_w, y2, field_w, row_h)
        add('apply', 'Aplicar ajustes', second, y2, available-(second-x0))
        y3 = y2+round(43*s)
        self.config_labels['delay'] = (x0, y3, 'Tempo')
        delay_w = min(round(75*s), int(available*.23))
        self.fields['delay'].rect = pygame.Rect(x0+label_w, y3, delay_w, row_h)
        self.sec_label_pos = (self.fields['delay'].rect.right+gap, y3)
        sx = self.fields['delay'].rect.right+round(26*s)
        self.delay.rect = pygame.Rect(sx, y3+row_h//2-6, max(25, p.right-pad-sx-8), 12)

        p = self.run_card
        x0, available = p.x+pad, p.w-2*pad
        y = p.y+round(40*s)
        half = (available-gap)//2
        add('step', 'Passo a passo', x0, y, half)
        add('slow', 'Executar devagar', x0+half+gap, y, available-half-gap)
        y2 = y+round(42*s)
        add('fast', 'Executar rápido', x0, y2, half)
        add('pause', 'Pausar', x0+half+gap, y2, available-half-gap)
        y3 = y2+round(40*s)
        add('reset', 'Reiniciar treinamento', x0, y3, available)

    def recalculate_axes(self):
        points = self.trainer.points
        if not points:
            self.axis_bounds = (-1.0, 3.0, -1.0, 6.0)
            return
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        dx = max(max(xs)-min(xs), 1.0)
        xmin, xmax = min(xs)-.24*dx, max(xs)+.24*dx
        # Inclui a reta inicial, para que ela seja visível desde o primeiro passo.
        ys.extend([xmin, xmax])  # w inicial = 1, b inicial = 0
        dy = max(max(ys)-min(ys), 1.0)
        self.axis_bounds = (xmin, xmax, min(ys)-.14*dy, max(ys)+.14*dy)

    def set_status(self, message, color=DIM):
        self.status, self.status_color = message, color

    def clear_focus(self):
        for field in self.fields.values():
            field.active = False
            field.select_all = False

    def settings(self, announce=False):
        try:
            rate = parse_number(self.fields['rate'].text, 'Taxa de aprendizado')
            target = parse_number(self.fields['target'].text, 'Perda alvo')
            delay = parse_number(self.fields['delay'].text, 'Tempo por passo')
            raw_steps = self.fields['max_steps'].text.strip()
            if not raw_steps.isdigit():
                raise ValueError('Limite de passos: informe um número inteiro.')
            max_steps = int(raw_steps)
            if not .01 <= delay <= 5.0:
                raise ValueError('Tempo por passo: escolha de 0,01 a 5,00 segundos.')
            self.trainer.configure(rate, target, max_steps)
            self.delay.value = round(delay, 2)
            self.fields['delay'].text = f'{self.delay.value:.2f}'
            if announce:
                self.set_status('Ajustes aplicados. O estado do modelo foi preservado.', GREEN)
            return True
        except (ValueError, OverflowError) as exc:
            self.mode = None
            self.set_status(str(exc), ERROR)
            return False

    def change_points(self, points, message):
        try:
            self.trainer.set_points(points)
            self.mode = None
            self.math_scroll = 0
            self.recalculate_axes()
            self.set_status(message + ' Treinamento reiniciado.', GREEN)
        except ValueError as exc:
            self.set_status(str(exc), ERROR)

    def add_point(self, x=None, y=None):
        try:
            if x is None:
                x = parse_number(self.fields['x'].text, 'Coordenada x')
                y = parse_number(self.fields['y'].text, 'Coordenada y')
            if len(self.trainer.points) >= MAX_POINTS:
                raise ValueError(f'O limite é de {MAX_POINTS} pontos.')
            self.change_points((*self.trainer.points, (x, y)), f'Ponto ({number(x)}, {number(y)}) adicionado.')
        except ValueError as exc:
            self.set_status(str(exc), ERROR)

    def do_step(self):
        reason = self.trainer.stop_reason()
        if reason:
            self.mode = None
            self.set_status(reason, GREEN if reason.startswith('Meta atingida') else YELLOW)
            return
        try:
            update = self.trainer.step()
            self.set_status(f'Passo {update.after.epoch}: perda {number(update.before.loss)} → {number(update.after.loss)}.', GREEN)
            reason = self.trainer.stop_reason()
            if reason:
                self.mode = None
                self.set_status(reason, GREEN if reason.startswith('Meta atingida') else YELLOW)
        except (ArithmeticError, ValueError) as exc:
            self.mode = None
            self.set_status(str(exc), ERROR)

    def action(self, key):
        self.clear_focus()
        if key == 'add':
            self.add_point()
        elif key == 'undo_point':
            if self.trainer.points:
                self.change_points(self.trainer.points[:-1], 'Último ponto removido.')
            else:
                self.set_status('Não há pontos para remover.', YELLOW)
        elif key == 'clear_points':
            self.change_points((), 'Pontos removidos.')
        elif key == 'example':
            self.fields['rate'].text = '0.1'
            self.fields['target'].text = '0.0001'
            self.fields['max_steps'].text = '5000'
            self.fields['delay'].text = '0.50'
            self.settings()
            self.click_to_add = False
            self.change_points(DEFAULT_POINTS, 'Exemplo da apostila restaurado.')
        elif key == 'plot_add':
            self.mode = None
            self.click_to_add = not self.click_to_add
            self.set_status('Clique no gráfico para adicionar pontos.' if self.click_to_add else 'Inclusão pelo gráfico desativada.', ACCENT)
        elif key == 'apply':
            self.settings(announce=True)
        elif key == 'pause':
            self.mode = None
            self.set_status('Execução pausada.', YELLOW)
        elif key == 'reset':
            self.mode = None
            self.trainer.reset()
            self.math_scroll = 0
            self.set_status('Treinamento reiniciado com w=1 e b=0. Pontos preservados.', GREEN)
        elif key in ('step', 'slow', 'fast'):
            if not self.settings():
                return
            reason = self.trainer.stop_reason()
            if reason:
                self.mode = None
                self.set_status(reason, GREEN if reason.startswith('Meta atingida') else YELLOW)
                return
            if key == 'step':
                self.mode = None
                self.do_step()
            else:
                self.mode = 'slow' if key == 'slow' else 'fast'
                self.next_step_at = time.monotonic()+self.delay.value
                self.set_status('Execução devagar iniciada.' if key == 'slow' else 'Execução rápida iniciada.', ACCENT)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.get_surface()
                self.layout()
                continue
            if event.type == pygame.MOUSEWHEEL:
                if self.math_card.collidepoint(pygame.mouse.get_pos()):
                    self.math_scroll = clamp(self.math_scroll-event.y*round(48*self.scale), 0, self.math_scroll_max)
                continue
            if event.type == pygame.MOUSEMOTION and self.delay.dragging:
                self.delay.set_from_x(event.pos[0])
                self.fields['delay'].text = f'{self.delay.value:.2f}'
                self.next_step_at = time.monotonic()+self.delay.value
                continue
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.delay.dragging = False
                continue
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                if event.button in (4, 5) and self.math_card.collidepoint(pos):
                    self.math_scroll = clamp(self.math_scroll+(-1 if event.button == 4 else 1)*round(48*self.scale), 0, self.math_scroll_max)
                    continue
                if event.button != 1:
                    continue
                if self.delay.rect.inflate(10, 20).collidepoint(pos):
                    self.clear_focus()
                    self.delay.dragging = True
                    self.delay.set_from_x(pos[0])
                    self.fields['delay'].text = f'{self.delay.value:.2f}'
                    self.next_step_at = time.monotonic()+self.delay.value
                    continue
                for field in self.fields.values():
                    if field.rect.collidepoint(pos):
                        if self.mode is not None:
                            self.mode = None
                            self.set_status('Execução pausada para edição.', YELLOW)
                        self.clear_focus()
                        field.active = True
                        field.select_all = True
                        break
                else:
                    for button in self.buttons.values():
                        if button.rect.collidepoint(pos):
                            self.action(button.key)
                            break
                    else:
                        self.clear_focus()
                        if self.click_to_add and self.plot.collidepoint(pos):
                            x, y = self.pixel_to_data(pos)
                            self.add_point(round(x, 3), round(y, 3))
                continue
            if event.type == pygame.KEYDOWN:
                active = next((f for f in self.fields.values() if f.active), None)
                if active:
                    if event.key == pygame.K_ESCAPE:
                        self.clear_focus()
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self.clear_focus()
                        if active.key in ('x', 'y'):
                            self.add_point()
                        else:
                            self.settings(announce=True)
                    elif event.key == pygame.K_TAB:
                        keys = list(self.fields)
                        index = keys.index(active.key)
                        self.clear_focus()
                        nxt = self.fields[keys[(index+1) % len(keys)]]
                        nxt.active = nxt.select_all = True
                    elif event.key == pygame.K_BACKSPACE:
                        active.text = '' if active.select_all else active.text[:-1]
                        active.select_all = False
                    elif event.key == pygame.K_a and event.mod & pygame.KMOD_CTRL:
                        active.select_all = True
                    elif event.unicode and event.unicode in '0123456789.,-+eE' and len(active.text) < 22:
                        if active.select_all:
                            active.text = ''
                        active.select_all = False
                        active.text += event.unicode
                    continue
                if event.key == pygame.K_SPACE:
                    self.action('step')
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.action('pause' if self.mode else 'slow')
                elif event.key == pygame.K_r:
                    self.action('reset')
                elif event.key == pygame.K_PAGEDOWN:
                    self.math_scroll = clamp(self.math_scroll+self.math_body.h//2, 0, self.math_scroll_max)
                elif event.key == pygame.K_PAGEUP:
                    self.math_scroll = clamp(self.math_scroll-self.math_body.h//2, 0, self.math_scroll_max)
        return True

    def tick_training(self):
        now = time.monotonic()
        if self.mode == 'slow' and now >= self.next_step_at:
            # Mantém o ritmo médio sem acumular atraso após suspensão da janela.
            if now-self.next_step_at > .25:
                self.next_step_at = now
            self.do_step()
            self.next_step_at += self.delay.value
        elif self.mode == 'fast':
            # Lotes pequenos mantêm a janela responsiva; cada passo é guardado.
            for _ in range(25):
                self.do_step()
                if self.mode != 'fast':
                    break

    def data_to_pixel(self, x, y):
        xmin, xmax, ymin, ymax = self.axis_bounds
        px = self.plot.left+(x-xmin)/(xmax-xmin)*self.plot.width
        py = self.plot.bottom-(y-ymin)/(ymax-ymin)*self.plot.height
        # Evita overflow da API de desenho quando há parâmetros muito grandes.
        return (int(clamp(px, -1e7, 1e7)), int(clamp(py, -1e7, 1e7)))

    def pixel_to_data(self, pos):
        xmin, xmax, ymin, ymax = self.axis_bounds
        x = xmin+(pos[0]-self.plot.left)/self.plot.width*(xmax-xmin)
        y = ymin+(self.plot.bottom-pos[1])/self.plot.height*(ymax-ymin)
        return x, y

    def card(self, rect):
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=max(5, round(9*self.scale)))
        pygame.draw.rect(self.screen, BORDER, rect, width=1, border_radius=max(5, round(9*self.scale)))

    def label(self, text, x, y, color=TEXT, font=None):
        surf = (font or self.font).render(text, True, color)
        self.screen.blit(surf, (round(x), round(y)))
        return surf.get_size()

    def draw_axes(self, rect, xmin, xmax, ymin, ymax):
        pygame.draw.rect(self.screen, PLOT_BG, rect)
        for i in range(6):
            x = rect.left+round(rect.width*i/5)
            y = rect.bottom-round(rect.height*i/5)
            pygame.draw.line(self.screen, GRID, (x, rect.top), (x, rect.bottom), 1)
            pygame.draw.line(self.screen, GRID, (rect.left, y), (rect.right, y), 1)
            xt = self.tiny.render(number(xmin+(xmax-xmin)*i/5, 2), True, DIM)
            yt = self.tiny.render(number(ymin+(ymax-ymin)*i/5, 2), True, DIM)
            self.screen.blit(xt, (x-xt.get_width()//2, rect.bottom+5))
            self.screen.blit(yt, (rect.left-yt.get_width()-6, y-yt.get_height()//2))
        pygame.draw.rect(self.screen, BORDER, rect, width=1)

    def draw_plot(self):
        self.card(self.plot_card)
        s = self.scale
        self.label('Pontos de observação e reta de previsão', self.plot_card.x+14*s, self.plot_card.y+10*s, TEXT, self.bold)
        legend_x = self.plot_card.x+15*s
        legend_y = self.plot_card.y+34*s
        for legend, color in [('● observações', ORANGE), ('━ previsão', ACCENT), ('│ erro', YELLOW)]:
            width, _ = self.label(legend, legend_x, legend_y, color, self.small)
            legend_x += width+18*s
        xmin, xmax, ymin, ymax = self.axis_bounds
        self.draw_axes(self.plot, xmin, xmax, ymin, ymax)
        self.label('x', self.plot.right-14*s, self.plot.bottom-18*s, DIM, self.small)
        self.label('y', self.plot.left+5*s, self.plot.top+4*s, DIM, self.small)
        old_clip = self.screen.get_clip()
        self.screen.set_clip(self.plot)
        w, b = self.trainer.w, self.trainer.b
        a = self.data_to_pixel(xmin, w*xmin+b)
        z = self.data_to_pixel(xmax, w*xmax+b)
        clipped = self.plot.clipline(a, z)
        if clipped:
            pygame.draw.line(self.screen, ACCENT, clipped[0], clipped[1], max(2, round(3*s)))
        for i, (x, y) in enumerate(self.trainer.points, 1):
            point = self.data_to_pixel(x, y)
            prediction = self.data_to_pixel(x, w*x+b)
            residual = self.plot.clipline(point, prediction)
            if residual:
                pygame.draw.line(self.screen, YELLOW, residual[0], residual[1], max(1, round(2*s)))
            if self.plot.collidepoint(point):
                pygame.draw.circle(self.screen, ORANGE, point, max(4, round(6*s)))
                pygame.draw.circle(self.screen, (255, 232, 201), point, max(4, round(6*s)), 1)
                self.label(str(i), point[0]+7*s, point[1]-16*s, ORANGE, self.tiny)
        self.screen.set_clip(old_clip)

    def draw_loss(self):
        self.card(self.loss_card)
        s = self.scale
        self.label('Evolução da perda J', self.loss_card.x+14*s, self.loss_card.y+10*s, TEXT, self.bold)
        history = self.trainer.history
        maximum = max((v for _, v in history), default=1.0)
        ymax = max(maximum*1.08, 1e-12)
        xmax = max(self.trainer.epoch, 1)
        self.draw_axes(self.loss_plot, 0, xmax, 0, ymax)
        self.label('passos', self.loss_plot.right-45*s, self.loss_plot.top+5*s, DIM, self.small)
        self.label('J', self.loss_plot.left+5*s, self.loss_plot.top+4*s, DIM, self.small)
        if len(history) > 1:
            stride = max(1, len(history)//max(2, 2*self.loss_plot.w))
            sampled = history[::stride]
            if sampled[-1] != history[-1]:
                sampled.append(history[-1])
            coords = [(int(self.loss_plot.left+i/xmax*self.loss_plot.width),
                       int(self.loss_plot.bottom-v/ymax*self.loss_plot.height)) for i, v in sampled]
            old_clip = self.screen.get_clip()
            self.screen.set_clip(self.loss_plot)
            pygame.draw.lines(self.screen, PINK, False, coords, max(2, round(2*s)))
            self.screen.set_clip(old_clip)
        elif history:
            initial_y = int(self.loss_plot.bottom-history[0][1]/ymax*self.loss_plot.height)
            pygame.draw.circle(self.screen, PINK, (self.loss_plot.left, initial_y), max(3, round(4*s)))
        if history:
            text = f'J atual = {number(history[-1][1], 7)}'
            surf = self.small.render(text, True, PINK)
            self.screen.blit(surf, (self.loss_card.right-surf.get_width()-15*s, self.loss_card.y+12*s))

    def math_lines(self):
        """Todas as linhas são calculadas a partir da mesma fotografia do estado."""
        t = self.trainer
        s = t.snapshot
        result = []
        def line(text='', color=TEXT, font='mono'):
            result.append((text, color, font))
        if s is None:
            line('Ainda não há pontos para calcular a perda.', YELLOW)
            line('Adicione pelo menos dois pontos com x distintos.', DIM)
            return result
        line(f'PASSO {s.epoch}   |   n = {len(s.rows)}   |   η = {number(t.learning_rate)}', ACCENT, 'bold')
        line(f'w = {number(s.w,7)}     b = {number(s.b,7)}')
        line(f'ŷ = ({number(s.w,7)})·x + ({number(s.b,7)})', GREEN)
        line(f'PERDA ATUAL J = {number(s.loss, 8)}', YELLOW, 'bold')
        if t.last_update:
            u = t.last_update
            line('')
            line('ÚLTIMA ATUALIZAÇÃO (simultânea)', ACCENT, 'bold')
            line(f'w: {number(u.before.w)} − {number(u.learning_rate)}·({number(u.before.gradient_w)}) = {number(u.after.w)}')
            line(f'b: {number(u.before.b)} − {number(u.learning_rate)}·({number(u.before.gradient_b)}) = {number(u.after.b)}')
            line(f'J: {number(u.before.loss,7)} → {number(u.after.loss,7)}')
        line('')
        line('FÓRMULAS DA APOSTILA', ACCENT, 'bold')
        line('ŷᵢ = w·xᵢ + b     eᵢ = ŷᵢ − yᵢ')
        line('J = Σ(eᵢ²)/(2n)')
        line('∂J/∂w = Σ(eᵢ·xᵢ)/n')
        line('∂J/∂b = Σ(eᵢ)/n')
        line('')
        line('CÁLCULO DE CADA PONTO', ACCENT, 'bold')
        for i, r in enumerate(s.rows, 1):
            line(f'P{i}: x={number(r.x)}   y={number(r.y)}', ORANGE)
            line(f'   ŷ = ({number(s.w)})·({number(r.x)}) + ({number(s.b)}) = {number(r.prediction)}')
            line(f'   e = {number(r.prediction)} − ({number(r.y)}) = {number(r.error)}')
            line(f'   e² = {number(r.squared_error)}    e·x = {number(r.error_times_x)}')
        line('')
        line('SOMAS E GRADIENTES', ACCENT, 'bold')
        n = len(s.rows)
        line(f'Σe² = {number(s.squared_error_sum, 7)}    Σ(e·x) = {number(s.error_times_x_sum, 7)}')
        line(f'Σe = {number(s.error_sum, 7)}')
        line(f'J = {number(s.squared_error_sum,7)}/(2·{n}) = {number(s.loss,8)}', YELLOW)
        line(f'∂J/∂w = {number(s.error_times_x_sum,7)}/{n} = {number(s.gradient_w,7)}')
        line(f'∂J/∂b = {number(s.error_sum,7)}/{n} = {number(s.gradient_b,7)}')
        line('')
        line('PRÓXIMO PASSO, SE EXECUTADO', ACCENT, 'bold')
        next_w = s.w-t.learning_rate*s.gradient_w
        next_b = s.b-t.learning_rate*s.gradient_b
        line(f'w novo = {number(s.w)} − {number(t.learning_rate)}·({number(s.gradient_w)}) = {number(next_w)}')
        line(f'b novo = {number(s.b)} − {number(t.learning_rate)}·({number(s.gradient_b)}) = {number(next_b)}')
        line('Os dois gradientes usam w e b anteriores.', DIM, 'small')
        line('Os valores exibidos são arredondados; o cálculo usa a precisão completa.', DIM, 'small')
        return result

    def draw_math(self):
        self.card(self.math_card)
        s = self.scale
        self.label('Cálculos em tempo real', self.math_card.x+14*s, self.math_card.y+10*s, TEXT, self.bold)
        hint = self.small.render('Role o mouse para ver tudo', True, DIM)
        self.screen.blit(hint, (self.math_card.right-hint.get_width()-16*s, self.math_card.y+13*s))
        entries = []
        available = self.math_body.w-round(10*s)
        for txt, color, name in self.math_lines():
            font = self.bold if name == 'bold' else self.small if name == 'small' else self.mono
            for chunk in text_lines(font, txt, available):
                entries.append((chunk, color, font, max(font.get_linesize(), round(16*s))))
        total = sum(x[3] for x in entries)+round(5*s)
        self.math_scroll_max = max(0, total-self.math_body.h)
        self.math_scroll = clamp(self.math_scroll, 0, self.math_scroll_max)
        old_clip = self.screen.get_clip()
        self.screen.set_clip(self.math_body)
        y = self.math_body.y-self.math_scroll
        for txt, color, font, height in entries:
            if y+height >= self.math_body.top and y < self.math_body.bottom:
                self.label(txt, self.math_body.x, y, color, font)
            y += height
        self.screen.set_clip(old_clip)
        if self.math_scroll_max:
            bar = pygame.Rect(self.math_card.right-round(10*s), self.math_body.y, max(3, round(4*s)), self.math_body.h)
            pygame.draw.rect(self.screen, GRID, bar, border_radius=3)
            h = max(round(25*s), int(bar.h*self.math_body.h/max(total, 1)))
            yy = bar.y+int((bar.h-h)*self.math_scroll/self.math_scroll_max)
            pygame.draw.rect(self.screen, ACCENT, (bar.x, yy, bar.w, h), border_radius=3)

    def draw_controls(self):
        s = self.scale
        for p in (self.points_card, self.config_card, self.run_card):
            self.card(p)
        pad = round(14*s)
        self.label('Pontos de observação', self.points_card.x+pad, self.points_card.y+10*s, TEXT, self.bold)
        self.label('Configuração do treinamento', self.config_card.x+pad, self.config_card.y+10*s, TEXT, self.bold)
        self.label('Execução', self.run_card.x+pad, self.run_card.y+10*s, TEXT, self.bold)
        self.label('x', *self.x_label_pos, color=DIM, font=self.small)
        self.label('y', *self.y_label_pos, color=DIM, font=self.small)
        for x, y, label in self.config_labels.values():
            self.label(label, x, y+5*s, DIM, self.small)
        self.label('s', self.sec_label_pos[0], self.sec_label_pos[1]+5*s, DIM, self.small)
        self.delay.draw(self.screen)
        self.label('0,01 s', self.delay.rect.left, self.delay.rect.bottom+6*s, DIM, self.tiny)
        max_surf = self.tiny.render('5,00 s', True, DIM)
        self.screen.blit(max_surf, (self.delay.rect.right-max_surf.get_width(), self.delay.rect.bottom+6*s))
        for f in self.fields.values():
            f.draw(self.screen, self.font)
        self.buttons['plot_add'].active = self.click_to_add
        self.buttons['slow'].active = self.mode == 'slow'
        self.buttons['fast'].active = self.mode == 'fast'
        for button in self.buttons.values():
            button.draw(self.screen, self.small, self.tiny, pygame.mouse.get_pos())
        p = self.points_card
        info = f'{len(self.trainer.points)} ponto(s) • adicione nos campos ou no gráfico.'
        self.label(fit_text(self.small, info, p.w-2*pad), p.x+pad, p.bottom-28*s, DIM, self.small)
        p = self.config_card
        info = 'Enter/Aplicar confirma • aceita ponto ou vírgula.'
        self.label(fit_text(self.small, info, p.w-2*pad), p.x+pad, p.bottom-28*s, DIM, self.small)
        p = self.run_card
        info = 'Espaço: passo   Enter: executar/pausar   R: reiniciar'
        self.label(fit_text(self.small, info, p.w-2*pad), p.x+pad, p.bottom-28*s, DIM, self.small)

    def draw(self):
        self.screen.fill(BG)
        s = self.scale
        self.label('REGRESSÃO LINEAR INTERATIVA', 16*s, 9*s, TEXT, self.title)
        subtitle = 'Aula 6 • Aprendizado de Máquina • Seção 5.3.5'
        self.label(subtitle, 17*s, 40*s, DIM, self.small)
        status_font = self.small
        max_w = max(120, self.screen.get_width()*.46)
        status = fit_text(status_font, self.status, int(max_w))
        surface = status_font.render(status, True, self.status_color)
        self.screen.blit(surface, (self.screen.get_width()-surface.get_width()-17*s, 26*s))
        self.draw_plot()
        self.draw_loss()
        self.draw_math()
        self.draw_controls()
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.tick_training()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == '__main__':
    RegressionApp().run()
