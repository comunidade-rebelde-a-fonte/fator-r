"""Limite de tamanho do corpo da requisição, aplicado antes de qualquer rota ou autenticação."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class LimiteCorpoMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        for nome, valor in scope.get("headers", []):
            if nome == b"content-length" and valor.isdigit() and int(valor) > self.max_bytes:
                await self._recusar(send)
                return

        recebidos = 0
        resposta_iniciada = False
        recusado = False

        async def receive_limitado() -> Message:
            nonlocal recebidos, recusado, resposta_iniciada
            if recusado:
                return {"type": "http.disconnect"}
            mensagem = await receive()
            if mensagem["type"] == "http.request":
                recebidos += len(mensagem.get("body", b""))
                if recebidos > self.max_bytes:
                    recusado = True
                    if not resposta_iniciada:
                        resposta_iniciada = True
                        await self._recusar(send)
                    return {"type": "http.disconnect"}
            return mensagem

        async def send_monitorado(mensagem: Message) -> None:
            nonlocal resposta_iniciada
            if recusado:
                return  # a resposta 413 já foi enviada
            if mensagem["type"] == "http.response.start":
                resposta_iniciada = True
            await send(mensagem)

        try:
            await self.app(scope, receive_limitado, send_monitorado)
        except Exception:
            if not recusado:
                raise

    @staticmethod
    async def _recusar(send: Send) -> None:
        corpo = b'{"detail":"Corpo da requisi\\u00e7\\u00e3o acima do limite"}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(corpo)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": corpo})
