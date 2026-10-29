"""Verificações do exemplo didático, derivadas e situações de borda."""
import math
import unittest
from modelo import DEFAULT_POINTS, Trainer, evaluate, training_problem


class ModeloTest(unittest.TestCase):
    def test_estado_inicial_do_livro(self):
        s = evaluate(DEFAULT_POINTS, 1.0, 0.0)
        self.assertEqual([r.prediction for r in s.rows], [1.0, 2.0])
        self.assertEqual([r.error for r in s.rows], [-2.0, -3.0])
        self.assertEqual(s.loss, 3.25)
        self.assertEqual(s.gradient_w, -4.0)
        self.assertEqual(s.gradient_b, -2.5)

    def test_atualizacao_simultanea_do_livro(self):
        t = Trainer()
        u = t.step()
        self.assertEqual(u.before.w, 1.0)
        self.assertEqual(u.before.b, 0.0)
        self.assertAlmostEqual(u.after.w, 1.4)
        self.assertAlmostEqual(u.after.b, .25)
        self.assertAlmostEqual(u.after.rows[0].prediction, 1.65)
        self.assertAlmostEqual(u.after.rows[1].prediction, 3.05)
        self.assertAlmostEqual(u.after.loss, 1.40625)
        self.assertEqual(len(t.history), 2)

    def test_gradientes_por_diferencas_finitas(self):
        points = ((-1., 2.), (0., -1.), (2., 3.5), (5., 4.))
        w, b, h = .71, -.34, 1e-6
        s = evaluate(points, w, b)
        dw = (evaluate(points, w+h, b).loss - evaluate(points, w-h, b).loss)/(2*h)
        db = (evaluate(points, w, b+h).loss - evaluate(points, w, b-h).loss)/(2*h)
        self.assertAlmostEqual(s.gradient_w, dw, places=6)
        self.assertAlmostEqual(s.gradient_b, db, places=6)

    def test_convergencia_para_exemplo_da_aula(self):
        t = Trainer()
        while t.stop_reason() is None:
            t.step()
        self.assertLessEqual(t.snapshot.loss, .0001)
        self.assertEqual(t.epoch, 250)
        self.assertTrue(t.stop_reason().startswith('Meta atingida'))

    def test_pontos_com_ruido_podem_ter_perda_minima_positiva(self):
        t = Trainer(((0., 0.), (1., 1.), (2., 0.)), target_loss=0, max_steps=5000)
        while t.stop_reason() is None:
            t.step()
        self.assertGreater(t.snapshot.loss, .1)
        self.assertIn('Gradiente muito pequeno', t.stop_reason())

    def test_restricoes_e_reinicio_apos_edicao(self):
        t = Trainer()
        t.step()
        t.set_points(((0., 1.), (1., 3.)))
        self.assertEqual((t.w, t.b, t.epoch), (1., 0., 0))
        self.assertEqual(len(t.history), 1)
        self.assertIsNotNone(training_problem(((1., 2.),)))
        self.assertIsNotNone(training_problem(((1., 2.), (1., 4.))))
        self.assertIsNone(training_problem(((1., 2.), (2., 2.))))
        for points in [((math.inf, 1.),), ((100001., 1.),)]:
            with self.assertRaises(ValueError):
                t.set_points(points)

    def test_divergencia_nao_salva_estado_invalido(self):
        t = Trainer(learning_rate=1e6)
        first = (t.w, t.b, t.epoch, t.snapshot.loss)
        with self.assertRaises(ArithmeticError):
            t.step()
        self.assertEqual(first, (t.w, t.b, t.epoch, t.snapshot.loss))

    def test_configuracao_atomica(self):
        t = Trainer()
        with self.assertRaises(ValueError):
            t.configure(-1, .3, 500)
        self.assertEqual((t.learning_rate, t.target_loss, t.max_steps), (.1, .0001, 5000))


if __name__ == '__main__':
    unittest.main()
