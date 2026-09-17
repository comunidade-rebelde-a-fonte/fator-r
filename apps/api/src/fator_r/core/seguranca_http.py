"""Headers de segurança e proteção CSRF por Origin (T-703)."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

METODOS_INSEGUROS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class SegurancaHttpMiddleware:
    def __init__(self, app: ASGIApp, origens_permitidas: list[str], hsts: bool) -> None:
        self.app = app
        self.origens = frozenset(o.rstrip("/") for o in origens_permitidas)
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        if scope["method"] in METODOS_INSEGUROS and not self._origem_aceita(headers):
            await self._responder(send, 403, b'{"detail":"Origem n\\u00e3o permitida"}')
            return

        async def send_com_headers(mensagem: Message) -> None:
            if mensagem["type"] == "http.response.start":
                extras = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
                    (b"cross-origin-resource-policy", b"same-site"),
                ]
                if self.hsts:
                    extras.append(
                        (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
                    )
                existentes = {k.lower() for k, _ in mensagem.get("headers", [])}
                mensagem["headers"] = list(mensagem.get("headers", [])) + [
                    (k, v) for k, v in extras if k not in existentes
                ]
            await send(mensagem)

        await self.app(scope, receive, send_com_headers)

    def _origem_aceita(self, headers: dict[str, str]) -> bool:
        """Navegadores enviam Origin/Sec-Fetch-Site; clientes sem navegador não (não há CSRF)."""
        if (
            headers.get("sec-fetch-site") == "cross-site"
            and headers.get("origin", "").rstrip("/") not in self.origens
        ):
            return False
        origem = headers.get("origin")
        return origem is None or origem.rstrip("/") in self.origens

    @staticmethod
    async def _responder(send: Send, status: int, corpo: bytes) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(corpo)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": corpo})
