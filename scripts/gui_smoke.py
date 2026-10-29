"""Real Tk window/calculation smoke check; no Windows or engineering acceptance."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lv_assist.gui import LVAssistApp, build_demo_project


def main():
    app = LVAssistApp()
    try:
        app.update()
        app.current_project, app.current_feeders = build_demo_project()
        app.action_recalculate()
        app.update()
        outputs, summary, checks = app.last_results
        assert len(outputs) == 4 and checks
        assert summary.run_metadata is not None
        assert app._results_are_current()
        print(f'GUI rendered and recalculated: {len(outputs)} feeders; {len(checks)} validation results')
    finally:
        app.destroy()


if __name__ == '__main__':
    main()
