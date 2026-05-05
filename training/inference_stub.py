from __future__ import annotations

from routercore.router import FakeRouter


class FineTunedRouterStub:
    """Drop-in boundary for a future fine-tuned Hugging Face routing model."""

    def __init__(self) -> None:
        self.fallback_router = FakeRouter()

    def route(self, request_text: str):
        return self.fallback_router.route(request_text)


def main() -> None:
    router = FineTunedRouterStub()
    print(router.route("Create a staging Python web app for the claims team in East US.").model_dump_json(indent=2))


if __name__ == "__main__":
    main()
