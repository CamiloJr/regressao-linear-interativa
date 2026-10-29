"""Smoke tests de eventos reais no backend de vídeo virtual do SDL."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import unittest
import pygame
from regressao_interativa import RegressionApp


def click(rect):
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=rect.center))


def type_text(text):
    for char in text:
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=ord(char), unicode=char, mod=0))


class InterfaceTest(unittest.TestCase):
    def setUp(self):
        self.app = RegressionApp((1200, 760))
        pygame.event.clear()

    def tearDown(self):
        pygame.quit()

    def test_um_passo_e_reinicio_via_botoes(self):
        click(self.app.buttons['step'].rect)
        self.app.handle_events()
        self.assertAlmostEqual(self.app.trainer.snapshot.loss, 1.40625)
        self.assertEqual(self.app.trainer.epoch, 1)
        click(self.app.buttons['reset'].rect)
        self.app.handle_events()
        self.assertEqual((self.app.trainer.w, self.app.trainer.b, self.app.trainer.epoch), (1., 0., 0))

    def test_inserir_pontos_por_campos_e_virgula(self):
        click(self.app.buttons['clear_points'].rect)
        self.app.handle_events()
        for field, value in [('x', '1,5'), ('y', '3,5')]:
            click(self.app.fields[field].rect)
            type_text(value)
            self.app.handle_events()
        click(self.app.buttons['add'].rect)
        self.app.handle_events()
        self.assertEqual(self.app.trainer.points, ((1.5, 3.5),))
        self.app.action('step')
        self.assertIn('pelo menos dois', self.app.status)

    def test_tempo_minimo_maximo_e_pausa(self):
        self.app.fields['delay'].text = '0,01'
        self.assertTrue(self.app.settings())
        self.assertEqual(self.app.delay.value, .01)
        self.app.fields['delay'].text = '5'
        self.assertTrue(self.app.settings())
        self.assertEqual(self.app.delay.value, 5.)
        self.app.action('slow')
        self.app.next_step_at = 0
        self.app.tick_training()
        self.assertEqual(self.app.trainer.epoch, 1)
        self.app.action('pause')
        self.app.next_step_at = 0
        self.app.tick_training()
        self.assertEqual(self.app.trainer.epoch, 1)

    def test_adicao_no_grafico_e_rolagem(self):
        self.app.draw()
        self.app.action('plot_add')
        click(self.app.plot)
        self.app.handle_events()
        self.assertEqual(len(self.app.trainer.points), 3)
        self.app.draw()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEDOWN, unicode='', mod=0))
        self.app.handle_events()
        self.assertGreater(self.app.math_scroll, 0)

    def test_taxa_invalida_impede_execucao(self):
        self.app.fields['rate'].text = '-1'
        self.app.action('slow')
        self.assertIsNone(self.app.mode)
        self.assertEqual(self.app.trainer.epoch, 0)
        self.assertIn('maior que zero', self.app.status)

    def test_execucao_rapida_para_na_meta(self):
        self.app.action('fast')
        for _ in range(20):
            if self.app.mode is None:
                break
            self.app.tick_training()
        self.assertIsNone(self.app.mode)
        self.assertEqual(self.app.trainer.epoch, 250)
        self.assertLessEqual(self.app.trainer.snapshot.loss, .0001)
        self.assertIn('Meta atingida', self.app.status)

    def test_arrastar_controle_de_tempo(self):
        rect = self.app.delay.rect
        for position, expected in [((rect.left, rect.centery), .01),
                                   ((rect.right, rect.centery), 5.0)]:
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=position))
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=position))
            self.app.handle_events()
            self.assertEqual(self.app.delay.value, expected)


if __name__ == '__main__':
    unittest.main()
