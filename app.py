from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


APP_PATH = Path(__file__).parent / "app" / "gradio_app.py"
spec = spec_from_file_location("routercore_gradio_app", APP_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load Gradio app from {APP_PATH}")

module = module_from_spec(spec)
spec.loader.exec_module(module)
demo = module.build_demo()


if __name__ == "__main__":
    demo.launch()
