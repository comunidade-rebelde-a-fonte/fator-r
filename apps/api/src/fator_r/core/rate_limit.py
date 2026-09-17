import time
from collections import deque


class LoginRateLimiter:
    """Limite de tentativas de login em memória (um processo; suficiente para a v1 interna).

    - Chave principal por par IP+e-mail: um atacante não tranca a conta de outra pessoa
      a partir de outro IP.
    - Chave por IP com teto maior: freia varredura de e-mails.
    - Consulta não cria chave; entradas vencidas são limpas periodicamente.
    """

    LIMPEZA_A_CADA = 1000

    def __init__(self, attempts: int, window_seconds: int, attempts_por_ip: int = 50) -> None:
        self._attempts = attempts
        self._attempts_por_ip = attempts_por_ip
        self._window = window_seconds
        self._failures: dict[str, deque[float]] = {}
        self._operacoes = 0

    @staticmethod
    def chaves(ip: str, email: str) -> tuple[str, str]:
        return f"par:{ip}|{email.lower()}", f"ip:{ip}"

    def _recentes(self, key: str, now: float) -> int:
        failures = self._failures.get(key)
        if not failures:
            return 0
        while failures and now - failures[0] > self._window:
            failures.popleft()
        return len(failures)

    def is_blocked(self, ip: str, email: str) -> bool:
        now = time.monotonic()
        par, por_ip = self.chaves(ip, email)
        return (
            self._recentes(par, now) >= self._attempts
            or self._recentes(por_ip, now) >= self._attempts_por_ip
        )

    def register_failure(self, ip: str, email: str) -> None:
        now = time.monotonic()
        for key in self.chaves(ip, email):
            self._recentes(key, now)
            self._failures.setdefault(key, deque()).append(now)
        self._operacoes += 1
        if self._operacoes % self.LIMPEZA_A_CADA == 0:
            self._limpar(now)

    def reset(self, ip: str, email: str) -> None:
        self._failures.pop(self.chaves(ip, email)[0], None)

    def _limpar(self, now: float) -> None:
        for key in list(self._failures):
            if self._recentes(key, now) == 0:
                del self._failures[key]

    def clear(self) -> None:
        self._failures.clear()
