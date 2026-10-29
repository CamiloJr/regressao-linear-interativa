"""Regressão linear por descida do gradiente, com cálculos inspecionáveis.

Implementa exatamente o exemplo da seção 5.3.5 da apostila:
    y_previsto = w*x + b
    J(w,b) = soma((y_previsto - y)**2) / (2*n)
Os dois gradientes são calculados usando os mesmos parâmetros antigos.
Não há dependências externas; a interface gráfica está em outro módulo.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable


Point = tuple[float, float]
DEFAULT_POINTS: tuple[Point, ...] = ((1.0, 3.0), (2.0, 5.0))
INITIAL_W = 1.0
INITIAL_B = 0.0
MAX_POINT_ABS = 100_000.0
MAX_POINTS = 100


@dataclass(frozen=True)
class PointCalculation:
    x: float
    y: float
    prediction: float
    error: float
    squared_error: float
    error_times_x: float


@dataclass(frozen=True)
class Snapshot:
    epoch: int
    w: float
    b: float
    rows: tuple[PointCalculation, ...]
    squared_error_sum: float
    error_times_x_sum: float
    error_sum: float
    loss: float
    gradient_w: float
    gradient_b: float


@dataclass(frozen=True)
class Update:
    before: Snapshot
    after: Snapshot
    learning_rate: float


def validate_points(points: Iterable[Point]) -> tuple[Point, ...]:
    validated = []
    for x, y in points:
        x, y = float(x), float(y)
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError('Os pontos precisam conter números finitos.')
        if abs(x) > MAX_POINT_ABS or abs(y) > MAX_POINT_ABS:
            raise ValueError(f'Use coordenadas entre -{MAX_POINT_ABS:g} e {MAX_POINT_ABS:g}.')
        validated.append((x, y))
    if len(validated) > MAX_POINTS:
        raise ValueError(f'O limite é de {MAX_POINTS} pontos.')
    return tuple(validated)


def training_problem(points: tuple[Point, ...]) -> str | None:
    """A interface exige duas entradas distintas para visualizar uma reta única."""
    if len(points) < 2:
        return 'Adicione pelo menos dois pontos de observação.'
    if len({x for x, _ in points}) < 2:
        return 'Use ao menos dois valores de x diferentes.'
    return None


def evaluate(points: tuple[Point, ...], w: float, b: float, epoch: int = 0) -> Snapshot:
    if not points:
        raise ValueError('Não há pontos para calcular a perda.')
    if not math.isfinite(w) or not math.isfinite(b):
        raise ArithmeticError('Os parâmetros precisam ser finitos.')
    rows = []
    try:
        for x, y in points:
            predicted = w*x + b
            error = predicted-y
            row = PointCalculation(x, y, predicted, error, error*error, error*x)
            if not all(math.isfinite(v) for v in (row.prediction, row.error, row.squared_error, row.error_times_x)):
                raise ArithmeticError('Os cálculos saíram da faixa numérica.')
            rows.append(row)
        sum_sq = math.fsum(r.squared_error for r in rows)
        sum_ex = math.fsum(r.error_times_x for r in rows)
        sum_e = math.fsum(r.error for r in rows)
        n = len(rows)
        result = Snapshot(epoch, w, b, tuple(rows), sum_sq, sum_ex, sum_e,
                          sum_sq/(2*n), sum_ex/n, sum_e/n)
        if not all(math.isfinite(v) for v in (result.loss, result.gradient_w, result.gradient_b)):
            raise ArithmeticError('Os cálculos saíram da faixa numérica.')
        return result
    except (OverflowError, ValueError) as exc:
        raise ArithmeticError('Os cálculos saíram da faixa numérica.') from exc


class Trainer:
    """Estado de treinamento. A interface controla o relógio e a velocidade."""
    def __init__(self, points: Iterable[Point] = DEFAULT_POINTS,
                 learning_rate: float = 0.1, target_loss: float = 0.0001,
                 max_steps: int = 5000):
        self.points = validate_points(points)
        self.learning_rate = 0.1
        self.target_loss = 0.0001
        self.max_steps = 5000
        self.configure(learning_rate, target_loss, max_steps)
        self.reset()

    def configure(self, learning_rate: float, target_loss: float, max_steps: int) -> None:
        if not math.isfinite(learning_rate) or learning_rate <= 0 or learning_rate > 1_000_000:
            raise ValueError('A taxa de aprendizado deve ser maior que zero e no máximo 1.000.000.')
        if not math.isfinite(target_loss) or target_loss < 0 or target_loss > 1e12:
            raise ValueError('A perda alvo deve estar entre 0 e 1.000.000.000.000.')
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or not 1 <= max_steps <= 100_000:
            raise ValueError('O limite de passos deve ser um inteiro entre 1 e 100.000.')
        self.learning_rate = learning_rate
        self.target_loss = target_loss
        self.max_steps = max_steps

    def set_points(self, points: Iterable[Point]) -> None:
        self.points = validate_points(points)
        self.reset()

    def reset(self) -> None:
        self.w = INITIAL_W
        self.b = INITIAL_B
        self.epoch = 0
        self.last_update: Update | None = None
        self.snapshot: Snapshot | None = evaluate(self.points, self.w, self.b) if self.points else None
        self.history: list[tuple[int, float]] = [(0, self.snapshot.loss)] if self.snapshot else []
        self.initial_loss = self.snapshot.loss if self.snapshot else 0.0

    def stop_reason(self) -> str | None:
        problem = training_problem(self.points)
        if problem:
            return problem
        assert self.snapshot is not None
        if self.snapshot.loss <= self.target_loss:
            return f'Meta atingida: perda J <= {self.target_loss:g}.'
        if self.epoch >= self.max_steps:
            return f'Limite de {self.max_steps} passos atingido.'
        if max(abs(self.snapshot.gradient_w), abs(self.snapshot.gradient_b)) < 1e-10:
            return 'Gradiente muito pequeno: o ajuste estabilizou; verifique a perda obtida.'
        return None

    def step(self) -> Update:
        problem = training_problem(self.points)
        if problem:
            raise ValueError(problem)
        if self.epoch >= self.max_steps:
            raise ValueError('O limite de passos foi atingido. Aumente-o ou reinicie.')
        assert self.snapshot is not None
        before = self.snapshot
        # Ambos os gradientes pertencem ao mesmo estado anterior: atualização simultânea.
        next_w = before.w - self.learning_rate*before.gradient_w
        next_b = before.b - self.learning_rate*before.gradient_b
        if not math.isfinite(next_w) or not math.isfinite(next_b):
            raise ArithmeticError('Divergência numérica. Reduza a taxa de aprendizado.')
        if next_w == before.w and next_b == before.b:
            raise ArithmeticError('A atualização é pequena demais para a precisão numérica.')
        try:
            after = evaluate(self.points, next_w, next_b, self.epoch+1)
        except ArithmeticError as exc:
            raise ArithmeticError('Divergência numérica. Reduza a taxa de aprendizado.') from exc
        if after.loss > max(1e12, self.initial_loss * 1e8):
            raise ArithmeticError('A perda cresceu excessivamente. Reduza a taxa de aprendizado.')
        update = Update(before, after, self.learning_rate)
        self.w, self.b, self.epoch = next_w, next_b, self.epoch+1
        self.snapshot, self.last_update = after, update
        self.history.append((self.epoch, after.loss))
        return update
